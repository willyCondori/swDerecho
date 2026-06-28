import re

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from modulo_usuarios.models.usuario import Usuario


class LoginSerializer(serializers.Serializer):
    usuario  = serializers.CharField(max_length=100)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        usuario  = attrs.get("usuario", "").strip()
        password = attrs.get("password", "")

        if not usuario:
            raise serializers.ValidationError({"usuario": "Este campo es obligatorio."})
        if not password:
            raise serializers.ValidationError({"password": "Este campo es obligatorio."})

        user = authenticate(username=usuario, password=password)
        if not user:
            raise serializers.ValidationError(
                {"non_field_errors": "Credenciales incorrectas. Verifique usuario y contraseña."}
            )
        if not user.estado:
            raise serializers.ValidationError(
                {"non_field_errors": "Usuario inactivo. Contacte al administrador."}
            )

        refresh = RefreshToken.for_user(user)
        return {
            "user"         : user,
            "access_token" : str(refresh.access_token),
            "refresh_token": str(refresh),
        }


class CambioPasswordSerializer(serializers.Serializer):
    password_actual  = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_nuevo   = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_password_actual(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("La contraseña actual es incorrecta.")
        return value

    def validate_password_nuevo(self, value):
        self._validar_fortaleza_password(value)
        return value

    def validate(self, attrs):
        if attrs["password_nuevo"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Las contraseñas nuevas no coinciden."}
            )
        if attrs["password_actual"] == attrs["password_nuevo"]:
            raise serializers.ValidationError(
                {"password_nuevo": "La nueva contraseña no puede ser igual a la actual."}
            )
        return attrs

    @staticmethod
    def _validar_fortaleza_password(value: str):
        errores = []
        if len(value) < 8:
            errores.append("Mínimo 8 caracteres.")
        if not re.search(r"[A-Z]", value):
            errores.append("Al menos una letra mayúscula.")
        if not re.search(r"[a-z]", value):
            errores.append("Al menos una letra minúscula.")
        if not re.search(r"\d", value):
            errores.append("Al menos un número.")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", value):
            errores.append("Al menos un carácter especial.")
        if errores:
            raise serializers.ValidationError(errores)


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate_refresh(self, value):
        if not value:
            raise serializers.ValidationError("El token de refresco es obligatorio.")
        return value
