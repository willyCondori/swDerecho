"""
Cifrado simétrico AES-256-GCM para datos personales sensibles.
Cumple con ISO/IEC 27001 — control A.10.1 (Controles criptográficos).

Campos protegidos:
  perfil_usuarios : nombres, apellidos, email, telefono
  clientes        : nombres, apellidos, fecha_nacimiento

Uso:
    from core.encryption.aes_encryption import encrypt, decrypt

    texto_cifrado = encrypt("Juan Pérez")
    texto_plano   = decrypt(texto_cifrado)
"""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings


def _get_key() -> bytes:
    """
    Lee la clave AES-256 desde settings.ENCRYPTION_KEY (variable de entorno).
    Debe ser exactamente 32 bytes en hex (64 caracteres).
    """
    key_hex: str = getattr(settings, "ENCRYPTION_KEY", "")
    if not key_hex or len(key_hex) != 64:
        raise ValueError(
            "ENCRYPTION_KEY debe ser una cadena hex de 64 caracteres (32 bytes)."
        )
    return bytes.fromhex(key_hex)


def encrypt(plaintext: str) -> str:
    """
    Cifra un texto con AES-256-GCM.
    Devuelve base64(nonce + ciphertext_con_tag) como string.
    """
    if not plaintext:
        return plaintext

    key    = _get_key()
    nonce  = os.urandom(12)          # 96 bits — estándar para GCM
    aesgcm = AESGCM(key)
    ct     = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("utf-8")


def decrypt(ciphertext: str) -> str:
    """
    Descifra un valor cifrado con encrypt().
    Devuelve el texto plano original.
    """
    if not ciphertext:
        return ciphertext

    key    = _get_key()
    raw    = base64.b64decode(ciphertext.encode("utf-8"))
    nonce  = raw[:12]
    ct     = raw[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None).decode("utf-8")

# core/encryption/aes_encryption.py
# ... tus funciones encrypt/decrypt existentes arriba ...

def safe_decrypt(value, fallback="[cifrado]"):
    """
    Descifra un valor de forma segura. Si el valor es falsy o el
    descifrado falla (dato corrupto, clave rotada, etc.), devuelve
    el fallback en vez de propagar la excepción.

    Centraliza el patrón try/except que antes estaba duplicado en
    cada serializer.
    """
    try:
        return decrypt(value) if value else value
    except Exception:
        return fallback


# ---------------------------------------------------------------------------
# Hash determinístico para búsqueda (no reversible)
# ---------------------------------------------------------------------------
# AES-GCM usa un nonce aleatorio en cada encrypt(), así que dos veces el
# mismo email en texto plano producen dos ciphertexts distintos: no se
# puede indexar ni buscar "= valor" contra la columna cifrada. Antes esto
# forzaba a descifrar TODA la tabla en un loop para chequear unicidad de
# email (ver validate_email en usuario_serializer.py) — O(n) en cada alta
# de usuario y, peor, imposible de usar para "recuperar contraseña por
# email" con un volumen real de usuarios.
#
# hash_lookup() resuelve esto con HMAC-SHA256 determinístico: mismo
# input -> mismo hash siempre, así que se puede guardar en una columna
# indexada (email_hash) y buscar con un simple filter(email_hash=...).
# No es reversible (a diferencia de encrypt/decrypt), por eso conviven
# las dos columnas: `email` (AES-256, se descifra para mostrar) y
# `email_hash` (HMAC-SHA256, solo para buscar/comparar).
import hashlib
import hmac


def hash_lookup(value: str) -> str:
    """
    HMAC-SHA256 determinístico de `value`, normalizado (strip + lower)
    para que "Juan@Mail.com" y "juan@mail.com" generen el mismo hash.
    Devuelve un hex digest de 64 caracteres.

    Si `value` es falsy (None, "" ...) devuelve None en vez de "" o el
    valor tal cual: con la columna email_hash siendo unique=True,
    Postgres permite múltiples NULL en una columna unique pero NO
    permite múltiples "" — así que dos perfiles con email vacío/no
    descifrable no chocan entre sí por un hash "vacío" compartido.

    Usa ENCRYPTION_KEY como clave del HMAC (misma clave que ya se
    protege como secreto para AES) en vez de definir una clave nueva
    a rotar por separado.
    """
    if not value:
        return None
    key = _get_key()
    normalizado = value.strip().lower()
    return hmac.new(key, normalizado.encode("utf-8"), hashlib.sha256).hexdigest()