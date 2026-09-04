import hashlib
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from core.encryption.aes_encryption import decrypt, hash_lookup
from core.permissions.auditoria_mixin import registrar_auditoria
from modulo_usuarios.serializers.auth_serializer import (
    CambioPasswordSerializer,
    ConfirmarRecuperacionSerializer,
    LoginSerializer,
    SolicitarRecuperacionSerializer,
)
from modulo_usuarios.serializers.rol_serializer import RolListSerializer

# ---------------------------------------------------------------------------
# Cookie httpOnly del refresh token
# ---------------------------------------------------------------------------
# El refresh token vive SOLO en una cookie httpOnly — nunca en el body de
# la respuesta ni en localStorage. Un script inyectado por XSS no puede
# leer document.cookie de una cookie httpOnly, así que aunque el frontend
# tenga un XSS, el refresh token queda fuera de alcance.
#
# El access token sí viaja en el body de la respuesta: el frontend lo
# guarda solo en memoria (nunca en localStorage) y lo vuelve a pedir con
# un refresh silencioso cada vez que se recarga la página.

REFRESH_COOKIE_NAME     = getattr(settings, "REFRESH_TOKEN_COOKIE_NAME", "refresh_token")
REFRESH_COOKIE_PATH     = getattr(settings, "REFRESH_TOKEN_COOKIE_PATH", "/api/usuarios/auth/")
REFRESH_COOKIE_SAMESITE = getattr(settings, "REFRESH_TOKEN_COOKIE_SAMESITE", "Lax")
REFRESH_COOKIE_SECURE   = getattr(settings, "REFRESH_TOKEN_COOKIE_SECURE", not settings.DEBUG)
REFRESH_COOKIE_MAX_AGE  = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        secure=REFRESH_COOKIE_SECURE,
        samesite=REFRESH_COOKIE_SAMESITE,
        path=REFRESH_COOKIE_PATH,
    )

def _delete_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if not serializer.is_valid():
            # 423 Locked específicamente para el bloqueo temporal por
            # intentos fallidos (LoginSerializer.validate marca
            # self._bloqueado antes de levantar el ValidationError) —
            # el resto de los errores de login (credenciales
            # incorrectas, usuario inactivo, campos faltantes) siguen
            # devolviendo el 400 de siempre. Así el frontend distingue
            # "bloqueado temporalmente" de un error de login común sin
            # tener que parsear el texto del mensaje.
            status_code = (
                status.HTTP_423_LOCKED
                if getattr(serializer, "_bloqueado", False)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response(serializer.errors, status=status_code)

        data = serializer.validated_data
        user = data["user"]

        # last_login correcto
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        registrar_auditoria(
            usuario=user,
            tabla="usuarios",
            accion="LOGIN",
            registro_id=user.pk,
            request=request,
        )

        response = Response(
            {
                "access_token": data["access_token"],
                "usuario": {
                    "id": user.id,
                    "usuario": user.usuario,
                    "rol": RolListSerializer(user.rol).data if user.rol else None,
                    "debe_cambiar_password": user.debe_cambiar_password,
                },
            },
            status=status.HTTP_200_OK,
        )
        _set_refresh_cookie(response, data["refresh_token"])
        return response


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Invalida el refresh token (blacklist) y borra la cookie httpOnly.
    El refresh token se lee de la cookie, ya no del body.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_str = request.COOKIES.get(REFRESH_COOKIE_NAME)

        if refresh_str:
            try:
                token = RefreshToken(refresh_str)
                token.blacklist()
            except TokenError:
                # Token ya inválido/expirado/blacklisteado: no bloquea el
                # logout, de todas formas se borra la cookie abajo.
                pass

        registrar_auditoria(
            usuario=request.user,
            tabla="usuarios",
            accion="LOGOUT",
            registro_id=request.user.pk,
            request=request,
        )

        response = Response({"detail": "Sesión cerrada correctamente."}, status=status.HTTP_200_OK)
        _delete_refresh_cookie(response)
        return response


class RefreshTokenView(APIView):
    """
    POST /api/auth/refresh/
    Renueva el access token usando el refresh token que viaja en la
    cookie httpOnly (ya no en el body). Con ROTATE_REFRESH_TOKENS=True
    (ver settings.SIMPLE_JWT) también emite un refresh token nuevo y
    blacklistea el anterior, actualizando la cookie.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_str = request.COOKIES.get(REFRESH_COOKIE_NAME)

        if not refresh_str:
            return Response(
                {"detail": "No hay sesión activa (falta el refresh token)."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            refresh       = RefreshToken(refresh_str)
            access_token  = str(refresh.access_token)
        except TokenError as e:
            response = Response(
                {"detail": f"Token inválido o expirado: {str(e)}"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            # El refresh que llegó ya no sirve: limpiamos la cookie para
            # que el frontend no siga reintentando con un token muerto.
            _delete_refresh_cookie(response)
            return response

        response = Response({"access_token": access_token}, status=status.HTTP_200_OK)

        if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS", False):
            if settings.SIMPLE_JWT.get("BLACKLIST_AFTER_ROTATION", False):
                try:
                    refresh.blacklist()
                except TokenError:
                    pass

            User = get_user_model()
            user = User.objects.get(pk=refresh["user_id"])
            nuevo_refresh = RefreshToken.for_user(user)
            _set_refresh_cookie(response, str(nuevo_refresh))

        return response


class CambioPasswordView(APIView):
    """
    POST /api/auth/cambiar-password/
    Permite al usuario autenticado cambiar su contraseña.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CambioPasswordSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user.set_password(serializer.validated_data["password_nuevo"])
        user.debe_cambiar_password = False
        user.save(update_fields=["password", "debe_cambiar_password"])

        registrar_auditoria(
            usuario=user,
            tabla="usuarios",
            accion="UPDATE",
            registro_id=user.pk,
            request=request,
            metadata={"campo": "password"},
        )

        return Response(
            {"detail": "Contraseña actualizada correctamente."},
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    """
    GET /api/auth/me/
    Devuelve los datos del usuario autenticado incluyendo su perfil.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from modulo_usuarios.serializers.usuario_serializer import UsuarioReadSerializer
        serializer = UsuarioReadSerializer(request.user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Recuperación de contraseña por correo
# ---------------------------------------------------------------------------
# Flujo en dos pasos, ambos AllowAny porque ocurren ANTES de tener sesión:
#   1) SolicitarRecuperacionView: el usuario manda su email. Si existe una
#      cuenta activa con ese email, se genera una contraseña temporal nueva
#      (mismo mecanismo que al crear un usuario, ver core.utils.passwords)
#      y se manda por Gmail. No se genera ningún enlace ni token de un solo
#      uso — la contraseña temporal en sí cumple ese rol.
#   2) ConfirmarRecuperacionView: el usuario manda email + esa contraseña
#      temporal (como prueba de identidad, igual que un login) + la
#      contraseña definitiva que eligió.
#
# La respuesta de (1) es SIEMPRE la misma frase genérica exista o no el
# email, para no revelar por enumeración qué correos están registrados
# en el sistema. El "silencio" (no encontrar el email, o estar sobre el
# límite de solicitudes) se resuelve simplemente no mandando el correo,
# nunca cambiando la respuesta HTTP.

_MENSAJE_GENERICO_SOLICITUD = (
    "Si el correo está registrado, te enviamos una contraseña temporal. "
    "Revisá tu bandeja de entrada (y spam) y usala acá abajo para elegir tu contraseña nueva."
)


def _blacklistear_sesiones(usuario) -> None:
    """
    Blacklistea todos los refresh tokens vigentes del usuario. Se usa
    tanto al generar la contraseña temporal (SolicitarRecuperacionView)
    como al confirmarla (ConfirmarRecuperacionView), porque en ambos
    puntos la contraseña real del usuario cambió: cualquier sesión
    abierta con la contraseña anterior debería cerrarse.
    """
    try:
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )
        for outstanding in OutstandingToken.objects.filter(user=usuario):
            BlacklistedToken.objects.get_or_create(token=outstanding)
    except Exception:
        # No debe tumbar el cambio de contraseña si el blacklist falla
        # por cualquier motivo (tabla no migrada, etc.).
        pass


class SolicitarRecuperacionView(APIView):
    """
    POST /api/usuarios/auth/recuperar-password/
    Body: {"email": "..."}

    Genera una contraseña temporal nueva (mismo generador que se usa
    al crear un usuario, ver core.utils.passwords) y la manda por
    correo — no un enlace. El usuario la usa como password_actual en
    ConfirmarRecuperacionView, en la misma pantalla donde pidió la
    recuperación, para terminar de elegir su contraseña definitiva.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from modulo_usuarios.models.password_reset_token import PasswordResetToken
        from modulo_usuarios.models.perfil import PerfilUsuario
        from core.utils.emails import enviar_password_recuperacion
        from core.utils.passwords import generar_password_aleatoria

        serializer = SolicitarRecuperacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        # Respuesta genérica desde el inicio: se devuelve igual pase lo
        # que pase más abajo (email no encontrado, cuenta inactiva,
        # límite de solicitudes alcanzado). Solo cambia si se manda el
        # correo o no, nunca la respuesta HTTP — evita que este
        # endpoint sirva para averiguar qué correos están registrados.
        respuesta = Response(
            {"detail": _MENSAJE_GENERICO_SOLICITUD}, status=status.HTTP_200_OK
        )

        perfil = (
            PerfilUsuario.objects
            .select_related("usuario")
            .filter(email_hash=hash_lookup(email))
            .first()
        )
        if not perfil or not perfil.usuario.estado:
            return respuesta

        usuario = perfil.usuario

        # Límite anti-abuso: no generar más de PASSWORD_RESET_MAX_SOLICITUDES
        # contraseñas temporales para el mismo usuario dentro de la
        # ventana configurada. Importante acá más que en el flujo de
        # enlace: cada solicitud invalida la contraseña anterior de
        # verdad, así que sin este límite alguien podría dejar a un
        # usuario legítimo sin poder entrar solo con su email, spameando
        # el endpoint.
        ventana_inicio = timezone.now() - timezone.timedelta(
            minutes=settings.PASSWORD_RESET_VENTANA_MINUTOS
        )
        solicitudes_recientes = PasswordResetToken.objects.filter(
            usuario=usuario, creado_en__gte=ventana_inicio
        ).count()
        if solicitudes_recientes >= settings.PASSWORD_RESET_MAX_SOLICITUDES:
            return respuesta

        nueva_password = generar_password_aleatoria()
        usuario.set_password(nueva_password)
        usuario.debe_cambiar_password = True
        usuario.save(update_fields=["password", "debe_cambiar_password"])

        _blacklistear_sesiones(usuario)

        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() \
            or request.META.get("REMOTE_ADDR")

        # Registro con fines de auditoría y límite de solicitudes. No
        # se usa para "confirmar" nada (a diferencia del diseño
        # anterior basado en enlace): la contraseña temporal en sí es
        # la prueba de identidad en el paso de confirmación.
        PasswordResetToken.objects.create(
            usuario=usuario,
            token_hash=hashlib.sha256(secrets.token_urlsafe(32).encode()).hexdigest(),
            expira_en=timezone.now() + timezone.timedelta(
                minutes=settings.PASSWORD_RESET_VIGENCIA_MINUTOS
            ),
            usado_en=timezone.now(),
            ip_solicitud=ip,
        )

        enviar_password_recuperacion(email=email, usuario=usuario.usuario, password=nueva_password)

        registrar_auditoria(
            usuario=usuario,
            tabla="usuarios",
            accion="UPDATE",
            registro_id=usuario.pk,
            request=request,
            metadata={"campo": "password", "origen": "recuperacion_password_temporal"},
        )

        return respuesta


class ConfirmarRecuperacionView(APIView):
    """
    POST /api/usuarios/auth/recuperar-password/confirmar/
    Body: {"email", "password_actual", "password_nuevo", "password_confirm"}

    password_actual es la contraseña temporal que llegó por correo
    desde SolicitarRecuperacionView. Se valida contra la BD igual que
    un login (check_password), no contra un token: si es correcta,
    prueba que quien hace este request tiene acceso a esa casilla.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from modulo_usuarios.models.perfil import PerfilUsuario

        serializer = ConfirmarRecuperacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        # Mismo mensaje genérico exista o no la cuenta, o esté mal la
        # contraseña temporal: no hay forma de distinguir "no existe
        # esta cuenta" de "contraseña temporal incorrecta" desde
        # afuera.
        mensaje_error = (
            "Los datos ingresados no son correctos. Verificá el correo y la "
            "contraseña temporal que te llegó por email, o pedí una nueva."
        )

        perfil = (
            PerfilUsuario.objects
            .select_related("usuario")
            .filter(email_hash=hash_lookup(datos["email"]))
            .first()
        )
        if not perfil:
            return Response({"detail": mensaje_error}, status=status.HTTP_400_BAD_REQUEST)

        usuario = perfil.usuario
        if not usuario.estado or not usuario.check_password(datos["password_actual"]):
            return Response({"detail": mensaje_error}, status=status.HTTP_400_BAD_REQUEST)

        usuario.set_password(datos["password_nuevo"])
        usuario.debe_cambiar_password = False
        usuario.save(update_fields=["password", "debe_cambiar_password"])

        _blacklistear_sesiones(usuario)

        registrar_auditoria(
            usuario=usuario,
            tabla="usuarios",
            accion="UPDATE",
            registro_id=usuario.pk,
            request=request,
            metadata={"campo": "password", "origen": "recuperacion_confirmacion"},
        )

        return Response(
            {"detail": "Contraseña actualizada correctamente. Ya podés iniciar sesión."},
            status=status.HTTP_200_OK,
        )