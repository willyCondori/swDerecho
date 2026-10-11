import uuid
from django.db import migrations, models

def asignar_uuid(apps, schema_editor):
    for nombre in ['DocumentoCaso', 'DocumentoGenerado']:
        modelo = apps.get_model('modulo_documentos', nombre)
        qs = modelo.objects.using(schema_editor.connection.alias)
        for registro in qs.filter(public_id__isnull=True).iterator(chunk_size=1000):
            qs.filter(pk=registro.pk).update(public_id=uuid.uuid4())

class Migration(migrations.Migration):
    dependencies = [('modulo_documentos', '0002_textodocumentocaso')]
    operations = [
        migrations.AddField(model_name='documentocaso', name='public_id', field=models.UUIDField(null=True, editable=False)),
        migrations.AddField(model_name='documentogenerado', name='public_id', field=models.UUIDField(null=True, editable=False)),
        migrations.RunPython(asignar_uuid, migrations.RunPython.noop),
        migrations.AlterField(model_name='documentocaso', name='public_id', field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
        migrations.AlterField(model_name='documentogenerado', name='public_id', field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
    ]
