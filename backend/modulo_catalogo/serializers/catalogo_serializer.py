from rest_framework import serializers

from modulo_catalogo.models.articulo import Articulo, ArticuloEntidad
from modulo_catalogo.models.entidad import EntidadJuridica
from modulo_catalogo.models.jerarquia import jerarquia as Jerarquia
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama import RamaDerecho


# ---------------------------------------------------------------------------
# Jerarquia
# ---------------------------------------------------------------------------
# NOTA: la escala de "nivel" es fija en todo el sistema:
#   1 Constitución · 2 Ley · 3 Ley Departamental · 4 Ley Municipal
#   5 Decreto Supremo · 6 Decreto Departamental · 7 Decreto Municipal
#   8 Reglamento · 9 Resolución Suprema · 10 Resolución Ministerial
# Cuanto más bajo el nivel, mayor la jerarquía normativa.

class JerarquiaSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Jerarquia
        fields = ["id", "nombre", "nivel", "estado"]

    def validate_nombre(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("El nombre debe tener al menos 3 caracteres.")
        qs = Jerarquia.objects.filter(nombre__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe una jerarquía con ese nombre.")
        return value

    def validate_nivel(self, value):
        if value < 1:
            raise serializers.ValidationError("El nivel debe ser un entero mayor o igual a 1.")
        return value


class JerarquiaListSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Jerarquia
        fields = ["id", "nombre", "nivel"]


# ---------------------------------------------------------------------------
# RamaDerecho
# ---------------------------------------------------------------------------

class RamaDerechoSerializer(serializers.ModelSerializer):
    class Meta:
        model  = RamaDerecho
        fields = ["id", "nombre", "descripcion", "estado"]

    def validate_nombre(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("El nombre debe tener al menos 3 caracteres.")
        qs = RamaDerecho.objects.filter(nombre__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe una rama con ese nombre.")
        return value


class RamaDerechoListSerializer(serializers.ModelSerializer):
    class Meta:
        model  = RamaDerecho
        fields = ["id", "nombre"]


# ---------------------------------------------------------------------------
# Norma
# ---------------------------------------------------------------------------

class NormaSerializer(serializers.ModelSerializer):
    jerarquia_id = serializers.PrimaryKeyRelatedField(
        queryset=Jerarquia.objects.filter(estado=True),
        source="jerarquia",
        required=False,
        allow_null=True,
    )
    jerarquia = JerarquiaListSerializer(read_only=True)

    class Meta:
        model  = Norma
        fields = ["id", "nombre", "sigla", "jerarquia_id", "jerarquia", "estado"]

    def validate_sigla(self, value):
        if value:
            value = value.strip().upper()
            if len(value) < 2:
                raise serializers.ValidationError("La sigla debe tener al menos 2 caracteres.")
            qs = Norma.objects.filter(sigla__iexact=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Ya existe una norma con esa sigla.")
        return value

    def validate_nombre(self, value):
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError("El nombre de la norma debe tener al menos 5 caracteres.")
        return value


class NormaListSerializer(serializers.ModelSerializer):
    jerarquia = JerarquiaListSerializer(read_only=True)

    class Meta:
        model  = Norma
        fields = ["id", "nombre", "sigla", "jerarquia"]


# ---------------------------------------------------------------------------
# EntidadJuridica
# ---------------------------------------------------------------------------

class EntidadJuridicaSerializer(serializers.ModelSerializer):
    class Meta:
        model  = EntidadJuridica
        fields = ["id", "nombre", "descripcion", "estado", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_nombre(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("El nombre debe tener al menos 3 caracteres.")
        qs = EntidadJuridica.objects.filter(nombre__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe una entidad jurídica con ese nombre.")
        return value


class EntidadJuridicaListSerializer(serializers.ModelSerializer):
    class Meta:
        model  = EntidadJuridica
        fields = ["id", "nombre"]


# ---------------------------------------------------------------------------
# Articulo
# ---------------------------------------------------------------------------
# La jerarquía normativa ya NO vive en Articulo: ahora es Norma.jerarquia
# (FK a Jerarquia). Un artículo hereda la jerarquía de su norma.

class ArticuloReadSerializer(serializers.ModelSerializer):
    norma     = NormaListSerializer(read_only=True)
    rama      = RamaDerechoListSerializer(read_only=True)
    entidades = EntidadJuridicaListSerializer(many=True, read_only=True)

    class Meta:
        model  = Articulo
        fields = [
            "id", "numero_articulo", "titulo", "contenido",
            "norma", "rama", "entidades",
            "frecuencia_historica", "estado", "created_at",
        ]


class ArticuloWriteSerializer(serializers.ModelSerializer):
    norma_id    = serializers.PrimaryKeyRelatedField(
                      queryset=Norma.objects.filter(estado=True),
                      source="norma",
                  )
    rama_id     = serializers.PrimaryKeyRelatedField(
                      queryset=RamaDerecho.objects.filter(estado=True),
                      source="rama",
                  )
    entidad_ids = serializers.PrimaryKeyRelatedField(
                      queryset=EntidadJuridica.objects.filter(estado=True),
                      many=True,
                      required=False,
                      write_only=True,
                  )

    class Meta:
        model  = Articulo
        fields = [
            "numero_articulo", "titulo", "contenido",
            "norma_id", "rama_id", "entidad_ids", "estado",
        ]

    def validate_numero_articulo(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El número de artículo es obligatorio.")
        # Unicidad dentro de la misma norma se valida en validate()
        return value

    def validate_contenido(self, value):
        value = value.strip()
        if len(value) < 20:
            raise serializers.ValidationError(
                "El contenido del artículo debe tener al menos 20 caracteres."
            )
        return value

    def validate(self, attrs):
        norma           = attrs.get("norma",           getattr(self.instance, "norma", None))
        numero_articulo = attrs.get("numero_articulo", getattr(self.instance, "numero_articulo", None))

        qs = Articulo.objects.filter(norma=norma, numero_articulo=numero_articulo)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {"numero_articulo": "Ya existe un artículo con ese número en esta norma."}
            )
        return attrs

    def _sync_entidades(self, articulo, entidades):
        ArticuloEntidad.objects.filter(articulo=articulo).delete()
        ArticuloEntidad.objects.bulk_create([
            ArticuloEntidad(articulo=articulo, entidad=e) for e in entidades
        ])

    def create(self, validated_data):
        entidades = validated_data.pop("entidad_ids", [])
        articulo  = super().create(validated_data)
        self._sync_entidades(articulo, entidades)
        return articulo

    def update(self, instance, validated_data):
        entidades = validated_data.pop("entidad_ids", None)
        articulo  = super().update(instance, validated_data)
        if entidades is not None:
            self._sync_entidades(articulo, entidades)
        return articulo


class ArticuloListSerializer(serializers.ModelSerializer):
    """Versión compacta para resultados del ranking."""
    norma_sigla      = serializers.CharField(source="norma.sigla", read_only=True)
    rama_nombre      = serializers.CharField(source="rama.nombre", read_only=True)
    jerarquia_nivel  = serializers.SerializerMethodField()
    jerarquia_nombre = serializers.SerializerMethodField()

    class Meta:
        model  = Articulo
        fields = [
            "id", "numero_articulo", "titulo", "contenido",
            "norma_sigla", "rama_nombre",
            "jerarquia_nivel", "jerarquia_nombre", "frecuencia_historica",
        ]

    def get_jerarquia_nivel(self, obj):
        return obj.norma.jerarquia.nivel if obj.norma.jerarquia_id else None

    def get_jerarquia_nombre(self, obj):
        return obj.norma.jerarquia.nombre if obj.norma.jerarquia_id else None