from django.conf import settings
from django.db import connection

from modulo_ia.models.jurisprudencia import (
    ResolucionJurisprudencia, FragmentoJurisprudencia, EmbeddingJurisprudencia, ResultadoJurisprudencia,
)
from modulo_ia.services.model_loader import version_activa


class JurisprudenciaService:
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
            # Máximo por resolución: una sentencia larga no ocupa varias posiciones.
            # Se comparan exclusivamente vectores generados con la MISMA versión.
            with connection.cursor() as cursor:
                cursor.execute("""
                    WITH candidatos AS (
                        SELECT candidato.*, ec.chunk_id
                        FROM embeddings_chunk ec
                        JOIN chunks_caso cc ON cc.id = ec.chunk_id
                        CROSS JOIN LATERAL (
                            SELECT r.id AS resolucion_id, f.id AS fragmento_id,
                                   f.contenido, r.huella,
                                   1 - (ej.vector <=> ec.vector) AS score
                            FROM jurisprudencia_embeddings ej
                            JOIN jurisprudencia_fragmentos f ON f.id = ej.fragmento_id
                            JOIN jurisprudencia_resoluciones r ON r.id = f.resolucion_id
                            WHERE ej.modelo_version = %s AND r.activa
                            ORDER BY ej.vector <=> ec.vector, f.id
                            LIMIT 30
                        ) candidato
                        WHERE cc.caso_id = %s AND ec.modelo_version = %s
                    ), mejores AS (
                        SELECT *, row_number() OVER (
                            PARTITION BY resolucion_id ORDER BY score DESC, fragmento_id, chunk_id
                        ) AS orden
                        FROM candidatos WHERE score >= %s
                    )
                    SELECT resolucion_id, contenido, huella, score
                    FROM mejores WHERE orden = 1
                    ORDER BY score DESC, resolucion_id LIMIT %s
                """, [version, caso.pk, version, settings.JURISPRUDENCIA_UMBRAL, settings.JURISPRUDENCIA_TOP_N])
                filas = cursor.fetchall()
            resultados = [ResultadoJurisprudencia(
                caso=caso, resolucion_id=fila[0], fragmento=fila[1], huella_fuente=fila[2],
                score_semantico=max(-1.0, min(1.0, fila[3])), posicion=i,
                modelo_version=version,
            ) for i, fila in enumerate(filas, 1)]
            estado = "completado" if resultados else "sin_coincidencias"
        ResultadoJurisprudencia.objects.filter(caso=caso).delete()
        ResultadoJurisprudencia.objects.bulk_create(resultados)
        return {"estado": estado, "modelo_version": version, "resultados": resultados}
