from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from core.permissions.auditoria_mixin import registrar_auditoria
from modulo_usuarios.serializers.auth_serializer import (
    CambioPasswordSerializer,
    LoginSerializer,
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

        serializer.is_valid(raise_exception=True)

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