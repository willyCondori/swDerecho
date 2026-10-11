"""
Búsqueda de clientes por nombre sobre datos cifrados (índice de prefijos con
HMAC, ver modulo_clientes.services.busqueda_service): coincidencias, reindexado
automático al crear/editar, GET /api/clientes/buscar/, papelera y backfill.
"""
from unittest import mock

from django.apps import apps as django_apps
from django.core.management import call_command
from rest_framework import status

from core.encryption import aes_encryption
from modulo_clientes.models.cliente import Cliente
from modulo_clientes.models.cliente_busqueda_token import ClienteBusquedaToken
from modulo_clientes.services.busqueda_service import (
    filtrar_por_busqueda,
    hashes_de_indexado,
    palabras,
    reindexar_cliente,
)
from modulo_clientes.services.papelera_service import enviar_cliente_a_papelera
from modulo_clientes.tests.test_papelera_clientes import (
    PapeleraClientesBase,
    crear_cliente,
    resultados,
)


def nombres_de(queryset):
    from core.encryption.aes_encryption import safe_decrypt
    return sorted(
        f"{safe_decrypt(c.nombres)} {safe_decrypt(c.apellidos)}" for c in queryset
    )


class PalabrasYHashesTests(PapeleraClientesBase):
    def test_palabras_sin_tildes_ni_mayusculas(self):
        self.assertEqual(palabras("Muñoz-Pérez  DE la Cruz"), ["munoz", "perez", "de", "la", "cruz"])

    def test_indexa_prefijos_de_2_o_mas_letras(self):
        # "ana" -> "an", "ana"  (1 sola letra no se indexa)
        self.assertEqual(len(hashes_de_indexado("Ana", "")), 2)
        self.assertEqual(hashes_de_indexado("", ""), set())

    def test_los_hashes_son_hmac_hexadecimales_y_no_el_texto(self):
        hashes = hashes_de_indexado("Ana", "Rojas")
        for h in hashes:
            self.assertEqual(len(h), 64)
            int(h, 16)  # hex válido
        self.assertTrue({"an", "ana", "ro", "roj", "rojas"}.isdisjoint(hashes))


class FiltrarPorBusquedaTests(PapeleraClientesBase):
    def setUp(self):
        super().setUp()  # Ana Rojas
        self.luis = crear_cliente("Luis", "Mamani Quispe")
        self.susana = crear_cliente("Susana", "Muñoz")
        self.juan = crear_cliente("Juan Carlos", "Pérez")

    def buscar(self, texto):
        return nombres_de(filtrar_por_busqueda(Cliente.objects.all(), texto))

    def test_prefijo_de_nombre_o_apellido(self):
        self.assertEqual(self.buscar("mam"), ["Luis Mamani Quispe"])
        self.assertEqual(self.buscar("LU"), ["Luis Mamani Quispe"])
        self.assertEqual(self.buscar("quis"), ["Luis Mamani Quispe"])

    def test_no_encuentra_por_mitad_de_palabra(self):
        # Cambio respecto de la búsqueda anterior ("contiene"): "ana" ya no
        # encuentra a "Susana", solo a quien tenga una palabra que EMPIECE así.
        self.assertEqual(self.buscar("ana"), ["Ana Rojas"])

    def test_ignora_tildes_y_mayusculas(self):
        self.assertEqual(self.buscar("munoz"), ["Susana Muñoz"])
        self.assertEqual(self.buscar("perez"), ["Juan Carlos Pérez"])
        self.assertEqual(self.buscar("PÉREZ"), ["Juan Carlos Pérez"])

    def test_varias_palabras_entre_nombres_y_apellidos(self):
        self.assertEqual(self.buscar("juan perez"), ["Juan Carlos Pérez"])
        self.assertEqual(self.buscar("carlos ju"), ["Juan Carlos Pérez"])
        self.assertEqual(self.buscar("juan rojas"), [])  # AND: las dos deben coincidir

    def test_palabra_repetida_no_duplica_resultados(self):
        self.assertEqual(self.buscar("mam mam"), ["Luis Mamani Quispe"])

    def test_sin_palabras_validas_no_devuelve_nada(self):
        self.assertEqual(self.buscar("a"), [])
        self.assertEqual(self.buscar("   "), [])
        self.assertEqual(self.buscar("a b"), [])


class IndiceSeMantieneSoloTests(PapeleraClientesBase):
    def tokens(self, cliente):
        return set(ClienteBusquedaToken.objects.filter(cliente=cliente).values_list("token_hash", flat=True))

    def test_se_indexa_al_crear(self):
        self.assertEqual(self.tokens(self.cliente), hashes_de_indexado("Ana", "Rojas"))

    def test_se_reindexa_al_editar_por_la_api(self):
        self.client.force_authenticate(self.abogado)
        r = self.client.patch(self.url("clientes-detail", self.cliente.public_id), {"apellidos": "Vargas"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertEqual(self.tokens(self.cliente), hashes_de_indexado("Ana", "Vargas"))
        r = self.client.get(self.url("clientes-buscar"), {"q": "rojas"})
        self.assertEqual(r.data, [])
        r = self.client.get(self.url("clientes-buscar"), {"q": "varg"})
        self.assertEqual([c["nombre_completo"] for c in r.data], ["Ana Vargas"])

    def test_se_indexa_al_crear_por_la_api(self):
        self.client.force_authenticate(self.abogado)
        r = self.client.post(
            self.url("clientes-list"),
            {"nombres": "Rosa", "apellidos": "Choque", "telefono": "76543210"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        r = self.client.get(self.url("clientes-buscar"), {"q": "cho"})
        self.assertEqual([c["nombre_completo"] for c in r.data], ["Rosa Choque"])

    def test_enviar_a_papelera_no_reindexa(self):
        # save(update_fields=...) sin tocar el nombre: el índice no se recalcula.
        with mock.patch("modulo_clientes.services.busqueda_service.reindexar_cliente") as reindexar:
            enviar_cliente_a_papelera(self.cliente, self.abogado)
        reindexar.assert_not_called()

    def test_un_nombre_no_descifrable_no_rompe_el_guardado(self):
        # Datos viejos sin cifrar (como los de otros tests): sin tokens, sin error.
        cliente = Cliente.objects.create(nombres="sin cifrar", apellidos="tampoco")
        self.assertEqual(self.tokens(cliente), set())

    def test_reindexar_borra_lo_que_sobra_y_agrega_lo_que_falta(self):
        ClienteBusquedaToken.objects.filter(cliente=self.cliente).delete()
        ClienteBusquedaToken.objects.create(cliente=self.cliente, token_hash="x" * 64)
        reindexar_cliente(self.cliente)
        self.assertEqual(self.tokens(self.cliente), hashes_de_indexado("Ana", "Rojas"))

    def test_comando_reindexar_reconstruye_todo(self):
        ClienteBusquedaToken.objects.all().delete()
        call_command("reindexar_busqueda_clientes", stdout=mock.MagicMock())
        self.assertEqual(self.tokens(self.cliente), hashes_de_indexado("Ana", "Rojas"))

    def test_backfill_de_la_migracion_indexa_los_clientes_existentes(self):
        import importlib
        migracion = importlib.import_module("modulo_clientes.migrations.0007_cliente_busqueda_tokens")
        ClienteBusquedaToken.objects.all().delete()
        migracion.indexar_clientes_existentes(django_apps, None)
        self.assertEqual(self.tokens(self.cliente), hashes_de_indexado("Ana", "Rojas"))
        migracion.indexar_clientes_existentes(django_apps, None)  # idempotente
        self.assertEqual(self.tokens(self.cliente), hashes_de_indexado("Ana", "Rojas"))

    def test_borrar_el_cliente_borra_su_indice(self):
        pk = self.cliente.pk
        self.cliente.delete()
        self.assertFalse(ClienteBusquedaToken.objects.filter(cliente_id=pk).exists())


class EndpointBuscarTests(PapeleraClientesBase):
    def setUp(self):
        super().setUp()
        for i in range(30):
            crear_cliente(f"Nombre{chr(97 + i % 26)}{chr(98 + i % 24)}", f"Apellido{chr(97 + i % 20)}")
        self.luis = crear_cliente("Luis", "Mamani")

    def test_devuelve_solo_los_que_coinciden(self):
        self.client.force_authenticate(self.abogado)
        r = self.client.get(self.url("clientes-buscar"), {"q": "mamani"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual([c["nombre_completo"] for c in r.data], ["Luis Mamani"])

    def test_no_descifra_a_los_clientes_que_no_coinciden(self):
        self.client.force_authenticate(self.abogado)
        total = Cliente.objects.count()
        with mock.patch.object(aes_encryption, "decrypt", wraps=aes_encryption.decrypt) as decrypt:
            r = self.client.get(self.url("clientes-buscar"), {"q": "mamani"})
        self.assertEqual(len(r.data), 1)
        # El serializer descifra los campos del único resultado (unas pocas veces);
        # antes se descifraban nombres y apellidos de TODOS los clientes.
        self.assertLess(decrypt.call_count, 10)
        self.assertGreater(total, 30)

    def test_menos_de_2_caracteres_es_400(self):
        self.client.force_authenticate(self.abogado)
        r = self.client.get(self.url("clientes-buscar"), {"q": "m"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_el_asistente_tambien_puede_buscar(self):
        self.client.force_authenticate(self.asistente)
        r = self.client.get(self.url("clientes-buscar"), {"q": "luis"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)

    def test_no_incluye_clientes_en_la_papelera(self):
        enviar_cliente_a_papelera(self.luis, self.abogado)
        self.client.force_authenticate(self.abogado)
        r = self.client.get(self.url("clientes-buscar"), {"q": "luis"})
        self.assertEqual(r.data, [])


class PapeleraBusquedaTests(PapeleraClientesBase):
    def test_busqueda_con_varias_palabras_y_casos_para_restaurar_no_se_infla(self):
        self.crear_caso()
        self.crear_caso()
        enviar_cliente_a_papelera(self.cliente, self.abogado, eliminar_casos=True)
        otro = crear_cliente("Luis", "Mamani")
        enviar_cliente_a_papelera(otro, self.abogado)
        self.client.force_authenticate(self.abogado)
        r = self.client.get(self.url("clientes-papelera"), {"search": "ana ro"})
        filas = resultados(r)
        self.assertEqual([f["nombre_completo"] for f in filas], ["Ana Rojas"])
        self.assertEqual(filas[0]["casos_para_restaurar"], 2)
