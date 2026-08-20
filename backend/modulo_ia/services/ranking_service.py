import heapq
import numpy as np
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from pgvector.django import CosineDistance

from modulo_ia.models.embedding import EmbeddingArticulo, EmbeddingChunk
from modulo_ia.models.embedding import EntidadDetectadaCaso
from modulo_catalogo.models.articulo import Articulo
from modulo_ia.serializers.ia_serializer import ResultadoArticuloWriteSerializer
from modulo_ia.services.clasificador_delito_service import ClasificadorDelitoService
from modulo_ia.services.figura_transversal_service import FiguraTransversalService

TOP_N_ARTICULOS = 15
CANDIDATOS_POR_CHUNK = 50
CUANTIZADOR = Decimal("0.000001")

UMBRAL_MINIMO_SCORE_TOTAL = 0.42
PESO_SEMANTICO   = Decimal("0.60")
PESO_DELITO      = Decimal("0.15")
PESO_ENTIDADES   = Decimal("0.10")
PESO_JERARQUIA   = Decimal("0.10")
PESO_FRECUENCIA  = Decimal("0.05")

# Figuras transversales (tentativa, legítima defensa, complicidad, etc.):
# no compiten por el umbral principal porque casi nunca tienen score_delito
# propio (no son "tipos de delito"). Se incluyen si el caso las menciona
# explícitamente y su score total supera este umbral secundario, más bajo,
# y hasta un máximo para no diluir el ranking con ruido.
UMBRAL_MINIMO_FIGURA_TRANSVERSAL = 0.20
MAX_FIGURAS_TRANSVERSALES_FORZADAS = 3


class RankingService:
    """
    Compara los embeddings de los chunks de un caso contra los
    embeddings de los artículos usando pgvector + índice HNSW, combina
    el resultado con los otros 4 sub-scores según la fórmula ponderada
    de ResultadoArticulo, y usa una cola de prioridad (heap) de tamaño
    fijo para quedarse con los TOP_N_ARTICULOS sin ordenar todo el
    universo de candidatos.

    Además, detecta figuras jurídicas transversales (tentativa, legítima
    defensa, complicidad, atenuantes...) mencionadas en el relato del
    caso y las incluye aunque no superen el umbral principal, porque su
    relevancia se determina por regla explícita, no por similitud pura.
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
    def _vectores_chunks_caso(caso) -> list:
        return list(
            EmbeddingChunk.objects
            .filter(chunk__caso=caso)
            .values_list("vector", flat=True)
        )

    @staticmethod
    def _score_semantico_articulo_especifico(articulo_id, vectores_chunks_caso) -> float:
        """
        Calcula la similitud semántica de UN artículo puntual contra los
        chunks del caso, sin pasar por el CosineDistance/top-50 de
        pgvector. Se usa para artículos "forzados" por regla (figuras
        transversales) que pueden no aparecer entre los vecinos más
        cercanos de ningún chunk, pero igual son relevantes.
        """
        emb_articulo = EmbeddingArticulo.objects.filter(articulo_id=articulo_id).first()
        if emb_articulo is None or not vectores_chunks_caso:
            return 0.0
        vector_articulo = np.array(emb_articulo.vector)
        mejor = 0.0
        for vector_chunk in vectores_chunks_caso:
            similitud = float(np.dot(vector_articulo, np.array(vector_chunk)))
            if similitud > mejor:
                mejor = similitud
        return mejor

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
    def _armar_candidato(cls, articulo, score_semantico, score_delito, entidades_del_caso, max_frecuencia):
        """
        Construye la tupla de candidato (score_float, articulo_id,
        score_total_decimal, sub_scores) para un artículo dado, con la
        misma fórmula ponderada usada para todos los candidatos.
        Extraído a un método propio para reutilizarlo tanto en el flujo
        semántico normal como en el de figuras transversales forzadas.
        """
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
        return (float(score_total), articulo.id, score_total, sub_scores)

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
            candidatos.append(
                cls._armar_candidato(articulo, score_semantico, score_delito, entidades_del_caso, max_frecuencia)
            )

        # Filtrar por umbral mínimo DESPUÉS de construir todos los candidatos,
        # para no forzar TOP_N_ARTICULOS completos cuando no hay suficientes
        # artículos realmente relevantes (evita relleno tipo "Fijación de la
        # pena", "Caja de Reparaciones", etc. solo para completar la lista).
        candidatos = [c for c in candidatos if c[0] >= UMBRAL_MINIMO_SCORE_TOTAL]
        # Importante: se calcula DESPUÉS del filtro por umbral. Un artículo
        # puede haber aparecido en scores_semanticos (top-50 de algún chunk)
        # y aun así haber sido descartado por no llegar al umbral principal;
        # ese caso NO cuenta como "ya considerado" para las figuras
        # transversales, que precisamente existen para rescatar artículos
        # relevantes que el filtro normal descarta.
        ids_ya_incluidos = {c[1] for c in candidatos}

        # --- Figuras jurídicas transversales (tentativa, legítima defensa,
        # complicidad, atenuantes...): no compiten por score_delito porque
        # no son "tipos de delito", así que casi nunca superan el umbral
        # principal aunque el caso las mencione explícitamente. Se agregan
        # aparte, con un umbral más bajo y un tope, para no perderlas ni
        # tampoco inundar el ranking de ruido.
        figuras_detectadas = FiguraTransversalService.detectar_figuras(texto_caso_completo, nombre_rama)
        if figuras_detectadas:
            articulos_figura = FiguraTransversalService.articulos_por_figuras(
                figuras_detectadas,
                rama_id=caso.rama_detectada_id,
                nombre_rama=nombre_rama,
            )
            vectores_chunks_caso = cls._vectores_chunks_caso(caso)

            candidatos_figura = []
            for articulo in articulos_figura:
                if articulo.id in ids_ya_incluidos:
                    continue  # ya va a persistirse por el flujo normal, no duplicar
                score_semantico = cls._score_semantico_articulo_especifico(
                    articulo.id, vectores_chunks_caso
                )
                # score_delito se mantiene en 0 a propósito: estas figuras no
                # son un "tipo de delito", su relevancia ya viene de la regla
                # que las detectó, no de coincidir con una categoría penal.
                candidato = cls._armar_candidato(
                    articulo, score_semantico, 0.0, entidades_del_caso, max_frecuencia
                )
                if candidato[0] >= UMBRAL_MINIMO_FIGURA_TRANSVERSAL:
                    candidatos_figura.append(candidato)

            candidatos_figura.sort(key=lambda c: c[0], reverse=True)
            candidatos.extend(candidatos_figura[:MAX_FIGURAS_TRANSVERSALES_FORZADAS])

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