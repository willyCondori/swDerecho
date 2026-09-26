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

    Un artículo puede tener VARIOS embeddings, uno por cada versión de
    modelo con la que se generó (ver modulo_ia.services.model_loader).
    Nunca se sobrescribe el de una versión anterior: cambiar de modelo
    (por ejemplo, al modelo afinado con el dataset de TSJ) agrega una
    fila nueva en vez de reemplazar la existente, así que volver al
    modelo anterior es instantáneo — sus embeddings ya están ahí.
    """
    articulo       = models.ForeignKey(
                         Articulo,
                         on_delete=models.CASCADE,
                         related_name="embeddings",
                     )
    modelo_version = models.CharField(
                         max_length=100,
                         help_text="Etiqueta de la versión de modelo con la que se generó "
                                   "este vector (ver settings.EMBEDDING_MODEL_VERSION).",
                     )
    vector          = VectorField(dimensions=768, help_text="Embedding 768-dim.")
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "embeddings_articulos"
        constraints = [
            models.UniqueConstraint(
                fields=["articulo", "modelo_version"],
                name="uq_embedding_articulo_version",
            ),
        ]
        indexes  = [
            models.Index(fields=["articulo"], name="idx_emb_art_articulo"),
            models.Index(fields=["modelo_version"], name="idx_emb_art_version"),
            # El índice HNSW se crea en migración personalizada:
            # CREATE INDEX idx_emb_art_vector ON embeddings_articulos
            # USING hnsw (vector vector_cosine_ops);
        ]

    def __str__(self):
        return f"Embedding [{self.modelo_version}] — {self.articulo}"


class EmbeddingChunk(models.Model):
    """
    Vector semántico de un chunk del caso.
    Se compara contra EmbeddingArticulo con cosine similarity (pgvector).

    Igual que EmbeddingArticulo: varios por chunk, uno por modelo_version.
    Reanalizar un caso con la misma versión activa reemplaza el vector de
    ESA versión (ver EmbeddingService), no crea filas nuevas cada vez.
    """
    chunk           = models.ForeignKey(
                         ChunkCaso,
                         on_delete=models.CASCADE,
                         related_name="embeddings",
                     )
    modelo_version  = models.CharField(max_length=100)
    vector          = VectorField(dimensions=768)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "embeddings_chunk"
        constraints = [
            models.UniqueConstraint(
                fields=["chunk", "modelo_version"],
                name="uq_embedding_chunk_version",
            ),
        ]
        indexes  = [
            models.Index(fields=["chunk"], name="idx_emb_chunk_chunk"),
            models.Index(fields=["modelo_version"], name="idx_emb_chunk_version"),
            # CREATE INDEX idx_emb_chunk_vector ON embeddings_chunk
            # USING hnsw (vector vector_cosine_ops);
        ]

    def __str__(self):
        return f"Embedding [{self.modelo_version}] — {self.chunk}"
