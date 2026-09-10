from django.db import migrations


def corregir_niveles_duplicados(apps, schema_editor):
    """
    Antes de que existiera la validación/cascada de niveles, se pudieron
    crear jerarquías activas con el mismo nivel (ej. dos jerarquías en
    nivel 4). Esta migración renumera las jerarquías activas de forma
    secuencial (1, 2, 3, ...) respetando el orden actual (nivel, id),
    de modo que ninguna quede repetida y se conserve el orden relativo
    que ya tenían.

    Las jerarquías eliminadas (estado=False) no se tocan: no aparecen
    en el catálogo activo y no participan de la escala visible.
    """
    Jerarquia = apps.get_model("modulo_catalogo", "jerarquia")

    activas = list(
        Jerarquia.objects.filter(estado=True).order_by("nivel", "id")
    )

    # Solo tocar la BD si de verdad hay niveles repetidos entre las
    # jerarquías activas.
    niveles = [j.nivel for j in activas]
    if len(niveles) == len(set(niveles)):
        return

    for nuevo_nivel, jerarquia in enumerate(activas, start=1):
        if jerarquia.nivel != nuevo_nivel:
            jerarquia.nivel = nuevo_nivel
            jerarquia.save(update_fields=["nivel"])


def revertir(apps, schema_editor):
    # No hay forma segura de recuperar los niveles originales duplicados;
    # esta migración de datos no es reversible.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_catalogo", "0005_seed_entidades"),
    ]

    operations = [
        migrations.RunPython(corregir_niveles_duplicados, revertir),
    ]
