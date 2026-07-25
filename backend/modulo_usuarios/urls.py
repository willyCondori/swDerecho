from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views.auth_view import (
    CambioPasswordView,
    LoginView,
    LogoutView,
    MeView,
    RefreshTokenView,
)
from .views.usuario_view import (
    UsuarioViewSet,
    RolViewSet
)

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

    path("", include(router.urls)),
]