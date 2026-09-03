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