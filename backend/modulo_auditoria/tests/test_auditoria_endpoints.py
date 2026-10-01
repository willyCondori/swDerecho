"""
Tests del endpoint de auditoría (GET /api/auditoria/ y sus acciones): que
solo el Administrador pueda verlo, que los filtros (usuario, tabla, acción,
fecha) funcionen, y que la lista venga paginada.
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from modulo_auditoria.models.auditoria import Auditoria
from modulo_usuarios.tests.factories import crear_rol, crear_usuario

URL = "/api/auditoria/"


def _ids(response):
    data = response.data
    items = data["results"] if isinstance(data, dict) and "results" in data else data
    return [item["id"] for item in items]


class AuditoriaPermisosTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin = crear_usuario("admin.auditoria", rol=crear_rol("Administrador"))
        cls.abogado = crear_usuario("abogado.auditoria", rol=crear_rol("Abogado"))
        Auditoria.objects.create(usuario=cls.admin, tabla="casos", accion="CREATE", registro_id=1)

    def test_requiere_autenticacion(self):
        resp = self.client.get(URL)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_abogado_no_puede_ver_la_auditoria(self):
        self.client.force_authenticate(self.abogado)
        resp = self.client.get(URL)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_si_puede_ver_la_auditoria(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class AuditoriaFiltrosYPaginacionTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin = crear_usuario("admin.auditoria2", rol=crear_rol("Administrador"))
        cls.otro = crear_usuario("otro.usuario", rol=crear_rol("Abogado"))

        hoy = timezone.now()
        cls.reg_caso = Auditoria.objects.create(
            usuario=cls.admin, tabla="casos", accion="CREATE", registro_id=10,
        )
        cls.reg_norma = Auditoria.objects.create(
            usuario=cls.admin, tabla="normas", accion="DELETE", registro_id=20,
        )
        cls.reg_otro_usuario = Auditoria.objects.create(
            usuario=cls.otro, tabla="casos", accion="UPDATE", registro_id=10,
        )
        # Uno viejo, fuera del rango de fecha que se prueba más abajo.
        cls.reg_viejo = Auditoria.objects.create(
            usuario=cls.admin, tabla="casos", accion="CREATE", registro_id=30,
        )
        Auditoria.objects.filter(pk=cls.reg_viejo.pk).update(
            created_at=hoy - timedelta(days=30)
        )

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_filtro_por_usuario_id(self):
        resp = self.client.get(URL, {"usuario_id": self.otro.pk})
        self.assertEqual(_ids(resp), [self.reg_otro_usuario.pk])

    def test_filtro_por_usuario_nombre_parcial(self):
        resp = self.client.get(URL, {"usuario": "otro.usu"})
        self.assertEqual(_ids(resp), [self.reg_otro_usuario.pk])

    def test_filtro_por_usuario_no_sensible_a_mayusculas(self):
        resp = self.client.get(URL, {"usuario": "OTRO.USUARIO"})
        self.assertEqual(_ids(resp), [self.reg_otro_usuario.pk])

    def test_filtro_por_tabla(self):
        resp = self.client.get(URL, {"tabla": "normas"})
        self.assertEqual(_ids(resp), [self.reg_norma.pk])

    def test_filtro_por_accion(self):
        resp = self.client.get(URL, {"accion": "DELETE"})
        self.assertEqual(_ids(resp), [self.reg_norma.pk])

    def test_filtro_por_rango_de_fechas_excluye_el_registro_viejo(self):
        hoy = timezone.now().date()
        resp = self.client.get(URL, {"fecha_desde": str(hoy - timedelta(days=1))})
        ids = _ids(resp)
        self.assertNotIn(self.reg_viejo.pk, ids)
        self.assertIn(self.reg_caso.pk, ids)

    def test_fecha_hasta_anterior_a_fecha_desde_da_400(self):
        resp = self.client.get(URL, {"fecha_desde": "2026-06-01", "fecha_hasta": "2026-01-01"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accion_invalida_da_400(self):
        resp = self.client.get(URL, {"accion": "INVENTADA"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filtros_combinados(self):
        resp = self.client.get(URL, {"tabla": "casos", "accion": "CREATE", "usuario_id": self.admin.pk})
        ids = set(_ids(resp))
        self.assertIn(self.reg_caso.pk, ids)
        self.assertNotIn(self.reg_norma.pk, ids)
        self.assertNotIn(self.reg_otro_usuario.pk, ids)

    def test_la_lista_viene_paginada(self):
        resp = self.client.get(URL)
        self.assertIn("count", resp.data)
        self.assertIn("results", resp.data)
        self.assertEqual(resp.data["count"], Auditoria.objects.count())

    def test_pagina_2_no_repite_registros_de_la_pagina_1(self):
        for i in range(30):
            Auditoria.objects.create(usuario=self.admin, tabla="casos", accion="READ", registro_id=100 + i)

        pagina1 = self.client.get(URL, {"page": 1, "page_size": 25})
        pagina2 = self.client.get(URL, {"page": 2, "page_size": 25})

        ids1, ids2 = set(_ids(pagina1)), set(_ids(pagina2))
        self.assertEqual(len(ids1), 25)
        self.assertTrue(ids2)
        self.assertEqual(ids1 & ids2, set())

    def test_endpoint_acciones_lista_el_catalogo(self):
        resp = self.client.get(f"{URL}acciones/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        valores = {a["value"] for a in resp.data}
        self.assertIn("CREATE", valores)
        self.assertIn("DELETE", valores)

    def test_endpoint_resumen_agrupa_por_accion(self):
        resp = self.client.get(f"{URL}resumen/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        por_accion = {r["accion"]: r["total"] for r in resp.data}
        self.assertEqual(por_accion.get("CREATE"), 2)  # reg_caso + reg_viejo

    def test_por_usuario_requiere_el_query_param(self):
        resp = self.client.get(f"{URL}por_usuario/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_por_usuario_devuelve_solo_lo_de_ese_usuario(self):
        resp = self.client.get(f"{URL}por_usuario/", {"usuario_id": self.otro.pk})
        self.assertEqual(_ids(resp), [self.reg_otro_usuario.pk])

    def test_por_tabla_devuelve_solo_esa_tabla(self):
        resp = self.client.get(f"{URL}por_tabla/", {"tabla": "NORMAS"})
        self.assertEqual(_ids(resp), [self.reg_norma.pk])
