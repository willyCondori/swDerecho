"""
Generación de contraseñas temporales aleatorias para el alta de
usuarios. La contraseña generada cumple las mismas reglas de
fortaleza que valida CambioPasswordSerializer._validar_fortaleza_password
(mínimo 8 caracteres, mayúscula, minúscula, número y carácter especial),
para que el usuario nunca reciba por correo una contraseña que el
propio backend rechazaría.
"""

import secrets
import string

_MAYUSCULAS = string.ascii_uppercase
_MINUSCULAS = string.ascii_lowercase
_NUMEROS    = string.digits
_ESPECIALES = "!@#$%^&*()_+-="

# Se excluyen caracteres ambiguos (0/O, 1/l/I) para que la contraseña
# se pueda transcribir a mano sin errores si hace falta.
_MAYUSCULAS = _MAYUSCULAS.replace("O", "").replace("I", "")
_MINUSCULAS = _MINUSCULAS.replace("l", "")
_NUMEROS    = _NUMEROS.replace("0", "").replace("1", "")


def generar_password_aleatoria(longitud: int = 12) -> str:
    """
    Genera una contraseña aleatoria criptográficamente segura que
    garantiza al menos: 1 mayúscula, 1 minúscula, 1 número y 1
    carácter especial.
    """
    if longitud < 8:
        longitud = 8

    # Garantiza al menos un carácter de cada categoría obligatoria.
    obligatorios = [
        secrets.choice(_MAYUSCULAS),
        secrets.choice(_MINUSCULAS),
        secrets.choice(_NUMEROS),
        secrets.choice(_ESPECIALES),
    ]

    resto_pool = _MAYUSCULAS + _MINUSCULAS + _NUMEROS + _ESPECIALES
    resto = [secrets.choice(resto_pool) for _ in range(longitud - len(obligatorios))]

    password_chars = obligatorios + resto
    # Barajado criptográficamente seguro (Fisher-Yates con secrets).
    for i in range(len(password_chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        password_chars[i], password_chars[j] = password_chars[j], password_chars[i]

    return "".join(password_chars)