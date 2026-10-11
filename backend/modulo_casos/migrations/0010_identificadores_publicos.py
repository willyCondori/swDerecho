import uuid
from django.db import migrations, models

def asignar_uuid(apps, schema_editor):
    for nombre in ['Caso']:
        modelo = apps.get_model('modulo_casos', nombre)
        qs = modelo.objects.using(schema_editor.connection.alias)
        for registro in qs.filter(public_id__isnull=True).iterator(chunk_size=1000):
            qs.filter(pk=registro.pk).update(public_id=uuid.uuid4())

class Migration(migrations.Migration):
    dependencies = [('modulo_casos', '0009_resultadocaso_jurisprudencia_estado_and_more')]
    operations = [
        migrations.AddField(model_name='caso', name='public_id', field=models.UUIDField(null=True, editable=False)),
        migrations.RunPython(asignar_uuid, migrations.RunPython.noop),
        migrations.AlterField(model_name='caso', name='public_id', field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
    ]
