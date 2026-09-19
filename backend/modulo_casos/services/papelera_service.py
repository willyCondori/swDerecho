"""
Papelera de casos (soft-delete recuperable).

Único punto por donde un caso entra a la papelera o sale de ella, para
que `estado`, `eliminado_at`/`eliminado_por` y la línea de tiempo del
seguimiento nunca queden desincronizados.
"""
from django.db import transaction
from django.utils import timezone

from modulo_casos.models.caso import Caso
from modulo_casos.services.seguimiento_service import registrar_seguimiento

NOTA_ENVIADO_PAPELERA = "Caso enviado a la papelera."
NOTA_RESTAURADO = "Caso restaurado desde la papelera."


class ClienteInactivoError(Exception):
    """El cliente del caso fue eliminado: no se puede reactivar el caso."""


def enviar_a_papelera(caso, usuario):
    """
    Marca el caso como eliminado (estado=False) y guarda quién y cuándo.
    Deja una entrada en la línea de tiempo (misma etapa, con nota).
    Si el caso ya estaba en la papelera no hace nada.
    """
    with transaction.atomic():
        bloqueado = Caso.objects.select_for_update().get(pk=caso.pk)
        if not bloqueado.estado:
            return caso

        registrar_seguimiento(bloqueado, etapa=bloqueado.etapa, usuario=usuario, nota=NOTA_ENVIADO_PAPELERA)
        bloqueado.estado = False
        bloqueado.eliminado_at = timezone.now()
        bloqueado.eliminado_por = usuario
        bloqueado.save(update_fields=["estado", "eliminado_at", "eliminado_por"])

    caso.estado = False
    caso.eliminado_at = bloqueado.eliminado_at
    caso.eliminado_por = usuario
    return caso


def restaurar_desde_papelera(caso, usuario):
    """
    Devuelve el caso a la lista de casos activos y limpia los datos de
    eliminación. Deja una entrada en la línea de tiempo.

    Lanza ClienteInactivoError si el cliente del caso fue eliminado
    (un caso activo no puede colgar de un cliente inactivo).
    """
    with transaction.atomic():
        bloqueado = Caso.objects.select_for_update().select_related("cliente").get(pk=caso.pk)
        if bloqueado.estado:
            return caso
        if not bloqueado.cliente.estado:
            raise ClienteInactivoError(
                "No se puede restaurar el caso porque su cliente fue eliminado."
            )

        bloqueado.estado = True
        bloqueado.eliminado_at = None
        bloqueado.eliminado_por = None
        bloqueado.save(update_fields=["estado", "eliminado_at", "eliminado_por"])
        registrar_seguimiento(bloqueado, etapa=bloqueado.etapa, usuario=usuario, nota=NOTA_RESTAURADO)

    caso.estado = True
    caso.eliminado_at = None
    caso.eliminado_por = None
    caso.etapa_actualizada_at = bloqueado.etapa_actualizada_at
    return caso
