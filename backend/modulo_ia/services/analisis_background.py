# modulo_ia/services/analisis_background.py
"""
Ejecuta el análisis IA de un caso en un hilo aparte (mismo patrón sin
Celery que ya usa modulo_catalogo/services/background_tasks.py para la
carga de PDF de normas), pero con una diferencia clave: el estado no vive
en el cache, vive directamente en el propio Caso (estado_analisis,
analisis_paso, analisis_error, analisis_completado_en). Eso significa que:

  - Sobrevive a un refresh de página (el cache podía expirar o vivir en
    otro worker si se escala a Gunicorn con varios procesos).
  - Un doble clic en "Analizar" no dispara dos corridas en paralelo: la
    vista bloquea con Caso.objects.select_for_update() antes de marcar
    "procesando" (ver iniciar_analisis más abajo).
  - Queda una base natural para, más adelante, crear una Notificacion
    cuando el análisis termina (completado o con error): ver el comentario
    en _ejecutar_en_hilo.
"""
import logging
import threading

logger = logging.getLogger(__name__)


def iniciar_analisis(caso, usuario):
    """
    Marca el caso como "procesando" (dentro de una transacción con lock,
    para que dos requests casi simultáneos no pasen los dos la validación)
    y lanza el pipeline real en un hilo aparte. Devuelve (ok, detalle):
      - (True, None) si arrancó.
      - (False, "mensaje") si ya había un análisis en curso — el caso no
        se toca.
    """
    from django.db import transaction
    from django.utils import timezone
    from modulo_casos.models.caso import Caso, EstadoAnalisis

    with transaction.atomic():
        caso_lock = Caso.objects.select_for_update().get(pk=caso.pk)
        if caso_lock.analisis_en_curso():
            return False, "Ya hay un análisis en curso para este caso."

        caso_lock.estado_analisis = EstadoAnalisis.PROCESANDO
        caso_lock.analisis_paso = "en_cola"
        caso_lock.analisis_iniciado_en = timezone.now()
        caso_lock.analisis_iniciado_por = usuario if getattr(usuario, "pk", None) else None
        caso_lock.analisis_completado_en = None
        caso_lock.analisis_error = None
        caso_lock.save(update_fields=[
            "estado_analisis", "analisis_paso", "analisis_iniciado_en",
            "analisis_iniciado_por", "analisis_completado_en", "analisis_error",
        ])

    usuario_id = getattr(usuario, "pk", None)
    hilo = threading.Thread(target=_ejecutar_en_hilo, args=(caso.pk, usuario_id), daemon=True)
    hilo.start()
    return True, None


def _ejecutar_en_hilo(caso_id: int, usuario_id):
    from django.db import close_old_connections
    from modulo_casos.models.caso import Caso, EstadoAnalisis
    from modulo_ia.tasks.analisis_task import ejecutar_analisis_caso
    from modulo_notificaciones.services.notificacion_service import (
        notificar_analisis_completado, notificar_analisis_error,
    )
    from modulo_usuarios.models.usuario import Usuario

    try:
        usuario = Usuario.objects.filter(pk=usuario_id).first() if usuario_id else None
        ejecutar_analisis_caso(caso_id, usuario)
    except Exception:
        # ejecutar_analisis_caso ya deja al Caso en estado ERROR por
        # cualquier falla del pipeline; esto solo cubre un error
        # verdaderamente inesperado (ej. el propio caso_id no existe).
        logger.exception("Fallo inesperado lanzando el análisis del caso %s", caso_id)
    finally:
        # El estado final (completado o error) ya quedó persistido en el
        # propio Caso por ejecutar_analisis_caso (o por el except de
        # arriba, si el caso sigue existiendo). Se lee de nuevo acá en
        # vez de confiar en una variable local porque es la única fuente
        # de verdad, igual que el resto de este módulo.
        caso = Caso.objects.filter(pk=caso_id).select_related("usuario").first()
        if caso is not None:
            if caso.estado_analisis == EstadoAnalisis.COMPLETADO:
                notificar_analisis_completado(caso)
            elif caso.estado_analisis == EstadoAnalisis.ERROR:
                notificar_analisis_error(caso)
        # Cada hilo abre su propia conexión a la BD; sin esto quedan
        # conexiones colgadas acumulándose con cada análisis.
        close_old_connections()
