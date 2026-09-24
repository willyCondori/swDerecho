"""
python manage.py vincular_documentos_norma: registra en DocumentoNorma
los PDF que ya estaban en MEDIA_ROOT/documentos_normativas/ antes de que
existiera ese modelo (ver la cabecera del comando para el porqué).
"""
import os
import shutil
import tempfile
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from modulo_catalogo.models.documento_norma import DocumentoNorma
from modulo_catalogo.models.norma import Norma


class VincularDocumentosNormaTests(TestCase):

    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        self._override = override_settings(MEDIA_ROOT=self.media_root)
        self._override.enable()
        self.addCleanup(self._override.disable)

        self.cp = Norma.objects.create(nombre="Norma Penal de Prueba", sigla="NPP")
        self.cpe = Norma.objects.create(nombre="Norma Constitucional de Prueba", sigla="NCP")

    def _crear_pdf(self, *partes):
        ruta = os.path.join(self.media_root, "documentos_normativas", *partes)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "wb") as f:
            f.write(b"%PDF-1.4 dummy")
        return ruta

    def _correr(self, *args):
        salida = StringIO()
        call_command("vincular_documentos_norma", *args, stdout=salida)
        return salida.getvalue()

    def test_carpeta_que_coincide_con_la_sigla_se_detecta(self):
        self._crear_pdf("npp", "npp_codigo_penal.pdf")

        salida = self._correr()  # simulación: no escribe nada

        self.assertIn("npp_codigo_penal.pdf", salida)
        self.assertEqual(DocumentoNorma.objects.count(), 0)

    def test_simulacion_no_escribe_nada(self):
        self._crear_pdf("npp", "npp_codigo_penal.pdf")
        self._correr()
        self.assertEqual(DocumentoNorma.objects.count(), 0)

    def test_aplicar_crea_el_documento_norma(self):
        self._crear_pdf("npp", "npp_codigo_penal.pdf")

        salida = self._correr("--aplicar")

        doc = DocumentoNorma.objects.get()
        self.assertEqual(doc.norma_id, self.cp.pk)
        self.assertEqual(doc.nombre_original, "npp_codigo_penal.pdf")
        self.assertEqual(doc.ruta_archivo, os.path.join("documentos_normativas", "npp", "npp_codigo_penal.pdf"))
        # El mensaje tiene que decir explícitamente el ID de la NORMA
        # (no solo el del DocumentoNorma recién creado), para que no se
        # confundan al elegir a mano el --norma-id de otro archivo.
        self.assertIn(f"norma id={self.cp.pk}", salida)

    def test_carpeta_que_coincide_con_el_nombre_completo(self):
        self._crear_pdf("norma_constitucional_de_prueba", "ncp.pdf")

        self._correr("--aplicar")

        self.assertEqual(DocumentoNorma.objects.get().norma_id, self.cpe.pk)

    def test_carpeta_sin_coincidencia_queda_pendiente_y_no_crea_nada(self):
        self._crear_pdf("penal", "penal_codigo_penal.pdf")

        salida = self._correr("--aplicar")

        self.assertEqual(DocumentoNorma.objects.count(), 0)
        self.assertIn("penal_codigo_penal.pdf", salida)
        self.assertIn("sin ninguna norma", salida)

    def test_correrlo_dos_veces_no_duplica(self):
        self._crear_pdf("npp", "npp_codigo_penal.pdf")

        self._correr("--aplicar")
        self._correr("--aplicar")

        self.assertEqual(DocumentoNorma.objects.count(), 1)

    def test_vincular_manual_de_una_carpeta_sin_coincidencia(self):
        self._crear_pdf("penal", "penal_codigo_penal.pdf")

        self._correr("--vincular", "documentos_normativas/penal/penal_codigo_penal.pdf",
                      "--norma-id", str(self.cp.pk))

        doc = DocumentoNorma.objects.get()
        self.assertEqual(doc.norma_id, self.cp.pk)
        self.assertEqual(doc.nombre_original, "penal_codigo_penal.pdf")

    def test_vincular_manual_sin_norma_id_da_error(self):
        self._crear_pdf("penal", "penal_codigo_penal.pdf")

        with self.assertRaises(Exception):
            self._correr("--vincular", "documentos_normativas/penal/penal_codigo_penal.pdf")
        self.assertEqual(DocumentoNorma.objects.count(), 0)

    def test_vincular_manual_de_un_archivo_inexistente_da_error(self):
        with self.assertRaises(Exception):
            self._correr("--vincular", "documentos_normativas/no_existe.pdf", "--norma-id", str(self.cp.pk))

    def test_vincular_manual_sobre_uno_ya_registrado_no_duplica(self):
        self._crear_pdf("penal", "penal_codigo_penal.pdf")
        self._correr("--vincular", "documentos_normativas/penal/penal_codigo_penal.pdf",
                      "--norma-id", str(self.cp.pk))

        self._correr("--vincular", "documentos_normativas/penal/penal_codigo_penal.pdf",
                      "--norma-id", str(self.cpe.pk))

        self.assertEqual(DocumentoNorma.objects.count(), 1)
        self.assertEqual(DocumentoNorma.objects.get().norma_id, self.cp.pk)  # no se pisó

    def test_archivos_ya_registrados_no_se_vuelven_a_listar(self):
        self._crear_pdf("npp", "ya_registrado.pdf")
        self._correr("--aplicar")

        salida = self._correr()  # simulación de nuevo

        self.assertNotIn("ya_registrado.pdf", salida)
        self.assertIn("No hay archivos pendientes", salida)

    def test_ignora_archivos_que_no_son_pdf(self):
        self._crear_pdf("npp", "notas.txt")

        self._correr("--aplicar")

        self.assertEqual(DocumentoNorma.objects.count(), 0)

    def test_sigla_ambigua_entre_dos_normas_queda_pendiente(self):
        Norma.objects.create(nombre="Otra norma con sigla NPP", sigla="npp")
        self._crear_pdf("npp", "ambiguo.pdf")

        salida = self._correr("--aplicar")

        self.assertEqual(DocumentoNorma.objects.count(), 0)
        self.assertIn("coincide con 2 normas distintas", salida)
