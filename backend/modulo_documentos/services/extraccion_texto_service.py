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

        version_extractor = f"pypdf-{version('pypdf')}-v1"
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
        return "\n\n".join(p.strip() for p in cls.paginas(archivo) if p.strip()).strip()
