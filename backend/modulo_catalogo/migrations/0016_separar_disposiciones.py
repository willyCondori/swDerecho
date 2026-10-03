from django.db import migrations


def separar(apps, schema_editor):
    Articulo = apps.get_model('modulo_catalogo', 'Articulo')
    Disposicion = apps.get_model('modulo_catalogo', 'DisposicionNormativa')
    for articulo in Articulo.objects.exclude(tipo_unidad='articulo').iterator():
        if articulo.documento_norma_id and articulo.tipo_unidad in ['final', 'derogatoria', 'abrogatoria']:
            Disposicion.objects.get_or_create(documento_id=articulo.documento_norma_id,
                numero=articulo.numero_articulo, defaults={'tipo': articulo.tipo_unidad,
                'titulo': articulo.titulo or '', 'contenido': articulo.contenido})
    # Mantener registros antiguos por sus referencias/historial, fuera del catálogo activo.
    Articulo.objects.exclude(tipo_unidad='articulo').update(estado=False)


class Migration(migrations.Migration):
    dependencies = [('modulo_catalogo', '0015_disposicionnormativa')]
    operations = [migrations.RunPython(separar, migrations.RunPython.noop)]
