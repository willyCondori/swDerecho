from django.db import migrations

JERARQUIAS = [
    ("Constitución", 1),
    ("Ley", 2),
    ("Ley Departamental", 3),
    ("Ley Municipal", 4),
    ("Decreto Supremo", 5),
    ("Decreto Departamental", 6),
    ("Decreto Municipal", 7),
    ("Reglamento", 8),
    ("Resolución Suprema", 9),
    ("Resolución Ministerial", 10),
]


def crear_jerarquias(apps, schema_editor):
    Jerarquia = apps.get_model("modulo_catalogo", "jerarquia")
    for nombre, nivel in JERARQUIAS:
        Jerarquia.objects.get_or_create(
            nivel=nivel,
            defaults={"nombre": nombre, "estado": True},
        )


def eliminar_jerarquias(apps, schema_editor):
    Jerarquia = apps.get_model("modulo_catalogo", "jerarquia")
    Jerarquia.objects.filter(
        nivel__in=[nivel for _, nivel in JERARQUIAS]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_catalogo", "0002_jerarquia_remove_articulo_jerarquia_normativa_and_more"),
    ]

    operations = [
        migrations.RunPython(crear_jerarquias, eliminar_jerarquias),
    ]