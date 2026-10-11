from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.core.cache import caches
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from modulo_casos.models.caso import Caso
from modulo_clientes.models.cliente import Cliente
from modulo_documentos.models.documento import DocumentoCaso, TipoDoc
from modulo_ia.models.chunk import ChunkCaso
from modulo_notificaciones.realtime import autenticar
from .factories import PASSWORD_VALIDA, crear_rol, crear_usuario


class SeguridadAPITests(APITestCase):
    def setUp(self):
        self.user = crear_usuario("seguridad", debe_cambiar_password=True)
        self.refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.refresh.access_token}")

    def test_password_temporal_bloquea_modulos_y_documentacion(self):
        for url in ["/api/casos/", "/api/clientes/", "/api/documentos/documentos/",
                    "/api/notificaciones/", "/api/schema/", "/api/docs/"]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.data["code"], "password_change_required")

    def test_password_temporal_permite_cambio_y_desbloquea_mismo_token(self):
        self.assertEqual(self.client.get("/api/usuarios/auth/me/").status_code, 200)
        response = self.client.post("/api/usuarios/auth/cambiar-password/", {
            "password_actual": PASSWORD_VALIDA, "password_nuevo": "OtraSegura#987",
            "password_confirm": "OtraSegura#987",
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.client.get("/api/casos/").status_code, 200)

    def test_password_temporal_permite_logout(self):
        self.client.cookies["refresh_token"] = str(self.refresh)
        self.assertEqual(self.client.post("/api/usuarios/auth/logout/").status_code, 200)

    def test_cuenta_inactiva_no_usa_token_ni_renueva(self):
        self.user.estado = False
        self.user.save(update_fields=["estado"])
        self.assertEqual(self.client.get("/api/usuarios/auth/me/").status_code, 401)
        self.client.cookies["refresh_token"] = str(self.refresh)
        response = self.client.post("/api/usuarios/auth/refresh/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.cookies["refresh_token"]["max-age"], 0)

    def test_documentacion_solo_para_administradores(self):
        self.user.debe_cambiar_password = False
        self.user.save(update_fields=["debe_cambiar_password"])
        for url in ["/api/docs/", "/api/schema/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.user.rol = crear_rol("Abogado")
        self.user.save(update_fields=["rol"])
        for url in ["/api/docs/", "/api/schema/"]:
            self.assertEqual(self.client.get(url).status_code, 403)
        self.client.credentials()
        for url in ["/api/docs/", "/api/schema/"]:
            self.assertEqual(self.client.get(url).status_code, 401)


class SeguridadWebSocketTests(TransactionTestCase):
    def test_password_temporal_no_conecta_websocket(self):
        # El consumidor cierra conexiones antiguas; no ejecutar dentro de
        # la transaccion envolvente de APITestCase.
        user = crear_usuario("ws-temporal", debe_cambiar_password=True)
        token = str(RefreshToken.for_user(user).access_token)
        with self.assertRaises(ValueError):
            async_to_sync(autenticar)(token)


class AccesoCasoDocumentosTests(APITestCase):
    def setUp(self):
        owner = crear_usuario("propietario", rol=crear_rol("Abogado"))
        self.caso = Caso.objects.create(codigo="SEG-CASO", titulo="Caso seguro",
            descripcion="Robo", usuario=owner,
            cliente=Cliente.objects.create(nombres="Cliente", apellidos="Seguro"))
        self.doc = DocumentoCaso.objects.create(caso=self.caso,
            nombre_original="ejemplo.pdf", ruta_archivo="no-existe.pdf",
            tipo_archivo="pdf", tamano=100, tipo_documento=TipoDoc.objects.create(tipo="prueba"))
        self.chunk = ChunkCaso.objects.create(caso=self.caso, contenido="Robo", orden=1)
        self.urls = [f"/api/casos/{self.caso.public_id}/",
                     f"/api/documentos/documentos/{self.doc.public_id}/"]

    def test_mismos_roles_leen_caso_y_documento_ajenos(self):
        for rol in ["Administrador", "Abogado", "Asistente"]:
            user = crear_usuario(f"lector-{rol}", rol=crear_rol(rol))
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
            for url in self.urls:
                self.assertEqual(self.client.get(url).status_code, 200, (rol, url))
            if rol == "Asistente":
                self.assertEqual(self.client.delete(self.urls[0]).status_code, 403)
                self.assertEqual(self.client.delete(self.urls[1]).status_code, 403)

    def test_papelera_oculta_documento_detalle_listado_y_descarga(self):
        user = crear_usuario("lector", rol=crear_rol("Asistente"))
        self.client.force_authenticate(user)
        self.caso.estado = False
        self.caso.save(update_fields=["estado"])
        for url in self.urls + [self.urls[1] + "descargar/"]:
            self.assertEqual(self.client.get(url).status_code, 404)
        response = self.client.get("/api/documentos/documentos/por_caso/",
                                   {"caso_id": str(self.caso.public_id)})
        self.assertEqual(response.data, [])
        response = self.client.get("/api/ia/chunks/por_caso/",
                                   {"caso_id": str(self.caso.public_id)})
        self.assertEqual(response.data, [])


@override_settings(API_RATE_LIMITS={"login": "1/min", "recovery": "1/hour",
    "recovery_confirm": "1/min", "analysis_burst": "1/min", "analysis_daily": "10/day"})
class LimitesPeticionesTests(APITestCase):
    def setUp(self):
        caches["security_throttles"].clear()

    def test_endpoints_publicos_limitan_y_envian_retry_after(self):
        for url in ["/api/usuarios/auth/login/", "/api/usuarios/auth/recuperar-password/",
                    "/api/usuarios/auth/recuperar-password/confirmar/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, {}, format="json").status_code, 400)
                response = self.client.post(url, {}, format="json")
                self.assertEqual(response.status_code, 429)
                self.assertGreater(int(response["Retry-After"]), 0)

    def test_dos_rutas_analisis_comparten_limite_y_usuarios_separados(self):
        user = crear_usuario("analista", rol=crear_rol("Abogado"))
        caso = Caso.objects.create(codigo="SEG-ANALISIS", titulo="Caso", descripcion="Robo",
            usuario=user, cliente=Cliente.objects.create(nombres="Prueba", apellidos="Limite"))
        self.client.force_authenticate(user)
        with patch("modulo_ia.services.analisis_background.iniciar_analisis", return_value=(True, "OK")) as iniciar:
            response = self.client.post(f"/api/casos/{caso.public_id}/analizar/")
            self.assertEqual(response.status_code, 202, response.data)
            self.assertEqual(self.client.post("/api/ia/analizar/", {"caso_id": str(caso.public_id)}).status_code, 429)
            self.assertEqual(iniciar.call_count, 1)
            self.assertEqual(self.client.get(f"/api/casos/{caso.public_id}/estado_analisis/").status_code, 200)
            other = crear_usuario("analista2", rol=crear_rol("Abogado"))
            self.client.force_authenticate(other)
            self.assertEqual(self.client.post("/api/ia/analizar/", {"caso_id": str(caso.public_id)}).status_code, 202)

    def test_cabecera_falsificada_no_elude_ip_del_proxy(self):
        url = "/api/usuarios/auth/login/"
        self.client.post(url, {}, HTTP_X_FORWARDED_FOR="falso, 10.0.0.1")
        response = self.client.post(url, {}, HTTP_X_FORWARDED_FOR="otro, 10.0.0.1")
        self.assertEqual(response.status_code, 429)
