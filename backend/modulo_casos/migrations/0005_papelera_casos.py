import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def rellenar_eliminacion_desde_auditoria(apps, schema_editor):
    """
    Los casos que ya estaban eliminados antes de la papelera no tienen
    fecha ni autor. Se recuperan, cuando existen, del último registro de
    auditoría DELETE de ese caso.
    """
    Caso = apps.get_model("modulo_casos", "Caso")
    Auditoria = apps.get_model("modulo_auditoria", "Auditoria")

    for caso in Caso.objects.filter(estado=False, eliminado_at__isnull=True):
        registro = (
            Auditoria.objects
            .filter(tabla="casos", accion="DELETE", registro_id=caso.pk)
            .order_by("-created_at")
            .first()
        )
        if registro is not None:
            caso.eliminado_at = registro.created_at
            caso.eliminado_por_id = registro.usuario_id
            caso.save(update_fields=["eliminado_at", "eliminado_por"])


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_casos", "0004_backfill_seguimiento_inicial"),
        ("modulo_auditoria", "0002_alter_auditoria_options_alter_auditoria_ip"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="caso",
            name="eliminado_at",
            field=models.DateTimeField(blank=True, help_text="Cuándo se envió el caso a la papelera. Nulo si está activo.", null=True),
        ),
        migrations.AddField(
            model_name="caso",
            name="eliminado_por",
            field=models.ForeignKey(blank=True, help_text="Quién envió el caso a la papelera. Nulo si está activo.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="casos_eliminados", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name="caso",
            name="estado",
            field=models.BooleanField(default=True, help_text="True = caso activo. False = caso en la papelera (soft-delete; se recupera con papelera_service.restaurar_desde_papelera)."),
        ),
        migrations.RunPython(rellenar_eliminacion_desde_auditoria, migrations.RunPython.noop),
    ]
