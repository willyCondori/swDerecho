from django.db import migrations, models
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.operations import AddIndexConcurrently
from pgvector.django import IvfflatIndex

class Migration(migrations.Migration):
    atomic = False
    dependencies = [('modulo_ia', '0010_jurisprudencia_hibrida')]
    operations = [
        migrations.AddField(model_name='fragmentojurisprudencia', name='busqueda',
            field=models.GeneratedField(expression=SearchVector('contenido', config='spanish'),
                output_field=SearchVectorField(), db_persist=True)),
        AddIndexConcurrently(model_name='fragmentojurisprudencia',
            index=GinIndex(fields=['busqueda'], name='idx_juris_texto')),
        # PostgreSQL de Docker tiene /dev/shm pequeño: no usar workers
        # paralelos para construir este índice; restaurar el ajuste al salir.
        migrations.RunSQL('SET max_parallel_maintenance_workers = 0', migrations.RunSQL.noop),
        AddIndexConcurrently(model_name='embeddingjurisprudencia',
            index=IvfflatIndex(fields=['vector'], name='idx_juris_vector', lists=200,
                opclasses=['vector_cosine_ops'])),
        migrations.RunSQL('RESET max_parallel_maintenance_workers', migrations.RunSQL.noop),
    ]
