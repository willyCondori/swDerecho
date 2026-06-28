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
    RefreshTokenSerializer,
)


class LoginView(APIView):
    """
    POST /api/auth/login/
    Autentica al usuario y devuelve access + refresh token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        user = data["user"]

        # Actualizar último login
        user.ultimo_login = timezone.now()
        user.save(update_fields=["ultimo_login"])

        registrar_auditoria(
            usuario=user,
            tabla="usuarios",
            accion="LOGIN",
            registro_id=user.pk,
            request=request,
        )

        return Response(
            {
                "access_token" : data["access_token"],
                "refresh_token": data["refresh_token"],
                "usuario": {
                    "id"     : user.id,
                    "usuario": user.usuario,
                    "rol"    : user.rol.nombre if user.rol else None,
                },
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Invalida el refresh token (blacklist).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
        except TokenError as e:
            return Response(
                {"detail": f"Token inválido o ya expirado: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        registrar_auditoria(
            usuario=request.user,
            tabla="usuarios",
            accion="LOGOUT",
            registro_id=request.user.pk,
            request=request,
        )

        return Response({"detail": "Sesión cerrada correctamente."}, status=status.HTTP_200_OK)


class RefreshTokenView(APIView):
    """
    POST /api/auth/refresh/
    Renueva el access token usando el refresh token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            refresh      = RefreshToken(serializer.validated_data["refresh"])
            access_token = str(refresh.access_token)
        except TokenError as e:
            return Response(
                {"detail": f"Token inválido o expirado: {str(e)}"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response({"access_token": access_token}, status=status.HTTP_200_OK)


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
        user.save(update_fields=["password"])

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
