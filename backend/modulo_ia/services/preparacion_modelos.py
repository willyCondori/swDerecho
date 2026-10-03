"""Precalentamiento del servidor, separado de migrate, shell y los tests."""
import logging
import threading
from time import perf_counter

from django.conf import settings

from modulo_ia.services.model_loader import obtener_modelo
from modulo_ia.services.vectorizacion_service import vectorizar_textos
from modulo_catalogo.services.ollama_normativo import precargar_modelo

logger = logging.getLogger(__name__)
_inicio_lock = threading.Lock()
_preparados = set()


def preparar_modelos_servidor():
    """El servidor acepta peticiones después de preparar los modelos habilitados."""
    with _inicio_lock:
        if settings.EMBEDDING_PRELOAD_STARTUP and 'embeddings' not in _preparados:
            inicio = perf_counter()
            logger.info("Preparando Sentence Transformers...")
            vectorizar_textos(["Preparación del modelo de búsqueda jurídica."], obtener_modelo())
            _preparados.add('embeddings')
            logger.info("Sentence Transformers listo en %.2f s", perf_counter() - inicio)
        if settings.OLLAMA_NORMATIVO_PRELOAD_STARTUP and 'qwen' not in _preparados:
            inicio = perf_counter()
            logger.info("Preparando Qwen (%s)...", settings.OLLAMA_NORMATIVO_MODELO)
            precargar_modelo()
            _preparados.add('qwen')
            logger.info("Qwen listo en %.2f s", perf_counter() - inicio)
