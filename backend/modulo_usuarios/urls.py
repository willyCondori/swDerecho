from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views.auth_view import (
    CambioPasswordView,
    ConfirmarRecuperacionView,
    LoginView,
    LogoutView,
    MeView,
    RefreshTokenView,
    SolicitarRecuperacionView,
)
from .views.usuario_view import UsuarioViewSet
from .views.rol_view import RolViewSet

router = DefaultRouter()
router.register(r"roles", RolViewSet, basename="roles")
router.register(r"usuarios", UsuarioViewSet, basename="usuarios")

urlpatterns = [
    # Auth
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/refresh/", RefreshTokenView.as_view(), name="auth-refresh"),
    path(
        "auth/cambiar-password/",
        CambioPasswordView.as_view(),
        name="auth-cambiar-password",
    ),
    path("auth/me/", MeView.as_view(), name="auth-me"),

    # Recuperación de contraseña por correo
    path(
        "auth/recuperar-password/",
        SolicitarRecuperacionView.as_view(),
        name="auth-recuperar-password",
    ),
    path(
        "auth/recuperar-password/confirmar/",
        ConfirmarRecuperacionView.as_view(),
        name="auth-recuperar-password-confirmar",
    ),

    path("", include(router.urls)),
]