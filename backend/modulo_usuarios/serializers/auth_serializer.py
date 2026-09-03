import re

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

class LoginSerializer(serializers.Serializer):
    usuario = serializers.CharField(max_length=100)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        usuario = attrs.get("usuario", "").strip()
        password = attrs.get("password", "")

        if not usuario:
            raise serializers.ValidationError({"usuario": "Este campo es obligatorio."})

        if not password:
            raise serializers.ValidationError({"password": "Este campo es obligatorio."})

        User = get_user_model()
        user = User.objects.filter(usuario=usuario).first()

        if not user or not user.check_password(password):
            raise serializers.ValidationError(
                {"non_field_errors": "Credenciales incorrectas."}
            )

        if not user.estado:
            raise serializers.ValidationError(
                {"non_field_errors": "Usuario inactivo."}
            )

        refresh = RefreshToken.for_user(user)

        return {
            "user": user,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
        }


class CambioPasswordSerializer(serializers.Serializer):
    """
    password_actual es opcional: en el cambio obligatorio del primer
    login (Usuario.debe_cambiar_password=True) el frontend no la manda,
    porque el usuario ya se autenticó con ella para conseguir el JWT
    con el que llega hasta acá — pedírsela de nuevo es una verificación
    redundante. Se deja opcional (en vez de sacarla del todo) por si en
    el futuro se agrega un cambio de contraseña "voluntario" desde el
    perfil, donde sí conviene volver a pedirla.
    """
    password_actual  = serializers.CharField(
                            write_only=True, style={"input_type": "password"},
                            required=False,
                        )
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

        user = self.context["request"].user
        # Si mandaron password_actual ya se comparó tal cual arriba;
        # si no la mandaron (cambio obligatorio del primer login),
        # igual chequeamos contra la contraseña ya guardada para que
        # no "cambie" a la misma contraseña temporal que le llegó por
        # correo.
        password_actual = attrs.get("password_actual")
        es_igual_a_actual = (
            password_actual == attrs["password_nuevo"]
            if password_actual is not None
            else user.check_password(attrs["password_nuevo"])
        )
        if es_igual_a_actual:
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