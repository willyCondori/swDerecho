from modulo_ia.models.embedding import EmbeddingChunk
from modulo_ia.services.model_loader import DIMENSION_VECTOR, obtener_modelo, version_activa


class EmbeddingService:
    """
    Genera y persiste el embedding (vector 768-dim) de cada ChunkCaso, con
    la versión de modelo activa (ver modulo_ia.services.model_loader).
    """

    @staticmethod
    def _obtener_vector(texto: str) -> list:
        modelo = obtener_modelo()
        return modelo.encode(texto, normalize_embeddings=True).tolist()

    @classmethod
    def generar_para_caso(cls, chunks):
        """
        Genera el embedding de cada chunk, con la versión de modelo
        activa, y lo persiste. update_or_create está keyed por
        (chunk, modelo_version): si el caso se reanaliza con la MISMA
        versión activa, actualiza ese vector en vez de duplicarlo; si se
        reanaliza después de cambiar de versión, agrega una fila nueva
        sin tocar la de la versión anterior.
        """
        version = version_activa()
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
                modelo_version=version,
                defaults={"vector": vector},
            )
            embeddings.append(embedding)
        return embeddings
