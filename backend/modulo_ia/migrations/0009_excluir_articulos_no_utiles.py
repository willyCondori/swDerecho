from importlib import import_module
from django.db import migrations, models


ANTERIOR = import_module('modulo_ia.migrations.0005_ranking_vigencia').ACTUAL
ACTUAL = ANTERIOR.replace(
    'AND (p_rama_id IS NULL OR a.rama_id = p_rama_id)',
    """AND (p_rama_id IS NULL OR a.rama_id = p_rama_id)
          AND COALESCE((
              SELECT v.valor FROM modulo_ia_valoracionarticulo v
              WHERE v.caso_id = p_caso_id AND v.articulo_id = a.id
              ORDER BY v.id DESC LIMIT 1
          ), 'sin_valorar') <> 'no_util'""",
)


class Migration(migrations.Migration):
    dependencies = [('modulo_ia', '0008_resultadoarticulo_contexto_evaluado')]
    operations = [
        migrations.AddIndex(
            model_name='valoracionarticulo',
            index=models.Index(fields=['caso', 'articulo', '-id'], name='idx_valoracion_caso_articulo'),
        ),
        migrations.RunSQL(ACTUAL, ANTERIOR),
    ]
