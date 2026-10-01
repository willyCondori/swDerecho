"""
Tests de GET /api/dashboard/resumen/.

Cubren: totales básicos, conteo por etapa/rama/estado_analisis, y que
un Asistente (sin ve_todo) nunca vea datos de casos ajenos ni las
secciones de bufete completo (casos_por_usuario, normas_mas_consultadas).
"""
from rest_framework import status
from rest_framework.test import APITestCase

from modulo_casos.models.caso import Caso, EstadoAnalisis
from modulo_casos.models.etapas import EtapaCaso
from modulo_catalogo.models.articulo import Articulo
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama import RamaDerecho
from modulo_clientes.models.cliente import Cliente
from modulo_usuarios.tests.factories import crear_rol, crear_usuario


class DashboardResumenTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.abogado_a = crear_usuario(usuario="abogado.dash.a", rol=crear_rol("Abogado"))
        cls.abogado_b = crear_usuario(usuario="abogado.dash.b", rol=crear_rol("Abogado"))
        cls.asistente = crear_usuario(usuario="asistente.dash", rol=crear_rol("Asistente"))

        cls.cliente = Cliente.objects.create(nombres="Cliente", apellidos="Dashboard")
        cls.rama_penal = RamaDerecho.objects.create(nombre="Penal dashboard test")
        cls.rama_civil = RamaDerecho.objects.create(nombre="Civil dashboard test")
        cls.norma = Norma.objects.create(nombre="Norma dashboard test")
        cls.articulo = Articulo.objects.create(
            numero_articulo="D1", titulo="Art. D1", contenido="contenido",
            norma=cls.norma, rama=cls.rama_penal, frecuencia_historica=7,
        )

        # 2 casos del abogado A (uno en papelera), 1 del abogado B.
        cls.caso_a1 = Caso.objects.create(
            codigo="DASH-A1", titulo="Caso A1", usuario=cls.abogado_a, cliente=cls.cliente,
            rama_detectada=cls.rama_penal, etapa=EtapaCaso.REGISTRADO,
            estado_analisis=EstadoAnalisis.COMPLETADO,
        )
        cls.caso_a2 = Caso.objects.create(
            codigo="DASH-A2", titulo="Caso A2 (papelera)", usuario=cls.abogado_a, cliente=cls.cliente,
            rama_detectada=cls.rama_civil, etapa=EtapaCaso.CERRADO, estado=False,
        )
        cls.caso_b1 = Caso.objects.create(
            codigo="DASH-B1", titulo="Caso B1", usuario=cls.abogado_b, cliente=cls.cliente,
            rama_detectada=cls.rama_penal, etapa=EtapaCaso.AUDIENCIAS,
            estado_analisis=EstadoAnalisis.PROCESANDO,
        )

    def test_requiere_autenticacion(self):
        r = self.client.get("/api/dashboard/resumen/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_abogado_ve_el_bufete_completo(self):
        self.client.force_authenticate(self.abogado_a)
        r = self.client.get("/api/dashboard/resumen/")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)

        self.assertEqual(r.data["totales"]["casos_activos"], 2)      # A1 + B1 (A2 está en papelera)
        self.assertEqual(r.data["totales"]["casos_en_papelera"], 1)  # A2
        self.assertEqual(r.data["totales"]["clientes_activos"], 1)
        self.assertIn("normas_activas", r.data["totales"])
        self.assertIn("usuarios_activos", r.data["totales"])

        por_etapa = {f["etapa"]: f["cantidad"] for f in r.data["casos_por_etapa"]}
        self.assertEqual(por_etapa[EtapaCaso.REGISTRADO], 1)   # A1
        self.assertEqual(por_etapa[EtapaCaso.AUDIENCIAS], 1)   # B1
        self.assertEqual(por_etapa[EtapaCaso.CERRADO], 0)      # A2 está en papelera, no cuenta

        por_rama = {f["rama"]: f["cantidad"] for f in r.data["casos_por_rama"]}
        self.assertEqual(por_rama.get(self.rama_penal.nombre), 2)   # A1 + B1
        self.assertNotIn(self.rama_civil.nombre, por_rama)          # solo A2, que está en papelera

        por_usuario = {f["usuario"]: f["cantidad"] for f in r.data["casos_por_usuario"]}
        self.assertEqual(por_usuario.get(self.abogado_a.usuario), 1)
        self.assertEqual(por_usuario.get(self.abogado_b.usuario), 1)

        self.assertEqual(len(r.data["normas_mas_consultadas"]), 1)
        self.assertEqual(r.data["normas_mas_consultadas"][0]["numero_articulo"], "D1")
        self.assertEqual(r.data["normas_mas_consultadas"][0]["frecuencia"], 7)

    def test_asistente_solo_ve_sus_propios_casos_y_sin_secciones_de_bufete(self):
        self.client.force_authenticate(self.asistente)
        r = self.client.get("/api/dashboard/resumen/")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)

        # El asistente no es dueño de ningún caso de los creados en setUp.
        self.assertEqual(r.data["totales"]["casos_activos"], 0)
        self.assertEqual(r.data["totales"]["casos_en_papelera"], 0)
        self.assertNotIn("clientes_activos", r.data["totales"])

        self.assertEqual(r.data["casos_por_usuario"], [])
        self.assertEqual(r.data["casos_por_mes"], [])
        self.assertEqual(r.data["normas_mas_consultadas"], [])

    def test_estado_analisis_cuenta_correctamente(self):
        self.client.force_authenticate(self.abogado_a)
        r = self.client.get("/api/dashboard/resumen/")
        por_estado = {f["estado"]: f["cantidad"] for f in r.data["estado_analisis"]}
        self.assertEqual(por_estado[EstadoAnalisis.COMPLETADO], 1)  # A1
        self.assertEqual(por_estado[EstadoAnalisis.PROCESANDO], 1)  # B1
