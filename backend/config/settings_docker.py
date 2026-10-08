"""Configuración del contenedor; mantiene intacto el desarrollo local."""
from .settings import *  # noqa: F403
from django.core.exceptions import ImproperlyConfigured

if not SECRET_KEY or SECRET_KEY == 'CAMBIAR':
    raise ImproperlyConfigured('Configura SECRET_KEY en .env.docker.')
try:
    if len(ENCRYPTION_KEY or '') != 64 or len(bytes.fromhex(ENCRYPTION_KEY)) != 32:
        raise ValueError
except (TypeError, ValueError):
    raise ImproperlyConfigured('ENCRYPTION_KEY debe contener 64 caracteres hexadecimales.') from None

DEBUG = config('DEBUG', default=False, cast=bool)
REFRESH_TOKEN_COOKIE_SECURE = config('COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_SECURE = REFRESH_TOKEN_COOKIE_SECURE
SESSION_COOKIE_SECURE = REFRESH_TOKEN_COOKIE_SECURE
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://localhost:8080,http://127.0.0.1:8080', cast=Csv())
STATIC_ROOT = BASE_DIR / 'staticfiles'
LOGGING = {
    'version': 1, 'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
