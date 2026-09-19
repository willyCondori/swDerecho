from django.db import migrations
from django.db.models import F, OuterRef, Subquery


def crear_historial_inicial(apps, schema_editor):
    """
    Los casos que ya existían antes del seguimiento arrancan en la etapa
    'registrado' con una primera entrada en su línea de tiempo, fechada
    en el momento en que se creó el caso.
    """
    Caso = apps.get_model("modulo_casos", "Caso")
    SeguimientoCaso = apps.get_model("modulo_casos", "SeguimientoCaso")

    sin_historial = Caso.objects.filter(seguimientos__isnull=True)
    SeguimientoCaso.objects.bulk_create(
        [
            SeguimientoCaso(
                caso_id=caso_id,
                etapa="registrado",
                etapa_anterior=None,
                nota="Caso registrado (historial iniciado al activar el seguimiento).",
                usuario_id=usuario_id,
            )
            for caso_id, usuario_id in sin_historial.values_list("pk", "usuario_id")
        ],
        batch_size=500,
    )

    # created_at es auto_now_add: se reemplaza por la fecha real del caso.
    SeguimientoCaso.objects.filter(
        etapa_anterior__isnull=True,
        nota__startswith="Caso registrado (historial iniciado",
    ).update(
        created_at=Subquery(
            Caso.objects.filter(pk=OuterRef("caso_id")).values("created_at")[:1]
        )
    )
    Caso.objects.filter(etapa_actualizada_at__isnull=True).update(
        etapa_actualizada_at=F("created_at")
    )


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_casos", "0003_seguimiento_etapas"),
    ]

    operations = [
        migrations.RunPython(crear_historial_inicial, migrations.RunPython.noop),
    ]
