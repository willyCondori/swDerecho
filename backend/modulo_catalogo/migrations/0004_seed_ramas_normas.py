from django.db import migrations

RAMAS = [
    "Penal",
    "Derecho Constitucional",
]

RAMAS_DESCRIPCION = {
    "Penal": "Derecho Penal — delitos, penas y procedimiento penal boliviano.",
    "Derecho Constitucional": (
        "Rama del derecho que estudia la Constitución Política del Estado "
        "y la organización del Estado."
    ),
}

# (nombre, sigla, nivel_jerarquia)
# nivel_jerarquia hace referencia a Jerarquia.nivel (ver 0003_seed_jerarquias)
NORMAS = [
    ("Código Penal Boliviano", "CP", 2),                    # Ley
    ("Constitución Política del Estado", "CPE", 1),          # Constitución
]


def crear_ramas_y_normas(apps, schema_editor):
    RamaDerecho = apps.get_model("modulo_catalogo", "RamaDerecho")
    Norma       = apps.get_model("modulo_catalogo", "Norma")
    Jerarquia   = apps.get_model("modulo_catalogo", "jerarquia")

    for nombre in RAMAS:
        RamaDerecho.objects.get_or_create(
            nombre=nombre,
            defaults={
                "descripcion": RAMAS_DESCRIPCION.get(nombre, ""),
                "estado": True,
            },
        )

    for nombre, sigla, nivel in NORMAS:
        jerarquia_obj = Jerarquia.objects.filter(nivel=nivel).first()
        norma, creada = Norma.objects.get_or_create(
            sigla=sigla,
            defaults={"nombre": nombre, "estado": True, "jerarquia": jerarquia_obj},
        )
        # Si la norma ya existía (por ejemplo, cargada antes de este cambio)
        # y todavía no tiene jerarquía asignada, se la completamos aquí.
        if not creada and norma.jerarquia_id is None and jerarquia_obj is not None:
            norma.jerarquia = jerarquia_obj
            norma.save(update_fields=["jerarquia"])


def eliminar_ramas_y_normas(apps, schema_editor):
    RamaDerecho = apps.get_model("modulo_catalogo", "RamaDerecho")
    Norma       = apps.get_model("modulo_catalogo", "Norma")

    Norma.objects.filter(sigla__in=[sigla for _, sigla, _ in NORMAS]).delete()
    RamaDerecho.objects.filter(nombre__in=RAMAS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_catalogo", "0003_seed_jerarquias"),
    ]

    operations = [
        migrations.RunPython(crear_ramas_y_normas, eliminar_ramas_y_normas),
    ]