from django.conf import settings

from modulo_ia.models.embedding import EmbeddingChunk

DIMENSION_VECTOR = 768  # coincide con paraphrase-mpnet-base-v2 y VectorField(dimensions=768)

_modelo_cache = None  # singleton a nivel de módulo/worker, evita recargar el modelo en cada chunk


def _obtener_modelo():
    global _modelo_cache
    if _modelo_cache is None:
        from sentence_transformers import SentenceTransformer
        _modelo_cache = SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL)
    return _modelo_cache


class EmbeddingService:
    """
    Genera y persiste el embedding (vector 768-dim) de cada ChunkCaso,
    usando el modelo configurado en settings.SENTENCE_TRANSFORMER_MODEL
    (por defecto: sentence-transformers/paraphrase-mpnet-base-v2).
    """

    @staticmethod
    def _obtener_vector(texto: str) -> list:
        modelo = _obtener_modelo()
        return modelo.encode(texto, normalize_embeddings=True).tolist()

    @classmethod
    def generar_para_caso(cls, chunks):
        """
        Genera el embedding de cada chunk y lo persiste. Usa
        update_or_create porque EmbeddingChunk.chunk es OneToOne: si el
        caso se reanaliza, actualiza el vector existente en vez de
        intentar crear un duplicado.
        """
        embeddings = []
        for chunk in chunks:
            vector = cls._obtener_vector(chunk.contenido)
            if len(vector) != DIMENSION_VECTOR:
                raise ValueError(
                    f"El embedding generado tiene {len(vector)} dimensiones, "
                    f"se esperaban {DIMENSION_VECTOR}."
                )
            embedding, _ = EmbeddingChunk.objects.update_or_create(
                chunk=chunk,
                defaults={"vector": vector},
            )
            embeddings.append(embedding)
        return embeddings