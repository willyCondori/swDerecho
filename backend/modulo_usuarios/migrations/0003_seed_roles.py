from django.db import migrations

ROLES = [
    ("Administrador", "Administrador del sistema"),
    ("Abogado", "Gestión de casos y clientes"),
    ("Asistente", "Apoyo administrativo"),
]


def crear_roles(apps, schema_editor):
    Rol = apps.get_model("modulo_usuarios", "Rol")
    for nombre, descripcion in ROLES:
        Rol.objects.get_or_create(
            nombre=nombre,
            defaults={"descripcion": descripcion, "estado": True},
        )


def eliminar_roles(apps, schema_editor):
    Rol = apps.get_model("modulo_usuarios", "Rol")
    Rol.objects.filter(nombre__in=[nombre for nombre, _ in ROLES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_usuarios", "0002_alter_usuario_password"),
    ]

    operations = [
        migrations.RunPython(crear_roles, eliminar_roles),
    ]