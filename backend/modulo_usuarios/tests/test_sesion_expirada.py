from datetime import timedelta

from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .factories import PASSWORD_VALIDA, crear_usuario


class SesionExpiradaTests(APITestCase):
    def setUp(self):
        self.user = crear_usuario(usuario="sesion", password=PASSWORD_VALIDA)
        access = AccessToken.for_user(self.user)
        access.set_exp(lifetime=timedelta(seconds=-60))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_login_acepta_credenciales_con_access_vencido(self):
        response = self.client.post(reverse("auth-login"), {
            "usuario": "sesion", "password": PASSWORD_VALIDA,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.data)

    def test_refresh_usa_cookie_aunque_access_este_vencido(self):
        self.client.cookies["refresh_token"] = str(RefreshToken.for_user(self.user))
        response = self.client.post(reverse("auth-refresh"), {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.data)
        self.assertTrue(response.cookies["refresh_token"]["httponly"])

    def test_refresh_invalido_borra_cookie_aunque_access_este_vencido(self):
        self.client.cookies["refresh_token"] = "invalido"
        response = self.client.post(reverse("auth-refresh"), {}, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.cookies["refresh_token"]["max-age"], 0)

    def test_rutas_protegidas_siguen_rechazando_access_vencido(self):
        response = self.client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, 401)

    def test_recuperacion_valida_campos_aunque_access_este_vencido(self):
        for name in ("auth-recuperar-password", "auth-recuperar-password-confirmar"):
            with self.subTest(name=name):
                response = self.client.post(reverse(name), {}, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn("email", response.data)
