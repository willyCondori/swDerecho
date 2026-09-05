from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .factories import PASSWORD_VALIDA, crear_usuario


class CambioPasswordViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("auth-cambiar-password")
        self.user = crear_usuario(usuario="jdoe", password=PASSWORD_VALIDA)
        self.client.force_authenticate(self.user)

    def test_requiere_autenticacion(self):
        self.client.force_authenticate(None)
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_actual_incorrecta_es_rechazada(self):
        response = self.client.post(
            self.url,
            {
                "password_actual": "otra-cosa",
                "password_nuevo": "NuevaClave#1",
                "password_confirm": "NuevaClave#1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_actual", response.data)

    def test_password_nuevo_debil_es_rechazada(self):
        response = self.client.post(
            self.url,
            {
                "password_actual": PASSWORD_VALIDA,
                "password_nuevo": "1234",
                "password_confirm": "1234",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_nuevo", response.data)

    def test_password_nuevo_y_confirm_deben_coincidir(self):
        response = self.client.post(
            self.url,
            {
                "password_actual": PASSWORD_VALIDA,
                "password_nuevo": "NuevaClave#1",
                "password_confirm": "OtraClave#2",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.data)

    def test_password_nuevo_igual_a_la_actual_es_rechazada(self):
        response = self.client.post(
            self.url,
            {
                "password_actual": PASSWORD_VALIDA,
                "password_nuevo": PASSWORD_VALIDA,
                "password_confirm": PASSWORD_VALIDA,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_nuevo", response.data)

    def test_cambio_correcto_actualiza_password_y_limpia_bandera(self):
        self.user.debe_cambiar_password = True
        self.user.save(update_fields=["debe_cambiar_password"])

        response = self.client.post(
            self.url,
            {
                "password_actual": PASSWORD_VALIDA,
                "password_nuevo": "NuevaClave#1",
                "password_confirm": "NuevaClave#1",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.debe_cambiar_password)
        self.assertTrue(self.user.check_password("NuevaClave#1"))

    def test_cambio_obligatorio_sin_password_actual_funciona(self):
        # Cambio obligatorio del primer login: el frontend no manda
        # password_actual porque el usuario ya se autenticó con ella
        # para conseguir el JWT.
        response = self.client.post(
            self.url,
            {
                "password_nuevo": "NuevaClave#1",
                "password_confirm": "NuevaClave#1",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NuevaClave#1"))

    def test_cambio_obligatorio_sin_password_actual_rechaza_repetir_la_temporal(self):
        response = self.client.post(
            self.url,
            {
                "password_nuevo": PASSWORD_VALIDA,
                "password_confirm": PASSWORD_VALIDA,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_nuevo", response.data)
