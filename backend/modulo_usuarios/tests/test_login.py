from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APITestCase

from .factories import PASSWORD_VALIDA, crear_usuario


@override_settings(LOGIN_MAX_INTENTOS=3, LOGIN_BLOQUEO_MINUTOS=15)
class LoginViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("auth-login")
        self.user = crear_usuario(usuario="jdoe", password=PASSWORD_VALIDA)

    def test_login_correcto_devuelve_tokens_y_datos_del_usuario(self):
        response = self.client.post(
            self.url, {"usuario": "jdoe", "password": PASSWORD_VALIDA}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertEqual(response.data["usuario"]["usuario"], "jdoe")
        # El refresh token nunca viaja en el body, solo por cookie httpOnly.
        self.assertNotIn("refresh_token", response.data)
        self.assertIn("refresh_token", response.cookies)
        self.assertTrue(response.cookies["refresh_token"]["httponly"])

    def test_login_correcto_resetea_intentos_fallidos_previos(self):
        self.user.intentos_fallidos = 2
        self.user.save(update_fields=["intentos_fallidos"])

        self.client.post(self.url, {"usuario": "jdoe", "password": PASSWORD_VALIDA}, format="json")

        self.user.refresh_from_db()
        self.assertEqual(self.user.intentos_fallidos, 0)

    def test_password_incorrecta_incrementa_intentos_fallidos(self):
        response = self.client.post(
            self.url, {"usuario": "jdoe", "password": "incorrecta"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertEqual(self.user.intentos_fallidos, 1)
        self.assertIsNone(self.user.bloqueado_hasta)

    def test_usuario_inexistente_no_revela_si_existe_la_cuenta(self):
        response_inexistente = self.client.post(
            self.url, {"usuario": "no-existe", "password": "cualquiera"}, format="json"
        )
        response_password_mala = self.client.post(
            self.url, {"usuario": "jdoe", "password": "incorrecta"}, format="json"
        )

        self.assertEqual(response_inexistente.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response_inexistente.data["non_field_errors"],
            response_password_mala.data["non_field_errors"],
        )

    def test_bloqueo_tras_alcanzar_el_maximo_de_intentos(self):
        # LOGIN_MAX_INTENTOS=3 vía override_settings.
        for _ in range(3):
            response = self.client.post(
                self.url, {"usuario": "jdoe", "password": "incorrecta"}, format="json"
            )

        self.assertEqual(response.status_code, status.HTTP_423_LOCKED)
        self.user.refresh_from_db()
        self.assertTrue(self.user.esta_bloqueado)
        # El contador se reinicia al activarse el bloqueo.
        self.assertEqual(self.user.intentos_fallidos, 0)

    def test_login_con_password_correcta_durante_bloqueo_sigue_rechazado(self):
        self.user.bloqueado_hasta = timezone.now() + timedelta(minutes=15)
        self.user.save(update_fields=["bloqueado_hasta"])

        response = self.client.post(
            self.url, {"usuario": "jdoe", "password": PASSWORD_VALIDA}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_423_LOCKED)

    def test_usuario_inactivo_no_puede_iniciar_sesion(self):
        self.user.estado = False
        self.user.save(update_fields=["estado"])

        response = self.client.post(
            self.url, {"usuario": "jdoe", "password": PASSWORD_VALIDA}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_campos_faltantes_devuelven_400(self):
        response = self.client.post(self.url, {"usuario": "jdoe"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
