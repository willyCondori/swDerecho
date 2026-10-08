from django.db import migrations
from django.db.models import Value
from django.db.models.functions import Replace


def normalizar_rutas(apps, schema_editor):
    DocumentoNorma = apps.get_model('modulo_catalogo', 'DocumentoNorma')
    DocumentoNorma.objects.using(schema_editor.connection.alias).filter(
        ruta_archivo__contains='\\',
    ).update(ruta_archivo=Replace('ruta_archivo', Value('\\'), Value('/')))


class Migration(migrations.Migration):
    dependencies = [('modulo_catalogo', '0018_cambionormativo_restaurado_at_and_more')]
    operations = [migrations.RunPython(normalizar_rutas, migrations.RunPython.noop)]
