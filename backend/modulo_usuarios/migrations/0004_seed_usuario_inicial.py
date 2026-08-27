from django.contrib.auth.hashers import make_password
from django.db import migrations

USUARIO  = "willy"
PASSWORD = "Willy114958*"


def crear_usuario_inicial(apps, schema_editor):
    Usuario = apps.get_model("modulo_usuarios", "Usuario")
    Rol     = apps.get_model("modulo_usuarios", "Rol")

    if Usuario.objects.filter(usuario=USUARIO).exists():
        return

    rol_admin, _ = Rol.objects.get_or_create(
        nombre="Administrador",
        defaults={"descripcion": "Administrador del sistema", "estado": True},
    )

    Usuario.objects.create(
        usuario=  USUARIO,
        password= make_password(PASSWORD),
        rol=      rol_admin,
        estado=   True,
    )


def eliminar_usuario_inicial(apps, schema_editor):
    Usuario = apps.get_model("modulo_usuarios", "Usuario")
    Usuario.objects.filter(usuario=USUARIO).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_usuarios", "0003_seed_roles"),
    ]

    operations = [
        migrations.RunPython(crear_usuario_inicial, eliminar_usuario_inicial),
    ]