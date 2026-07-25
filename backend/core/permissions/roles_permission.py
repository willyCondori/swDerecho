from rest_framework.permissions import BasePermission


class EsAdmin(BasePermission):
    """Solo usuarios con rol 'admin'."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.estado
            and hasattr(request.user, "rol")
            and request.user.rol is not None
            and request.user.rol.nombre.lower() == "administrador"
        )


class EsAbogado(BasePermission):
    """Usuarios con rol 'abogado' o 'admin'."""
    ROLES_PERMITIDOS = {"administrador", "abogado"}

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.estado
            and hasattr(request.user, "rol")
            and request.user.rol is not None
            and request.user.rol.nombre.lower() in self.ROLES_PERMITIDOS
        )


class EsUsuarioAutenticado(BasePermission):
    """Cualquier usuario autenticado y activo."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.estado
        )


class EsPropietarioOAdmin(BasePermission):
    """
    Permite acceso si el usuario es el dueño del objeto
    o tiene rol 'admin'.
    Se usa como permiso de objeto (has_object_permission).
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        rol = getattr(request.user.rol, "nombre", "").lower() if request.user.rol else ""
        if rol == "Administrador":
            return True
        # El objeto puede tener 'usuario' o 'user'
        owner = getattr(obj, "usuario", getattr(obj, "user", None))
        return owner == request.user
