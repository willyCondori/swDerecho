import re

from rest_framework import serializers

from core.encryption.aes_encryption import decrypt, encrypt
from modulo_usuarios.models.perfil import PerfilUsuario
from modulo_usuarios.models.rol import Rol
from modulo_usuarios.models.usuario import Usuario
from .rol_serializer import RolListSerializer


# ---------------------------------------------------------------------------
# PerfilUsuario
# ---------------------------------------------------------------------------

class PerfilUsuarioReadSerializer(serializers.ModelSerializer):
    """
    Lectura: descifra los campos sensibles antes de devolverlos al cliente.
    Nunca expone el texto cifrado crudo.
    """
    nombres   = serializers.SerializerMethodField()
    apellidos = serializers.SerializerMethodField()
    email     = serializers.SerializerMethodField()
    telefono  = serializers.SerializerMethodField()
    ci        = serializers.SerializerMethodField()

    class Meta:
        model  = PerfilUsuario
        fields = [
            "id", "usuario", "nombres", "apellidos",
            "email", "telefono", "ci", "estado",
            "created_at", "updated_at",
        ]

    def _safe_decrypt(self, value):
        try:
            return decrypt(value) if value else value
        except Exception:
            return "[cifrado]"

    def get_nombres(self, obj):   return self._safe_decrypt(obj.nombres)
    def get_apellidos(self, obj): return self._safe_decrypt(obj.apellidos)
    def get_email(self, obj):     return self._safe_decrypt(obj.email)
    def get_telefono(self, obj):  return self._safe_decrypt(obj.telefono)
    def get_ci(self, obj):        return self._safe_decrypt(obj.ci)


class PerfilUsuarioWriteSerializer(serializers.ModelSerializer):
    """
    Escritura: valida y cifra los campos sensibles antes de guardar.
    """
    nombres   = serializers.CharField(max_length=150)
    apellidos = serializers.CharField(max_length=150)
    email     = serializers.EmailField(max_length=150)
    telefono  = serializers.CharField(max_length=50, required=False, allow_blank=True)
    ci        = serializers.CharField(max_length=50)

    class Meta:
        model  = PerfilUsuario
        fields = ["nombres", "apellidos", "email", "telefono", "ci", "estado"]

    # --- validaciones individuales ---

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

    def validate_email(self, value):
        value = value.strip().lower()
        # Verificar unicidad descifrando registros existentes
        qs = PerfilUsuario.objects.exclude(
            pk=self.instance.pk if self.instance else None
        )
        for perfil in qs:
            try:
                if decrypt(perfil.email) == value:
                    raise serializers.ValidationError("Este correo electrónico ya está registrado.")
            except Exception:
                continue
        return value

    def validate_ci(self, value):
        value = value.strip()
        if not re.match(r"^\d{5,10}[A-Za-z]?$", value):
            raise serializers.ValidationError(
                "El CI debe contener entre 5 y 10 dígitos con un complemento de letra opcional."
            )
        qs = PerfilUsuario.objects.exclude(
            pk=self.instance.pk if self.instance else None
        )
        for perfil in qs:
            try:
                if decrypt(perfil.ci) == value:
                    raise serializers.ValidationError("Este CI ya está registrado.")
            except Exception:
                continue
        return value

    def validate_telefono(self, value):
        if value:
            value = value.strip()
            if not re.match(r"^\+?[\d\s\-]{7,15}$", value):
                raise serializers.ValidationError("Número de teléfono no válido.")
        return value

    # --- cifrado antes de guardar ---

    def _encrypt_fields(self, validated_data: dict) -> dict:
        campos_sensibles = ["nombres", "apellidos", "email", "telefono", "ci"]
        for campo in campos_sensibles:
            if campo in validated_data and validated_data[campo]:
                validated_data[campo] = encrypt(validated_data[campo])
        return validated_data

    def create(self, validated_data):
        return super().create(self._encrypt_fields(validated_data))

    def update(self, instance, validated_data):
        return super().update(instance, self._encrypt_fields(validated_data))


# ---------------------------------------------------------------------------
# Usuario
# ---------------------------------------------------------------------------

class UsuarioReadSerializer(serializers.ModelSerializer):
    rol    = RolListSerializer(read_only=True)
    perfil = PerfilUsuarioReadSerializer(read_only=True)

    class Meta:
        model  = Usuario
        fields = [
            "id", "usuario", "rol", "perfil",
            "ultimo_login", "estado", "created_at",
        ]


class UsuarioCreateSerializer(serializers.ModelSerializer):
    """Creación de usuario con contraseña y perfil en un solo request."""
    password        = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm= serializers.CharField(write_only=True, style={"input_type": "password"})
    rol_id          = serializers.PrimaryKeyRelatedField(
                          queryset=Rol.objects.filter(estado=True),
                          source="rol",
                      )
    perfil          = PerfilUsuarioWriteSerializer()

    class Meta:
        model  = Usuario
        fields = [
            "usuario", "password", "password_confirm",
            "rol_id", "estado", "perfil",
        ]

    def validate_usuario(self, value):
        value = value.strip().lower()
        if len(value) < 4:
            raise serializers.ValidationError("El usuario debe tener al menos 4 caracteres.")
        if not re.match(r"^[a-z0-9._]+$", value):
            raise serializers.ValidationError(
                "El usuario solo puede contener letras minúsculas, números, puntos y guiones bajos."
            )
        if Usuario.objects.filter(usuario=value).exists():
            raise serializers.ValidationError("Este nombre de usuario ya está en uso.")
        return value

    def validate_password(self, value):
        from .auth_serializer import CambioPasswordSerializer
        CambioPasswordSerializer._validar_fortaleza_password(value)
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Las contraseñas no coinciden."}
            )
        return attrs

    def create(self, validated_data):
        perfil_data = validated_data.pop("perfil")
        password    = validated_data.pop("password")
        usuario     = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()

        perfil_serializer = PerfilUsuarioWriteSerializer(data=perfil_data)
        perfil_serializer.is_valid(raise_exception=True)
        perfil_serializer.save(usuario=usuario)
        return usuario


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    """Actualización parcial: rol y estado. Contraseña se cambia aparte."""
    rol_id = serializers.PrimaryKeyRelatedField(
                 queryset=Rol.objects.filter(estado=True),
                 source="rol",
                 required=False,
             )

    class Meta:
        model  = Usuario
        fields = ["rol_id", "estado"]
