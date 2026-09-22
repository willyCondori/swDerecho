"""
Tests de core.utils.archivos.validar_pdf: firma del PDF, que se pueda abrir
con pypdf y que tenga al menos una página. No dependen de la base de datos.
"""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from core.utils.archivos import validar_pdf

PDF_MINIMO_1_PAGINA = b"%PDF-1.3\n%\x93\x8c\x8b\x9e ReportLab Generated PDF document (opensource)\n1 0 obj\n<<\n/F1 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/BaseFont /Helvetica /Encoding /WinAnsiEncoding /Name /F1 /Subtype /Type1 /Type /Font\n>>\nendobj\n3 0 obj\n<<\n/Contents 7 0 R /MediaBox [ 0 0 595.2756 841.8898 ] /Parent 6 0 R /Resources <<\n/Font 1 0 R /ProcSet [ /PDF /Text /ImageB /ImageC /ImageI ]\n>> /Rotate 0 /Trans <<\n\n>> \n  /Type /Page\n>>\nendobj\n4 0 obj\n<<\n/PageMode /UseNone /Pages 6 0 R /Type /Catalog\n>>\nendobj\n5 0 obj\n<<\n/Author (anonymous) /CreationDate (D:20260922030645+00'00') /Creator (anonymous) /Keywords () /ModDate (D:20260922030645+00'00') /Producer (ReportLab PDF Library - \\(opensource\\)) \n  /Subject (unspecified) /Title (untitled) /Trapped /False\n>>\nendobj\n6 0 obj\n<<\n/Count 1 /Kids [ 3 0 R ] /Type /Pages\n>>\nendobj\n7 0 obj\n<<\n/Filter [ /ASCII85Decode /FlateDecode ] /Length 114\n>>\nstream\nGapQh0E=F,0U\\H3T\\pNYT^QKk?tc>IP,;W#U1^23ihPEM_?CW4KISi::p;W-:^G0Ccu@*&0$R,8/'1j`8Q@/e.SWW0e5Q^q;@(YOku$@?!6%nQ)u~>endstream\nendobj\nxref\n0 8\n0000000000 65535 f \n0000000061 00000 n \n0000000092 00000 n \n0000000199 00000 n \n0000000402 00000 n \n0000000470 00000 n \n0000000731 00000 n \n0000000790 00000 n \ntrailer\n<<\n/ID \n[<e3c564374ff070f36f1213b0fb8d46a5><e3c564374ff070f36f1213b0fb8d46a5>]\n% ReportLab generated PDF document -- digest (opensource)\n\n/Info 5 0 R\n/Root 4 0 R\n/Size 8\n>>\nstartxref\n994\n%%EOF\n"


def subir(contenido, nombre="doc.pdf"):
    return SimpleUploadedFile(nombre, contenido, content_type="application/pdf")


class ValidarPdfTests(SimpleTestCase):
    def test_pdf_valido_pasa_y_deja_el_archivo_al_inicio(self):
        archivo = subir(PDF_MINIMO_1_PAGINA)
        valido, motivo = validar_pdf(archivo)
        self.assertTrue(valido)
        self.assertEqual(motivo, "")
        self.assertEqual(archivo.tell(), 0)

    def test_extension_pdf_con_contenido_ajeno_se_rechaza_por_la_firma(self):
        # Un .exe (o cualquier binario) renombrado a .pdf: pasa el filtro
        # de extensión y tamaño, pero no tiene la firma %PDF-.
        archivo = subir(b"MZ\x90\x00\x03\x00\x00\x00binario falso")
        valido, motivo = validar_pdf(archivo)
        self.assertFalse(valido)
        self.assertIn("firma", motivo)
        self.assertEqual(archivo.tell(), 0)

    def test_texto_plano_renombrado_a_pdf_se_rechaza(self):
        archivo = subir(b"Esto es un documento de texto comun, no un PDF.")
        valido, motivo = validar_pdf(archivo)
        self.assertFalse(valido)
        self.assertIn("firma", motivo)

    def test_archivo_vacio_se_rechaza_por_la_firma(self):
        valido, motivo = validar_pdf(subir(b""))
        self.assertFalse(valido)
        self.assertIn("firma", motivo)

    def test_firma_correcta_pero_pdf_truncado_se_rechaza_al_abrirlo(self):
        # Empieza con %PDF- (pasa la firma) pero el resto está corrupto/incompleto.
        archivo = subir(b"%PDF-1.4\nesto no es una estructura de PDF valida en absoluto")
        valido, motivo = validar_pdf(archivo)
        self.assertFalse(valido)
        self.assertIn("dañado", motivo)

    def test_deja_el_archivo_reposicionado_al_inicio_incluso_si_es_invalido(self):
        archivo = subir(b"no es un pdf")
        validar_pdf(archivo)
        self.assertEqual(archivo.tell(), 0)
        # y se puede seguir leyendo con normalidad después
        self.assertEqual(archivo.read(), b"no es un pdf")

    def test_no_consume_el_archivo_para_quien_lo_use_despues(self):
        archivo = subir(PDF_MINIMO_1_PAGINA)
        validar_pdf(archivo)
        # simula el guardado posterior en disco vía .chunks()
        contenido = b"".join(archivo.chunks())
        self.assertEqual(contenido, PDF_MINIMO_1_PAGINA)

    def test_funciona_con_un_archivo_en_memoria_tipo_bytesio_con_name(self):
        # Como cuando el contenido llega ya leído en memoria (InMemoryUploadedFile).
        buf = io.BytesIO(PDF_MINIMO_1_PAGINA)
        buf.seek(0)
        valido, _ = validar_pdf(buf)
        self.assertTrue(valido)
