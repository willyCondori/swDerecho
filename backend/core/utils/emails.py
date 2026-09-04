"""
Envío del correo de bienvenida con las credenciales de acceso cuando
se crea un usuario nuevo. Usa el backend SMTP de Django, configurado
para Gmail en settings.py (ver EMAIL_* en config/settings.py).

El envío no debe tumbar la creación del usuario si falla (SMTP caído,
credenciales de Gmail mal configuradas, etc.): se captura cualquier
excepción y se registra en el logger, y quien llama decide qué avisar
al administrador que creó el usuario.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def enviar_credenciales_usuario(email: str, usuario: str, password: str) -> bool:
    """
    Envía al correo del nuevo usuario su nombre de usuario y la
    contraseña temporal generada. Devuelve True si el envío fue
    exitoso, False si falló (el error queda registrado en el log).
    """
    asunto = "Tus credenciales de acceso — JurisIA"
    mensaje = (
        "Hola,\n\n"
        "Se ha creado una cuenta para vos en el sistema JurisIA. "
        "Estas son tus credenciales de acceso:\n\n"
        f"    Usuario:               {usuario}\n"
        f"    Contraseña temporal:   {password}\n\n"
        "Por seguridad, al iniciar sesión por primera vez se te pedirá "
        "que cambies esta contraseña antes de continuar.\n\n"
        "Si no esperabas este correo, contactá al administrador del sistema.\n\n"
        "— JurisIA"
    )

    try:
        send_mail(
            subject=asunto,
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception(
            "No se pudo enviar el correo de credenciales al usuario '%s'.", usuario
        )
        return False


def enviar_password_recuperacion(email: str, usuario: str, password: str) -> bool:
    """
    Envía al correo del usuario una contraseña temporal nueva para
    recuperar el acceso a su cuenta. Mismo patrón que
    enviar_credenciales_usuario() (contraseña en texto plano en el
    cuerpo del correo), pero con el texto adaptado al contexto de
    "recuperación" en vez de "alta de cuenta nueva".

    La contraseña vieja del usuario ya quedó invalidada ANTES de
    llamar a esta función (ver SolicitarRecuperacionView): generar la
    temporal y guardarla es lo que realmente "resetea" el acceso, el
    correo es solo el medio para entregársela. Si el envío falla acá,
    igual queda registrado en el log para que se pueda reenviar a
    mano si hace falta.
    """
    asunto = "Recuperación de contraseña — JurisIA"
    mensaje = (
        "Hola,\n\n"
        f"Recibimos una solicitud para recuperar el acceso a tu cuenta '{usuario}' en JurisIA. "
        "Generamos una contraseña temporal nueva:\n\n"
        f"    Contraseña temporal:   {password}\n\n"
        "Usala para entrar a la pantalla de recuperación (el mismo lugar donde pediste "
        "este correo) y ahí vas a poder elegir tu contraseña definitiva.\n\n"
        "Por seguridad, esta contraseña temporal deja de servir apenas la uses para "
        "elegir la nueva.\n\n"
        "Si vos no pediste este cambio, contactá al administrador del sistema: tu "
        "contraseña anterior ya no es válida.\n\n"
        "— JurisIA"
    )

    try:
        send_mail(
            subject=asunto,
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception(
            "No se pudo enviar el correo de recuperación de contraseña al usuario '%s'.", usuario
        )
        return False