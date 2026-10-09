from .chunk import ChunkCaso
from .embedding import EntidadDetectadaCaso, EmbeddingArticulo, EmbeddingChunk
from .resultado import ResultadoArticulo
from .jurisprudencia import (
    ResolucionJurisprudencia, FragmentoJurisprudencia,
    EmbeddingJurisprudencia, ResultadoJurisprudencia,
)

__all__ = [
    "ChunkCaso",
    "EntidadDetectadaCaso",
    "EmbeddingArticulo",
    "EmbeddingChunk",
    "ResultadoArticulo",
]
