import uuid
from django.db import migrations, models

def asignar_uuid(apps, schema_editor):
    for nombre in ['Notificacion']:
        modelo = apps.get_model('modulo_notificaciones', nombre)
        qs = modelo.objects.using(schema_editor.connection.alias)
        for registro in qs.filter(public_id__isnull=True).iterator(chunk_size=1000):
            qs.filter(pk=registro.pk).update(public_id=uuid.uuid4())

class Migration(migrations.Migration):
    dependencies = [('modulo_notificaciones', '0003_eventos_tiempo_real')]
    operations = [
        migrations.AddField(model_name='notificacion', name='public_id', field=models.UUIDField(null=True, editable=False)),
        migrations.RunPython(asignar_uuid, migrations.RunPython.noop),
        migrations.AlterField(model_name='notificacion', name='public_id', field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
    ]
