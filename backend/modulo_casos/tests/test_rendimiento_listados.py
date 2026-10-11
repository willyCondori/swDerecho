from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APITestCase

from core.encryption.aes_encryption import encrypt
from modulo_casos.models.caso import Caso
from modulo_casos.models.resultado_caso import ResultadoCaso
from modulo_catalogo.models.rama import RamaDerecho
from modulo_clientes.models.cliente import Cliente
from modulo_documentos.models.documento import DocumentoCaso, TipoDoc
from modulo_usuarios.tests.factories import crear_rol, crear_usuario


class RendimientoListadosTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.abogado = crear_usuario('abogado.rendimiento', rol=crear_rol('Abogado'))
        cls.cliente = Cliente.objects.create(nombres=encrypt('Ana'), apellidos=encrypt('Quispe'))
        cls.rama = RamaDerecho.objects.create(nombre='Civil rendimiento')
        cls.caso = Caso.objects.create(
            codigo='PERF-1', titulo='Caso rendimiento', usuario=cls.abogado,
            cliente=cls.cliente, rama_detectada=cls.rama,
        )

    def setUp(self):
        self.client.force_authenticate(self.abogado)

    def comprobar_consultas_constantes(self, url):
        with CaptureQueriesContext(connection) as pequena:
            respuesta = self.client.get(url, {'page_size': 50})
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.assertEqual(len(respuesta.data['results']), 1)

        Caso.objects.bulk_create([
            Caso(codigo=f'PERF-{i}', titulo=f'Caso rendimiento {i}', usuario=self.abogado,
                 cliente=self.cliente, rama_detectada=self.rama)
            for i in range(2, 13)
        ])
        with CaptureQueriesContext(connection) as grande:
            respuesta = self.client.get(url, {'page_size': 50})
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.assertEqual(len(respuesta.data['results']), 12)
        print(f'{url}: 1 caso={len(pequena)} consultas; 12 casos={len(grande)} consultas')
        self.assertLessEqual(len(grande), len(pequena))
        self.assertLessEqual(len(grande), 4)

    def test_listado_general_no_consulta_por_cada_caso(self):
        self.comprobar_consultas_constantes('/api/casos/')

    def test_mis_casos_no_consulta_por_cada_caso(self):
        self.comprobar_consultas_constantes('/api/casos/mis_casos/')

    def test_casos_del_cliente_no_consulta_por_cada_caso(self):
        self.comprobar_consultas_constantes(f'/api/clientes/{self.cliente.public_id}/casos/')

    def test_indicadores_y_filtro_pdf_conservan_resultados_sin_duplicados(self):
        sin_pdf = Caso.objects.create(
            codigo='PERF-SIN-PDF', titulo='Caso sin PDF', usuario=self.abogado,
            cliente=self.cliente, rama_detectada=self.rama,
        )
        tipo = TipoDoc.objects.create(tipo='rendimiento_pdf')
        for nombre in ('uno.pdf', 'dos.pdf'):
            DocumentoCaso.objects.create(
                caso=self.caso, nombre_original=nombre, ruta_archivo=nombre,
                tipo_archivo='pdf', tamano=1, tipo_documento=tipo,
            )
        DocumentoCaso.objects.create(
            caso=sin_pdf, nombre_original='texto.txt', ruta_archivo='texto.txt',
            tipo_archivo='txt', tamano=1, tipo_documento=tipo,
        )
        ResultadoCaso.objects.create(caso=self.caso, resumen='Resultado de prueba')
        respuesta = self.client.get('/api/casos/', {'tiene_pdf': 'true'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data['count'], 1)
        self.assertTrue(respuesta.data['results'][0]['tiene_documento'])
        self.assertTrue(respuesta.data['results'][0]['tiene_resultado'])
        respuesta = self.client.get('/api/casos/', {'tiene_pdf': 'false'})
        self.assertEqual(respuesta.data['count'], 1)
        self.assertEqual(respuesta.data['results'][0]['id'], str(sin_pdf.public_id))
        self.assertFalse(respuesta.data['results'][0]['tiene_documento'])
        self.assertFalse(respuesta.data['results'][0]['tiene_resultado'])
