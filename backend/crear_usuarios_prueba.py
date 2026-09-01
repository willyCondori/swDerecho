# Ejecutar con: python manage.py shell
# (o: python manage.py shell < crear_usuarios_prueba.py)

from core.encryption.aes_encryption import encrypt
from modulo_usuarios.models.rol import Rol
from modulo_usuarios.models.usuario import Usuario
from modulo_usuarios.models.perfil import PerfilUsuario

# Los roles ya existen por la migración 0003_seed_roles.py — get_or_create
# es solo defensivo por si corrés esto en una DB sin seed.
rol_abogado, _   = Rol.objects.get_or_create(
    nombre="Abogado", defaults={"descripcion": "Gestión de casos y clientes", "estado": True}
)
rol_asistente, _ = Rol.objects.get_or_create(
    nombre="Asistente", defaults={"descripcion": "Apoyo administrativo", "estado": True}
)

USUARIOS = [
    {
        "usuario":   "abogado1",
        "password":  "Abogado123!",
        "rol":       rol_abogado,
        "nombres":   "Juan",
        "apellidos": "Pérez",
        "email":     "abogado1@swderecho.test",
        "telefono":  "70000001",
    },
    {
        "usuario":   "asistente1",
        "password":  "Asistente123!",
        "rol":       rol_asistente,
        "nombres":   "Maria",
        "apellidos": "Lopez",
        "email":     "asistente1@swderecho.test",
        "telefono":  "70000002",
    },
]

for datos in USUARIOS:
    if Usuario.objects.filter(usuario=datos["usuario"]).exists():
        print(f"Ya existe: {datos['usuario']} — se omite.")
        continue

    usuario = Usuario.objects.create_user(
        usuario=datos["usuario"],
        password=datos["password"],
        rol=datos["rol"],
        estado=True,
    )

    PerfilUsuario.objects.create(
        usuario=usuario,
        nombres=encrypt(datos["nombres"]),
        apellidos=encrypt(datos["apellidos"]),
        email=encrypt(datos["email"]),
        telefono=encrypt(datos["telefono"]),
        estado=True,
    )

    print(f"Creado: {datos['usuario']}  (rol={datos['rol'].nombre}, password={datos['password']})")

print("Listo.")