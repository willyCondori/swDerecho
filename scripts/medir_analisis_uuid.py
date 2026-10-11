"""Ejecutar con manage.py shell por stdin; todo cambio del pipeline se revierte."""
import json, time
from unittest.mock import patch
from django.conf import settings
from django.db import connection, transaction
from modulo_casos.models import Caso
from modulo_ia.services.jurisprudencia_service import JurisprudenciaService
from modulo_ia.services.jurisprudencia_relevancia import contexto_busqueda, patron_sql, evaluar_fragmento, fragmento_sustantivo
from modulo_ia.services.model_loader import version_activa
from modulo_ia.services.embedding_service import EmbeddingService
from modulo_ia.services.chunking_service import ChunkingService
from modulo_ia.tasks.analisis_task import ejecutar_analisis_caso

def original(caso):
    version=version_activa()
    texto=' '.join(caso.chunks.order_by('orden','id').values_list('contenido',flat=True))
    grupos,figuras=contexto_busqueda(texto)
    fuerte=settings.JURISPRUDENCIA_UMBRAL
    menor=min(fuerte,settings.JURISPRUDENCIA_UMBRAL_RECOMENDACION)
    candidatos={}
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SET LOCAL enable_indexscan = off")
        for patron in ['',patron_sql(grupos,figuras)] if grupos or figuras else ['']:
            cursor.execute("""
                SELECT candidato.* FROM embeddings_chunk ec
                JOIN chunks_caso cc ON cc.id=ec.chunk_id CROSS JOIN LATERAL (
                    SELECT r.id,f.id,f.contenido,r.huella,1-(ej.vector <=> ec.vector) AS score
                    FROM jurisprudencia_embeddings ej
                    JOIN jurisprudencia_fragmentos f ON f.id=ej.fragmento_id
                    JOIN jurisprudencia_resoluciones r ON r.id=f.resolucion_id
                    WHERE ej.modelo_version=%s AND r.activa AND (%s='' OR f.contenido ~* %s)
                    ORDER BY ej.vector <=> ec.vector,f.id LIMIT 100
                ) candidato WHERE cc.caso_id=%s AND ec.modelo_version=%s
            """,[version,patron,patron,caso.pk,version])
            for rid,fid,contenido,huella,score in cursor.fetchall():
                e=evaluar_fragmento(contenido,score,grupos,figuras,fuerte,menor)
                if e is None:continue
                hibrido,sugerencia,coincidencias,motivo=e
                item=dict(resolucion_id=rid,fragmento_id=fid,fragmento=fragmento_sustantivo(contenido),
                    huella_fuente=huella,score_semantico=max(-1.,min(1.,score)),score_hibrido=hibrido,
                    es_sugerencia=sugerencia,coincidencias=coincidencias,motivo_recomendacion=motivo)
                anterior=candidatos.get(rid)
                if anterior is None or (sugerencia,-hibrido,fid)<(anterior['es_sugerencia'],-anterior['score_hibrido'],anterior['fragmento_id']):
                    candidatos[rid]=item
    return sorted(candidatos.values(),key=lambda r:(r['es_sugerencia'],-r['score_hibrido'],r['resolucion_id']))[:settings.JURISPRUDENCIA_TOP_N]

caso=Caso.objects.get(pk=1)
registro={'modelo':version_activa(),'muestras':[],'comparacion_resoluciones':{}}
for nombre,funcion in [('anterior',original),('optimizada',JurisprudenciaService.recuperar)]:
    t=time.perf_counter(); filas=funcion(caso)
    registro['muestras'].append({'operacion':'recuperacion','version':nombre,'segundos':round(time.perf_counter()-t,3)})
    registro['comparacion_resoluciones'][nombre]=[r['resolucion_id'] for r in filas]
# Calentar el modelo para comparar búsquedas con el mismo estado de carga.
t=time.perf_counter(); EmbeddingService.preparar_vectores(ChunkingService.preparar_chunks(caso))
registro['calentamiento_modelo_segundos']=round(time.perf_counter()-t,3)
for nombre,funcion in [('anterior',original),('optimizada',JurisprudenciaService.recuperar),('optimizada',JurisprudenciaService.recuperar)]:
    with transaction.atomic():
        try:
            with patch.object(JurisprudenciaService,'recuperar',staticmethod(funcion)):
                t=time.perf_counter(); resultado=ejecutar_analisis_caso(caso.pk)
                registro['muestras'].append({'operacion':'pipeline','version':nombre,'segundos':round(time.perf_counter()-t,3),'error':resultado.get('error')})
        finally:
            transaction.set_rollback(True)
print('MEDICION_JSON='+json.dumps(registro))
