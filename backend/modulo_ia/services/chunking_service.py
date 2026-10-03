import re

from django.db import transaction

from modulo_ia.models.chunk import ChunkCaso

TAMANO_CHUNK = 300     # caracteres aprox. por chunk
SOLAPAMIENTO = 50     # caracteres compartidos entre chunk y chunk


def extraer_texto_pdf(documento) -> str:
    """Lee ruta_archivo mediante el storage y reutiliza la extracción por hash."""
    from modulo_documentos.services.extraccion_texto_service import ExtraccionTextoService

    return ExtraccionTextoService.extraer_documento(documento)


class ChunkingService:
    """
    Convierte el texto de un Caso (descripción redactada, o el texto
    extraído del PDF adjunto) en fragmentos (ChunkCaso).

    Se usan chunks en vez de vectorizar el texto completo porque los
    modelos de embeddings tienen límite de tokens, y porque un caso
    puede tocar varios temas jurídicos a la vez.
    """

    @staticmethod
    def _obtener_texto_y_tipo(caso):
        """
        Prioriza el PDF si existe (extrayendo su texto real con
        pypdf); si no hay PDF, usa la descripción redactada.
        Devuelve (texto, tipo) donde tipo ∈ ChunkCaso.TIPO_CHOICES.
        """
        documento_pdf = caso.documentos.filter(tipo_archivo="pdf").order_by("-created_at").first()
        if documento_pdf:
            texto = extraer_texto_pdf(documento_pdf)
            if texto:
                return texto, "pdf"
            # PDF sin texto extraíble (ej. escaneado sin OCR): cae a la descripción
        return (caso.descripcion or ""), "texto"

    @staticmethod
    def _partir_en_fragmentos(texto, tamano=TAMANO_CHUNK, solapamiento=SOLAPAMIENTO):
        parrafos = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
        fragmentos = []
        buffer = ""

        for parrafo in parrafos:
            if len(buffer) + len(parrafo) <= tamano:
                buffer = f"{buffer}\n\n{parrafo}".strip()
            else:
                if buffer:
                    fragmentos.append(buffer)
                if len(parrafo) > tamano:
                    inicio = 0
                    while inicio < len(parrafo):
                        fragmentos.append(parrafo[inicio: inicio + tamano])
                        inicio += tamano - solapamiento
                    buffer = ""
                else:
                    buffer = parrafo

        if buffer:
            fragmentos.append(buffer)

        return fragmentos

    @classmethod
    def preparar_chunks(cls, caso):
        """
        Extrae y fragmenta sin reemplazar todavía el análisis anterior.
        """
        texto, tipo = cls._obtener_texto_y_tipo(caso)
        if not texto.strip():
            raise ValueError(
                "El caso no tiene texto para analizar: la descripción está "
                "vacía y el PDF (si existe) no tiene texto extraíble "
                "(posiblemente es un escaneo sin OCR)."
            )

        fragmentos = cls._partir_en_fragmentos(texto)

        return [
            ChunkCaso(caso=caso, orden=i, contenido=fragmento, tipo=tipo)
            for i, fragmento in enumerate(fragmentos)
        ]

    @staticmethod
    def persistir_chunks(caso, chunks):
        ChunkCaso.objects.filter(caso=caso).delete()
        return ChunkCaso.objects.bulk_create(chunks)

    @classmethod
    def crear_chunks(cls, caso):
        chunks = cls.preparar_chunks(caso)
        with transaction.atomic():
            return cls.persistir_chunks(caso, chunks)
