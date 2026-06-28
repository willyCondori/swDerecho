"""
Cifrado simétrico AES-256-GCM para datos personales sensibles.
Cumple con ISO/IEC 27001 — control A.10.1 (Controles criptográficos).

Campos protegidos:
  perfil_usuarios : nombres, apellidos, email, telefono, ci
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
