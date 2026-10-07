from datetime import date
from unittest.mock import patch
from rest_framework.test import APITestCase
from modulo_catalogo.models import Norma, RamaDerecho, Articulo, DocumentoNorma, CambioNormativo, HistorialArticulo
from modulo_catalogo.services.vigencia_service import registrar_cambios, confirmar
from modulo_usuarios.tests.factories import crear_usuario, crear_rol


class RestauracionTests(APITestCase):
    def setUp(self):
        self.admin = crear_usuario('restaurar.admin', rol=crear_rol('Administrador'))
        self.client.force_authenticate(self.admin)
        self.rama = RamaDerecho.objects.create(nombre='Penal restauración')
        self.base = Norma.objects.create(nombre='Ley anterior restauración', tipo_norma='Ley', numero_norma='99001', fecha_norma=date(2000, 1, 1))
        self.nueva = Norma.objects.create(nombre='Ley restauración', tipo_norma='Ley', numero_norma='99002', fecha_norma=date(2025, 1, 1))
        self.doc = DocumentoNorma.objects.create(norma=self.nueva, rama=self.rama, nombre_original='fuente.pdf', ruta_archivo='fuente.pdf', tamano=10)
        self.antes = 'I. Parte vigente.\nII. Parte retirada.\nIII. Otra parte vigente.'
        self.articulo = Articulo.objects.create(norma=self.base, rama=self.rama, numero_articulo='1', contenido=self.antes)

    def crear_cambio(self, operacion='deroga', alcance='Parágrafo II', efecto='2025-01-01'):
        dato = {'operacion': operacion, 'norma': 'Ley 99001', 'unidad': '1' if operacion == 'deroga' else '', 'alcance': alcance,
                'cita': 'Se deroga el Parágrafo II del Artículo 1.' if operacion == 'deroga' else 'Se abroga la Ley 99001.',
                'origen': 'clausula', 'unidad_fuente': 'DD ÚNICA'}
        registrar_cambios(self.doc, [], [dato], {'tipo_norma': 'Ley', 'numero_norma': '99002', 'fecha_norma': '2025-01-01'})
        cambio = CambioNormativo.objects.get(fuente=self.doc)
        return confirmar(cambio, {'fecha_efecto': efecto}, self.admin)

    def restaurar(self, cambio):
        return self.client.post(f'/api/catalogo/cambios-normativos/{cambio.pk}/restaurar/', {'confirmar': True}, format='json')

    def test_restauracion_parcial_recupera_texto_con_auditoria_y_fuente(self):
        cambio = self.crear_cambio()
        historial = HistorialArticulo.objects.get(cambio=cambio)
        fecha_original = cambio.revisado_at
        resp = self.client.get(f'/api/catalogo/cambios-normativos/{cambio.pk}/preparar-restauracion/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['restaurable'])
        self.assertEqual(resp.data['historial'][0]['texto_antes'], self.antes)
        resp = self.restaurar(cambio)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.articulo.refresh_from_db(); cambio.refresh_from_db(); historial.refresh_from_db()
        self.assertEqual(self.articulo.contenido, self.antes)
        self.assertEqual(cambio.estado_revision, 'revertido')
        self.assertEqual(cambio.restaurado_por, self.admin)
        self.assertIsNotNone(cambio.restaurado_at)
        self.assertEqual(cambio.revisado_at, fecha_original)
        self.assertEqual(historial.texto_antes, self.antes)
        self.assertNotEqual(historial.texto_despues, self.antes)
        self.assertEqual(self.articulo.avisos_vigencia, [])
        self.assertEqual(self.restaurar(cambio).status_code, 400)

    def test_no_sobrescribe_cambios_posteriores(self):
        cambio = self.crear_cambio()
        self.articulo.contenido = 'Reforma posterior.'; self.articulo.save()
        resp = self.restaurar(cambio)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('cambió después', resp.data['detail'])
        self.articulo.refresh_from_db(); cambio.refresh_from_db()
        self.assertEqual(self.articulo.contenido, 'Reforma posterior.')
        self.assertEqual(cambio.estado_revision, 'confirmado')

    def test_restaurar_exige_admin_y_confirmacion_explicita(self):
        cambio = self.crear_cambio()
        resp = self.client.post(f'/api/catalogo/cambios-normativos/{cambio.pk}/restaurar/', {}, format='json')
        self.assertEqual(resp.status_code, 400)
        abogado = crear_usuario('restaurar.abogado', rol=crear_rol('Abogado'))
        self.client.force_authenticate(abogado)
        self.assertEqual(self.restaurar(cambio).status_code, 403)
        self.assertEqual(self.client.get(f'/api/catalogo/cambios-normativos/{cambio.pk}/preparar-restauracion/').status_code, 403)

    def test_fallo_de_busqueda_revierte_restauracion_completa(self):
        cambio = self.crear_cambio()
        self.articulo.refresh_from_db(); despues = self.articulo.contenido
        with patch('modulo_catalogo.services.historial_articulos_service.actualizar_busqueda', side_effect=ValueError('Fallo de vectorización')):
            self.assertEqual(self.restaurar(cambio).status_code, 400)
        self.articulo.refresh_from_db(); cambio.refresh_from_db()
        self.assertEqual(self.articulo.contenido, despues)
        self.assertEqual(cambio.estado_revision, 'confirmado')
        self.assertIsNone(cambio.restaurado_at)

    def test_abrogacion_de_norma_restaura_confirmacion_completa(self):
        otro = Articulo.objects.create(norma=self.base, rama=self.rama, numero_articulo='2', contenido='Otro artículo.')
        cambio = self.crear_cambio(operacion='abroga', alcance='total')
        self.assertEqual(HistorialArticulo.objects.filter(cambio=cambio).count(), 2)
        self.assertEqual(self.restaurar(cambio).status_code, 200)
        self.base.refresh_from_db(); self.articulo.refresh_from_db(); otro.refresh_from_db()
        self.assertEqual(self.base.avisos_vigencia, [])
        self.assertEqual(self.articulo.contenido, self.antes)
        self.assertEqual(otro.contenido, 'Otro artículo.')

    def test_cancelar_efecto_futuro_no_modifica_texto(self):
        cambio = self.crear_cambio(efecto='2099-01-01')
        self.assertEqual(self.restaurar(cambio).status_code, 200)
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.contenido, self.antes)
        from modulo_catalogo.services.historial_articulos_service import aplicar_texto_confirmado
        aplicar_texto_confirmado(cambio)  # Un objeto antiguo no puede reaplicar el efecto cancelado.
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.contenido, self.antes)

    def test_recarga_no_reaplica_confirmacion_restaurada(self):
        cambio = self.crear_cambio()
        self.restaurar(cambio)
        registrar_cambios(self.doc, [], self.doc.analisis_normativo['cambios_aplicados'], self.doc.metadatos)
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.contenido, self.antes)
        self.assertEqual(CambioNormativo.objects.count(), 1)
        self.assertEqual(self.articulo.avisos_vigencia, [])
