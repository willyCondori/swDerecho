from django.contrib.postgres.operations import CreateExtension
from django.db import migrations


class Migration(migrations.Migration):
    """
    Habilita la extensión `vector` (pgvector) en la base de datos antes
    de crear cualquier columna VectorField (ver modulo_ia/migrations/
    0001_initial.py: EmbeddingArticulo.vector, EmbeddingChunk.vector).

    Antes esto se resolvía a mano ejecutando

        CREATE EXTENSION IF NOT EXISTS vector;

    directamente contra Postgres antes de correr `migrate` por primera
    vez. Eso funciona una vez que alguien se acuerda de hacerlo, pero
    rompe en cualquier base de datos nueva que no haya pasado por ese
    paso manual: la base de test que crea `manage.py test` desde cero,
    un pipeline de CI, la base de un compañero nuevo en el equipo, un
    entorno de staging, etc. (falla con
    `django.db.utils.ProgrammingError: type "vector" does not exist`).

    Con esta migración, `manage.py migrate` habilita la extensión
    automáticamente como parte del propio proceso de migración, así
    que no hay ningún paso manual que se pueda olvidar. CreateExtension
    usa `CREATE EXTENSION IF NOT EXISTS` internamente, así que es
    seguro correrla también sobre una base de datos que ya la tenga
    habilitada a mano (como las que ya estaban en uso antes de este
    cambio): no falla ni la duplica.

    `run_before` hace que esta migración corra antes de
    modulo_ia.0001_initial sin necesidad de modificar ese archivo, que
    ya está aplicado en las bases de datos existentes.
    """

    run_before = [
        ("modulo_ia", "0001_initial"),
    ]

    operations = [
        CreateExtension("vector"),
    ]
