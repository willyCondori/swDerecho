"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()

# Solo al arrancar el servidor, sin cargar modelos durante migrate ni los tests.
from modulo_ia.services.preparacion_modelos import preparar_modelos_servidor

preparar_modelos_servidor()
