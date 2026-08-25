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