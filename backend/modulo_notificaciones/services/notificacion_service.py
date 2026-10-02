# modulo_notificaciones/services/notificacion_service.py
"""
Punto único para crear notificaciones. Deliberadamente defensivo: una
notificación es un "nice to have" — si falla crearla (por el motivo que
sea), eso NUNCA debe tumbar el flujo real que la disparó (terminar un
análisis, subir un documento). Por eso atrapa cualquier excepción acá
adentro y solo la loguea.
"""
import logging

from django.db import transaction
from core.permissions.roles import administradores_activos_qs
from core.utils.usuarios import nombre_visible_usuario

from modulo_notificaciones.models import Notificacion, TipoNotificacion

logger = logging.getLogger(__name__)


def crear_notificacion(*, usuario, tipo, titulo, mensaje, caso=None):
    """
    usuario: destinatario (instancia de Usuario). Si es None, no hace nada
             (ej. un caso sin dueño no debería poder llegar a esto, pero
             por las dudas no se intenta notificar a nadie).
    tipo:    uno de TipoNotificacion.
    """
    if usuario is None:
        return None
    try:
        return Notificacion.objects.create(
            usuario=usuario,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            caso=caso,
        )
    except Exception:
        logger.exception(
            "No se pudo crear la notificación tipo=%s para usuario_id=%s",
            tipo, getattr(usuario, "pk", None),
        )
        return None


def notificar_analisis_completado(caso):
    crear_notificacion(
        usuario=caso.usuario,
        tipo=TipoNotificacion.ANALISIS_COMPLETADO,
        titulo="Tu análisis terminó",
        mensaje=f'El análisis del caso "{caso.titulo}" ({caso.codigo}) ya está listo.',
        caso=caso,
    )


def notificar_analisis_error(caso):
    crear_notificacion(
        usuario=caso.usuario,
        tipo=TipoNotificacion.ANALISIS_ERROR,
        titulo="Tu análisis falló",
        mensaje=(
            f'El análisis del caso "{caso.titulo}" ({caso.codigo}) terminó con un error. '
            "Puedes volver a intentarlo desde el caso."
        ),
        caso=caso,
    )


def notificar_documento_nuevo(documento, usuario_subio):
    """
    Solo tiene sentido si quien subió el documento NO es el dueño del
    caso (ej. un Administrador o Asistente con acceso subió algo por él);
    si el propio dueño lo sube, no hace falta notificarle algo que acaba
    de hacer él mismo. Ese chequeo vive en el llamador (ver
    DocumentoCasoViewSet.perform_create), acá solo se arma el mensaje.
    """
    caso = documento.caso
    nombre_subio = getattr(usuario_subio, "usuario", "Alguien")
    crear_notificacion(
        usuario=caso.usuario,
        tipo=TipoNotificacion.DOCUMENTO_NUEVO,
        titulo="Nuevo documento en tu caso",
        mensaje=(
            f'{nombre_subio} subió "{documento.nombre_original}" '
            f'al caso "{caso.titulo}" ({caso.codigo}).'
        ),
        caso=caso,
    )


def notificar_caso_nuevo(caso, creador):
    """Avisa a los administradores activos quién creó el caso confirmado."""
    try:
        nombre = nombre_visible_usuario(creador)
        autor = f"{nombre} ({creador.usuario})" if nombre != creador.usuario else nombre
        for administrador in administradores_activos_qs():
            # Un fallo de inserción no debe romper una transacción externa
            # ni impedir los avisos a los demás administradores.
            with transaction.atomic():
                crear_notificacion(
                    usuario=administrador,
                    tipo=TipoNotificacion.CASO_NUEVO,
                    titulo="Nuevo caso creado",
                    mensaje=f'{autor} creó el caso "{caso.titulo}" ({caso.codigo}).',
                    caso=caso,
                )
    except Exception:
        logger.exception("No se pudo notificar la creación del caso %s", caso.pk)
