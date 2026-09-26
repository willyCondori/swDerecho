"""
Pipeline IA completo para un caso:
  1. Chunking: parte el texto del caso en fragmentos.
  2. Embeddings: vectoriza cada fragmento.
  3. Entidades: detecta qué entidades jurídicas del catálogo aparecen en
     el texto del caso.
  4. Ranking: compara contra los embeddings de artículos y arma el top N
     con la fórmula ponderada (ver RankingService).
  5. Análisis IA (GPT4All): resumen, fortalezas, debilidades, estrategias.
     PENDIENTE de integrar — por ahora se guardan en None como placeholder.
  6. Guarda/actualiza el ResultadoCaso asociado.

Antes esto era una @shared_task de Celery, pero Celery nunca llegó a
configurarse (config/celery.py vacío) y las vistas la llamaban directo
como función normal, síncronamente, dentro del propio request HTTP.
Ahora es una función simple: quien la corre en un hilo aparte es
analisis_background.py, y el estado de avance se persiste en el propio
Caso (estado_analisis/analisis_paso) en vez de reportarse por
self.update_state — así sobrevive a un refresh de página o a que el
usuario cierre la pestaña mientras corre.
"""
import logging

from django.db import transaction
from django.utils import timezone

from core.permissions.auditoria_mixin import registrar_auditoria
from modulo_casos.models.caso import Caso, EstadoAnalisis

logger = logging.getLogger(__name__)


def _actualizar_paso(caso_id: int, paso: str) -> None:
    """
    UPDATE directo (no caso.save()) para no arrastrar en memoria cambios
    de otras partes del pipeline ni pisar algo que se haya escrito por
    otro lado mientras tanto; es solo un dato informativo para la UI.
    """
    Caso.objects.filter(pk=caso_id).update(analisis_paso=paso)


def ejecutar_analisis_caso(caso_id: int, usuario=None) -> dict:
    """
    Corre el pipeline completo de forma síncrona y deja el resultado en
    estado_analisis. `usuario` es quien disparó esta corrida (para la
    auditoría); si no se indica, se audita a nombre del dueño del caso.

    Pensada para llamarse desde analisis_background.py (en un hilo aparte)
    o directamente en un test/management command. No lanza la excepción
    hacia afuera en el caso general: dejar a Caso en estado ERROR con el
    mensaje es la señal de fallo. Solo re-lanza si ni siquiera se pudo
    obtener el Caso (caso_id inválido), porque ahí no hay dónde persistir
    el error.
    """
    from modulo_ia.services.chunking_service import ChunkingService
    from modulo_ia.services.embedding_service import EmbeddingService
    from modulo_ia.services.entidad_service import EntidadDetectionService
    from modulo_ia.services.ranking_service import RankingService
    from modulo_casos.models.resultado_caso import ResultadoCaso

    caso = Caso.objects.get(pk=caso_id)
    usuario_auditoria = usuario or caso.usuario

    try:
        # Todo el paso de mutación de datos en una sola transacción: si
        # falla a mitad (ej. el 4to de 5 pasos), no queda el caso con
        # chunks nuevos pero ranking viejo, ni con la mitad del ranking
        # borrado y la otra mitad sin reemplazar.
        with transaction.atomic():
            _actualizar_paso(caso_id, "chunking")
            chunks = ChunkingService.crear_chunks(caso)

            _actualizar_paso(caso_id, "embeddings")
            embeddings = EmbeddingService.generar_para_caso(chunks)

            _actualizar_paso(caso_id, "entidades")
            entidades = EntidadDetectionService.detectar_para_caso(chunks)

            _actualizar_paso(caso_id, "ranking")
            resultados = RankingService.calcular_ranking(caso)

            _actualizar_paso(caso_id, "guardando")
            # PENDIENTE: integrar GPT4All para resumen/fortalezas/
            # debilidades/estrategias. Por ahora el caso ya queda marcado
            # como "analizado" porque existe el ResultadoCaso asociado.
            resultado_caso, _creado = ResultadoCaso.objects.update_or_create(
                caso=caso,
                defaults={
                    "resumen"      : None,
                    "fortalezas"   : None,
                    "debilidades"  : None,
                    "estrategias"  : None,
                    "observaciones": None,
                },
            )

        Caso.objects.filter(pk=caso_id).update(
            estado_analisis=EstadoAnalisis.COMPLETADO,
            analisis_paso="completado",
            analisis_completado_en=timezone.now(),
            analisis_error=None,
        )

        registrar_auditoria(
            usuario=usuario_auditoria,
            tabla="casos",
            accion="ANALYZE",
            registro_id=caso.pk,
            metadata={
                "chunks": len(chunks),
                "embeddings": len(embeddings),
                "entidades_detectadas": len(entidades),
                "articulos_rankeados": len(resultados),
                "resultado_caso_id": resultado_caso.pk,
            },
        )

        return {
            "caso_id": caso_id,
            "chunks": len(chunks),
            "entidades_detectadas": len(entidades),
            "articulos_rankeados": len(resultados),
            "resultado_caso_id": resultado_caso.pk,
        }

    except Exception as e:
        logger.exception("Error analizando el caso %s", caso_id)
        mensaje = str(e)[:2000]
        Caso.objects.filter(pk=caso_id).update(
            estado_analisis=EstadoAnalisis.ERROR,
            analisis_paso=None,
            analisis_error=mensaje,
        )
        registrar_auditoria(
            usuario=usuario_auditoria,
            tabla="casos",
            accion="ANALYZE",
            registro_id=caso_id,
            metadata={"error": mensaje},
        )
        return {"caso_id": caso_id, "error": mensaje}
