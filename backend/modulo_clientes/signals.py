from django.db.models.signals import post_save
from django.dispatch import receiver

from modulo_clientes.models.cliente import Cliente

_CAMPOS_DEL_NOMBRE = {"nombres", "apellidos"}


@receiver(post_save, sender=Cliente, dispatch_uid="cliente_reindexar_busqueda")
def reindexar_busqueda_al_guardar(sender, instance, created, raw=False, update_fields=None, **kwargs):
    """
    Mantiene al día el índice de búsqueda (ClienteBusquedaToken) sin importar
    por dónde se guarde el cliente: API, shell, scripts o tests.

    No hace nada al cargar fixtures (raw) ni cuando un save(update_fields=...)
    no toca el nombre (p. ej. enviar a la papelera). Los cambios con
    QuerySet.update() o bulk_create() no disparan señales: para esos casos
    existe `python manage.py reindexar_busqueda_clientes`.
    """
    if raw:
        return
    if update_fields is not None and not (_CAMPOS_DEL_NOMBRE & set(update_fields)):
        return

    from modulo_clientes.services.busqueda_service import reindexar_cliente
    reindexar_cliente(instance)
