import math
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken


def validar_fortaleza_password(value: str):
    """
    Reglas de fortaleza compartidas por todo cambio de contraseña del
    sistema (cambio voluntario, cambio obligatorio del primer login y
    recuperación por correo). Antes vivía como método estático solo
    dentro de CambioPasswordSerializer; se saca a función de módulo
    para que ConfirmarRecuperacionSerializer la reuse sin duplicar
    las reglas ni depender de una clase que no le corresponde.
    """
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

class LoginSerializer(serializers.Serializer):
    usuario = serializers.CharField(max_length=100)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        usuario_input = attrs.get("usuario", "").strip()
        password = attrs.get("password", "")

        if not usuario_input:
            raise serializers.ValidationError({"usuario": "Este campo es obligatorio."})

        if not password:
            raise serializers.ValidationError({"password": "Este campo es obligatorio."})

        User = get_user_model()
        user = User.objects.filter(usuario=usuario_input).first()

        # Bloqueo temporal por intentos fallidos: se chequea ANTES de
        # verificar la contraseña. Así, si el bloqueo está vigente, ni
        # siquiera una contraseña correcta destraba el login — si
        # alguien la adivinó justo durante la ventana de bloqueo, de
        # nada le sirve.
        if user and user.esta_bloqueado:
            minutos_restantes = max(
                1, math.ceil((user.bloqueado_hasta - timezone.now()).total_seconds() / 60)
            )
            # self._bloqueado la lee LoginView después de is_valid() para
            # devolver 423 Locked en vez del 400 genérico — así el
            # frontend puede darle un tratamiento visual distinto sin
            # tener que andar interpretando el texto del mensaje.
            self._bloqueado = True
            raise serializers.ValidationError(
                {"non_field_errors": (
                    "Usuario bloqueado temporalmente por demasiados intentos "
                    f"fallidos. Probá de nuevo en {minutos_restantes} minuto(s), "
                    "o contactá a un administrador para desbloquearlo antes."
                )}
            )

        if not user or not user.check_password(password):
            # El contador de intentos fallidos solo existe para cuentas
            # reales — si el 'usuario' ni siquiera existe, no hay nada
            # que incrementar. Importante: el mensaje de error es
            # idéntico en los dos casos ("no existe" y "existe pero la
            # contraseña está mal"), para no filtrar por enumeración
            # cuáles nombres de usuario son válidos.
            if user:
                user.intentos_fallidos += 1
                if user.intentos_fallidos >= settings.LOGIN_MAX_INTENTOS:
                    user.bloqueado_hasta = timezone.now() + timezone.timedelta(
                        minutes=settings.LOGIN_BLOQUEO_MINUTOS
                    )
                    user.intentos_fallidos = 0
                    user.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
                    self._bloqueado = True
                    raise serializers.ValidationError(
                        {"non_field_errors": (
                            "Demasiados intentos fallidos. El usuario quedó "
                            f"bloqueado por {settings.LOGIN_BLOQUEO_MINUTOS} minutos."
                        )}
                    )
                user.save(update_fields=["intentos_fallidos"])
            raise serializers.ValidationError(
                {"non_field_errors": "Credenciales incorrectas."}
            )

        if not user.estado:
            raise serializers.ValidationError(
                {"non_field_errors": "Usuario inactivo."}
            )

        # Login correcto: limpia el contador y cualquier bloqueo viejo
        # que hubiera quedado vencido sin limpiarse (esta_bloqueado ya
        # dio False para llegar hasta acá, pero los campos pueden
        # seguir con valores viejos hasta que se guarden en None/0).
        if user.intentos_fallidos or user.bloqueado_hasta:
            user.intentos_fallidos = 0
            user.bloqueado_hasta = None
            user.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])

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
        validar_fortaleza_password(value)
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


class SolicitarRecuperacionSerializer(serializers.Serializer):
    """
    Paso 1 del flujo: el usuario pide el enlace de recuperación con
    su email. No valida acá si el email existe o no en el sistema
    (eso lo decide la vista) para no filtrar esa información en un
    error de serializer — solo normaliza el formato.
    """
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class ConfirmarRecuperacionSerializer(serializers.Serializer):
    """
    Confirma la recuperación: el usuario llega con el email que usó
    para pedirla, la contraseña temporal que le llegó por correo
    (password_actual, generada por SolicitarRecuperacionView) y la
    contraseña definitiva que eligió. No hay JWT todavía en este
    punto (por eso es AllowAny en la vista) — la contraseña temporal
    ES la prueba de identidad, igual que un login normal.
    """
    email             = serializers.EmailField()
    password_actual   = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_nuevo    = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm  = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_email(self, value):
        return value.strip().lower()

    def validate_password_nuevo(self, value):
        validar_fortaleza_password(value)
        return value

    def validate(self, attrs):
        if attrs["password_nuevo"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Las contraseñas no coinciden."}
            )
        if attrs["password_nuevo"] == attrs["password_actual"]:
            raise serializers.ValidationError(
                {"password_nuevo": "La nueva contraseña no puede ser igual a la temporal."}
            )
        return attrs


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate_refresh(self, value):
        if not value:
            raise serializers.ValidationError("El token de refresco es obligatorio.")
        return value