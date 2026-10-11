from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from pgvector.django import IvfflatIndex
from django.db import models
from pgvector.django import VectorField


class ResolucionJurisprudencia(models.Model):
    fuente_id = models.CharField(max_length=40, unique=True)
    numero = models.CharField(max_length=150, blank=True)
    expediente = models.CharField(max_length=255, blank=True)
    fecha = models.DateField(null=True, blank=True)
    materia = models.CharField(max_length=150, default="Penal")
    sala = models.CharField(max_length=255, blank=True)
    departamento = models.CharField(max_length=150, blank=True)
    url_fuente = models.URLField(max_length=1000)
    url_pdf = models.URLField(max_length=2000, blank=True)
    texto = models.TextField()
    huella = models.CharField(max_length=64)
    activa = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jurisprudencia_resoluciones"


class FragmentoJurisprudencia(models.Model):
    busqueda = models.GeneratedField(expression=SearchVector("contenido", config="spanish"),
        output_field=SearchVectorField(), db_persist=True)
    resolucion = models.ForeignKey(ResolucionJurisprudencia, on_delete=models.CASCADE, related_name="fragmentos")
    orden = models.PositiveIntegerField()
    contenido = models.TextField()

    class Meta:
        db_table = "jurisprudencia_fragmentos"
        indexes = [GinIndex(fields=["busqueda"], name="idx_juris_texto")]
        constraints = [models.UniqueConstraint(fields=["resolucion", "orden"], name="uq_juris_fragmento_orden")]


class EmbeddingJurisprudencia(models.Model):
    fragmento = models.ForeignKey(FragmentoJurisprudencia, on_delete=models.CASCADE, related_name="embeddings")
    modelo_version = models.CharField(max_length=100, db_index=True)
    vector = VectorField(dimensions=768)

    class Meta:
        db_table = "jurisprudencia_embeddings"
        indexes = [IvfflatIndex(fields=["vector"], name="idx_juris_vector", lists=200, opclasses=["vector_cosine_ops"])]
        constraints = [models.UniqueConstraint(fields=["fragmento", "modelo_version"], name="uq_juris_embedding_version")]


class ResultadoJurisprudencia(models.Model):
    contexto_evaluado = models.JSONField(default=dict)
    caso = models.ForeignKey("modulo_casos.Caso", on_delete=models.CASCADE, related_name="resultado_jurisprudencia")
    resolucion = models.ForeignKey(ResolucionJurisprudencia, on_delete=models.PROTECT, related_name="resultados")
    posicion = models.PositiveIntegerField()
    score_semantico = models.FloatField()
    score_hibrido = models.FloatField(default=0)
    es_sugerencia = models.BooleanField(default=False)
    coincidencias = models.JSONField(default=list)
    motivo_recomendacion = models.TextField(blank=True)
    fragmento = models.TextField(help_text="Copia del fragmento que justificó la coincidencia.")
    huella_fuente = models.CharField(max_length=64)
    modelo_version = models.CharField(max_length=100)

    class Meta:
        db_table = "jurisprudencia_resultados"
        ordering = ["posicion"]
        constraints = [models.UniqueConstraint(fields=["caso", "resolucion"], name="uq_juris_resultado_caso")]
