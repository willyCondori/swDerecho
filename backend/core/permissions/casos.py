from .roles import ROLES_VEN_TODOS, ROL_ASISTENTE, rol_de


def casos_visibles(queryset, usuario, prefijo=""):
    """Lectura compartida de casos activos y recursos vinculados, por rol."""
    if not (usuario and usuario.is_authenticated and usuario.estado
            and not usuario.debe_cambiar_password
            and rol_de(usuario) in [*ROLES_VEN_TODOS, ROL_ASISTENTE]):
        return queryset.none()
    return queryset.filter(**{f"{prefijo}estado": True})
