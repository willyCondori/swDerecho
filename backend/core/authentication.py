from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme


class PasswordRequiredJWTAuthentication(JWTAuthentication):
    """La contraseña temporal solo habilita completar el ingreso o salir."""
    onboarding_routes = {"auth-me", "auth-cambiar-password", "auth-logout"}

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not user.estado:
            raise AuthenticationFailed("Usuario inactivo.", code="user_inactive")
        return user

    def authenticate(self, request):
        result = super().authenticate(request)
        if result:
            user, _ = result
            match = request.resolver_match
            if user.debe_cambiar_password and (
                not match or match.url_name not in self.onboarding_routes
            ):
                raise PermissionDenied(
                    {"detail": "Debes cambiar tu contraseña antes de continuar.",
                     "code": "password_change_required"}
                )
        return result


class PasswordRequiredJWTScheme(SimpleJWTScheme):
    target_class = "core.authentication.PasswordRequiredJWTAuthentication"
