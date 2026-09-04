"""
Helpers compartidos para los tests de modulo_usuarios.

Centraliza la creación de Rol / Usuario / PerfilUsuario (con el
cifrado AES-256 del email y su email_hash correspondiente) para que
cada archivo de test no tenga que repetir el mismo boilerplate de
`encrypt()` / `hash_lookup()`.
"""

from core.encryption.aes_encryption import encrypt, hash_lookup
from modulo_usuarios.models.perfil import PerfilUsuario
from modulo_usuarios.models.rol import Rol
from modulo_usuarios.models.usuario import Usuario

PASSWORD_VALIDA = "Segura#123"


def crear_rol(nombre="Administrador"):
    rol, _ = Rol.objects.get_or_create(
        nombre=nombre,
        defaults={"descripcion": nombre, "estado": True},
    )
    return rol


def crear_usuario(usuario="jdoe", password=PASSWORD_VALIDA, rol=None, estado=True, **extra):
    if rol is None:
        rol = crear_rol()
    return Usuario.objects.create_user(
        usuario=usuario, password=password, rol=rol, estado=estado, **extra
    )


def crear_perfil(usuario, email="jdoe@example.com", nombres="Juan", apellidos="Doe", telefono="70000000"):
    return PerfilUsuario.objects.create(
        usuario=usuario,
        nombres=encrypt(nombres),
        apellidos=encrypt(apellidos),
        email=encrypt(email),
        email_hash=hash_lookup(email),
        telefono=encrypt(telefono) if telefono else telefono,
    )


def crear_usuario_con_perfil(usuario="jdoe", password=PASSWORD_VALIDA, email="jdoe@example.com", **extra):
    user = crear_usuario(usuario=usuario, password=password, **extra)
    perfil = crear_perfil(user, email=email)
    return user, perfil
