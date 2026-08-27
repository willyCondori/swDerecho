from django.db import migrations

ENTIDADES = [
    "Menor de edad",
    "Mayor de edad",
    "Mujer",
    "Hombre",
    "Víctima",
    "Imputado",
    "Acusado",
    "Denunciante",
    "Querellante",
    "Demandante",
    "Demandado",
    "Testigo",
    "Perito",
    "Juez",
    "Fiscal",
    "Abogado",
    "Defensor",
    "Servidor Público",
    "Funcionario Público",
    "Policía",
    "Ministerio Público",
    "Estado",
    "Empresa",
    "Persona Natural",
    "Persona Jurídica",
    "Niño",
    "Niña",
    "Adolescente",
    "Adulto Mayor",
    "Persona con Discapacidad",
    "Trabajador",
    "Empleador",
    "Propietario",
    "Poseedor",
    "Arrendador",
    "Arrendatario",
    "Heredero",
    "Cónyuge",
    "Conviviente",
    "Padre",
    "Madre",
    "Tutor",
    "Curador",
]


def crear_entidades(apps, schema_editor):
    EntidadJuridica = apps.get_model("modulo_catalogo", "EntidadJuridica")
    for nombre in ENTIDADES:
        EntidadJuridica.objects.get_or_create(
            nombre=nombre,
            defaults={"descripcion": "", "estado": True},
        )


def eliminar_entidades(apps, schema_editor):
    EntidadJuridica = apps.get_model("modulo_catalogo", "EntidadJuridica")
    EntidadJuridica.objects.filter(nombre__in=ENTIDADES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_catalogo", "0004_seed_ramas_normas"),
    ]

    operations = [
        migrations.RunPython(crear_entidades, eliminar_entidades),
    ]