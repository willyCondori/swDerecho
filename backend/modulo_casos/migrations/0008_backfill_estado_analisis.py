from django.db import migrations


def marcar_completados(apps, schema_editor):
    """
    Antes de este cambio, "tiene análisis" se sabía por la existencia de un
    ResultadoCaso (relación resultado), no por un campo de estado. Los casos
    que ya pasaron por el pipeline (viejo, síncrono) quedan marcados
    COMPLETADO para no mostrarlos como "Sin analizar" con el nuevo flujo.
    """
    Caso = apps.get_model("modulo_casos", "Caso")
    Caso.objects.filter(resultado__isnull=False).update(estado_analisis="completado")


def revertir(apps, schema_editor):
    Caso = apps.get_model("modulo_casos", "Caso")
    Caso.objects.filter(resultado__isnull=False).update(estado_analisis="pendiente")


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_casos", "0007_estado_analisis"),
    ]

    operations = [
        migrations.RunPython(marcar_completados, revertir),
    ]
