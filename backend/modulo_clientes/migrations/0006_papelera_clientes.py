import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def rellenar_eliminacion_desde_auditoria(apps, schema_editor):
    """
    Los clientes que ya estaban eliminados antes de la papelera no tienen
    fecha ni autor. Se recuperan, cuando existen, del último registro de
    auditoría DELETE de ese cliente.
    """
    Cliente = apps.get_model("modulo_clientes", "Cliente")
    Auditoria = apps.get_model("modulo_auditoria", "Auditoria")

    for cliente in Cliente.objects.filter(estado=False, eliminado_at__isnull=True):
        registro = (
            Auditoria.objects
            .filter(tabla="clientes", accion="DELETE", registro_id=cliente.pk)
            .order_by("-created_at")
            .first()
        )
        if registro is not None:
            cliente.eliminado_at = registro.created_at
            cliente.eliminado_por_id = registro.usuario_id
            cliente.save(update_fields=["eliminado_at", "eliminado_por"])


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_clientes", "0005_cliente_hash_unique"),
        ("modulo_auditoria", "0002_alter_auditoria_options_alter_auditoria_ip"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="eliminado_at",
            field=models.DateTimeField(blank=True, help_text="Cuándo se envió el cliente a la papelera. Nulo si está activo.", null=True),
        ),
        migrations.AddField(
            model_name="cliente",
            name="eliminado_por",
            field=models.ForeignKey(blank=True, help_text="Quién envió el cliente a la papelera. Nulo si está activo.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="clientes_eliminados", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name="cliente",
            name="estado",
            field=models.BooleanField(default=True, help_text="True = cliente activo. False = cliente en la papelera (soft-delete; se recupera con papelera_service.restaurar_cliente)."),
        ),
        migrations.RunPython(rellenar_eliminacion_desde_auditoria, migrations.RunPython.noop),
    ]
