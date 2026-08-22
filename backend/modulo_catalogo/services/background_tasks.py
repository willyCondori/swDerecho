# modulo_catalogo/services/background_tasks.py
"""
Ejecutor en background SIN Celery, para reemplazar el patrón síncrono
que causaba el bug: "el backend termina bien pero el frontend muestra
error" (el request se cortaba por timeout del lado del cliente antes
de que la respuesta HTTP llegara, aunque los INSERT a la BD ya se
habían hecho artículo por artículo durante el loop).

Cómo funciona:
    1. La vista llama a lanzar_carga_en_background(...) y esto devuelve
       un task_id al toque (milisegundos), sin esperar a que termine
       el procesamiento del PDF.
    2. El procesamiento real corre en un hilo (threading.Thread) aparte,
       fuera del ciclo request/response.
    3. El progreso se guarda en el cache de Django bajo ese task_id.
    4. El frontend hace polling a un endpoint GET que lee ese cache
       (mismo patrón que ya tenían con EstadoTareaView de Celery).

IMPORTANTE — limitación a tener en cuenta:
    Si en algún momento corrés esto con más de un proceso worker
    (ej. Gunicorn con --workers 2+), y el cache de Django está en
    LOCMEM (el default), cada worker tiene su propia memoria de cache
    aislada. El hilo puede arrancar en el worker A, pero el polling
    puede caer en el worker B, que no va a "ver" el task_id.
    Con `runserver` (un solo proceso) esto no es problema. Si más
    adelante escalás a Gunicorn con varios workers, hace falta cambiar
    el cache backend a Redis (o Memcached) en settings.py para que
    todos los workers compartan el mismo storage de progreso.
"""

import logging
import threading
import uuid

from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_PREFIX = "carga_pdf_task:"
CACHE_TTL_SEGUNDOS = 60 * 60 * 2  # 2 horas — tiempo de sobra para que el usuario revise el resultado


class ProgresoTask:
    """
    Objeto liviano compatible con la interfaz que ya espera
    cargar_articulos_desde_bytes(task=...): expone update_state(state, meta).
    En vez de reportar a un broker de Celery, escribe el progreso
    directamente al cache de Django.
    """

    def __init__(self, task_id: str):
        self.task_id = task_id

    def update_state(self, state: str = "STARTED", meta: dict = None):
        cache.set(
            CACHE_PREFIX + self.task_id,
            {"state": state, "meta": meta or {}},
            timeout=CACHE_TTL_SEGUNDOS,
        )


def obtener_progreso(task_id: str):
    """Devuelve {"state": ..., "meta": {...}} o None si no existe/expiró."""
    return cache.get(CACHE_PREFIX + task_id)


def lanzar_carga_en_background(
    contenido_pdf: bytes,
    fuente: str,
    norma_id: int,
    rama_id: int,
    sobrescribir: bool = False,
) -> str:
    """
    Arranca el procesamiento del PDF en un hilo aparte y devuelve
    inmediatamente un task_id para hacer polling del progreso.
    """
    from modulo_catalogo.services.carga_pdf_service import cargar_articulos_desde_bytes

    task_id = str(uuid.uuid4())
    progreso = ProgresoTask(task_id)

    cache.set(
        CACHE_PREFIX + task_id,
        {"state": "PENDING", "meta": {"paso": "En cola..."}},
        timeout=CACHE_TTL_SEGUNDOS,
    )

    def _run():
        try:
            resultado = cargar_articulos_desde_bytes(
                contenido_pdf=contenido_pdf,
                fuente=fuente,
                norma_id=norma_id,
                rama_id=rama_id,
                task=progreso,
                sobrescribir=sobrescribir,
            )
            cache.set(
                CACHE_PREFIX + task_id,
                {"state": "SUCCESS", "meta": {"resumen": resultado.resumen()}},
                timeout=CACHE_TTL_SEGUNDOS,
            )
        except Exception as e:
            logger.exception("Error en carga de PDF en background (task_id=%s)", task_id)
            cache.set(
                CACHE_PREFIX + task_id,
                {"state": "FAILURE", "meta": {"error": str(e)}},
                timeout=CACHE_TTL_SEGUNDOS,
            )

    hilo = threading.Thread(target=_run, daemon=True)
    hilo.start()

    return task_id