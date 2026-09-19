"""
Tests de la papelera de clientes: eliminar (con o sin sus casos), listado
GET /api/clientes/papelera/, restauración POST /api/clientes/{id}/restaurar/
(que devuelve los casos eliminados junto con el cliente), permisos y
aviso de duplicado en papelera.
"""
import importlib
from datetime import timedelta

from django.apps import apps as django_apps
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.encryption.aes_encryption import encrypt, hash_lookup, safe_decrypt
from modulo_auditoria.models.auditoria import Auditoria
from modulo_casos.models.caso import Caso
from modulo_casos.services.papelera_service import (
    NOTA_ENVIADO_CON_CLIENTE,
    NOTA_RESTAURADO_CON_CLIENTE,
    enviar_a_papelera,
)
from modulo_casos.services.seguimiento_service import registrar_seguimiento_inicial
from modulo_catalogo.models.rama import RamaDerecho
from modulo_clientes.models.cliente import Cliente
from modulo_clientes.services.papelera_service import (
    ClienteConCasosActivosError,
    enviar_cliente_a_papelera,
    restaurar_cliente,
)
from modulo_usuarios.tests.factories import crear_perfil, crear_rol, crear_usuario


def resultados(response):
    data = response.data
    return data["results"] if isinstance(data, dict) else data


def crear_cliente(nombres="Ana", apellidos="Rojas", telefono=None):
    return Cliente.objects.create(
        nombres=encrypt(nombres),
        apellidos=encrypt(apellidos),
        telefono=encrypt(telefono) if telefono else None,
        telefono_hash=hash_lookup(telefono) if telefono else None,
        nombre_completo_hash=hash_lookup(f"{nombres} {apellidos}"),
    )


class PapeleraClientesBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = crear_usuario(usuario="admin1", rol=crear_rol("Administrador"))
        cls.abogado = crear_usuario(usuario="abogado1", rol=crear_rol("Abogado"))
        cls.asistente = crear_usuario(usuario="asistente1", rol=crear_rol("Asistente"))
        crear_perfil(cls.abogado, email="abogado1@example.com", nombres="Laura", apellidos="Quispe")
        cls.rama = RamaDerecho.objects.create(nombre="Penal")

    def setUp(self):
        self.cliente = crear_cliente("Ana", "Rojas", "71234567")
        self._n = 0

    def crear_caso(self, cliente=None, titulo="Caso de prueba"):
        self._n += 1
        caso = Caso.objects.create(
            codigo=f"CASO-CLI{self._n:04d}",
            titulo=titulo,
            descripcion="Descripción del caso de prueba",
            usuario=self.abogado,
            cliente=cliente or self.cliente,
            rama_detectada=self.rama,
        )
        registrar_seguimiento_inicial(caso, self.abogado)
        return caso

    def url(self, nombre, *args):
        return reverse(nombre, args=args)

    def eliminar(self, cliente=None, usuario=None, eliminar_casos=None):
        self.client.force_authenticate(usuario or self.abogado)
        url = self.url("clientes-detail", (cliente or self.cliente).pk)
        if eliminar_casos is not None:
            url += f"?eliminar_casos={'true' if eliminar_casos else 'false'}"
        return self.client.delete(url)

    def restaurar(self, cliente=None):
        return self.client.post(self.url("clientes-restaurar", (cliente or self.cliente).pk))


class ServicioPapeleraClientesTests(PapeleraClientesBase):
    def test_enviar_sin_casos_guarda_quien_y_cuando(self):
        casos = enviar_cliente_a_papelera(self.cliente, self.admin)
        self.cliente.refresh_from_db()
        self.assertEqual(casos, [])
        self.assertFalse(self.cliente.estado)
        self.assertEqual(self.cliente.eliminado_por, self.admin)
        self.assertIsNotNone(self.cliente.eliminado_at)

    def test_con_casos_activos_y_sin_pedir_eliminarlos_no_cambia_nada(self):
        caso = self.crear_caso()
        with self.assertRaises(ClienteConCasosActivosError) as ctx:
            enviar_cliente_a_papelera(self.cliente, self.admin)
        self.assertEqual(ctx.exception.casos_activos, 1)
        self.cliente.refresh_from_db()
        caso.refresh_from_db()
        self.assertTrue(self.cliente.estado)
        self.assertTrue(caso.estado)

    def test_eliminar_casos_los_envia_a_la_papelera_marcados_con_el_cliente(self):
        caso1, caso2 = self.crear_caso(), self.crear_caso()
        casos = enviar_cliente_a_papelera(self.cliente, self.admin, eliminar_casos=True)
        self.assertEqual({c.pk for c in casos}, {caso1.pk, caso2.pk})
        for caso in (caso1, caso2):
            caso.refresh_from_db()
            self.assertFalse(caso.estado)
            self.assertTrue(caso.eliminado_con_cliente)
            self.assertEqual(caso.eliminado_por, self.admin)
            self.assertEqual(caso.seguimientos.first().nota, NOTA_ENVIADO_CON_CLIENTE)

    def test_enviar_dos_veces_no_repite_nada(self):
        self.crear_caso()
        enviar_cliente_a_papelera(self.cliente, self.admin, eliminar_casos=True)
        self.assertEqual(enviar_cliente_a_papelera(self.cliente, self.abogado, eliminar_casos=True), [])
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.eliminado_por, self.admin)

    def test_restaurar_devuelve_solo_los_casos_eliminados_con_el_cliente(self):
        con_cliente = self.crear_caso(titulo="Se elimina con el cliente")
        antes = self.crear_caso(titulo="Ya estaba eliminado por separado")
        enviar_a_papelera(antes, self.abogado)  # eliminado ANTES, individualmente

        enviar_cliente_a_papelera(self.cliente, self.admin, eliminar_casos=True)
        casos = restaurar_cliente(self.cliente, self.abogado)

        self.assertEqual([c.pk for c in casos], [con_cliente.pk])
        self.cliente.refresh_from_db()
        con_cliente.refresh_from_db()
        antes.refresh_from_db()
        self.assertTrue(self.cliente.estado)
        self.assertIsNone(self.cliente.eliminado_at)
        self.assertIsNone(self.cliente.eliminado_por)
        self.assertTrue(con_cliente.estado)
        self.assertFalse(con_cliente.eliminado_con_cliente)
        self.assertEqual(con_cliente.seguimientos.first().nota, NOTA_RESTAURADO_CON_CLIENTE)
        self.assertFalse(antes.estado)  # sigue en la papelera de casos

    def test_restaurar_un_cliente_activo_no_hace_nada(self):
        self.assertEqual(restaurar_cliente(self.cliente, self.admin), [])

    def test_todo_ocurre_en_una_transaccion(self):
        caso = self.crear_caso()
        from unittest.mock import patch

        with patch("modulo_clientes.services.papelera_service.enviar_a_papelera", side_effect=RuntimeError("falla")):
            with self.assertRaises(RuntimeError):
                enviar_cliente_a_papelera(self.cliente, self.admin, eliminar_casos=True)
        self.cliente.refresh_from_db()
        caso.refresh_from_db()
        self.assertTrue(self.cliente.estado)
        self.assertTrue(caso.estado)


class EliminarClienteTests(PapeleraClientesBase):
    def test_delete_sin_casos_envia_a_la_papelera_y_sale_del_listado(self):
        r = self.eliminar()
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.estado)
        self.assertEqual(self.cliente.eliminado_por, self.abogado)
        self.assertEqual(resultados(self.client.get(self.url("clientes-list"))), [])
        self.assertEqual(self.client.get(self.url("clientes-detail", self.cliente.pk)).status_code, 404)

    def test_delete_con_casos_activos_responde_400_con_el_detalle_para_ofrecer_eliminarlos(self):
        self.crear_caso()
        self.crear_caso()
        r = self.eliminar()
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data["code"], "cliente_con_casos_activos")
        self.assertEqual(r.data["casos_activos"], 2)
        self.assertIn("casos activos", r.data["detail"])
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.estado)

    def test_delete_con_eliminar_casos_envia_cliente_y_casos_a_la_papelera(self):
        caso = self.crear_caso()
        r = self.eliminar(eliminar_casos=True)
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.cliente.refresh_from_db()
        caso.refresh_from_db()
        self.assertFalse(self.cliente.estado)
        self.assertFalse(caso.estado)
        self.assertTrue(caso.eliminado_con_cliente)

    def test_eliminar_casos_false_se_comporta_como_no_pasarlo(self):
        self.crear_caso()
        self.assertEqual(self.eliminar(eliminar_casos=False).status_code, status.HTTP_400_BAD_REQUEST)

    def test_los_casos_eliminados_con_el_cliente_aparecen_en_la_papelera_de_casos_marcados(self):
        self.crear_caso()
        self.eliminar(eliminar_casos=True)
        r = self.client.get(self.url("casos-papelera"))
        self.assertTrue(resultados(r)[0]["eliminado_con_cliente"])

    def test_los_casos_de_otro_cliente_no_se_tocan(self):
        otro = crear_cliente("Luis", "Mamani")
        ajeno = self.crear_caso(cliente=otro)
        self.crear_caso()
        self.eliminar(eliminar_casos=True)
        ajeno.refresh_from_db()
        self.assertTrue(ajeno.estado)

    def test_asistente_no_puede_eliminar(self):
        r = self.eliminar(usuario=self.asistente)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.estado)

    def test_queda_en_auditoria_el_cliente_y_cada_caso(self):
        caso = self.crear_caso()
        self.eliminar(eliminar_casos=True)
        aud_cliente = Auditoria.objects.get(tabla="clientes", registro_id=self.cliente.pk, accion="DELETE")
        self.assertEqual(aud_cliente.metadata["casos_eliminados"], [caso.pk])
        aud_caso = Auditoria.objects.get(tabla="casos", registro_id=caso.pk, accion="DELETE")
        self.assertEqual(aud_caso.metadata["motivo"], "cliente_eliminado")
        self.assertEqual(aud_caso.metadata["cliente_id"], self.cliente.pk)

    def test_desactivar_por_patch_tambien_va_a_la_papelera(self):
        self.client.force_authenticate(self.abogado)
        r = self.client.patch(self.url("clientes-detail", self.cliente.pk), {"estado": False}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.estado)
        self.assertEqual(self.cliente.eliminado_por, self.abogado)
        self.assertIsNotNone(self.cliente.eliminado_at)

    def test_desactivar_por_patch_respeta_la_regla_de_los_casos_activos(self):
        self.crear_caso()
        self.client.force_authenticate(self.abogado)
        r = self.client.patch(
            self.url("clientes-detail", self.cliente.pk),
            {"nombres": "Otro", "estado": False}, format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("estado", r.data)
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.estado)
        # el rechazo revierte también el resto de los cambios del PATCH
        self.assertEqual(safe_decrypt(self.cliente.nombres), "Ana")


class ListadoPapeleraClientesTests(PapeleraClientesBase):
    def test_requiere_autenticacion(self):
        self.assertEqual(self.client.get(self.url("clientes-papelera")).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_asistente_no_ve_la_papelera(self):
        self.client.force_authenticate(self.asistente)
        self.assertEqual(self.client.get(self.url("clientes-papelera")).status_code, status.HTTP_403_FORBIDDEN)

    def test_solo_lista_clientes_eliminados_con_quien_y_cuando(self):
        self.client.force_authenticate(self.abogado)
        self.assertEqual(resultados(self.client.get(self.url("clientes-papelera"))), [])
        enviar_cliente_a_papelera(self.cliente, self.abogado)
        fila = resultados(self.client.get(self.url("clientes-papelera")))[0]
        self.assertEqual(fila["id"], self.cliente.pk)
        self.assertEqual(fila["nombre_completo"], "Ana Rojas")
        self.assertEqual(fila["telefono"], "71234567")
        self.assertEqual(fila["eliminado_por_nombre"], "Laura Quispe")
        self.assertIsNotNone(fila["eliminado_at"])
        self.assertEqual(fila["casos_para_restaurar"], 0)

    def test_casos_para_restaurar_cuenta_solo_los_eliminados_con_el_cliente(self):
        self.crear_caso()
        self.crear_caso()
        antes = self.crear_caso()
        enviar_a_papelera(antes, self.abogado)
        enviar_cliente_a_papelera(self.cliente, self.abogado, eliminar_casos=True)
        self.client.force_authenticate(self.admin)
        fila = resultados(self.client.get(self.url("clientes-papelera")))[0]
        self.assertEqual(fila["casos_para_restaurar"], 2)

    def test_orden_mas_reciente_primero_y_sin_fecha_al_final(self):
        viejo = crear_cliente("Viejo", "Uno")
        nuevo = crear_cliente("Nuevo", "Dos")
        sin_fecha = crear_cliente("Antiguo", "Tres")
        ahora = timezone.now()
        Cliente.objects.filter(pk=viejo.pk).update(estado=False, eliminado_at=ahora - timedelta(days=2))
        Cliente.objects.filter(pk=nuevo.pk).update(estado=False, eliminado_at=ahora - timedelta(hours=1))
        Cliente.objects.filter(pk=sin_fecha.pk).update(estado=False)
        self.client.force_authenticate(self.abogado)
        filas = resultados(self.client.get(self.url("clientes-papelera")))
        self.assertEqual([f["nombre_completo"] for f in filas], ["Nuevo Dos", "Viejo Uno", "Antiguo Tres"])
        self.assertIsNone(filas[-1]["eliminado_at"])
        self.assertIsNone(filas[-1]["eliminado_por_nombre"])

    def test_busqueda_por_nombre_o_apellido(self):
        otro = crear_cliente("Luis", "Mamani")
        enviar_cliente_a_papelera(self.cliente, self.abogado)
        enviar_cliente_a_papelera(otro, self.abogado)
        self.client.force_authenticate(self.abogado)
        r = self.client.get(self.url("clientes-papelera"), {"search": "mamani"})
        self.assertEqual([f["nombre_completo"] for f in resultados(r)], ["Luis Mamani"])
        r = self.client.get(self.url("clientes-papelera"), {"search": "x"})  # < 2 caracteres: se ignora
        self.assertEqual(len(resultados(r)), 2)


class RestaurarClienteTests(PapeleraClientesBase):
    def setUp(self):
        super().setUp()
        self.caso_con = self.crear_caso(titulo="Se elimina con el cliente")
        self.caso_antes = self.crear_caso(titulo="Eliminado antes, por separado")
        enviar_a_papelera(self.caso_antes, self.abogado)
        enviar_cliente_a_papelera(self.cliente, self.abogado, eliminar_casos=True)

    def test_restaurar_devuelve_el_cliente_y_sus_casos(self):
        self.client.force_authenticate(self.abogado)
        r = self.restaurar()
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["estado"])
        self.assertEqual(r.data["nombre_completo"], "Ana Rojas")
        self.assertEqual(r.data["casos_restaurados"], 1)

        self.caso_con.refresh_from_db()
        self.caso_antes.refresh_from_db()
        self.assertTrue(self.caso_con.estado)
        self.assertFalse(self.caso_antes.estado)
        self.assertEqual(resultados(self.client.get(self.url("clientes-papelera"))), [])
        activos = self.client.get(self.url("clientes-list"))
        self.assertEqual([c["id"] for c in resultados(activos)], [self.cliente.pk])

    def test_el_caso_eliminado_antes_se_puede_restaurar_una_vez_activo_el_cliente(self):
        self.client.force_authenticate(self.abogado)
        # Con el cliente eliminado no se puede: 409 con la indicación de restaurar primero al cliente
        r = self.client.post(self.url("casos-restaurar", self.caso_antes.pk))
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("Restaura primero al cliente", r.data["detail"])
        # Restaurado el cliente, ya se puede
        self.restaurar()
        r = self.client.post(self.url("casos-restaurar", self.caso_antes.pk))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_restaurar_queda_en_auditoria_del_cliente_y_de_cada_caso(self):
        self.client.force_authenticate(self.admin)
        self.restaurar()
        aud = Auditoria.objects.filter(tabla="clientes", registro_id=self.cliente.pk, accion="UPDATE").last()
        self.assertEqual(aud.metadata["accion"], "restaurar")
        self.assertEqual(aud.metadata["casos_restaurados"], [self.caso_con.pk])
        aud_caso = Auditoria.objects.filter(tabla="casos", registro_id=self.caso_con.pk, accion="UPDATE").last()
        self.assertEqual(aud_caso.metadata["motivo"], "cliente_restaurado")

    def test_asistente_no_puede_restaurar(self):
        self.client.force_authenticate(self.asistente)
        self.assertEqual(self.restaurar().status_code, status.HTTP_403_FORBIDDEN)
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.estado)

    def test_restaurar_un_cliente_activo_o_inexistente_da_404(self):
        self.client.force_authenticate(self.abogado)
        self.restaurar()
        self.assertEqual(self.restaurar().status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.client.post(self.url("clientes-restaurar", 999999)).status_code, status.HTTP_404_NOT_FOUND
        )


class DuplicadosConClientesEnPapeleraTests(PapeleraClientesBase):
    def crear_via_api(self, **datos):
        self.client.force_authenticate(self.abogado)
        return self.client.post(self.url("clientes-list"), datos, format="json")

    def test_telefono_de_un_cliente_en_la_papelera_avisa_donde_recuperarlo(self):
        enviar_cliente_a_papelera(self.cliente, self.abogado)
        r = self.crear_via_api(nombres="Otra", apellidos="Persona", telefono="71234567")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("papelera", str(r.data["telefono"]))

    def test_nombre_de_un_cliente_en_la_papelera_avisa_donde_recuperarlo(self):
        enviar_cliente_a_papelera(self.cliente, self.abogado)
        r = self.crear_via_api(nombres="Ana", apellidos="Rojas", telefono="61234567")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("papelera", str(r.data["nombres"]))

    def test_duplicado_con_cliente_activo_no_menciona_la_papelera(self):
        r = self.crear_via_api(nombres="Otra", apellidos="Persona", telefono="71234567")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("papelera", str(r.data["telefono"]))


class MigracionBackfillClientesTests(PapeleraClientesBase):
    def test_rellena_eliminado_at_y_por_desde_la_auditoria(self):
        migracion = importlib.import_module("modulo_clientes.migrations.0006_papelera_clientes")
        con_auditoria = crear_cliente("Con", "Auditoria")
        sin_auditoria = crear_cliente("Sin", "Auditoria")
        Cliente.objects.filter(pk__in=[con_auditoria.pk, sin_auditoria.pk]).update(estado=False)
        aud = Auditoria.objects.create(
            usuario=self.admin, tabla="clientes", accion="DELETE", registro_id=con_auditoria.pk
        )

        migracion.rellenar_eliminacion_desde_auditoria(django_apps, None)

        con_auditoria.refresh_from_db()
        sin_auditoria.refresh_from_db()
        self.assertEqual(con_auditoria.eliminado_at, aud.created_at)
        self.assertEqual(con_auditoria.eliminado_por, self.admin)
        self.assertIsNone(sin_auditoria.eliminado_at)
        self.assertIsNone(sin_auditoria.eliminado_por)
