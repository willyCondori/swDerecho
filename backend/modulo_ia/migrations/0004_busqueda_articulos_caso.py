from django.db import migrations


SQL = """
CREATE FUNCTION buscar_articulos_caso(
    p_caso_id bigint, p_version text, p_rama_id bigint, p_limite integer
)
RETURNS TABLE(chunk_id bigint, articulo_id bigint, distancia double precision)
LANGUAGE sql STABLE SECURITY INVOKER AS $$
    SELECT ec.chunk_id, vecinos.articulo_id, vecinos.distancia
    FROM embeddings_chunk ec
    JOIN chunks_caso c ON c.id = ec.chunk_id
    LEFT JOIN LATERAL (
        SELECT ea.articulo_id, ea.vector <=> ec.vector AS distancia
        FROM embeddings_articulos ea
        JOIN articulos a ON a.id = ea.articulo_id
        JOIN normas n ON n.id = a.norma_id
        WHERE ea.modelo_version = p_version AND a.estado AND n.estado
          AND (p_rama_id IS NULL OR a.rama_id = p_rama_id)
        ORDER BY ea.vector <=> ec.vector
        LIMIT LEAST(GREATEST(p_limite, 1), 200)
    ) vecinos ON TRUE
    WHERE c.caso_id = p_caso_id AND ec.modelo_version = p_version
    ORDER BY c.orden, ec.chunk_id;
$$;
"""


class Migration(migrations.Migration):
    dependencies = [("modulo_ia", "0003_versionar_embeddings")]
    operations = [migrations.RunSQL(
        SQL, "DROP FUNCTION buscar_articulos_caso(bigint, text, bigint, integer);"
    )]
