from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings

from core.utils.emails import (
    enviar_credenciales_usuario,
    enviar_password_recuperacion,
)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EnviarCredencialesUsuarioTests(TestCase):
    def test_envia_un_correo_con_usuario_y_password(self):
        resultado = enviar_credenciales_usuario(
            email="nuevo@example.com", usuario="nuevo.usuario", password="Temporal#123"
        )

        self.assertTrue(resultado)
        self.assertEqual(len(mail.outbox), 1)
        enviado = mail.outbox[0]
        self.assertEqual(enviado.to, ["nuevo@example.com"])
        self.assertIn("nuevo.usuario", enviado.body)
        self.assertIn("Temporal#123", enviado.body)

    def test_devuelve_false_y_no_propaga_si_falla_el_envio(self):
        with patch("core.utils.emails.send_mail", side_effect=Exception("SMTP caído")):
            resultado = enviar_credenciales_usuario(
                email="nuevo@example.com", usuario="nuevo.usuario", password="Temporal#123"
            )
        self.assertFalse(resultado)
        self.assertEqual(len(mail.outbox), 0)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EnviarPasswordRecuperacionTests(TestCase):
    def test_envia_un_correo_con_la_password_temporal(self):
        resultado = enviar_password_recuperacion(
            email="usuario@example.com", usuario="jdoe", password="Recup#456"
        )

        self.assertTrue(resultado)
        self.assertEqual(len(mail.outbox), 1)
        enviado = mail.outbox[0]
        self.assertEqual(enviado.to, ["usuario@example.com"])
        self.assertIn("jdoe", enviado.body)
        self.assertIn("Recup#456", enviado.body)
        self.assertIn("Recuperación de contraseña", enviado.subject)

    def test_devuelve_false_y_no_propaga_si_falla_el_envio(self):
        with patch("core.utils.emails.send_mail", side_effect=Exception("SMTP caído")):
            resultado = enviar_password_recuperacion(
                email="usuario@example.com", usuario="jdoe", password="Recup#456"
            )
        self.assertFalse(resultado)
        self.assertEqual(len(mail.outbox), 0)
