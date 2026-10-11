"""Inventario de solo lectura, sin valores personales ni credenciales.

Ejecutar: python manage.py shell -c "exec(open('../scripts/inventario_bd.py').read())"
Una tabla vacía NO implica que esté fuera de uso. Revisar también sus referencias.
"""
import json
from django.apps import apps
from django.db import connection

tablas = set(connection.introspection.table_names())
modelos = []
for modelo in apps.get_models(include_auto_created=True):
    if modelo._meta.proxy:
        continue
    tabla = modelo._meta.db_table
    filas = None
    if tabla in tablas:
        with connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM ' + connection.ops.quote_name(tabla))
            filas = cursor.fetchone()[0]
    modelos.append({'modelo': modelo._meta.label, 'tabla': tabla,
                    'existe': tabla in tablas, 'filas': filas})
print(json.dumps({'modelos': modelos, 'tablas_sin_modelo': sorted(
    tablas - {m['tabla'] for m in modelos})}, ensure_ascii=False, indent=2))
