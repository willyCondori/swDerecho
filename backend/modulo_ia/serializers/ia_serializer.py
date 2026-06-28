from rest_framework import serializers

from modulo_catalogo.serializers.catalogo_serializer import ArticuloListSerializer
from modulo_ia.models.chunk import ChunkCaso
from modulo_ia.models.embedding import (
    EmbeddingArticulo,
    EmbeddingChunk,
    EntidadDetectadaCaso,
)
from modulo_ia.models.resultado import ResultadoArticulo


# ---------------------------------------------------------------------------
# ChunkCaso
# ---------------------------------------------------------------------------

class ChunkCasoSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ChunkCaso
        fields = ["id", "caso", "contenido", "orden", "tipo", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_contenido(self, value):
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError(
                "El contenido del chunk debe tener al menos 5 caracteres."
            )
        if len(value) > 4000:
            raise serializers.ValidationError(
                "El chunk no puede exceder 4000 caracteres."
            )
        return value

    def validate_orden(self, value):
        if value < 0:
            raise serializers.ValidationError("El orden debe ser un número positivo.")
        return value

    def validate_tipo(self, value):
        permitidos = [c[0] for c in ChunkCaso.TIPO_CHOICES]
        if value not in permitidos:
            raise serializers.ValidationError(
                f"Tipo no válido. Permitidos: {permitidos}"
            )
        return value

    def validate(self, attrs):
        # Unicidad de orden dentro del caso
        caso  = attrs.get("caso",  getattr(self.instance, "caso",  None))
        orden = attrs.get("orden", getattr(self.instance, "orden", None))
        qs    = ChunkCaso.objects.filter(caso=caso, orden=orden)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {"orden": f"Ya existe un chunk con orden={orden} en este caso."}
            )
        return attrs


# ---------------------------------------------------------------------------
# EntidadDetectadaCaso
# ---------------------------------------------------------------------------

class EntidadDetectadaSerializer(serializers.ModelSerializer):
    class Meta:
        model  = EntidadDetectadaCaso
        fields = ["id", "chunk", "valor_detectado", "score"]
        read_only_fields = ["id"]

    def validate_score(self, value):
        if not (0.0 <= value <= 1.0):
            raise serializers.ValidationError("El score debe estar entre 0.0 y 1.0.")
        return round(value, 6)

    def validate_valor_detectado(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError(
                "El valor detectado debe tener al menos 2 caracteres."
            )
        return value


# ---------------------------------------------------------------------------
# EmbeddingArticulo / EmbeddingChunk
# (solo lectura — los embeddings se generan internamente por el servicio IA)
# ---------------------------------------------------------------------------

class EmbeddingArticuloSerializer(serializers.ModelSerializer):
    class Meta:
        model  = EmbeddingArticulo
        fields = ["id", "articulo", "created_at"]
        read_only_fields = fields


class EmbeddingChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model  = EmbeddingChunk
        fields = ["id", "chunk", "created_at"]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# ResultadoArticulo — ranking jurídico
# ---------------------------------------------------------------------------

class ResultadoArticuloSerializer(serializers.ModelSerializer):
    """
    Ranking de artículos aplicables a un caso.
    Incluye los datos completos del artículo y todos los sub-scores.
    """
    articulo = ArticuloListSerializer(read_only=True)

    class Meta:
        model  = ResultadoArticulo
        fields = [
            "id", "caso", "articulo", "posicion",
            "score_total",
            "score_semantico", "score_delito",
            "score_entidades", "score_jerarquia", "score_frecuencia",
        ]
        read_only_fields = fields

    def validate_score_total(self, value):
        if not (0 <= value <= 1):
            raise serializers.ValidationError("score_total debe estar entre 0 y 1.")
        return value


class ResultadoArticuloWriteSerializer(serializers.ModelSerializer):
    """
    Escritura interna usada por ranking_service.
    No se expone directamente al cliente HTTP.
    """
    class Meta:
        model  = ResultadoArticulo
        fields = [
            "caso", "articulo", "posicion",
            "score_total", "score_semantico", "score_delito",
            "score_entidades", "score_jerarquia", "score_frecuencia",
        ]

    def _validar_score(self, value, nombre):
        if not (0 <= float(value) <= 1):
            raise serializers.ValidationError(f"{nombre} debe estar entre 0 y 1.")
        return value

    def validate_score_total(self, v):      return self._validar_score(v, "score_total")
    def validate_score_semantico(self, v):  return self._validar_score(v, "score_semantico")
    def validate_score_delito(self, v):     return self._validar_score(v, "score_delito")
    def validate_score_entidades(self, v):  return self._validar_score(v, "score_entidades")
    def validate_score_jerarquia(self, v):  return self._validar_score(v, "score_jerarquia")
    def validate_score_frecuencia(self, v): return self._validar_score(v, "score_frecuencia")

    def validate_posicion(self, value):
        if value < 1:
            raise serializers.ValidationError("La posición debe ser mayor o igual a 1.")
        return value

    def validate(self, attrs):
        caso     = attrs.get("caso",     getattr(self.instance, "caso",     None))
        articulo = attrs.get("articulo", getattr(self.instance, "articulo", None))
        qs       = ResultadoArticulo.objects.filter(caso=caso, articulo=articulo)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {"articulo": "Este artículo ya está en el ranking de este caso."}
            )
        return attrs


# ---------------------------------------------------------------------------
# Serializer de entrada para disparar el análisis IA completo
# ---------------------------------------------------------------------------

class AnalisisCasoSerializer(serializers.Serializer):
    """
    Recibe el caso_id y dispara todo el pipeline IA:
    chunking → embeddings → ranking → LLM → generación de resultados.
    """
    caso_id = serializers.IntegerField()

    def validate_caso_id(self, value):
        from modulo_casos.models.caso import Caso
        try:
            caso = Caso.objects.get(pk=value, estado=True)
        except Caso.DoesNotExist:
            raise serializers.ValidationError("El caso no existe o está inactivo.")

        # Verificar que tenga texto o documento PDF
        tiene_texto = bool(caso.descripcion and caso.descripcion.strip())
        tiene_pdf   = caso.documentos.filter(tipo_archivo="pdf").exists()
        if not tiene_texto and not tiene_pdf:
            raise serializers.ValidationError(
                "El caso no tiene texto ni documento PDF para analizar."
            )
        return value
