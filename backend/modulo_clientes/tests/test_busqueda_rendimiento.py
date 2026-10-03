from unittest.mock import patch

from rest_framework.test import APITestCase

from core.encryption.aes_encryption import encrypt, safe_decrypt
from modulo_clientes.models.cliente import Cliente
from modulo_clientes.serializers.cliente_serializer import ClienteReadSerializer
from modulo_clientes.services.busqueda_service import reindexar_cliente
from modulo_usuarios.tests.factories import crear_rol, crear_usuario


class BusquedaRendimientoTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.abogado = crear_usuario('abogado.busqueda', rol=crear_rol('Abogado'))
        clientes = Cliente.objects.bulk_create([
            Cliente(nombres=encrypt('Ana'), apellidos=encrypt('Quispe'), telefono=encrypt('71234567'))
            for _ in range(60)
        ])
        # bulk_create no dispara las señales que mantienen el índice.
        for cliente in clientes:
            reindexar_cliente(cliente)
        Cliente.objects.create(nombres=encrypt('Ana'), apellidos=encrypt('Perez'), estado=False)

    def setUp(self):
        self.client.force_authenticate(self.abogado)

    def test_selector_limita_respuesta_y_detiene_descifrado(self):
        with self.assertNumQueries(1), patch(
            'modulo_clientes.serializers.cliente_serializer.safe_decrypt', wraps=safe_decrypt,
        ) as descifrar:
            respuesta = self.client.get('/api/clientes/buscar/', {
                'q': 'ana', 'limit': 20, 'compacto': 'true',
            })
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.assertEqual(len(respuesta.data), 20)
        self.assertEqual(descifrar.call_count, 40)
        self.assertEqual(set(respuesta.data[0]), {'id', 'nombre_completo'})
        self.assertEqual(respuesta.data[0]['nombre_completo'], 'Ana Quispe')

    def test_busqueda_general_conserva_todos_los_resultados_y_campos(self):
        respuesta = self.client.get('/api/clientes/buscar/', {'q': 'ana'})
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.assertEqual(len(respuesta.data), 60)
        self.assertEqual(respuesta.data[0]['telefono'], '71234567')

    def test_limite_tiene_maximo_y_rechaza_valores_invalidos(self):
        respuesta = self.client.get('/api/clientes/buscar/', {'q': 'ana', 'limit': 999})
        self.assertEqual(len(respuesta.data), 50)
        for limite in ('0', '-1', 'abc', '1.5'):
            with self.subTest(limite=limite):
                respuesta = self.client.get('/api/clientes/buscar/', {'q': 'ana', 'limit': limite})
                self.assertEqual(respuesta.status_code, 400)

    def test_serializacion_no_descifra_dos_veces_nombres_y_apellidos(self):
        cliente = Cliente.objects.filter(estado=True).first()
        with patch('modulo_clientes.serializers.cliente_serializer.safe_decrypt', wraps=safe_decrypt) as descifrar:
            datos = ClienteReadSerializer(cliente).data
        self.assertEqual(datos['nombres'], 'Ana')
        self.assertEqual(datos['apellidos'], 'Quispe')
        self.assertEqual(datos['nombre_completo'], 'Ana Quispe')
        self.assertEqual(descifrar.call_count, 3)  # nombre, apellido y teléfono

    def test_cache_de_serializacion_se_invalida_si_cambia_el_nombre(self):
        cliente = Cliente.objects.filter(estado=True).first()
        serializer = ClienteReadSerializer()
        self.assertEqual(serializer.get_nombre_completo(cliente), 'Ana Quispe')
        cliente.nombres = encrypt('Maria')
        self.assertEqual(serializer.get_nombre_completo(cliente), 'Maria Quispe')
