from datetime import date
from unittest.mock import patch
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework.exceptions import ValidationError
from modulo_catalogo.models import Norma, RamaDerecho, Articulo, DocumentoNorma, CambioNormativo
from modulo_catalogo.models.jerarquia import jerarquia
from modulo_catalogo.serializers.carga_pdf_serializer import CargaArticulosPDFSerializer
from modulo_catalogo.services.revision_carga_service import aplicar_carga_revisada
from modulo_catalogo.services.vigencia_service import confirmar, aviso, resolver_norma
from modulo_catalogo.views.revision_carga_view import validar_revision
from modulo_usuarios.tests.factories import crear_rol, crear_usuario
from .test_validacion_pdf_endpoints import PDF_MINIMO_1_PAGINA

TEXTO = """LEY N° 200
LEY DE 10 DE SEPTIEMBRE DE 2025
ARTÍCULO 1. Objeto de esta norma de prueba.
DISPOSICIÓN TRANSITORIA
PRIMERA. El plazo es de noventa días.
DISPOSICIÓN FINAL
ÚNICA. No implica recursos adicionales.
DISPOSICIÓN DEROGATORIA
ÚNICA. Se derogan expresamente las siguientes disposiciones del Código Penal:
1. El Parágrafo III del Artículo 323 Bis,
2. El Artículo 281 Quater.
DISPOSICIÓN ABROGATORIA
ÚNICA. Queda abrogado el Decreto Ley N° 11080 de 19 de diciembre de 1973.
"""


class ParidadMotoresTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.usuario = crear_usuario('paridad.admin', rol=crear_rol('Administrador'))
        self.client.force_authenticate(self.usuario)
        self.rama = RamaDerecho.objects.create(nombre='Penal paridad')
        self.ley = jerarquia.objects.get_or_create(nombre='Ley', defaults={'nivel': 2})[0]
        self.codigo = resolver_norma('Código Penal') or Norma.objects.create(nombre='Código Penal')
        self.codigo.fecha_norma = date(1972, 8, 23)
        self.codigo.jerarquia = self.ley
        self.codigo.save()
        self.articulo = Articulo.objects.create(norma=self.codigo, rama=self.rama, numero_articulo='323 BIS',
            contenido='I. Texto conservado.\nII. Otro texto conservado.\nIII. Texto afectado.\nIV. Texto restante.')
        self.antigua = Norma.objects.create(nombre='Decreto Ley 11080', tipo_norma='Decreto Ley', numero_norma='11080',
            fecha_norma=date(1973, 12, 19), jerarquia=self.ley)
        Articulo.objects.create(norma=self.antigua, rama=self.rama, numero_articulo='1', contenido='Texto original cargado.')

    def archivo(self):
        return SimpleUploadedFile('norma.pdf', PDF_MINIMO_1_PAGINA, content_type='application/pdf')

    def respuesta_qwen(self, instruccion, texto, esquema):
        if 'unidades' in esquema['properties']:
            return {'unidades': []}  # El mapa literal completa cabeceras verificadas.
        if 'numero_norma' in esquema['properties']:
            return {'tipo_norma': 'Ley', 'numero_norma': '200', 'fecha_norma': '2025-09-10'}
        self.fail('La prueba expresa no debe pedir interpretación adicional: ' + instruccion)

    def revisar(self, motor):
        resultados = {}
        def ejecutar(usuario, trabajo, final=None):
            resultados.update(trabajo(lambda resumen: None))
            return 'paridad-' + motor
        with patch('modulo_catalogo.views.tareas_normativas_view.iniciar', side_effect=ejecutar), \
             patch('modulo_catalogo.services.pdf_normativo_service.leer_pdf', return_value=(TEXTO, [])), \
             patch('modulo_catalogo.services.lectura_normativa_service.consultar', side_effect=self.respuesta_qwen) as ollama:
            respuesta = self.client.post('/api/catalogo/cargar-articulos/revisar-iniciar/', {
                'archivo': self.archivo(), 'rama_id': self.rama.pk, 'nombre_documento': 'Ley 200',
                'motor_lectura': motor}, format='multipart')
        self.assertEqual(respuesta.status_code, 202, respuesta.data)
        if motor == 'clasico':
            ollama.assert_not_called()
        else:
            self.assertTrue(ollama.called)
        return resultados

    def test_ambos_revisan_separan_publican_y_exigen_confirmacion(self):
        for motor in ['clasico', 'qwen']:
            with self.subTest(motor=motor):
                revision = self.revisar(motor)
                self.assertEqual(revision['motor'], motor)
                self.assertEqual([u['numero'] for u in revision['articulos']], ['1'])
                self.assertEqual({u['tipo_unidad'] for u in revision['disposiciones']}, {'final', 'derogatoria', 'abrogatoria'})
                plan = cache.get('revision_carga_pdf:' + revision['revision_token'])
                self.assertEqual({(c['operacion'], c['unidad']) for c in plan['cambios']},
                                 {('deroga', '323 BIS'), ('deroga', '281 QUATER'), ('abroga', '')})
                self.assertFalse(CambioNormativo.objects.exists())
                self.assertFalse(Norma.objects.filter(nombre='Ley 200').exists())
                serializer = CargaArticulosPDFSerializer(data={'archivo': self.archivo(), 'rama_id': self.rama.pk,
                    'nombre_documento': 'Ley 200', 'motor_lectura': motor, 'revision_token': revision['revision_token'],
                    'modo_actualizacion': 'articulos', 'articulos_seleccionados': []}, context={'solo_revision': True})
                serializer.is_valid(raise_exception=True)
                datos = serializer.validated_data
                self.assertEqual(validar_revision(datos, self.usuario.pk)['motor'], motor)
                datos['motor_lectura'] = 'qwen' if motor == 'clasico' else 'clasico'
                with self.assertRaises(ValidationError):
                    validar_revision(datos, self.usuario.pk)
                fuente = Norma.objects.create(nombre='Ley 200', tipo_norma='Ley', numero_norma='200', jerarquia=self.ley)
                documento = DocumentoNorma.objects.create(norma=fuente, rama=self.rama, nombre_original='norma.pdf',
                    ruta_archivo='norma.pdf', tamano=100, vigente=False, metadatos=plan['metadatos'],
                    analisis_normativo={'motor': motor, 'cambios': plan['cambios']})
                aplicar_carga_revisada(fuente, self.rama, plan['articulos'], 'articulos', [], plan['huella'], documento.pk)
                self.assertEqual(documento.disposiciones.count(), 3)
                eventos = list(CambioNormativo.objects.filter(fuente=documento))
                self.assertEqual(len(eventos), 3)
                self.assertTrue(all(e.estado_revision == 'pendiente' for e in eventos))
                parcial = next(e for e in eventos if e.referencia.get('unidad') == '323 BIS')
                ausente = next(e for e in eventos if e.referencia.get('unidad') == '281 QUATER')
                abrogacion = next(e for e in eventos if e.operacion == 'abroga')
                self.assertTrue(aviso(parcial)['destino_catalogo']['encontrado'])
                self.assertFalse(aviso(ausente)['destino_catalogo']['encontrado'])
                with self.assertRaises(ValueError):
                    confirmar(ausente, {'fecha_efecto': '2025-09-10', 'observacion': 'Fuente, fecha, alcance y jerarquía verificados en la norma original.'}, self.usuario)
                with self.assertRaises(ValueError):
                    parcial = confirmar(parcial, {'fecha_efecto': '1970-01-01'}, self.usuario)
                parcial = confirmar(parcial, {'fecha_efecto': '2025-09-10', 'observacion': 'Fuente, fecha, alcance y jerarquía verificados en la norma original.'}, self.usuario)
                abrogacion = confirmar(abrogacion, {'fecha_efecto': '2025-09-10', 'observacion': 'Fuente, fecha, alcance y jerarquía verificados en la norma original.'}, self.usuario)
                self.assertEqual(parcial.estado_revision, 'confirmado')
                self.assertEqual(abrogacion.estado_revision, 'confirmado')
                self.articulo.refresh_from_db()
                self.assertIn('IV. Texto restante.', self.articulo.contenido)
                # Repetir el mismo escenario sin efectos del primer motor.
                CambioNormativo.objects.all().delete()
                documento.disposiciones.all().delete()
                documento.delete()
                fuente.delete()
