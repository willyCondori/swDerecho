import io
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import override_settings
from pypdf import PdfWriter
from rest_framework.test import APITestCase

from core.encryption.aes_encryption import safe_decrypt
from modulo_auditoria.models.auditoria import Auditoria
from modulo_casos.models.caso import Caso
from modulo_casos.models.seguimiento import SeguimientoCaso
from modulo_catalogo.models.rama import RamaDerecho
from modulo_clientes.models.cliente import Cliente
from modulo_clientes.serializers.cliente_serializer import ClienteWriteSerializer
from modulo_documentos.models.documento import DocumentoCaso
from modulo_usuarios.tests.factories import crear_rol, crear_usuario


class CreacionConClienteTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.abogado = crear_usuario('abogado.creacion', rol=crear_rol('Abogado'))
        cls.rama = RamaDerecho.objects.create(nombre='Civil creación')

    def setUp(self):
        self.client.force_authenticate(self.abogado)
        self.datos = {
            'nombres': 'Ana', 'apellidos': 'Quispe', 'telefono': '71234567',
            'titulo': 'Demanda por incumplimiento',
            'descripcion': 'Incumplimiento del contrato de alquiler.',
            'rama_detectada_id': self.rama.pk,
        }
        self.clientes_iniciales = Cliente.objects.count()
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)

    def crear(self, **cambios):
        return self.client.post(
            '/api/casos/crear_con_cliente/', {**self.datos, **cambios}, format='json',
        )

    def crear_pdf(self, contenido=None, *, cliente_id=None):
        if contenido is None:
            writer = PdfWriter()
            writer.add_blank_page(width=72, height=72)
            output = io.BytesIO()
            writer.write(output)
            contenido = output.getvalue()
        datos = {**self.datos, 'descripcion': '', 'archivo_pdf': SimpleUploadedFile(
            'caso.pdf', contenido, content_type='application/pdf',
        )}
        url = '/api/casos/crear_con_cliente/'
        if cliente_id is not None:
            url = '/api/casos/'
            datos = {key: value for key, value in datos.items()
                     if key not in ('nombres', 'apellidos', 'telefono')}
            datos['cliente_id'] = cliente_id
        return self.client.post(url, datos, format='multipart')

    def assert_sin_registros_nuevos(self):
        self.assertEqual(Cliente.objects.count(), self.clientes_iniciales)
        self.assertFalse(Caso.objects.exists())
        self.assertFalse(SeguimientoCaso.objects.exists())
        self.assertFalse(DocumentoCaso.objects.exists())
        self.assertFalse(Auditoria.objects.filter(tabla='casos', accion='CREATE').exists())

    def test_texto_crea_cliente_con_telefono_cifrado_y_caso(self):
        respuesta = self.crear()
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        caso = Caso.objects.get(pk=respuesta.data['id'])
        self.assertEqual(safe_decrypt(caso.cliente.telefono), '71234567')
        self.assertNotEqual(caso.cliente.telefono, '71234567')
        self.assertEqual(caso.usuario, self.abogado)
        self.assertEqual(caso.rama_detectada, self.rama)
        self.assertEqual(caso.seguimientos.count(), 1)
        self.assertEqual(Cliente.objects.count(), self.clientes_iniciales + 1)

    def test_datos_invalidos_del_caso_no_crean_cliente(self):
        for campo, valor in [('titulo', 'x'), ('descripcion', 'x'), ('rama_detectada_id', -1)]:
            with self.subTest(campo=campo):
                respuesta = self.crear(**{campo: valor})
                self.assertEqual(respuesta.status_code, 400, respuesta.data)
                self.assertIn(campo, respuesta.data)
                self.assert_sin_registros_nuevos()

    def test_telefono_invalido_no_crea_cliente_ni_caso(self):
        respuesta = self.crear(telefono='123')
        self.assertEqual(respuesta.status_code, 400, respuesta.data)
        self.assertIn('telefono', respuesta.data)
        self.assert_sin_registros_nuevos()

    def test_telefono_duplicado_no_crea_cliente_ni_caso(self):
        serializer = ClienteWriteSerializer(data={
            'nombres': 'Maria', 'apellidos': 'Perez', 'telefono': self.datos['telefono'],
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.clientes_iniciales += 1
        respuesta = self.crear()
        self.assertEqual(respuesta.status_code, 400, respuesta.data)
        self.assertIn('telefono', respuesta.data)
        self.assert_sin_registros_nuevos()

    def test_error_al_guardar_caso_revierte_cliente_ya_insertado(self):
        def fallar_seguimiento(*args):
            self.assertEqual(Cliente.objects.count(), self.clientes_iniciales + 1)
            self.assertEqual(Caso.objects.count(), 1)
            raise IntegrityError('Fallo simulado al guardar el seguimiento')

        with patch('modulo_casos.serializers.caso_serializer.registrar_seguimiento_inicial',
                   side_effect=fallar_seguimiento):
            with self.assertRaises(IntegrityError):
                self.crear()
        self.assert_sin_registros_nuevos()

    def test_pdf_invalido_revierte_cliente_caso_y_notificaciones(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            respuesta = self.crear_pdf(b'Esto no es un PDF')
        self.assertEqual(respuesta.status_code, 400, respuesta.data)
        self.assertEqual(callbacks, [])
        self.assert_sin_registros_nuevos()

    def test_reintentar_despues_de_pdf_invalido_no_encuentra_cliente_duplicado(self):
        respuesta = self.crear_pdf(b'Esto no es un PDF')
        self.assertEqual(respuesta.status_code, 400, respuesta.data)
        self.assert_sin_registros_nuevos()

        respuesta = self.crear_pdf()
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertEqual(Cliente.objects.count(), self.clientes_iniciales + 1)
        self.assertEqual(Caso.objects.count(), 1)

    def test_error_de_almacenamiento_pdf_revierte_cliente_y_caso(self):
        with patch('modulo_documentos.serializers.documento_serializer.DocumentoCasoWriteSerializer.create',
                   side_effect=OSError('Fallo simulado de almacenamiento')):
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                with self.assertRaises(OSError):
                    self.crear_pdf()
        self.assertEqual(callbacks, [])
        self.assert_sin_registros_nuevos()

    def test_pdf_valido_guarda_cliente_caso_y_documento(self):
        respuesta = self.crear_pdf()
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        caso = Caso.objects.get(pk=respuesta.data['id'])
        self.assertEqual(safe_decrypt(caso.cliente.telefono), self.datos['telefono'])
        self.assertEqual(caso.documentos.count(), 1)
        self.assertTrue(respuesta.data['tiene_documento'])

    def test_pdf_invalido_con_cliente_existente_no_deja_caso(self):
        cliente = Cliente.objects.create(nombres='Cliente existente', apellidos='Prueba')
        self.clientes_iniciales += 1
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            respuesta = self.crear_pdf(b'Esto no es un PDF', cliente_id=cliente.pk)
        self.assertEqual(respuesta.status_code, 400, respuesta.data)
        self.assertEqual(callbacks, [])
        self.assertTrue(Cliente.objects.filter(pk=cliente.pk).exists())
        self.assert_sin_registros_nuevos()
