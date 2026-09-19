"""
Tests de la papelera de casos: enviar a la papelera (DELETE y PATCH
estado=false), listado GET /api/casos/papelera/, restauración
POST /api/casos/{id}/restaurar/, permisos y línea de tiempo.
"""
import importlib
from datetime import timedelta

from django.apps import apps as django_apps
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.encryption.aes_encryption import encrypt
from modulo_auditoria.models.auditoria import Auditoria
from modulo_casos.models.caso import Caso
from modulo_casos.services.papelera_service import (
    NOTA_ENVIADO_PAPELERA,
    NOTA_RESTAURADO,
    ClienteInactivoError,
    enviar_a_papelera,
    restaurar_desde_papelera,
)
from modulo_casos.services.seguimiento_service import registrar_seguimiento_inicial
from modulo_catalogo.models.rama import RamaDerecho
from modulo_clientes.models.cliente import Cliente
from modulo_usuarios.tests.factories import crear_perfil, crear_rol, crear_usuario


def crear_caso(usuario, rama, cliente, codigo="CASO-PAP0001", titulo="Caso de prueba"):
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


def resultados(response):
    """El listado va paginado ({'results': [...]}) pero se tolera una lista simple."""
    data = response.data
    return data["results"] if isinstance(data, dict) else data


class PapeleraBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = crear_usuario(usuario="admin1", rol=crear_rol("Administrador"))
        cls.abogado = crear_usuario(usuario="abogado1", rol=crear_rol("Abogado"))
        cls.asistente = crear_usuario(usuario="asistente1", rol=crear_rol("Asistente"))
        crear_perfil(cls.abogado, email="abogado1@example.com", nombres="Laura", apellidos="Quispe")
        cls.rama = RamaDerecho.objects.create(nombre="Penal")
        cls.cliente = Cliente.objects.create(
            nombres=encrypt("Ana"), apellidos=encrypt("Rojas")
        )
        cls.caso = crear_caso(cls.abogado, cls.rama, cls.cliente)

    def url(self, nombre, *args):
        return reverse(nombre, args=args)

    def eliminar(self, caso=None, usuario=None):
        self.client.force_authenticate(usuario or self.abogado)
        return self.client.delete(self.url("casos-detail", (caso or self.caso).pk))

    def restaurar(self, caso=None):
        return self.client.post(self.url("casos-restaurar", (caso or self.caso).pk))


class ServicioPapeleraTests(PapeleraBase):
    def test_enviar_a_papelera_guarda_quien_y_cuando_y_deja_nota_en_la_linea_de_tiempo(self):
        enviar_a_papelera(self.caso, self.admin)
        self.caso.refresh_from_db()
        self.assertFalse(self.caso.estado)
        self.assertEqual(self.caso.eliminado_por, self.admin)
        self.assertIsNotNone(self.caso.eliminado_at)
        ultima = self.caso.seguimientos.first()
        self.assertEqual(ultima.nota, NOTA_ENVIADO_PAPELERA)
        self.assertEqual(ultima.usuario, self.admin)
        self.assertEqual(ultima.etapa, self.caso.etapa)

    def test_enviar_dos_veces_no_duplica_la_entrada(self):
        enviar_a_papelera(self.caso, self.admin)
        enviar_a_papelera(self.caso, self.abogado)
        self.caso.refresh_from_db()
        self.assertEqual(self.caso.eliminado_por, self.admin)
        self.assertEqual(self.caso.seguimientos.count(), 2)  # inicial + papelera

    def test_restaurar_reactiva_limpia_datos_y_deja_nota(self):
        enviar_a_papelera(self.caso, self.admin)
        restaurar_desde_papelera(self.caso, self.abogado)
        self.caso.refresh_from_db()
        self.assertTrue(self.caso.estado)
        self.assertIsNone(self.caso.eliminado_at)
        self.assertIsNone(self.caso.eliminado_por)
        ultima = self.caso.seguimientos.first()
        self.assertEqual(ultima.nota, NOTA_RESTAURADO)
        self.assertEqual(ultima.usuario, self.abogado)
        self.assertEqual(self.caso.seguimientos.count(), 3)

    def test_restaurar_conserva_la_etapa(self):
        self.caso.etapa = "juicio"
        self.caso.save(update_fields=["etapa"])
        enviar_a_papelera(self.caso, self.admin)
        restaurar_desde_papelera(self.caso, self.admin)
        self.caso.refresh_from_db()
        self.assertEqual(self.caso.etapa, "juicio")

    def test_no_restaura_si_el_cliente_fue_eliminado(self):
        enviar_a_papelera(self.caso, self.admin)
        Cliente.objects.filter(pk=self.cliente.pk).update(estado=False)
        with self.assertRaises(ClienteInactivoError):
            restaurar_desde_papelera(self.caso, self.admin)
        self.caso.refresh_from_db()
        self.assertFalse(self.caso.estado)
        self.assertEqual(self.caso.seguimientos.count(), 2)


class EliminarCasoTests(PapeleraBase):
    def test_delete_envia_a_la_papelera_y_sale_del_listado(self):
        r = self.eliminar()
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.caso.refresh_from_db()
        self.assertFalse(self.caso.estado)
        self.assertEqual(self.caso.eliminado_por, self.abogado)

        listado = self.client.get(self.url("casos-list"))
        self.assertEqual(resultados(listado), [])
        detalle = self.client.get(self.url("casos-detail", self.caso.pk))
        self.assertEqual(detalle.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_queda_en_auditoria(self):
        self.eliminar()
        self.assertTrue(
            Auditoria.objects.filter(tabla="casos", registro_id=self.caso.pk, accion="DELETE").exists()
        )

    def test_asistente_no_puede_eliminar(self):
        r = self.eliminar(usuario=self.asistente)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.caso.refresh_from_db()
        self.assertTrue(self.caso.estado)

    def test_desactivar_por_patch_tambien_va_a_la_papelera(self):
        self.client.force_authenticate(self.abogado)
        r = self.client.patch(
            self.url("casos-detail", self.caso.pk), {"estado": False}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.caso.refresh_from_db()
        self.assertFalse(self.caso.estado)
        self.assertEqual(self.caso.eliminado_por, self.abogado)
        self.assertIsNotNone(self.caso.eliminado_at)
        self.assertEqual(self.caso.seguimientos.first().nota, NOTA_ENVIADO_PAPELERA)

    def test_patch_de_otros_campos_no_toca_la_papelera(self):
        self.client.force_authenticate(self.abogado)
        r = self.client.patch(
            self.url("casos-detail", self.caso.pk),
            {"titulo": "Título nuevo del caso", "estado": True},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.caso.refresh_from_db()
        self.assertTrue(self.caso.estado)
        self.assertEqual(self.caso.titulo, "Título nuevo del caso")
        self.assertEqual(self.caso.seguimientos.count(), 1)


class ListadoPapeleraTests(PapeleraBase):
    def test_requiere_autenticacion(self):
        r = self.client.get(self.url("casos-papelera"))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_asistente_no_ve_la_papelera(self):
        self.client.force_authenticate(self.asistente)
        r = self.client.get(self.url("casos-papelera"))
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_solo_lista_casos_eliminados(self):
        self.client.force_authenticate(self.abogado)
        self.assertEqual(resultados(self.client.get(self.url("casos-papelera"))), [])
        enviar_a_papelera(self.caso, self.abogado)
        r = self.client.get(self.url("casos-papelera"))
        self.assertEqual([c["codigo"] for c in resultados(r)], ["CASO-PAP0001"])

    def test_incluye_quien_y_cuando_lo_elimino(self):
        enviar_a_papelera(self.caso, self.abogado)
        self.client.force_authenticate(self.admin)
        fila = resultados(self.client.get(self.url("casos-papelera")))[0]
        self.assertEqual(fila["eliminado_por_nombre"], "Laura Quispe")
        self.assertIsNotNone(fila["eliminado_at"])
        self.assertEqual(fila["cliente_nombre"], "Ana Rojas")
        self.assertEqual(fila["etapa"], "registrado")
        self.assertEqual(fila["etapa_display"], "Caso registrado")

    def test_orden_mas_reciente_primero_y_sin_fecha_al_final(self):
        viejo = crear_caso(self.abogado, self.rama, self.cliente, codigo="CASO-PAP0002")
        nuevo = crear_caso(self.abogado, self.rama, self.cliente, codigo="CASO-PAP0003")
        sin_fecha = crear_caso(self.abogado, self.rama, self.cliente, codigo="CASO-PAP0004")
        ahora = timezone.now()
        Caso.objects.filter(pk=viejo.pk).update(estado=False, eliminado_at=ahora - timedelta(days=2))
        Caso.objects.filter(pk=nuevo.pk).update(estado=False, eliminado_at=ahora - timedelta(hours=1))
        Caso.objects.filter(pk=sin_fecha.pk).update(estado=False)  # eliminado antes de la papelera

        self.client.force_authenticate(self.abogado)
        r = self.client.get(self.url("casos-papelera"))
        self.assertEqual(
            [c["codigo"] for c in resultados(r)],
            ["CASO-PAP0003", "CASO-PAP0002", "CASO-PAP0004"],
        )
        self.assertIsNone(resultados(r)[-1]["eliminado_at"])
        self.assertIsNone(resultados(r)[-1]["eliminado_por_nombre"])

    def test_busqueda_por_codigo_o_titulo(self):
        otro = crear_caso(self.abogado, self.rama, self.cliente, codigo="CASO-PAP0002", titulo="Robo agravado")
        enviar_a_papelera(self.caso, self.abogado)
        enviar_a_papelera(otro, self.abogado)
        self.client.force_authenticate(self.abogado)
        r = self.client.get(self.url("casos-papelera"), {"search": "agravado"})
        self.assertEqual([c["codigo"] for c in resultados(r)], ["CASO-PAP0002"])


class RestaurarCasoTests(PapeleraBase):
    def setUp(self):
        enviar_a_papelera(self.caso, self.abogado)

    def test_restaurar_devuelve_el_caso_y_vuelve_al_listado(self):
        self.client.force_authenticate(self.abogado)
        r = self.restaurar()
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["estado"])
        self.assertEqual(r.data["codigo"], "CASO-PAP0001")

        listado = self.client.get(self.url("casos-list"))
        self.assertEqual([c["codigo"] for c in resultados(listado)], ["CASO-PAP0001"])
        papelera = self.client.get(self.url("casos-papelera"))
        self.assertEqual(resultados(papelera), [])

    def test_restaurar_queda_en_la_linea_de_tiempo_y_en_auditoria(self):
        self.client.force_authenticate(self.admin)
        self.restaurar()
        notas = list(self.caso.seguimientos.values_list("nota", flat=True))
        self.assertEqual(notas[0], NOTA_RESTAURADO)
        aud = Auditoria.objects.filter(tabla="casos", registro_id=self.caso.pk, accion="UPDATE").last()
        self.assertEqual(aud.metadata["accion"], "restaurar")

    def test_asistente_no_puede_restaurar(self):
        self.client.force_authenticate(self.asistente)
        r = self.restaurar()
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.caso.refresh_from_db()
        self.assertFalse(self.caso.estado)

    def test_restaurar_un_caso_activo_da_404(self):
        self.client.force_authenticate(self.abogado)
        self.restaurar()
        r = self.restaurar()
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_restaurar_inexistente_da_404(self):
        self.client.force_authenticate(self.abogado)
        r = self.client.post(self.url("casos-restaurar", 999999))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_cliente_eliminado_da_409_y_el_caso_sigue_en_la_papelera(self):
        Cliente.objects.filter(pk=self.cliente.pk).update(estado=False)
        self.client.force_authenticate(self.abogado)
        r = self.restaurar()
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("cliente", r.data["detail"])
        self.caso.refresh_from_db()
        self.assertFalse(self.caso.estado)


class MigracionBackfillTests(PapeleraBase):
    def test_rellena_eliminado_at_y_por_desde_la_auditoria(self):
        migracion = importlib.import_module("modulo_casos.migrations.0005_papelera_casos")
        con_auditoria = crear_caso(self.abogado, self.rama, self.cliente, codigo="CASO-PAP0002")
        sin_auditoria = crear_caso(self.abogado, self.rama, self.cliente, codigo="CASO-PAP0003")
        Caso.objects.filter(pk__in=[con_auditoria.pk, sin_auditoria.pk]).update(estado=False)
        aud = Auditoria.objects.create(
            usuario=self.admin, tabla="casos", accion="DELETE", registro_id=con_auditoria.pk
        )

        migracion.rellenar_eliminacion_desde_auditoria(django_apps, None)

        con_auditoria.refresh_from_db()
        sin_auditoria.refresh_from_db()
        self.assertEqual(con_auditoria.eliminado_at, aud.created_at)
        self.assertEqual(con_auditoria.eliminado_por, self.admin)
        self.assertIsNone(sin_auditoria.eliminado_at)
        self.assertIsNone(sin_auditoria.eliminado_por)
