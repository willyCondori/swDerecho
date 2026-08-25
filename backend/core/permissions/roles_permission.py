from rest_framework.permissions import BasePermission
from .roles import ROL_ADMINISTRADOR, ROLES_VEN_TODOS, rol_de


class EsAdmin(BasePermission):
    """Solo usuarios con rol 'administrador'."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.estado
            and rol_de(request.user) == ROL_ADMINISTRADOR
        )


class EsAbogado(BasePermission):
    """Usuarios con rol 'abogado' o 'administrador'."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.estado
            and rol_de(request.user) in ROLES_VEN_TODOS
        )


class EsUsuarioAutenticado(BasePermission):
    """Cualquier usuario autenticado y activo (incluye Asistente)."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.estado
        )


class EsPropietarioOAdmin(BasePermission):
    """
    Permite acceso si el usuario es el dueño del objeto,
    o tiene rol Administrador/Abogado (visibilidad total).
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if rol_de(request.user) in ROLES_VEN_TODOS:
            return True
        owner = getattr(obj, "usuario", getattr(obj, "user", None))
        return owner == request.user