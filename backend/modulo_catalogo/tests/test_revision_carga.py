import shutil
import tempfile
from unittest.mock import Mock, patch

import numpy as np
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from modulo_catalogo.models.articulo import Articulo
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama import RamaDerecho
from modulo_catalogo.models.documento_norma import DocumentoNorma
from modulo_catalogo.services.revision_carga_service import (
    aplicar_carga_revisada, comparar_articulos, filas_actuales, huella_catalogo, indica_derogacion,
)
from modulo_ia.models.embedding import EmbeddingArticulo
from modulo_usuarios.tests.factories import crear_rol, crear_usuario
from .test_validacion_pdf_endpoints import PDF_MINIMO_1_PAGINA

ARTICULOS = [
    {'numero': '1', 'titulo': 'Art. 1 - OBJETO', 'texto': 'ARTÍCULO 1. (OBJETO). Texto actualizado suficientemente largo.'},
    {'numero': '2', 'titulo': 'Art. 2 - Derogado', 'texto': 'ARTÍCULO 2. (Derogado).'},
]


class ComparacionCargaTests(TestCase):
    def setUp(self):
        self.norma = Norma.objects.create(nombre='Norma de revisión')
        self.rama = RamaDerecho.objects.create(nombre='Rama de revisión')
        self.anterior = DocumentoNorma.objects.create(norma=self.norma, rama=self.rama, nombre_original='anterior.pdf', ruta_archivo='anterior.pdf', tamano=20)
        self.nuevo = DocumentoNorma.objects.create(norma=self.norma, rama=self.rama, nombre_original='nuevo.pdf', ruta_archivo='nuevo.pdf', tamano=20, vigente=False)
        self.art1 = Articulo.objects.create(numero_articulo='1', norma=self.norma, rama=self.rama, titulo='Anterior', contenido='Texto previo', documento_norma=self.anterior, frecuencia_historica=8)
        self.art99 = Articulo.objects.create(numero_articulo='99', norma=self.norma, rama=self.rama, contenido='Artículo ausente', documento_norma=self.anterior)
        self.modelo = Mock()
        self.modelo.encode.side_effect = lambda textos, **kwargs: np.ones((len(textos), 768))

    def cargar(self, modo, seleccion=None, huella=None):
        with patch('modulo_catalogo.services.carga_pdf_service._obtener_modelo', return_value=self.modelo):
            return aplicar_carga_revisada(self.norma, self.rama, ARTICULOS, modo, seleccion,
                huella or huella_catalogo(filas_actuales(self.norma.pk, self.rama.pk)), self.nuevo.pk)

    def test_comparacion_distingue_nuevo_modificado_y_sobrante(self):
        plan = comparar_articulos(ARTICULOS, filas_actuales(self.norma.pk, self.rama.pk))
        self.assertEqual(plan['conteos'], {'nuevo': 1, 'actualizar': 1, 'sin_cambios': 0})
        self.assertEqual([a['numero'] for a in plan['sobrantes']], ['99'])
        self.assertEqual(plan['derogados_en_pdf'], 1)

    def test_no_interpreta_como_derogacion_la_cita_del_cuerpo(self):
        self.assertFalse(indica_derogacion({'texto': 'ARTÍCULO 1. (OBJETO). El artículo 2 queda derogado.'}))

    def test_extractor_conserva_una_cabecera_corta_de_articulo_derogado(self):
        from modulo_catalogo.services.carga_pdf_service import dividir_por_articulos
        articulos = dividir_por_articulos('Art. 2. (Derogado)\nArt. 3. Texto suficiente del siguiente artículo.')
        self.assertEqual([a['numero'] for a in articulos], ['2', '3'])
        self.assertTrue(indica_derogacion(articulos[0]))

    def test_actualizacion_selectiva_preserva_ids_y_articulos_no_elegidos(self):
        self.cargar('articulos', ['1'])
        self.art1.refresh_from_db()
        self.art99.refresh_from_db()
        self.assertEqual(self.art1.contenido, ARTICULOS[0]['texto'])
        self.assertEqual(self.art1.frecuencia_historica, 8)
        self.assertEqual(self.art1.documento_norma, self.nuevo)
        self.assertTrue(self.art99.estado)
        self.assertEqual(self.art99.documento_norma, self.anterior)
        self.assertFalse(Articulo.objects.filter(norma=self.norma, numero_articulo='2').exists())
        self.anterior.refresh_from_db()
        self.assertTrue(self.anterior.vigente)

    def test_reemplazo_completo_retira_ausentes_sin_borrar_sus_ids(self):
        resultado = self.cargar('completo')
        self.assertEqual(resultado.resumen()['revision']['retirados'], 1)
        self.art99.refresh_from_db()
        self.assertFalse(self.art99.estado)
        self.assertEqual(Articulo.objects.filter(norma=self.norma, estado=True).count(), 2)
        self.anterior.refresh_from_db()
        self.nuevo.refresh_from_db()
        self.assertFalse(self.anterior.vigente)
        self.assertTrue(self.nuevo.vigente)
        self.assertTrue(EmbeddingArticulo.objects.filter(articulo_id=self.art1.pk).exists())

    def test_fallo_embedding_no_modifica_catalogo_ni_documentos(self):
        self.modelo.encode.side_effect = ValueError('Modelo no disponible')
        with self.assertRaises(ValueError): self.cargar('completo')
        self.art1.refresh_from_db()
        self.art99.refresh_from_db()
        self.nuevo.refresh_from_db()
        self.assertEqual(self.art1.contenido, 'Texto previo')
        self.assertTrue(self.art99.estado)
        self.assertFalse(self.nuevo.vigente)

    def test_fallo_publicacion_revierte_actualizaciones_y_retiros(self):
        with patch('modulo_catalogo.services.carga_pdf_service._update_task', side_effect=lambda _, p, __: (
            (_ for _ in ()).throw(RuntimeError('Publicación fallida')) if p == 98 else None)):
            with self.assertRaises(RuntimeError): self.cargar('completo')
        self.art1.refresh_from_db()
        self.art99.refresh_from_db()
        self.nuevo.refresh_from_db()
        self.assertEqual(self.art1.contenido, 'Texto previo')
        self.assertTrue(self.art99.estado)
        self.assertFalse(self.nuevo.vigente)

    def test_rechaza_catalogo_cambiado_desde_revision(self):
        huella = huella_catalogo(filas_actuales(self.norma.pk, self.rama.pk))
        self.art1.contenido = 'Cambio simultáneo'
        self.art1.save()
        with self.assertRaisesRegex(ValueError, 'catálogo cambió'): self.cargar('completo', huella=huella)
        self.modelo.encode.assert_not_called()


class RevisionCargaAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = crear_usuario('revision.pdf', rol=crear_rol('Abogado'))
        cls.norma = Norma.objects.create(nombre='Destino revisión API')
        cls.rama = RamaDerecho.objects.create(nombre='Rama revisión API')

    def setUp(self):
        cache.clear()
        self.client.force_authenticate(self.usuario)
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        ajuste = override_settings(MEDIA_ROOT=self.media)
        ajuste.enable()
        self.addCleanup(ajuste.disable)

    def post(self, ruta, **datos):
        return self.client.post('/api/catalogo/cargar-articulos/' + ruta,
            {'archivo': SimpleUploadedFile('norma.pdf', PDF_MINIMO_1_PAGINA, content_type='application/pdf'),
             'rama_id': self.rama.pk, **datos}, format='multipart')

    def revisar(self, **datos):
        with patch('modulo_catalogo.views.revision_carga_view.extraer_texto_pdf_bytes', return_value='\n'.join(a['texto'] for a in ARTICULOS)):
            return self.post('revisar/', **datos)

    def test_revisar_no_crea_norma_documento_articulos_ni_embeddings(self):
        anteriores = [m.objects.count() for m in [Norma, DocumentoNorma, Articulo, EmbeddingArticulo]]
        respuesta = self.revisar(nombre_documento='Una norma completamente nueva')
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.assertEqual(respuesta.data['conteos']['nuevo'], 2)
        self.assertEqual(anteriores, [m.objects.count() for m in [Norma, DocumentoNorma, Articulo, EmbeddingArticulo]])

    def test_no_permite_confirmar_sin_revision(self):
        respuesta = self.post('', norma_id=self.norma.pk, modo_actualizacion='completo')
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(DocumentoNorma.objects.filter(norma=self.norma).exists())

    def test_no_permite_token_de_otro_usuario(self):
        revision = self.revisar(norma_id=self.norma.pk).data
        otro = crear_usuario('otra.revision', rol=crear_rol('Abogado'))
        self.client.force_authenticate(otro)
        respuesta = self.post('', norma_id=self.norma.pk, modo_actualizacion='completo', revision_token=revision['revision_token'])
        self.assertEqual(respuesta.status_code, 400)

    def test_no_permite_cambiar_pdf_despues_de_revisarlo(self):
        revision = self.revisar(norma_id=self.norma.pk).data
        respuesta = self.client.post('/api/catalogo/cargar-articulos/', {
            'archivo': SimpleUploadedFile('otro.pdf', PDF_MINIMO_1_PAGINA + b'\n% otra version\n', content_type='application/pdf'),
            'norma_id': self.norma.pk, 'rama_id': self.rama.pk,
            'modo_actualizacion': 'completo', 'revision_token': revision['revision_token'],
        }, format='multipart')
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(DocumentoNorma.objects.filter(norma=self.norma).exists())

    def test_revision_caducada_no_crea_norma_nueva(self):
        revision = self.revisar(nombre_documento='Norma todavía no creada').data
        cache.clear()
        respuesta = self.post('', nombre_documento='Norma todavía no creada',
                              modo_actualizacion='completo', revision_token=revision['revision_token'])
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(Norma.objects.filter(nombre='Norma todavía no creada').exists())

    def test_confirmar_norma_nueva_crea_destino_solo_despues_de_validar_revision(self):
        revision = self.revisar(nombre_documento='Norma nueva confirmada').data
        with patch('modulo_catalogo.views.carga_articulos_view.lanzar_carga_en_background', return_value='task-nueva'):
            respuesta = self.post('', nombre_documento='Norma nueva confirmada',
                                  modo_actualizacion='completo', revision_token=revision['revision_token'])
        self.assertEqual(respuesta.status_code, 202, respuesta.data)
        self.assertTrue(Norma.objects.filter(nombre='Norma nueva confirmada').exists())

    def test_no_permite_seleccionar_numero_ausente_del_pdf(self):
        revision = self.revisar(norma_id=self.norma.pk).data
        respuesta = self.post('', norma_id=self.norma.pk, modo_actualizacion='articulos',
                              revision_token=revision['revision_token'], articulos_seleccionados='["99"]')
        self.assertEqual(respuesta.status_code, 400)

    def test_confirmacion_envia_plan_revisado_y_fuente_al_procesamiento(self):
        revision = self.revisar(norma_id=self.norma.pk).data
        with patch('modulo_catalogo.views.carga_articulos_view.lanzar_carga_en_background', return_value='task-revision') as lanzar:
            respuesta = self.post('', norma_id=self.norma.pk, modo_actualizacion='completo', revision_token=revision['revision_token'])
        self.assertEqual(respuesta.status_code, 202, respuesta.data)
        argumentos = lanzar.call_args.kwargs
        self.assertEqual(argumentos['modo_actualizacion'], 'completo')
        self.assertEqual(len(argumentos['revision']['articulos']), 2)
        self.assertIsNone(argumentos['on_exito'])
        self.assertFalse(DocumentoNorma.objects.get(pk=argumentos['documento_id']).vigente)
