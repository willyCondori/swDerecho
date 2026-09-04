import re

from rest_framework import serializers

from core.encryption.aes_encryption import decrypt, encrypt, hash_lookup
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

    class Meta:
        model  = PerfilUsuario
        fields = [
            "id", "usuario", "nombres", "apellidos",
            "email", "telefono", "estado",
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


class PerfilUsuarioWriteSerializer(serializers.ModelSerializer):
    """
    Escritura: valida y cifra los campos sensibles antes de guardar.
    """
    nombres   = serializers.CharField(max_length=150)
    apellidos = serializers.CharField(max_length=150)
    email     = serializers.EmailField(max_length=150)
    telefono  = serializers.CharField(max_length=50, required=False, allow_blank=True)

    class Meta:
        model  = PerfilUsuario
        fields = ["nombres", "apellidos", "email", "telefono", "estado"]

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
        # Unicidad vía email_hash (HMAC-SHA256 determinístico): antes
        # esto descifraba TODA la tabla de perfiles en un loop para
        # comparar uno por uno (O(n) en cada alta/edición de usuario).
        # Con email_hash es un filter() indexado directo. Ver
        # core.encryption.aes_encryption.hash_lookup.
        qs = PerfilUsuario.objects.filter(email_hash=hash_lookup(value)).exclude(
            pk=self.instance.pk if self.instance else None
        )
        if qs.exists():
            raise serializers.ValidationError("Este correo electrónico ya está registrado.")
        return value

    def validate_telefono(self, value):
        if value:
            value = value.strip()
            if not re.match(r"^\+?[\d\s\-]{7,15}$", value):
                raise serializers.ValidationError("Número de teléfono no válido.")
        return value

    # --- cifrado antes de guardar ---

    def _encrypt_fields(self, validated_data: dict) -> dict:
        campos_sensibles = ["nombres", "apellidos", "email", "telefono"]
        for campo in campos_sensibles:
            if campo in validated_data and validated_data[campo]:
                validated_data[campo] = encrypt(validated_data[campo])
        return validated_data

    def create(self, validated_data):
        if validated_data.get("email"):
            validated_data["email_hash"] = hash_lookup(validated_data["email"])
        return super().create(self._encrypt_fields(validated_data))

    def update(self, instance, validated_data):
        if validated_data.get("email"):
            validated_data["email_hash"] = hash_lookup(validated_data["email"])
        return super().update(instance, self._encrypt_fields(validated_data))


# ---------------------------------------------------------------------------
# Usuario
# ---------------------------------------------------------------------------

class UsuarioReadSerializer(serializers.ModelSerializer):
    rol    = RolListSerializer(read_only=True)
    perfil = PerfilUsuarioReadSerializer(read_only=True)
    esta_bloqueado = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Usuario
        fields = [
            "id", "usuario", "rol", "perfil",
            "estado", "debe_cambiar_password", "created_at",
            "esta_bloqueado", "bloqueado_hasta",
        ]


class UsuarioCreateSerializer(serializers.ModelSerializer):
    """
    Creación de usuario y perfil en un solo request.

    La contraseña ya NO la ingresa el administrador: se genera
    automáticamente de forma aleatoria y se envía por correo al email
    del perfil, junto con el nombre de usuario. El usuario queda
    marcado con debe_cambiar_password=True, así que en su primer
    login el frontend lo manda a cambiarla antes de dejarlo entrar
    al resto del sistema (ver CambioPasswordView y AuthStore.login
    en el frontend).
    """
    rol_id          = serializers.PrimaryKeyRelatedField(
                          queryset=Rol.objects.filter(estado=True),
                          source="rol",
                      )
    perfil          = PerfilUsuarioWriteSerializer()

    class Meta:
        model  = Usuario
        fields = [
            "usuario", "rol_id", "estado", "perfil",
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

    def create(self, validated_data):
        from core.utils.emails import enviar_credenciales_usuario
        from core.utils.passwords import generar_password_aleatoria

        perfil_data = validated_data.pop("perfil")

        password = generar_password_aleatoria()
        usuario  = Usuario(debe_cambiar_password=True, **validated_data)
        usuario.set_password(password)
        usuario.save()

        perfil_serializer = PerfilUsuarioWriteSerializer(data=perfil_data)
        perfil_serializer.is_valid(raise_exception=True)
        perfil = perfil_serializer.save(usuario=usuario)

        # El email se guarda cifrado (AES-256) en PerfilUsuario.email;
        # perfil_data["email"] todavía es el texto plano validado por
        # el serializer, así que lo usamos directo en vez de descifrar.
        correo_enviado = enviar_credenciales_usuario(
            email=perfil_data["email"],
            usuario=usuario.usuario,
            password=password,
        )

        # Se guarda en la instancia (no en BD) para que la vista pueda
        # informarle al administrador si el correo salió o no.
        usuario._correo_credenciales_enviado = correo_enviado
        return usuario

    def to_representation(self, instance):
        data = UsuarioReadSerializer(instance, context=self.context).data
        data["correo_credenciales_enviado"] = getattr(
            instance, "_correo_credenciales_enviado", None
        )
        return data


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