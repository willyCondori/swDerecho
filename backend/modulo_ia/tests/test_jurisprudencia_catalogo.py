from unittest.mock import patch

import requests
from django.test import override_settings
from rest_framework.test import APITestCase

from modulo_ia.models.jurisprudencia import ResolucionJurisprudencia, FragmentoJurisprudencia, EmbeddingJurisprudencia
from modulo_ia.services.model_loader import version_activa
from modulo_usuarios.tests.factories import crear_rol, crear_usuario


class CatalogoJurisprudenciaTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.asistente = crear_usuario("lectura.tsj", rol=crear_rol("Asistente"))
        cls.abogado = crear_usuario("escritura.tsj", rol=crear_rol("Abogado"))
        cls.r = ResolucionJurisprudencia.objects.create(
            fuente_id="123", numero="AS/123/2024", expediente="EXP-ROBO", fecha="2024-01-15",
            materia="Penal", sala="Sala Penal", departamento="La Paz", texto="Resolución completa sobre robo agravado.",
            url_fuente="https://apigenesis.tsj.bo/api/v1/resoluciones/123", huella="a" * 64,
        )
        f = FragmentoJurisprudencia.objects.create(resolucion=cls.r, orden=0, contenido=cls.r.texto)
        EmbeddingJurisprudencia.objects.create(fragmento=f, modelo_version=version_activa(), vector=[1.] + [0.] * 767)
        ResolucionJurisprudencia.objects.create(fuente_id="124", numero="AS/124/2023", texto="Estafa", huella="b" * 64, fecha="2023-01-10")
        ResolucionJurisprudencia.objects.create(fuente_id="125", texto="Inactiva", activa=False, huella="c" * 64)

    def setUp(self):
        self.client.force_authenticate(self.asistente)

    def test_lista_paginada_filtra_texto_fecha_y_modelo_sin_incluir_texto_completo(self):
        base = "/api/ia/jurisprudencia/"
        self.assertEqual(self.client.get(base).data["count"], 2)
        respuesta = self.client.get(base, {"search": "robo", "desde": "2024-01-01", "sala": "Sala Penal", "indexada": "true"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["count"], 1)
        self.assertNotIn("texto", respuesta.data["results"][0])
        self.assertEqual(respuesta.data["results"][0]["extracto"], self.r.texto)
        self.assertTrue(respuesta.data["results"][0]["indexada"])
        self.assertEqual(self.client.get(base, {"indexada": "false"}).data["count"], 1)
        self.assertEqual(self.client.get(base, {"desde": "fecha inválida"}).status_code, 400)
        self.assertEqual(self.client.get(base, {"desde": "2025-01-01", "hasta": "2024-01-01"}).status_code, 400)

    def test_lector_y_resumen_requieren_sesion_y_no_exponen_inactivas(self):
        detalle = self.client.get(f"/api/ia/jurisprudencia/{self.r.pk}/")
        self.assertEqual(detalle.data["texto"], self.r.texto)
        resumen = self.client.get("/api/ia/jurisprudencia/resumen/")
        self.assertEqual(resumen.data["resoluciones"], 2)
        self.assertEqual(resumen.data["indexadas"], 1)
        self.assertEqual(resumen.data["embeddings"], 1)
        self.r.activa = False; self.r.save()
        self.assertEqual(self.client.get(f"/api/ia/jurisprudencia/{self.r.pk}/").status_code, 404)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/ia/jurisprudencia/").status_code, 401)

    @override_settings(TSJ_API_KEY="prueba-no-publicar")
    def test_busqueda_proxy_sanea_html_y_indica_resoluciones_ya_guardadas(self):
        with patch("modulo_ia.views.jurisprudencia_view.TSJApi") as api:
            api.return_value.buscar.return_value = {"data": [{"id": 123, "nro_resolucion": "AS/123/2024", "resumen": "<p>Robo</p><script>alert(1)</script>"}], "meta": {"count": 1, "page": 1, "totalPages": 1}}
            respuesta = self.client.get("/api/ia/tsj/buscar/", {"palabras": "robo", "page": 1})
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta.data["results"][0]["extracto"], "Robo")
            self.assertEqual(respuesta.data["results"][0]["registro_id"], self.r.pk)
            api.return_value.buscar.assert_called_once_with(1, "robo")
            api.return_value.close.assert_called_once()
        with patch("modulo_ia.views.jurisprudencia_view.TSJApi") as api:
            api.return_value.buscar.side_effect = requests.Timeout("información interna")
            respuesta = self.client.get("/api/ia/tsj/buscar/")
            self.assertEqual(respuesta.status_code, 502)
            self.assertNotIn("información interna", str(respuesta.data))
        self.assertEqual(self.client.get("/api/ia/tsj/buscar/", {"page": 0}).status_code, 400)

    @override_settings(TSJ_API_KEY="prueba-no-publicar")
    def test_asistente_no_incorpora_abogado_inicia_tarea(self):
        url = "/api/ia/tsj/incorporar/"
        self.assertEqual(self.client.post(url, {"fuente_id": "123"}).status_code, 403)
        self.client.force_authenticate(self.abogado)
        def iniciar(usuario, trabajo, final):
            final()
            return "tarea-tsj"
        with patch("modulo_ia.views.jurisprudencia_view.iniciar", side_effect=iniciar):
            respuesta = self.client.post(url, {"fuente_id": "123"})
        self.assertEqual(respuesta.status_code, 202)
        self.assertEqual(respuesta.data["task_id"], "tarea-tsj")
        self.assertEqual(self.client.post(url, {"fuente_id": "../1"}).status_code, 400)
