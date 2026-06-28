from rest_framework import serializers
from modulo_usuarios.models.rol import Rol


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Rol
        fields = ["id", "nombre", "descripcion", "estado", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_nombre(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("El nombre del rol debe tener al menos 3 caracteres.")
        # Unicidad case-insensitive
        qs = Rol.objects.filter(nombre__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un rol con ese nombre.")
        return value

    def validate_descripcion(self, value):
        if value and len(value.strip()) < 10:
            raise serializers.ValidationError("La descripción debe tener al menos 10 caracteres.")
        return value.strip() if value else value


class RolListSerializer(serializers.ModelSerializer):
    """Versión compacta para listas desplegables."""
    class Meta:
        model  = Rol
        fields = ["id", "nombre"]
