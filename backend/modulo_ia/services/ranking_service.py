import heapq
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from pgvector.django import CosineDistance

from modulo_ia.models.embedding import EmbeddingArticulo, EmbeddingChunk
from modulo_ia.models.embedding import EntidadDetectadaCaso
from modulo_catalogo.models.articulo import Articulo
from modulo_ia.serializers.ia_serializer import ResultadoArticuloWriteSerializer
from modulo_ia.services.clasificador_delito_service import ClasificadorDelitoService

TOP_N_ARTICULOS = 15
CANDIDATOS_POR_CHUNK = 50
CUANTIZADOR = Decimal("0.000001")

UMBRAL_MINIMO_SCORE_TOTAL = 0.42
PESO_SEMANTICO   = Decimal("0.60")
PESO_DELITO      = Decimal("0.15")
PESO_ENTIDADES   = Decimal("0.10")
PESO_JERARQUIA   = Decimal("0.10")
PESO_FRECUENCIA  = Decimal("0.05")


class RankingService:
    """
    Compara los embeddings de los chunks de un caso contra los
    embeddings de los artículos usando pgvector + índice HNSW, combina
    el resultado con los otros 4 sub-scores según la fórmula ponderada
    de ResultadoArticulo, y usa una cola de prioridad (heap) de tamaño
    fijo para quedarse con los TOP_N_ARTICULOS sin ordenar todo el
    universo de candidatos.
    """

    @staticmethod
    def _score_semantico_por_articulo(caso):
        scores = defaultdict(float)

        embeddings_chunk = (
            EmbeddingChunk.objects
            .filter(chunk__caso=caso)
            .select_related("chunk")
        )
        if not embeddings_chunk.exists():
            raise ValueError("El caso no tiene chunks con embeddings para comparar.")

        candidatos_qs = EmbeddingArticulo.objects.filter(articulo__estado=True)

        if caso.rama_detectada_id:
            candidatos_qs = candidatos_qs.filter(articulo__rama_id=caso.rama_detectada_id)

        for emb_chunk in embeddings_chunk:
            candidatos = (
                candidatos_qs
                .annotate(distancia=CosineDistance("vector", emb_chunk.vector))
                .order_by("distancia")[:CANDIDATOS_POR_CHUNK]
            )
            for candidato in candidatos:
                similitud = 1 - candidato.distancia
                articulo_id = candidato.articulo_id
                if similitud > scores[articulo_id]:
                    scores[articulo_id] = similitud

        return scores

    @staticmethod
    def _entidades_detectadas_del_caso(caso) -> set:
        valores = (
            EntidadDetectadaCaso.objects
            .filter(chunk__caso=caso)
            .values_list("valor_detectado", flat=True)
        )
        return {v.strip().lower() for v in valores if v}

    @staticmethod
    def _score_entidades(articulo, entidades_del_caso: set) -> float:
        if not entidades_del_caso:
            return 0.0
        nombres_articulo = {
            nombre.strip().lower()
            for nombre in articulo.entidades.values_list("nombre", flat=True)
        }
        if not nombres_articulo:
            return 0.0
        coincidencias = entidades_del_caso & nombres_articulo
        return round(len(coincidencias) / len(entidades_del_caso), 6)

    @staticmethod
    def _score_jerarquia(articulo) -> float:
        return float(articulo.jerarquia_normativa or 0.0)

    @staticmethod
    def _score_frecuencia(articulo, max_frecuencia: int) -> float:
        if max_frecuencia <= 0:
            return 0.0
        return round((articulo.frecuencia_historica or 0) / max_frecuencia, 6)

    @classmethod
    def calcular_ranking(cls, caso):
        scores_semanticos = cls._score_semantico_por_articulo(caso)
        entidades_del_caso = cls._entidades_detectadas_del_caso(caso)

        texto_caso_completo = " ".join(
            EmbeddingChunk.objects
            .filter(chunk__caso=caso)
            .values_list("chunk__contenido", flat=True)
        )
        nombre_rama = caso.rama_detectada.nombre if caso.rama_detectada_id else None
        categorias_caso = ClasificadorDelitoService.clasificar_texto(texto_caso_completo, nombre_rama)

        articulos = (
            Articulo.objects
            .filter(id__in=scores_semanticos.keys())
            .prefetch_related("entidades")
            .select_related("norma", "rama")
        )
        articulos_por_id = {a.id: a for a in articulos}
        max_frecuencia = max(
            (a.frecuencia_historica or 0 for a in articulos), default=0
        )

        candidatos = []
        for articulo_id, score_semantico in scores_semanticos.items():
            articulo = articulos_por_id.get(articulo_id)
            if articulo is None:
                continue

            score_delito = ClasificadorDelitoService.score_delito_articulo(
                articulo, categorias_caso, nombre_rama
            )

            sub_scores = {
                "score_semantico": Decimal(str(round(score_semantico, 6))),
                "score_delito": Decimal(str(round(score_delito, 6))),
                "score_entidades": Decimal(str(cls._score_entidades(articulo, entidades_del_caso))),
                "score_jerarquia": Decimal(str(cls._score_jerarquia(articulo))),
                "score_frecuencia": Decimal(str(cls._score_frecuencia(articulo, max_frecuencia))),
            }
            score_total = (
                PESO_SEMANTICO  * sub_scores["score_semantico"]
                + PESO_DELITO    * sub_scores["score_delito"]
                + PESO_ENTIDADES * sub_scores["score_entidades"]
                + PESO_JERARQUIA * sub_scores["score_jerarquia"]
                + PESO_FRECUENCIA* sub_scores["score_frecuencia"]
            )
            candidatos.append((float(score_total), articulo_id, score_total, sub_scores))

        # Filtrar por umbral mínimo DESPUÉS de construir todos los candidatos,
        # para no forzar TOP_N_ARTICULOS completos cuando no hay suficientes
        # artículos realmente relevantes (evita relleno tipo "Fijación de la
        # pena", "Caja de Reparaciones", etc. solo para completar la lista).
        candidatos = [c for c in candidatos if c[0] >= UMBRAL_MINIMO_SCORE_TOTAL]

        heap = []
        for score_float, articulo_id, score_total, sub_scores in candidatos:
            item = (score_float, articulo_id, score_total, sub_scores)
            if len(heap) < TOP_N_ARTICULOS:
                heapq.heappush(heap, item)
            elif score_float > heap[0][0]:
                heapq.heapreplace(heap, item)

        top_ordenado = sorted(heap, key=lambda item: item[0], reverse=True)

        from modulo_ia.models.resultado import ResultadoArticulo
        ResultadoArticulo.objects.filter(caso=caso).delete()

        resultados = []
        for posicion, (_, articulo_id, score_total, sub_scores) in enumerate(top_ordenado, start=1):
            data = {
                "caso": caso.pk,
                "articulo": articulo_id,
                "posicion": posicion,
                "score_total": score_total.quantize(CUANTIZADOR, rounding=ROUND_HALF_UP),
                **sub_scores,
            }
            serializer = ResultadoArticuloWriteSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            resultados.append(serializer.save())

        return resultados