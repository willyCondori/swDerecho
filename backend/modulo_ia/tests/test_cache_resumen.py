from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from modulo_ia.services.model_loader import version_activa
from modulo_usuarios.tests.factories import crear_rol, crear_usuario


class CacheResumenTests(APITestCase):
    def setUp(self):
        self.clave = f"jurisprudencia:resumen:v1:{version_activa()}"
        cache.delete(self.clave)
        self.addCleanup(cache.delete, self.clave)
        self.usuario = crear_usuario("cache.abogado", rol=crear_rol("Abogado"))
        self.client.force_authenticate(self.usuario)
        self.url = "/api/ia/jurisprudencia/resumen/"

    def test_segunda_lectura_evita_las_cinco_consultas_del_corpus(self):
        primera = self.client.get(self.url)
        self.assertEqual(primera.status_code, 200)
        with self.assertNumQueries(0):
            segunda = self.client.get(self.url)
        self.assertEqual(segunda.data, primera.data)

    def test_cache_no_omite_los_permisos(self):
        self.client.get(self.url)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.usuario.estado = False
        self.client.force_authenticate(self.usuario)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_expiracion_refresca_y_no_borra_tareas_normativas(self):
        cache.set("prueba:tarea-normativa", {"estado": "procesando"}, 60)
        self.addCleanup(cache.delete, "prueba:tarea-normativa")
        with patch("modulo_ia.views.jurisprudencia_view.cache.set", wraps=cache.set) as guardar:
            self.client.get(self.url)
        self.assertEqual(guardar.call_args.kwargs["timeout"], 15)
        cache.delete(self.clave)  # Simula el vencimiento del resultado.
        with self.assertNumQueries(5):
            self.client.get(self.url)
        self.assertEqual(cache.get("prueba:tarea-normativa"), {"estado": "procesando"})

    def test_cambiar_modelo_no_reutiliza_contadores_de_otra_version(self):
        self.client.get(self.url)
        otra_clave = "jurisprudencia:resumen:v1:cache-otro-modelo"
        cache.delete(otra_clave)
        self.addCleanup(cache.delete, otra_clave)
        with override_settings(EMBEDDING_MODEL_VERSION="cache-otro-modelo"):
            with self.assertNumQueries(5):
                self.assertEqual(self.client.get(self.url).status_code, 200)
