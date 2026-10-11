from django.conf import settings
from django.db import connection, transaction

from modulo_ia.models.jurisprudencia import (
    ResolucionJurisprudencia, FragmentoJurisprudencia, EmbeddingJurisprudencia, ResultadoJurisprudencia,
)
from modulo_ia.services.model_loader import version_activa
from .jurisprudencia_relevancia import contexto_busqueda, consulta_lexica, evaluar_fragmento, fragmento_sustantivo


class JurisprudenciaService:
    @staticmethod
    def recuperar(caso):
        """Consulta sin escrituras, útil también para evaluar umbrales."""
        version = version_activa()
        texto = ' '.join(caso.chunks.order_by('orden', 'id').values_list('contenido', flat=True))
        grupos, figuras = contexto_busqueda(texto)
        fuerte = settings.JURISPRUDENCIA_UMBRAL
        menor = min(fuerte, settings.JURISPRUDENCIA_UMBRAL_RECOMENDACION)
        candidatos = {}
        from .valoracion_jurisprudencia_service import excluidas
        excluidas_ids = excluidas(caso)
        with transaction.atomic(), connection.cursor() as cursor:
            # Ajustes locales: no contaminan la conexión de otras peticiones.
            cursor.execute("SET LOCAL ivfflat.probes = 30")
            cursor.execute("SET LOCAL ivfflat.iterative_scan = relaxed_order")
            for consulta in ['', consulta_lexica(grupos, figuras)] if grupos or figuras else ['']:
                # La vía semántica usa el índice vectorial. La vía léxica usa
                # GIN y ordena exactamente SOLO los fragmentos con términos.
                if consulta:
                    sql = """
                        WITH lexicos AS MATERIALIZED (
                            SELECT r.id AS rid, f.id AS fid, f.contenido, r.huella, ej.vector
                            FROM jurisprudencia_fragmentos f
                            JOIN jurisprudencia_embeddings ej ON ej.fragmento_id = f.id
                            JOIN jurisprudencia_resoluciones r ON r.id = f.resolucion_id
                            WHERE f.busqueda @@ to_tsquery('spanish', %s)
                              AND ej.modelo_version = %s AND r.activa
                              AND NOT (r.id = ANY(%s))
                        )
                        SELECT candidato.* FROM embeddings_chunk ec
                        JOIN chunks_caso cc ON cc.id = ec.chunk_id
                        CROSS JOIN LATERAL (
                            SELECT l.rid, l.fid, l.contenido, l.huella,
                                   1 - (l.vector <=> ec.vector) AS score
                            FROM lexicos l ORDER BY l.vector <=> ec.vector, l.fid LIMIT 100
                        ) candidato
                        WHERE cc.caso_id = %s AND ec.modelo_version = %s
                    """
                    parametros = [consulta, version, excluidas_ids, caso.pk, version]
                else:
                    sql = """
                        SELECT candidato.* FROM embeddings_chunk ec
                        JOIN chunks_caso cc ON cc.id = ec.chunk_id
                        CROSS JOIN LATERAL (
                            SELECT r.id, f.id, f.contenido, r.huella,
                                   1 - (ej.vector <=> ec.vector) AS score
                            FROM jurisprudencia_embeddings ej
                            JOIN jurisprudencia_fragmentos f ON f.id = ej.fragmento_id
                            JOIN jurisprudencia_resoluciones r ON r.id = f.resolucion_id
                            WHERE ej.modelo_version = %s AND r.activa
                              AND NOT (r.id = ANY(%s))
                            ORDER BY ej.vector <=> ec.vector LIMIT 100
                        ) candidato
                        WHERE cc.caso_id = %s AND ec.modelo_version = %s
                    """
                    parametros = [version, excluidas_ids, caso.pk, version]
                cursor.execute(sql, parametros)
                for rid, fid, contenido, huella, score in cursor.fetchall():
                    contenido = fragmento_sustantivo(contenido)
                    evaluacion = evaluar_fragmento(contenido, score, grupos, figuras, fuerte, menor)
                    if evaluacion is None:
                        continue
                    hibrido, sugerencia, coincidencias, motivo = evaluacion
                    item = dict(resolucion_id=rid, fragmento_id=fid, fragmento=contenido,
                                huella_fuente=huella, score_semantico=max(-1., min(1., score)),
                                score_hibrido=hibrido, es_sugerencia=sugerencia,
                                coincidencias=coincidencias, motivo_recomendacion=motivo)
                    anterior = candidatos.get(rid)
                    if anterior is None or (sugerencia, -hibrido, fid) < (
                            anterior['es_sugerencia'], -anterior['score_hibrido'], anterior['fragmento_id']):
                        candidatos[rid] = item
        return sorted(candidatos.values(), key=lambda r: (r['es_sugerencia'], -r['score_hibrido'], r['resolucion_id']))[:settings.JURISPRUDENCIA_TOP_N]

    @staticmethod
    def calcular(caso):
        version = version_activa()
        resultados = []
        rama = caso.rama_detectada.nombre.casefold() if caso.rama_detectada_id else ""
        if rama and "penal" not in rama:
            estado = "fuera_cobertura"
        elif not ResolucionJurisprudencia.objects.filter(activa=True).exists():
            estado = "sin_corpus"
        elif (not EmbeddingJurisprudencia.objects.filter(modelo_version=version, fragmento__resolucion__activa=True).exists()
              or FragmentoJurisprudencia.objects.filter(resolucion__activa=True).exclude(embeddings__modelo_version=version).exists()):
            estado = "sin_embeddings"
        else:
            filas = JurisprudenciaService.recuperar(caso)
            from .valoracion_service import contexto_caso
            contexto = contexto_caso(caso)
            resultados = [ResultadoJurisprudencia(caso=caso, posicion=i, modelo_version=version,
                contexto_evaluado=contexto,
                **{k: valor for k, valor in fila.items() if k != 'fragmento_id'})
                for i, fila in enumerate(filas, 1)]
            estado = "completado" if resultados else "sin_coincidencias"
        ResultadoJurisprudencia.objects.filter(caso=caso).delete()
        ResultadoJurisprudencia.objects.bulk_create(resultados)
        return {"estado": estado, "modelo_version": version, "resultados": resultados}
