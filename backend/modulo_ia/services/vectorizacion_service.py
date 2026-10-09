import numpy as np
from django.conf import settings

from modulo_ia.services.model_loader import DIMENSION_VECTOR, obtener_modelo


def vectorizar_textos(textos, modelo=None, *, tipo="passage"):
    """Encode por lotes; valida antes de escribir cualquier vector en la BD."""
    if not textos:
        return []
    if tipo not in ("query", "passage"):
        raise ValueError("Tipo de embedding inválido: use query o passage.")
    if settings.EMBEDDING_USE_E5_PREFIXES:
        textos = [f"{tipo}: {texto}" for texto in textos]
    modelo = modelo if modelo is not None else obtener_modelo()
    vectores = np.asarray(modelo.encode(
        textos, batch_size=settings.EMBEDDING_BATCH_SIZE, normalize_embeddings=True,
    ))
    if vectores.shape != (len(textos), DIMENSION_VECTOR) or not np.isfinite(vectores).all():
        raise ValueError(f"Los embeddings deben tener {DIMENSION_VECTOR} dimensiones finitas por texto.")
    return vectores.tolist()
