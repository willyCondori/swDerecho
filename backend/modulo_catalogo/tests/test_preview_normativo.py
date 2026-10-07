from datetime import date
from unittest.mock import patch
from rest_framework.test import APITestCase
from modulo_catalogo.models import Norma, RamaDerecho, Articulo, DocumentoNorma, CambioNormativo, HistorialArticulo
from modulo_catalogo.services.vigencia_service import registrar_cambios, confirmar
from modulo_usuarios.tests.factories import crear_usuario, crear_rol


class PreviewNormativoTests(APITestCase):
    def setUp(self):
        self.admin = crear_usuario('preview.admin', rol=crear_rol('Administrador'))
        self.client.force_authenticate(self.admin)
        rama = RamaDerecho.objects.create(nombre='Penal preview')
        self.base = Norma.objects.create(nombre='Ley 99001', numero_norma='99001', tipo_norma='Ley', fecha_norma=date(2000, 1, 1))
        nueva = Norma.objects.create(nombre='Ley 99002', numero_norma='99002', tipo_norma='Ley', fecha_norma=date(2025, 1, 1))
        self.doc = DocumentoNorma.objects.create(norma=nueva, rama=rama, nombre_original='fuente.pdf', ruta_archivo='fuente.pdf', tamano=10)
        self.antes = 'I. Parte vigente.\nII. Parte retirada.\nIII. Otra parte vigente.'
        self.articulo = Articulo.objects.create(norma=self.base, rama=rama, numero_articulo='1', contenido=self.antes)

    def crear(self, operacion='deroga', alcance='Parágrafo II'):
        registrar_cambios(self.doc, [], [{'operacion': operacion, 'norma': 'Ley 99001',
            'unidad': '1' if operacion == 'deroga' else '', 'alcance': alcance,
            'cita': 'Se deroga el Parágrafo II del Artículo 1.' if operacion == 'deroga' else 'Se abroga la Ley 99001.',
            'origen': 'clausula', 'unidad_fuente': 'DD ÚNICA'}],
            {'tipo_norma': 'Ley', 'numero_norma': '99002', 'fecha_norma': '2025-01-01'})
        return CambioNormativo.objects.get(fuente=self.doc)

    @patch('modulo_catalogo.services.historial_articulos_service.actualizar_busqueda')
    def test_preview_parcial_no_modifica_y_coincide_con_confirmacion(self, _):
        cambio = self.crear()
        response = self.client.post(f'/api/catalogo/cambios-normativos/{cambio.pk}/preparar-revision/', {}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        preview = response.data['articulos'][0]
        self.assertEqual(preview['texto_antes'], self.antes)
        self.assertNotIn('II. Parte retirada.', preview['texto_despues'])
        self.articulo.refresh_from_db(); cambio.refresh_from_db()
        self.assertEqual(self.articulo.contenido, self.antes)
        self.assertEqual(cambio.estado_revision, 'pendiente')
        self.assertFalse(HistorialArticulo.objects.exists())
        confirmar(cambio, {'fecha_efecto': '2025-01-01'}, self.admin)
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.contenido, preview['texto_despues'])

    def test_abrogacion_conserva_texto_y_preview_no_confirma(self):
        cambio = self.crear('abroga', 'total')
        response = self.client.post(f'/api/catalogo/cambios-normativos/{cambio.pk}/preparar-revision/', {}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['articulos'][0]['texto_despues'], self.antes)
        cambio.refresh_from_db()
        self.assertEqual(cambio.estado_revision, 'pendiente')

    def test_fragmento_incorrecto_no_genera_preview(self):
        cambio = self.crear()
        response = self.client.post(f'/api/catalogo/cambios-normativos/{cambio.pk}/preparar-revision/', {'fragmento_afectado': 'texto inexistente'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(HistorialArticulo.objects.exists())
