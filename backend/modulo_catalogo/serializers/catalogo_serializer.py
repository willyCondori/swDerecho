from rest_framework import serializers

from modulo_catalogo.models.articulo import Articulo, ArticuloEntidad
from modulo_catalogo.models.entidad import EntidadJuridica
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama import RamaDerecho


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
    class Meta:
        model  = Norma
        fields = ["id", "nombre", "sigla", "estado"]

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
    class Meta:
        model  = Norma
        fields = ["id", "nombre", "sigla"]


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

JERARQUIA_CHOICES_VALUES = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4]


class ArticuloReadSerializer(serializers.ModelSerializer):
    norma    = NormaListSerializer(read_only=True)
    rama     = RamaDerechoListSerializer(read_only=True)
    entidades= EntidadJuridicaListSerializer(many=True, read_only=True)
    jerarquia_label = serializers.SerializerMethodField()

    class Meta:
        model  = Articulo
        fields = [
            "id", "numero_articulo", "titulo", "contenido",
            "norma", "rama", "entidades",
            "jerarquia_normativa", "jerarquia_label",
            "frecuencia_historica", "estado", "created_at",
        ]

    def get_jerarquia_label(self, obj):
        mapping = {
            1.0: "Constitución Política del Estado",
            0.9: "Ley Orgánica",
            0.8: "Código (Penal, Civil, etc.)",
            0.7: "Ley Ordinaria",
            0.6: "Decreto Supremo",
            0.5: "Resolución Ministerial",
            0.4: "Ordenanza Municipal",
        }
        return mapping.get(round(obj.jerarquia_normativa, 1), "Otro")


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
            "norma_id", "rama_id", "entidad_ids",
            "jerarquia_normativa", "estado",
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

    def validate_jerarquia_normativa(self, value):
        if round(value, 1) not in JERARQUIA_CHOICES_VALUES:
            raise serializers.ValidationError(
                f"Jerarquía no válida. Valores permitidos: {JERARQUIA_CHOICES_VALUES}"
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
    norma_sigla = serializers.CharField(source="norma.sigla", read_only=True)
    rama_nombre = serializers.CharField(source="rama.nombre", read_only=True)

    class Meta:
        model  = Articulo
        fields = [
            "id", "numero_articulo", "titulo",
            "norma_sigla", "rama_nombre",
            "jerarquia_normativa", "frecuencia_historica",
        ]
