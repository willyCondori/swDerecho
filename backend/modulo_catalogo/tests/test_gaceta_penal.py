import hashlib
import tempfile
from unittest.mock import patch
from datetime import date
from django.test import TestCase, SimpleTestCase, override_settings
from django.core.files.storage import default_storage
from modulo_catalogo.models import DocumentoOficial
from modulo_catalogo.services.gaceta_service import analizar_listado, es_penal, recolectar, url_oficial
from .test_validacion_pdf_endpoints import PDF_MINIMO_1_PAGINA

BASE = 'http://www.gacetaoficialdebolivia.gob.bo'
LISTADO = """<html><body><div class="card h-100">
<p>Fecha de Publicación: 2026-10-02</p><h6>Ley N° 1773</h6><p>Título general de una norma</p>
<a href="/normas/verGratis_gob/301978">Ver Norma</a>
<a href="/normas/verGratis_gob1/301978">Word</a>
<a href="/normas/descargarNrms/301978">Descargar PDF</a></div>
<a href="/normas/listadonor/10/page:2">siguiente &gt;&gt;</a></body></html>""".encode()
CONSULTA = '<html><div id="seleccion"><p>ARTÍCULO ÚNICO. Se incorpora un parágrafo al Código Penal.</p></div></html>'.encode()

class ParserGacetaTests(SimpleTestCase):
    def test_listado_real_conserva_fecha_numero_y_pdf_sin_confundir_word(self):
        filas, siguiente = analizar_listado(LISTADO, BASE + '/normas/listadonor/10')
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]['numero'], '1773')
        self.assertEqual(filas[0]['fecha_publicacion'], date(2026,10,2))
        self.assertEqual(filas[0]['url_pdf'], BASE + '/normas/descargarNrms/301978')
        self.assertTrue(siguiente.endswith('/page:2'))

    def test_detecta_area_penal_en_contenido_sin_depender_del_titulo(self):
        self.assertTrue(es_penal('Se reforma el Código Penal.'))
        self.assertTrue(es_penal('Se reconoce la redención por trabajo.'))
        self.assertFalse(es_penal('Se fija un incentivo fiscal para la importación de trigo.'))

    def test_no_admite_urls_arbitrarias_ni_credenciales(self):
        for url in ['http://127.0.0.1/admin', 'file:///etc/passwd', 'http://www.gacetaoficialdebolivia.gob.bo.evil.test/a', 'http://user:pass@www.gacetaoficialdebolivia.gob.bo/a']:
            with self.subTest(url=url), self.assertRaises(ValueError): url_oficial(url)

class RecolectorGacetaTests(TestCase):
    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        self.addCleanup(self.directorio.cleanup)
        config = override_settings(MEDIA_ROOT=self.directorio.name, GACETA_BASE_URL=BASE, GACETA_PAUSA_SEGUNDOS=0)
        config.enable(); self.addCleanup(config.disable)

    def descargar(self, url, *args):
        if 'descargarNrms' in url: return PDF_MINIMO_1_PAGINA
        if 'verGratis' in url: return CONSULTA
        if 'page:2' in url: return b'<html><a href="/normas/verGratis_gob/301978">Ver Norma</a></html>'
        return LISTADO

    @patch('modulo_catalogo.services.gaceta_service.descargar')
    def test_descarga_original_deduplica_y_no_confunde_descarga_con_carga_al_catalogo(self, descargar):
        descargar.side_effect = self.descargar
        resumen = recolectar(1, fuentes=['/normas/listadonor/10'])
        documento = DocumentoOficial.objects.get()
        self.assertEqual(resumen['descargados'], 1)
        self.assertEqual(resumen['cobertura'], 'parcial')
        self.assertEqual(documento.hash_pdf, hashlib.sha256(PDF_MINIMO_1_PAGINA).hexdigest())
        self.assertIsNone(documento.documento_catalogo)
        self.assertTrue(default_storage.exists(documento.ruta_archivo))
        repetida = recolectar(1, fuentes=['/normas/listadonor/10'])
        self.assertEqual(repetida['existentes'], 1)
        self.assertEqual(DocumentoOficial.objects.count(), 1)

    @patch('modulo_catalogo.services.gaceta_service.descargar')
    def test_pdf_falso_se_registra_como_error_y_se_puede_reintentar(self, descargar):
        descargar.side_effect = lambda url, *args: b'<html>Error</html>' if 'descargarNrms' in url else self.descargar(url)
        resumen = recolectar(1, fuentes=['/normas/listadonor/10'])
        self.assertTrue(resumen['errores'])
        self.assertEqual(DocumentoOficial.objects.get().estado_descarga, 'error')
        descargar.side_effect = self.descargar
        self.assertEqual(recolectar(1, fuentes=['/normas/listadonor/10'])['descargados'], 1)

    @patch('modulo_catalogo.services.gaceta_service.descargar')
    def test_corte_de_fecha_no_descarga_publicaciones_fuera_del_intervalo(self, descargar):
        descargar.side_effect = self.descargar
        resumen = recolectar(1, desde=date(2026,10,3), fuentes=['/normas/listadonor/10'])
        self.assertEqual(resumen['consultados'], 0)
        self.assertFalse(DocumentoOficial.objects.exists())

    @patch('modulo_catalogo.services.gaceta_service.descargar')
    def test_recorrido_sin_limite_sigue_paginacion_hasta_ultima_pagina(self, descargar):
        descargar.side_effect = self.descargar
        resumen = recolectar(0, fuentes=['/normas/listadonor/10'])
        self.assertEqual(resumen['paginas'], 2)
        self.assertEqual(resumen['descargados'], 1)
        self.assertEqual(resumen['cobertura'], 'listados_recorridos')

    @patch('modulo_catalogo.services.gaceta_service.descargar')
    def test_resoluciones_sin_pdf_no_se_informan_como_cobertura_completa(self, descargar):
        descargar.side_effect = [b'<a href="/resolucions/listadonor1/AGRARIAS">Agrarias</a>',
            '<div class="card"><h6>Resolución Suprema N° 10</h6></div>'.encode()]
        resumen = recolectar(0, fuentes=['/resolucions/listadomin'])
        self.assertEqual(resumen['cobertura'], 'parcial')
        self.assertIn('sin enlaces', resumen['errores'][0]['error'])
