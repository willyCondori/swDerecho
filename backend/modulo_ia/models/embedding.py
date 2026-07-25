from django.db import models
from pgvector.django import VectorField
from .chunk import ChunkCaso
from modulo_catalogo.models.articulo import Articulo


class EntidadDetectadaCaso(models.Model):
    """
    Entidad jurídica detectada automáticamente en un chunk del caso.
    valor_detectado: texto exacto detectado (ej: 'menor de edad').
    score: confianza de la detección (0-1).
    """
    chunk           = models.ForeignKey(
                          ChunkCaso,
                          on_delete=models.CASCADE,
                          related_name="entidades_detectadas",
                      )
    valor_detectado = models.CharField(max_length=255)
    score           = models.FloatField(default=0.0)

    class Meta:
        db_table = "entidades_detectadas_caso"
        indexes  = [
            models.Index(fields=["chunk"],  name="idx_entdet_chunk"),
            models.Index(fields=["-score"], name="idx_entdet_score"),
        ]

    def __str__(self):
        return f"{self.valor_detectado} (score={self.score:.2f})"


class EmbeddingArticulo(models.Model):
    """
    Vector semántico de un artículo jurídico generado con Sentence Transformers.
    Se indexa con HNSW (pgvector) para búsqueda coseno eficiente.
    """
    articulo   = models.OneToOneField(
                     Articulo,
                     on_delete=models.CASCADE,
                     related_name="embedding",
                 )
    vector     = VectorField(dimensions=768, help_text="Embedding 768-dim (all-mpnet-base-v2).")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "embeddings_articulos"
        indexes  = [
            models.Index(fields=["articulo"], name="idx_emb_art_articulo"),
            # El índice HNSW se crea en migración personalizada:
            # CREATE INDEX idx_emb_art_vector ON embeddings_articulos
            # USING hnsw (vector vector_cosine_ops);
        ]

    def __str__(self):
        return f"Embedding — {self.articulo}"


class EmbeddingChunk(models.Model):
    """
    Vector semántico de un chunk del caso.
    Se compara contra EmbeddingArticulo con cosine similarity (pgvector).
    """
    chunk      = models.OneToOneField(
                     ChunkCaso,
                     on_delete=models.CASCADE,
                     related_name="embedding",
                 )
    vector     = VectorField(dimensions=768)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "embeddings_chunk"
        indexes  = [
            models.Index(fields=["chunk"], name="idx_emb_chunk_chunk"),
            # CREATE INDEX idx_emb_chunk_vector ON embeddings_chunk
            # USING hnsw (vector vector_cosine_ops);
        ]

    def __str__(self):
        return f"Embedding — {self.chunk}"
