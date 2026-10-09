from modulo_ia.models.embedding import EmbeddingChunk
from modulo_ia.services.model_loader import DIMENSION_VECTOR, version_activa
from modulo_ia.services.vectorizacion_service import vectorizar_textos


class EmbeddingService:
    """
    Genera y persiste el embedding (vector 768-dim) de cada ChunkCaso, con
    la versión de modelo activa (ver modulo_ia.services.model_loader).
    """

    @staticmethod
    def _obtener_vector(texto: str) -> list:
        return vectorizar_textos([texto], tipo="query")[0]

    @classmethod
    def preparar_vectores(cls, chunks):
        return vectorizar_textos([chunk.contenido for chunk in chunks], tipo="query")

    @classmethod
    def generar_para_caso(cls, chunks, vectores=None):
        """
        Genera el embedding de cada chunk, con la versión de modelo
        activa, y lo persiste. update_or_create está keyed por
        (chunk, modelo_version): si el caso se reanaliza con la MISMA
        versión activa, actualiza ese vector en vez de duplicarlo; si se
        reanaliza después de cambiar de versión, agrega una fila nueva
        sin tocar la de la versión anterior.
        """
        version = version_activa()
        chunks = list(chunks)
        vectores = cls.preparar_vectores(chunks) if vectores is None else vectores
        if len(vectores) != len(chunks):
            raise ValueError("Cada chunk debe tener exactamente un embedding.")
        embeddings = []
        for chunk, vector in zip(chunks, vectores):
            if len(vector) != DIMENSION_VECTOR:
                raise ValueError(
                    f"El embedding generado tiene {len(vector)} dimensiones, "
                    f"se esperaban {DIMENSION_VECTOR}."
                )
            embeddings.append(EmbeddingChunk(chunk=chunk, modelo_version=version, vector=vector))
        return EmbeddingChunk.objects.bulk_create(
            embeddings, update_conflicts=True, update_fields=["vector"],
            unique_fields=["chunk", "modelo_version"],
        )
