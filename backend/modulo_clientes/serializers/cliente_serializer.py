import re
from datetime import date

from rest_framework import serializers

from core.encryption.aes_encryption import decrypt, encrypt
from modulo_clientes.models.cliente import Cliente


class ClienteReadSerializer(serializers.ModelSerializer):
    """Descifra campos sensibles antes de devolver al cliente HTTP."""
    nombres          = serializers.SerializerMethodField()
    apellidos        = serializers.SerializerMethodField()
    fecha_nacimiento = serializers.SerializerMethodField()
    nombre_completo  = serializers.SerializerMethodField()

    class Meta:
        model  = Cliente
        fields = [
            "id", "nombres", "apellidos",
            "nombre_completo", "fecha_nacimiento",
            "estado", "created_at",
        ]

    def _safe_decrypt(self, value):
        try:
            return decrypt(value) if value else value
        except Exception:
            return "[cifrado]"

    def get_nombres(self, obj):          return self._safe_decrypt(obj.nombres)
    def get_apellidos(self, obj):        return self._safe_decrypt(obj.apellidos)
    def get_fecha_nacimiento(self, obj): return self._safe_decrypt(obj.fecha_nacimiento)

    def get_nombre_completo(self, obj):
        n = self._safe_decrypt(obj.nombres)
        a = self._safe_decrypt(obj.apellidos)
        return f"{n} {a}".strip()


class ClienteWriteSerializer(serializers.ModelSerializer):
    """Valida y cifra campos sensibles antes de persistir."""
    nombres          = serializers.CharField(max_length=200)
    apellidos        = serializers.CharField(max_length=200)
    fecha_nacimiento = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model  = Cliente
        fields = ["nombres", "apellidos", "fecha_nacimiento", "estado"]

    def validate_nombres(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("El nombre debe tener al menos 2 caracteres.")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$", value):
            raise serializers.ValidationError("El nombre solo puede contener letras y espacios.")
        return value

    def validate_apellidos(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Los apellidos deben tener al menos 2 caracteres.")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$", value):
            raise serializers.ValidationError("Los apellidos solo pueden contener letras y espacios.")
        return value

    def validate_fecha_nacimiento(self, value):
        if value:
            if value > date.today():
                raise serializers.ValidationError("La fecha de nacimiento no puede ser futura.")
            edad = (date.today() - value).days // 365
            if edad > 120:
                raise serializers.ValidationError("La fecha de nacimiento no es válida.")
        return value

    def _encrypt_fields(self, validated_data: dict) -> dict:
        if "nombres" in validated_data:
            validated_data["nombres"] = encrypt(validated_data["nombres"])
        if "apellidos" in validated_data:
            validated_data["apellidos"] = encrypt(validated_data["apellidos"])
        if "fecha_nacimiento" in validated_data and validated_data["fecha_nacimiento"]:
            validated_data["fecha_nacimiento"] = encrypt(
                str(validated_data["fecha_nacimiento"])
            )
        return validated_data

    def create(self, validated_data):
        return super().create(self._encrypt_fields(validated_data))

    def update(self, instance, validated_data):
        return super().update(instance, self._encrypt_fields(validated_data))


class ClienteListSerializer(serializers.ModelSerializer):
    """Versión compacta para selects y búsquedas."""
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model  = Cliente
        fields = ["id", "nombre_completo"]

    def get_nombre_completo(self, obj):
        try:
            n = decrypt(obj.nombres)
            a = decrypt(obj.apellidos)
            return f"{n} {a}".strip()
        except Exception:
            return f"Cliente #{obj.id}"
