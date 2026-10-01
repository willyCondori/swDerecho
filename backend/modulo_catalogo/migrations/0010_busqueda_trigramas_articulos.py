from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations

# SearchFilter (icontains) arma UPPER(col) LIKE UPPER('%texto%'). Un GIN de
# trigramas sobre UPPER(col) lo acelera sin cambiar ningún resultado. Se crea
# con SQL porque GinIndex(OpClass(Upper(...))) genera SQL inválido en Django 5.2
# ("USING gin ((UPPER(col) gin_trgm_ops))").


class Migration(migrations.Migration):

    dependencies = [
        ('modulo_catalogo', '0009_documentonorma_vigente'),
    ]

    operations = [
        # pg_trgm viene con PostgreSQL (contrib), igual que pgvector se habilita
        # por migración (ver modulo_ia 0000_enable_pgvector_extension).
        TrigramExtension(),
        migrations.RunSQL(
            sql='CREATE INDEX IF NOT EXISTS idx_articulos_contenido_trgm '
                'ON articulos USING gin (UPPER(contenido) gin_trgm_ops);',
            reverse_sql='DROP INDEX IF EXISTS idx_articulos_contenido_trgm;',
        ),
        migrations.RunSQL(
            sql='CREATE INDEX IF NOT EXISTS idx_articulos_titulo_trgm '
                'ON articulos USING gin (UPPER(titulo) gin_trgm_ops);',
            reverse_sql='DROP INDEX IF EXISTS idx_articulos_titulo_trgm;',
        ),
        migrations.RunSQL(
            sql='CREATE INDEX IF NOT EXISTS idx_articulos_numero_trgm '
                'ON articulos USING gin (UPPER(numero_articulo) gin_trgm_ops);',
            reverse_sql='DROP INDEX IF EXISTS idx_articulos_numero_trgm;',
        ),
    ]
