from core.encryption.aes_encryption import safe_decrypt


def nombre_visible_usuario(usuario):
    """Nombre y apellidos del perfil (descifrados); si no hay, el usuario. None si no hay usuario."""
    if usuario is None:
        return None
    perfil = getattr(usuario, "perfil", None)
    if perfil is not None:
        nombres   = safe_decrypt(perfil.nombres, fallback=None)
        apellidos = safe_decrypt(perfil.apellidos, fallback=None)
        if nombres is not None and apellidos is not None:
            completo = f"{nombres} {apellidos}".strip()
            if completo:
                return completo
    return usuario.usuario
