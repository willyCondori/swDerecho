from importlib import import_module
from django.db import migrations


ANTERIOR = import_module('modulo_ia.migrations.0004_busqueda_articulos_caso').SQL.replace(
    'CREATE FUNCTION buscar_articulos_caso', 'CREATE OR REPLACE FUNCTION buscar_articulos_caso')

VIGENCIA = """
CREATE FUNCTION articulo_disponible_ranking(p_articulo_id bigint, p_norma_id bigint)
RETURNS boolean LANGUAGE sql STABLE SECURITY INVOKER AS $$
    SELECT NOT EXISTS (
        SELECT 1 FROM modulo_catalogo_cambionormativo cambio
        WHERE cambio.estado_revision = 'confirmado'
          AND cambio.operacion IN ('deroga', 'abroga')
          AND cambio.fecha_efecto <= (CURRENT_TIMESTAMP AT TIME ZONE 'America/La_Paz')::date
          AND (cambio.articulo_afectado_id = p_articulo_id OR
               (cambio.articulo_afectado_id IS NULL AND cambio.norma_afectada_id = p_norma_id))
          AND COALESCE(cambio.referencia->'parte_afectada'->>'tipo', '') <> 'parcial'
          AND (cambio.referencia->'parte_afectada'->>'tipo' = 'total' OR
               lower(trim(cambio.referencia->>'alcance')) IN
                 ('total', 'completo', 'articulo completo', 'artículo completo', 'norma completa'))
    );
$$;
"""
ACTUAL = ANTERIOR.replace(
    'AND a.estado AND n.estado',
    "AND a.estado AND n.estado AND a.tipo_unidad = 'articulo' "
    'AND articulo_disponible_ranking(a.id, a.norma_id)')


class Migration(migrations.Migration):
    dependencies = [
        ('modulo_ia', '0004_busqueda_articulos_caso'),
        ('modulo_catalogo', '0018_cambionormativo_restaurado_at_and_more'),
    ]
    operations = [
        migrations.RunSQL(VIGENCIA, 'DROP FUNCTION articulo_disponible_ranking(bigint, bigint);'),
        migrations.RunSQL(ACTUAL, ANTERIOR),
    ]
