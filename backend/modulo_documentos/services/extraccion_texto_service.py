import hashlib
from importlib.metadata import version

from django.core.files.storage import default_storage


class ExtraccionTextoService:
    """
    Extrae el texto plano de un archivo PDF subido. El backend hace
    esta extracción al momento de guardar el documento — el frontend
    nunca envía texto extraído, solo el archivo.
    """

    @staticmethod
    def paginas(archivo):
        """Un solo extractor para casos y catálogo; restaura el puntero."""
        from pypdf import PdfReader

        posicion = archivo.tell()
        try:
            archivo.seek(0)
            return [pagina.extract_text() or "" for pagina in PdfReader(archivo).pages]
        finally:
            archivo.seek(posicion)

    @classmethod
    def extraer_documento(cls, documento):
        from modulo_documentos.models.documento import TextoDocumentoCaso

        from django.conf import settings
        version_extractor = f"pypdf-{version('pypdf')}-ocr-v2-{settings.PDF_OCR_IDIOMA}"
        # El hash detecta incluso un PDF reemplazado conservando su ruta.
        with default_storage.open(documento.ruta_archivo, "rb") as archivo:
            digest = hashlib.sha256()
            for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
                digest.update(bloque)
            hash_pdf = digest.hexdigest()
            cache = TextoDocumentoCaso.objects.filter(
                documento=documento, hash_pdf=hash_pdf, version_extractor=version_extractor,
            ).first()
            if cache is not None:
                return cache.texto
            texto = cls.extraer(archivo)
        TextoDocumentoCaso.objects.update_or_create(
            documento=documento,
            defaults={"hash_pdf": hash_pdf, "version_extractor": version_extractor, "texto": texto},
        )
        return texto

    @classmethod
    def extraer(cls, archivo) -> str:
        """
        `archivo` es un objeto file-like (ej. request.FILES['archivo_pdf']
        o el campo `archivo` de un Documento ya guardado). Devuelve el
        texto concatenado de todas las páginas.
        """
        paginas = cls.paginas(archivo)
        if any(len(texto.strip()) < 15 for texto in paginas):
            import fitz
            from modulo_catalogo.services.ocr_local_service import transcribir_pagina
            posicion = archivo.tell()
            try:
                archivo.seek(0)
                with fitz.open(stream=archivo.read(), filetype='pdf') as pdf:
                    for indice, texto in enumerate(paginas):
                        pagina = pdf[indice]
                        # Las páginas realmente vacías no requieren OCR. Una página con
                        # imagen/dibujos y sin texto legible nunca se omite silenciosamente.
                        if len(texto.strip()) < 15 and (pagina.get_images() or pagina.get_drawings()):
                            try:
                                paginas[indice] = transcribir_pagina(pagina, indice + 1)
                            except ValueError as exc:
                                raise ValueError(f'No se pudo extraer el texto del PDF del caso. {exc}') from exc
            finally:
                archivo.seek(posicion)
        return "\n\n".join(p.strip() for p in paginas if p.strip()).strip()
