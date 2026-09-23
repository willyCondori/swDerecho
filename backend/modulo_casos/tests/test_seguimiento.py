"""
Tests del seguimiento de casos: etapa actual + línea de tiempo
(SeguimientoCaso), endpoints /api/casos/etapas/, /seguimiento/ y
/cambiar_etapa/, y creación de la entrada inicial al registrar un caso.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.encryption.aes_encryption import encrypt
from modulo_auditoria.models.auditoria import Auditoria
from modulo_casos.models.caso import Caso
from modulo_casos.models.etapas import EtapaCaso
from modulo_casos.models.seguimiento import SeguimientoCaso
from modulo_casos.services.seguimiento_service import (
    registrar_seguimiento,
    registrar_seguimiento_inicial,
)
from modulo_catalogo.models.rama import RamaDerecho
from modulo_clientes.models.cliente import Cliente
from modulo_usuarios.tests.factories import crear_perfil, crear_rol, crear_usuario


def crear_caso(usuario, rama, cliente, codigo="CASO-TEST0001", titulo="Caso de prueba"):
    caso = Caso.objects.create(
        codigo=codigo,
        titulo=titulo,
        descripcion="Descripción del caso de prueba",
        usuario=usuario,
        cliente=cliente,
        rama_detectada=rama,
    )
    registrar_seguimiento_inicial(caso, usuario)
    return caso


class SeguimientoBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = crear_usuario(usuario="admin1", rol=crear_rol("Administrador"))
        cls.abogado = crear_usuario(usuario="abogado1", rol=crear_rol("Abogado"))
        cls.asistente = crear_usuario(usuario="asistente1", rol=crear_rol("Asistente"))
        cls.rama = RamaDerecho.objects.create(nombre="Penal")
        cls.cliente = Cliente.objects.create(
            nombres=encrypt("Ana"), apellidos=encrypt("Rojas")
        )
        cls.caso = crear_caso(cls.abogado, cls.rama, cls.cliente)

    def url(self, nombre, *args):
        return reverse(nombre, args=args)


class ServicioSeguimientoTests(SeguimientoBase):
    def test_caso_nuevo_arranca_registrado_con_entrada_inicial(self):
        self.assertEqual(self.caso.etapa, EtapaCaso.REGISTRADO)
        self.assertIsNotNone(self.caso.etapa_actualizada_at)
        entradas = list(self.caso.seguimientos.all())
        self.assertEqual(len(entradas), 1)
        self.assertEqual(entradas[0].etapa, EtapaCaso.REGISTRADO)
        self.assertIsNone(entradas[0].etapa_anterior)

    def test_registrar_seguimiento_actualiza_caso_y_guarda_etapa_anterior(self):
        seg = registrar_seguimiento(
            self.caso, EtapaCaso.INVESTIGACION_PRELIMINAR, self.abogado, "  Se inició la investigación  "
        )
        self.caso.refresh_from_db()
        self.assertEqual(self.caso.etapa, EtapaCaso.INVESTIGACION_PRELIMINAR)
        self.assertEqual(self.caso.etapa_actualizada_at, seg.created_at)
        self.assertEqual(seg.etapa_anterior, EtapaCaso.REGISTRADO)
        self.assertEqual(seg.nota, "Se inició la investigación")
        self.assertEqual(seg.usuario, self.abogado)

    def test_cada_cambio_agrega_una_entrada(self):
        registrar_seguimiento(self.caso, EtapaCaso.EN_ANALISIS, self.abogado)
        registrar_seguimiento(self.caso, EtapaCaso.AUDIENCIAS, self.abogado)
        self.assertEqual(self.caso.seguimientos.count(), 3)  # inicial + 2


class EtapasEndpointTests(SeguimientoBase):
    def test_lista_etapas_en_orden(self):
        self.client.force_authenticate(self.asistente)
        r = self.client.get(self.url("casos-etapas"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data[0]["value"], "registrado")
        self.assertEqual(r.data[-1]["value"], "cerrado")
        self.assertEqual([e["orden"] for e in r.data], list(range(1, len(r.data) + 1)))

    def test_requiere_autenticacion(self):
        r = self.client.get(self.url("casos-etapas"))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


class CambiarEtapaEndpointTests(SeguimientoBase):
    def cambiar(self, etapa, nota=None, caso=None):
        data = {"etapa": etapa}
        if nota is not None:
            data["nota"] = nota
        return self.client.post(
            self.url("casos-cambiar-etapa", (caso or self.caso).pk), data, format="json"
        )

    def test_abogado_cambia_etapa_y_queda_historial(self):
        self.client.force_authenticate(self.abogado)
        r = self.cambiar("investigacion_preliminar", "Se presentó la denuncia ante la FELCC")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["etapa"], "investigacion_preliminar")
        self.assertEqual(r.data["etapa_display"], "Investigación preliminar")
        self.assertEqual(r.data["seguimiento"]["etapa_anterior"], "registrado")
        self.caso.refresh_from_db()
        self.assertEqual(self.caso.etapa, EtapaCaso.INVESTIGACION_PRELIMINAR)
        self.assertEqual(self.caso.seguimientos.count(), 2)

    def test_administrador_tambien_puede(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.cambiar("en_analisis").status_code, status.HTTP_201_CREATED)

    def test_asistente_no_puede_cambiar_etapa(self):
        self.client.force_authenticate(self.asistente)
        r = self.cambiar("en_analisis")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.caso.refresh_from_db()
        self.assertEqual(self.caso.etapa, EtapaCaso.REGISTRADO)
        self.assertEqual(self.caso.seguimientos.count(), 1)

    def test_etapa_invalida_es_rechazada(self):
        self.client.force_authenticate(self.abogado)
        r = self.cambiar("inventada")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("etapa", r.data)

    def test_falta_etapa(self):
        self.client.force_authenticate(self.abogado)
        r = self.client.post(self.url("casos-cambiar-etapa", self.caso.pk), {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_misma_etapa_sin_nota_es_rechazada(self):
        self.client.force_authenticate(self.abogado)
        r = self.cambiar("registrado")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.caso.seguimientos.count(), 1)

    def test_misma_etapa_con_nota_registra_actualizacion(self):
        self.client.force_authenticate(self.abogado)
        r = self.cambiar("registrado", "Se recibió documentación adicional del cliente")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["seguimiento"]["etapa_anterior"], "registrado")
        self.assertEqual(self.caso.seguimientos.count(), 2)
    def test_registrado_con_nota_tambien_es_rechazada(self):
        # "Caso registrado" no se puede volver a elegir aunque se le
        # agregue una nota: es la etapa inicial automática y una segunda
        # entrada no aportaría nada a la trazabilidad (ver
        # CambiarEtapaSerializer.validate). Distinto de cualquier otra
        # etapa, donde repetirla CON nota sí está permitido — ver
        # test_misma_etapa_con_nota_registra_actualizacion más abajo.
        self.client.force_authenticate(self.abogado)
        r = self.cambiar("registrado", "Se recibió documentación adicional del cliente")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("etapa", r.data)
        self.assertEqual(self.caso.seguimientos.count(), 1)

    def test_misma_etapa_con_nota_registra_actualizacion(self):
        self.client.force_authenticate(self.abogado)
        self.cambiar("en_analisis")  # sale de "registrado" para probar el caso general

        r = self.cambiar("en_analisis", "Se recibió documentación adicional del cliente")

        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["seguimiento"]["etapa_anterior"], "en_analisis")
        self.assertEqual(self.caso.seguimientos.count(), 3)

    def test_nota_demasiado_larga(self):
        self.client.force_authenticate(self.abogado)
        r = self.cambiar("en_analisis", "x" * 2001)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nota", r.data)

    def test_caso_inactivo_no_se_puede_modificar(self):
        self.caso.estado = False
        self.caso.save(update_fields=["estado"])
        self.client.force_authenticate(self.abogado)
        self.assertEqual(self.cambiar("en_analisis").status_code, status.HTTP_404_NOT_FOUND)

    def test_queda_registrado_en_auditoria(self):
        self.client.force_authenticate(self.abogado)
        self.cambiar("en_analisis")
        aud = Auditoria.objects.filter(tabla="casos", registro_id=self.caso.pk, accion="UPDATE").last()
        self.assertIsNotNone(aud)
        self.assertEqual(aud.metadata["accion"], "cambiar_etapa")
        self.assertEqual(aud.metadata["etapa_anterior"], "registrado")
        self.assertEqual(aud.metadata["etapa_nueva"], "en_analisis")

    def test_patch_no_permite_saltarse_el_historial(self):
        self.client.force_authenticate(self.abogado)
        r = self.client.patch(
            self.url("casos-detail", self.caso.pk), {"etapa": "cerrado"}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.caso.refresh_from_db()
        self.assertEqual(self.caso.etapa, EtapaCaso.REGISTRADO)


class LineaDeTiempoEndpointTests(SeguimientoBase):
    def test_devuelve_historial_mas_reciente_primero_con_autor(self):
        crear_perfil(self.abogado, email="abogado1@example.com", nombres="María", apellidos="Quispe")
        registrar_seguimiento(self.caso, EtapaCaso.EN_ANALISIS, self.abogado, "Primer análisis")
        registrar_seguimiento(self.caso, EtapaCaso.AUDIENCIAS, self.admin, "Audiencia fijada")

        self.client.force_authenticate(self.asistente)  # el asistente puede leer
        r = self.client.get(self.url("casos-seguimiento", self.caso.pk))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual([e["etapa"] for e in r.data], ["audiencias", "en_analisis", "registrado"])
        self.assertEqual(r.data[0]["usuario_nombre"], "admin1")  # sin perfil: cae al usuario
        self.assertEqual(r.data[1]["usuario_nombre"], "María Quispe")
        self.assertEqual(r.data[0]["etapa_display"], "En audiencias")
        self.assertEqual(r.data[0]["etapa_anterior_display"], "En análisis y estrategia")
        self.assertIsNone(r.data[2]["etapa_anterior_display"])

    def test_caso_inexistente(self):
        self.client.force_authenticate(self.abogado)
        self.assertEqual(
            self.client.get(self.url("casos-seguimiento", 999999)).status_code,
            status.HTTP_404_NOT_FOUND,
        )


class ListadoYDetalleTests(SeguimientoBase):
    def test_detalle_y_listado_incluyen_etapa(self):
        registrar_seguimiento(self.caso, EtapaCaso.JUICIO, self.abogado)
        self.client.force_authenticate(self.abogado)

        detalle = self.client.get(self.url("casos-detail", self.caso.pk))
        self.assertEqual(detalle.data["etapa"], "juicio")
        self.assertEqual(detalle.data["etapa_display"], "En juicio (etapa probatoria)")
        self.assertIsNotNone(detalle.data["etapa_actualizada_at"])

        listado = self.client.get(self.url("casos-list"))
        self.assertEqual(listado.data["results"][0]["etapa"], "juicio")

    def test_filtro_por_etapa(self):
        otro = crear_caso(self.abogado, self.rama, self.cliente, codigo="CASO-TEST0002", titulo="Otro caso")
        registrar_seguimiento(otro, EtapaCaso.SENTENCIA, self.abogado)
        self.client.force_authenticate(self.abogado)

        r = self.client.get(self.url("casos-list"), {"etapa": "sentencia"})
        self.assertEqual([c["codigo"] for c in r.data["results"]], ["CASO-TEST0002"])
        r = self.client.get(self.url("casos-list"), {"etapa": "registrado"})
        self.assertEqual([c["codigo"] for c in r.data["results"]], ["CASO-TEST0001"])


class CrearCasoGeneraEntradaInicialTests(SeguimientoBase):
    def test_crear_caso_crea_entrada_inicial(self):
        self.client.force_authenticate(self.abogado)
        r = self.client.post(
            self.url("casos-list"),
            {
                "titulo": "Nuevo caso de prueba",
                "descripcion": "Descripción suficiente del caso",
                "cliente_id": self.cliente.pk,
                "rama_detectada_id": self.rama.pk,
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["etapa"], "registrado")
        caso = Caso.objects.get(pk=r.data["id"])
        entradas = SeguimientoCaso.objects.filter(caso=caso)
        self.assertEqual(entradas.count(), 1)
        self.assertEqual(entradas[0].usuario, self.abogado)

    def test_crear_con_cliente_crea_entrada_inicial(self):
        self.client.force_authenticate(self.abogado)
        r = self.client.post(
            self.url("casos-crear-con-cliente"),
            {
                "nombres": "Luis",
                "apellidos": "Mamani",
                "titulo": "Caso con cliente nuevo",
                "descripcion": "Descripción suficiente del caso",
                "rama_detectada_id": self.rama.pk,
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(SeguimientoCaso.objects.filter(caso_id=r.data["id"]).count(), 1)
