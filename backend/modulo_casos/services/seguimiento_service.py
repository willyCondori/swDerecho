"""
Lógica de seguimiento de casos.

Único punto por donde cambia la etapa de un caso: así el historial
(SeguimientoCaso) y Caso.etapa nunca quedan desincronizados.
"""
from django.db import transaction

from modulo_casos.models.caso import Caso
from modulo_casos.models.etapas import EtapaCaso
from modulo_casos.models.seguimiento import SeguimientoCaso

NOTA_INICIAL = "Caso registrado."


def registrar_seguimiento(caso, etapa, usuario, nota=""):
    """
    Mueve el caso a `etapa` y deja una entrada en el historial, todo
    en una transacción. Bloquea la fila del caso para que dos cambios
    simultáneos no registren la misma etapa_anterior.

    También sirve para registrar una nota de seguimiento sin cambiar
    de etapa (etapa == etapa actual). Devuelve el SeguimientoCaso creado.
    """
    with transaction.atomic():
        caso_bloqueado = Caso.objects.select_for_update().get(pk=caso.pk)
        seguimiento = SeguimientoCaso.objects.create(
            caso=caso_bloqueado,
            etapa=etapa,
            etapa_anterior=caso_bloqueado.etapa,
            nota=(nota or "").strip(),
            usuario=usuario,
        )
        caso_bloqueado.etapa = etapa
        caso_bloqueado.etapa_actualizada_at = seguimiento.created_at
        caso_bloqueado.save(update_fields=["etapa", "etapa_actualizada_at"])

    # Deja el objeto que recibió la vista al día con la BD.
    caso.etapa = caso_bloqueado.etapa
    caso.etapa_actualizada_at = caso_bloqueado.etapa_actualizada_at
    return seguimiento


def registrar_seguimiento_inicial(caso, usuario):
    """Primera entrada de la línea de tiempo, al crear el caso."""
    with transaction.atomic():
        seguimiento = SeguimientoCaso.objects.create(
            caso=caso,
            etapa=EtapaCaso.REGISTRADO,
            etapa_anterior=None,
            nota=NOTA_INICIAL,
            usuario=usuario,
        )
        Caso.objects.filter(pk=caso.pk).update(
            etapa=EtapaCaso.REGISTRADO,
            etapa_actualizada_at=seguimiento.created_at,
        )
    caso.etapa = EtapaCaso.REGISTRADO
    caso.etapa_actualizada_at = seguimiento.created_at
    return seguimiento
