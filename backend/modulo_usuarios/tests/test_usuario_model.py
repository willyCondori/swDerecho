from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .factories import crear_usuario


class EstaBloqueadoTests(TestCase):
    def test_sin_bloqueado_hasta_no_esta_bloqueado(self):
        user = crear_usuario()
        self.assertIsNone(user.bloqueado_hasta)
        self.assertFalse(user.esta_bloqueado)

    def test_bloqueado_hasta_en_el_futuro_esta_bloqueado(self):
        user = crear_usuario()
        user.bloqueado_hasta = timezone.now() + timedelta(minutes=10)
        self.assertTrue(user.esta_bloqueado)

    def test_bloqueado_hasta_en_el_pasado_no_esta_bloqueado(self):
        user = crear_usuario()
        user.bloqueado_hasta = timezone.now() - timedelta(minutes=1)
        self.assertFalse(user.esta_bloqueado)
