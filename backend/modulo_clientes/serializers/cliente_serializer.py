import re
from datetime import date

from rest_framework import serializers

from core.encryption.aes_encryption import encrypt, safe_decrypt
from modulo_clientes.models.cliente import Cliente


class ClienteNombreMixin:
    """
    Lógica compartida para descifrar nombres/apellidos y construir
    el nombre completo. La usan tanto el serializer de detalle como
    el compacto, evitando repetir el mismo try/except en cada uno.
    """

    def get_nombres(self, obj):
        return safe_decrypt(obj.nombres)

    def get_apellidos(self, obj):
        return safe_decrypt(obj.apellidos)

    def get_nombre_completo(self, obj):
        nombres = safe_decrypt(obj.nombres)
        apellidos = safe_decrypt(obj.apellidos)
        if nombres == "[cifrado]" or apellidos == "[cifrado]":
            return f"Cliente #{obj.id}"
        return f"{nombres} {apellidos}".strip()

class ClienteReadSerializer(ClienteNombreMixin, serializers.ModelSerializer):
    nombres = serializers.SerializerMethodField()
    apellidos = serializers.SerializerMethodField()
    telefono = serializers.SerializerMethodField()
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = Cliente
        fields = [
            "id",
            "nombres",
            "apellidos",
            "telefono",
            "nombre_completo",
            "estado",
            "created_at",
        ]

    def get_telefono(self, obj):
        return safe_decrypt(obj.telefono)


class ClienteListSerializer(ClienteNombreMixin, serializers.ModelSerializer):
    """Versión compacta para selects y búsquedas."""
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model  = Cliente
        fields = ["id", "nombre_completo"]


class ClienteWriteSerializer(serializers.ModelSerializer):
    """Valida y cifra campos sensibles antes de persistir."""
    nombres          = serializers.CharField(max_length=200)
    apellidos        = serializers.CharField(max_length=200)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)

    NOMBRE_REGEX = re.compile(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$")

    class Meta:
        model  = Cliente
        fields = ["nombres", "apellidos", "telefono", "estado"]

    def _validar_nombre(self, value, campo_label):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError(
                f"{campo_label} debe tener al menos 2 caracteres."
            )
        if not self.NOMBRE_REGEX.match(value):
            raise serializers.ValidationError(
                f"{campo_label} solo puede contener letras y espacios."
            )
        return value

    def validate_nombres(self, value):
        return self._validar_nombre(value, "El nombre")

    def validate_apellidos(self, value):
        return self._validar_nombre(value, "Los apellidos")

    def validate_telefono(self, value):
        if not value:
            return value

        value = value.strip()

        if not value.isdigit():
            raise serializers.ValidationError(
                "El teléfono solo puede contener números."
            )

        if len(value) != 8:
            raise serializers.ValidationError(
                "El teléfono debe tener 8 dígitos."
            )

        return value    

    def _encrypt_fields(self, validated_data: dict) -> dict:
        if "nombres" in validated_data:
            validated_data["nombres"] = encrypt(validated_data["nombres"])

        if "apellidos" in validated_data:
            validated_data["apellidos"] = encrypt(validated_data["apellidos"])

        if validated_data.get("telefono"):
            validated_data["telefono"] = encrypt(validated_data["telefono"])

        return validated_data

    def create(self, validated_data):
        return super().create(self._encrypt_fields(validated_data))

    def update(self, instance, validated_data):
        return super().update(instance, self._encrypt_fields(validated_data))