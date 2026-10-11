from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('modulo_ia', '0009_excluir_articulos_no_utiles')]
    operations = [
        migrations.AddField('resultadojurisprudencia', 'score_hibrido', models.FloatField(default=0)),
        migrations.AddField('resultadojurisprudencia', 'es_sugerencia', models.BooleanField(default=False)),
        migrations.AddField('resultadojurisprudencia', 'coincidencias', models.JSONField(default=list)),
        migrations.AddField('resultadojurisprudencia', 'motivo_recomendacion', models.TextField(blank=True)),
    ]
