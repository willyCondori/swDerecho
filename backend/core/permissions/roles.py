# core/permissions/roles.py

ROL_ADMINISTRADOR = "administrador"
ROL_ABOGADO       = "abogado"
ROL_ASISTENTE     = "asistente"

ROLES_VEN_TODOS = [ROL_ADMINISTRADOR, ROL_ABOGADO]


def rol_de(usuario) -> str:
    """Devuelve el nombre del rol del usuario en minúsculas, o '' si no tiene."""
    return getattr(usuario.rol, "nombre", "").lower() if usuario.rol else ""


def ve_todo(usuario) -> bool:
    """True si el usuario tiene visibilidad total (Admin o Abogado)."""
    return rol_de(usuario) in ROLES_VEN_TODOS


def es_administrador(usuario) -> bool:
    """True si el usuario tiene el rol Administrador (comparación case-insensitive)."""
    return rol_de(usuario) == ROL_ADMINISTRADOR


def administradores_activos_qs():
    """
    Queryset de usuarios con rol Administrador y estado activo.
    Import local del modelo para evitar import circular
    (modulo_usuarios.models.usuario -> core.permissions.roles).
    """
    from modulo_usuarios.models.usuario import Usuario

    return Usuario.objects.filter(rol__nombre__iexact=ROL_ADMINISTRADOR, estado=True)
