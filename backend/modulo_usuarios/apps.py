# modulo_usuarios/apps.py
"""
Limpieza automática de tokens JWT vencidos, sin Celery — mismo patrón
de hilo en background que modulo_catalogo/services/background_tasks.py.

Qué borra `flushexpiredtokens` (comando de rest_framework_simplejwt.
token_blacklist, ya en INSTALLED_APPS):
    - OutstandingToken cuyo `expires_at` ya pasó.
    - Sus BlacklistedToken asociados (los que quedaron marcados al
      hacer logout o al rotar el refresh en /auth/refresh/).

Sin esto, ambas tablas crecen indefinidamente: cada login crea un
OutstandingToken nuevo y cada logout/rotación agrega un
BlacklistedToken, pero nada los borra — el comando existe pero
alguien tiene que llamarlo.

Por qué un hilo y no Celery beat / django-crontab:
    El proyecto ya sacó Celery del stack (ver AnalisisCasoView /
    carga de PDFs, ambos migrados a threading). Meter una dependencia
    de scheduling nueva solo para esto sería inconsistente con esa
    decisión. Un hilo daemon que duerme y se despierta una vez al día
    alcanza de sobra para este volumen.

Limitación a tener en cuenta (igual que en background_tasks.py):
    Con Gunicorn + varios workers, cada worker arranca su propio hilo
    y ejecuta el borrado por su cuenta. No es un problema de
    integridad (es un DELETE idempotente, no hay condición de
    carrera), solo trabajo duplicado sin importancia a esta escala.
"""

import logging
import os
import sys
import threading

from django.apps import AppConfig

logger = logging.getLogger(__name__)

# Comandos de manage.py durante los que NO tiene sentido levantar el
# scheduler: no sirven requests, y en migrate/test corriendo en CI no
# queremos un hilo daemon colgado esperando 24 horas.
_COMANDOS_SIN_SCHEDULER = {
    "makemigrations", "migrate", "shell", "shell_plus", "test",
    "collectstatic", "createsuperuser", "dumpdata", "loaddata",
    "flushexpiredtokens",
}

INTERVALO_SEGUNDOS = 24 * 60 * 60  # una vez al día alcanza


class ModuloUsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modulo_usuarios"

    def ready(self):
        # El autoreloader de `runserver` importa la app dos veces: una
        # en el proceso "watcher" y otra en el proceso real que sirve
        # requests. RUN_MAIN solo está seteado en este último — sin
        # este check el scheduler arrancaría duplicado en desarrollo.
        if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
            return

        comando = sys.argv[1] if len(sys.argv) > 1 else ""
        if comando in _COMANDOS_SIN_SCHEDULER:
            return

        _iniciar_scheduler_limpieza_tokens()


def _iniciar_scheduler_limpieza_tokens():
    def loop():
        # Import diferido: ready() corre muy temprano en el arranque,
        # antes de que el registro de apps esté completamente listo
        # para que call_command pueda resolver el comando.
        from django.core.management import call_command

        while True:
            try:
                call_command("flushexpiredtokens")
                logger.info("Limpieza de tokens JWT expirados/blacklisteados ejecutada.")
            except Exception:
                logger.exception("Falló la limpieza automática de tokens JWT.")
            threading.Event().wait(INTERVALO_SEGUNDOS)

    hilo = threading.Thread(target=loop, name="limpieza-tokens-jwt", daemon=True)
    hilo.start()