from unittest.mock import patch

from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from modulo_usuarios.models.password_reset_token import PasswordResetToken

from .factories import PASSWORD_VALIDA, crear_usuario_con_perfil

TEMP_PASSWORD = "Temporal#123"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SolicitarRecuperacionViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("auth-recuperar-password")
        self.user, self.perfil = crear_usuario_con_perfil(
            usuario="jdoe", password=PASSWORD_VALIDA, email="jdoe@example.com"
        )

    def _solicitar(self, email="jdoe@example.com"):
        with patch(
            "core.utils.passwords.generar_password_aleatoria",
            return_value=TEMP_PASSWORD,
        ):
            return self.client.post(self.url, {"email": email}, format="json")

    def test_respuesta_generica_para_email_existente(self):
        response = self._solicitar("jdoe@example.com")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_respuesta_generica_es_identica_para_email_inexistente(self):
        # No debe poder distinguirse por la respuesta HTTP si el email
        # está o no registrado.
        response_existente = self._solicitar("jdoe@example.com")
        response_inexistente = self._solicitar("no-registrado@example.com")

        self.assertEqual(response_existente.status_code, response_inexistente.status_code)
        self.assertEqual(response_existente.data, response_inexistente.data)

    def test_email_inexistente_no_envia_correo(self):
        mail.outbox = []
        self._solicitar("no-registrado@example.com")
        self.assertEqual(len(mail.outbox), 0)

    def test_email_existente_envia_correo_y_actualiza_password(self):
        mail.outbox = []
        self._solicitar("jdoe@example.com")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["jdoe@example.com"])

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(TEMP_PASSWORD))
        self.assertFalse(self.user.check_password(PASSWORD_VALIDA))
        self.assertTrue(self.user.debe_cambiar_password)

    def test_usuario_inactivo_no_recibe_correo(self):
        self.user.estado = False
        self.user.save(update_fields=["estado"])

        mail.outbox = []
        self._solicitar("jdoe@example.com")
        self.assertEqual(len(mail.outbox), 0)

    def test_registra_una_solicitud_por_pedido(self):
        self._solicitar("jdoe@example.com")
        self.assertEqual(
            PasswordResetToken.objects.filter(usuario=self.user).count(), 1
        )

    @override_settings(PASSWORD_RESET_MAX_SOLICITUDES=2)
    def test_respeta_el_limite_de_solicitudes_en_la_ventana(self):
        mail.outbox = []
        self._solicitar("jdoe@example.com")
        self._solicitar("jdoe@example.com")
        # La tercera solicitud dentro de la ventana no debe generar ni
        # enviar una contraseña temporal nueva (protección anti-abuso).
        self._solicitar("jdoe@example.com")

        self.assertEqual(len(mail.outbox), 2)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ConfirmarRecuperacionViewTests(APITestCase):
    def setUp(self):
        self.solicitar_url = reverse("auth-recuperar-password")
        self.confirmar_url = reverse("auth-recuperar-password-confirmar")
        self.user, self.perfil = crear_usuario_con_perfil(
            usuario="jdoe", password=PASSWORD_VALIDA, email="jdoe@example.com"
        )
        with patch(
            "core.utils.passwords.generar_password_aleatoria",
            return_value=TEMP_PASSWORD,
        ):
            self.client.post(self.solicitar_url, {"email": "jdoe@example.com"}, format="json")

    def test_confirmar_con_password_temporal_correcta(self):
        response = self.client.post(
            self.confirmar_url,
            {
                "email": "jdoe@example.com",
                "password_actual": TEMP_PASSWORD,
                "password_nuevo": "Definitiva#1",
                "password_confirm": "Definitiva#1",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Definitiva#1"))
        self.assertFalse(self.user.debe_cambiar_password)

    def test_confirmar_con_password_temporal_incorrecta(self):
        response = self.client.post(
            self.confirmar_url,
            {
                "email": "jdoe@example.com",
                "password_actual": "no-es-la-temporal",
                "password_nuevo": "Definitiva#1",
                "password_confirm": "Definitiva#1",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        # La contraseña temporal sigue siendo válida: el intento fallido
        # no debe alterarla.
        self.assertTrue(self.user.check_password(TEMP_PASSWORD))

    def test_confirmar_con_email_no_registrado(self):
        response = self.client.post(
            self.confirmar_url,
            {
                "email": "otro@example.com",
                "password_actual": TEMP_PASSWORD,
                "password_nuevo": "Definitiva#1",
                "password_confirm": "Definitiva#1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_nuevo_no_puede_ser_igual_a_la_temporal(self):
        response = self.client.post(
            self.confirmar_url,
            {
                "email": "jdoe@example.com",
                "password_actual": TEMP_PASSWORD,
                "password_nuevo": TEMP_PASSWORD,
                "password_confirm": TEMP_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_nuevo", response.data)

    def test_password_nuevo_debil_es_rechazada(self):
        response = self.client.post(
            self.confirmar_url,
            {
                "email": "jdoe@example.com",
                "password_actual": TEMP_PASSWORD,
                "password_nuevo": "abc",
                "password_confirm": "abc",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_nuevo_y_confirm_deben_coincidir(self):
        response = self.client.post(
            self.confirmar_url,
            {
                "email": "jdoe@example.com",
                "password_actual": TEMP_PASSWORD,
                "password_nuevo": "Definitiva#1",
                "password_confirm": "OtraCosa#2",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.data)
