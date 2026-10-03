from django.db import connection
from django.test import TestCase


class IndicesBusquedaTests(TestCase):
    def test_fusion_conserva_un_solo_indice_trigrama_por_campo(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT indexname, indexdef FROM pg_indexes "
                "WHERE tablename = %s AND schemaname = current_schema()",
                ['articulos'],
            )
            indices = dict(cursor.fetchall())
        for campo in ['titulo', 'contenido', 'numero']:
            nombre = f'idx_art_{campo}_trgm'
            self.assertIn(nombre, indices)
            self.assertIn('gin_trgm_ops', indices[nombre])
            self.assertNotIn(f'idx_articulos_{campo}_trgm', indices)
