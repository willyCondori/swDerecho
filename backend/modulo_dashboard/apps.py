# modulo_dashboard/apps.py
from django.apps import AppConfig


class ModuloDashboardConfig(AppConfig):
    """
    Módulo sin modelos propios: agrega datos de modulo_casos, modulo_clientes,
    modulo_catalogo y modulo_usuarios para la pantalla de inicio (panorama
    general del bufete). Deliberadamente de solo lectura — no es dueño de
    ninguna tabla, por eso no tiene migrations/.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "modulo_dashboard"
