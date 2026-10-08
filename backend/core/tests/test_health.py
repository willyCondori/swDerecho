from unittest.mock import patch
from django.db import DatabaseError
from django.test import TestCase


class HealthTests(TestCase):
    def test_disponible_si_responde_la_base(self):
        respuesta = self.client.get('/health/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {'status': 'ok'})

    def test_base_no_disponible_no_expone_credenciales(self):
        with patch('config.health.connection.cursor', side_effect=DatabaseError('dato privado')):
            respuesta = self.client.get('/health/')
        self.assertEqual(respuesta.status_code, 503)
        self.assertEqual(respuesta.json(), {'status': 'unavailable'})

    def test_no_admite_escrituras(self):
        self.assertEqual(self.client.post('/health/').status_code, 405)
