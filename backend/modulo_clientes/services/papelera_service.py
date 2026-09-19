"""
Papelera de clientes (soft-delete recuperable), con sus casos.

Único punto por donde un cliente entra a la papelera o sale de ella.

- Al eliminar un cliente que tiene casos activos hay que decidir: o se
  rechaza (por defecto) o se eliminan también sus casos (eliminar_casos=True).
  Esos casos quedan marcados como "eliminados con el cliente".
- Al restaurar al cliente vuelven SOLO los casos que se eliminaron junto con
  él; los que alguien había eliminado por separado antes siguen en la
  papelera de casos y se restauran uno por uno.
- Todo ocurre en una transacción: si algo falla no queda un cliente
  eliminado con casos activos ni al revés.
"""
from django.db import transaction
from django.utils import timezone

from modulo_casos.models.caso import Caso
from modulo_casos.services.papelera_service import enviar_a_papelera, restaurar_desde_papelera
from modulo_clientes.models.cliente import Cliente


class ClienteConCasosActivosError(Exception):
    """El cliente tiene casos activos y no se pidió eliminarlos con él."""

    def __init__(self, casos_activos):
        self.casos_activos = casos_activos
        super().__init__(
            f"El cliente tiene {casos_activos} "
            f"{'caso activo' if casos_activos == 1 else 'casos activos'}."
        )


def enviar_cliente_a_papelera(cliente, usuario, eliminar_casos=False):
    """
    Marca al cliente como eliminado (estado=False) y guarda quién y cuándo.

    Si tiene casos activos: con eliminar_casos=False lanza
    ClienteConCasosActivosError sin tocar nada; con eliminar_casos=True los
    envía también a la papelera. Devuelve la lista de casos eliminados
    (vacía si no había o si el cliente ya estaba en la papelera).
    """
    with transaction.atomic():
        bloqueado = Cliente.objects.select_for_update().get(pk=cliente.pk)
        if not bloqueado.estado:
            return []

        casos = list(
            Caso.objects.select_for_update()
            .filter(cliente=bloqueado, estado=True)
            .order_by("id")
        )
        if casos and not eliminar_casos:
            raise ClienteConCasosActivosError(len(casos))

        for caso in casos:
            enviar_a_papelera(caso, usuario, con_cliente=True)

        bloqueado.estado = False
        bloqueado.eliminado_at = timezone.now()
        bloqueado.eliminado_por = usuario
        bloqueado.save(update_fields=["estado", "eliminado_at", "eliminado_por"])

    cliente.estado = False
    cliente.eliminado_at = bloqueado.eliminado_at
    cliente.eliminado_por = usuario
    return casos


def restaurar_cliente(cliente, usuario):
    """
    Devuelve al cliente a la lista de clientes activos, limpia los datos de
    eliminación y restaura los casos que se eliminaron junto con él.
    Devuelve la lista de casos restaurados. Si el cliente ya estaba
    activo no hace nada.
    """
    with transaction.atomic():
        bloqueado = Cliente.objects.select_for_update().get(pk=cliente.pk)
        if bloqueado.estado:
            return []

        bloqueado.estado = True
        bloqueado.eliminado_at = None
        bloqueado.eliminado_por = None
        bloqueado.save(update_fields=["estado", "eliminado_at", "eliminado_por"])

        casos = list(
            Caso.objects.select_for_update()
            .filter(cliente=bloqueado, estado=False, eliminado_con_cliente=True)
            .order_by("id")
        )
        for caso in casos:
            restaurar_desde_papelera(caso, usuario, con_cliente=True)

    cliente.estado = True
    cliente.eliminado_at = None
    cliente.eliminado_por = None
    return casos
