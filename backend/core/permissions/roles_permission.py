from rest_framework.permissions import SAFE_METHODS, BasePermission
from .roles import ROL_ADMINISTRADOR, ROL_ASISTENTE, ROLES_VEN_TODOS, rol_de


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


class EsOperativo(BasePermission):
    """
    Permiso para los módulos operativos (casos, clientes, documentos, IA):

    - Administrador y Abogado: acceso total (crear, editar, eliminar
      lógicamente, disparar análisis, etc.).
    - Asistente: solo lectura (GET / HEAD / OPTIONS). Cualquier método
      que modifique datos (POST, PATCH, PUT, DELETE) queda bloqueado,
      sin necesidad de listar acción por acción en cada vista.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.estado):
            return False

        rol = rol_de(user)
        if rol in ROLES_VEN_TODOS:  # administrador, abogado
            return True
        if rol == ROL_ASISTENTE:
            return request.method in SAFE_METHODS
        return False


class EsUsuarioAutenticado(BasePermission):
    """Cualquier usuario autenticado y activo (incluye Asistente)."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.estado
        )
