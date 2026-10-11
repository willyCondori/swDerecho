from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("modulo_usuarios", "0010_identificadores_publicos")]
    operations = [migrations.RunSQL(
        sql='''CREATE TABLE security_throttle_cache (
            cache_key varchar(255) PRIMARY KEY,
            value text NOT NULL,
            expires timestamp with time zone NOT NULL
        );
        CREATE INDEX security_throttle_cache_expires ON security_throttle_cache (expires);''',
        reverse_sql='DROP TABLE security_throttle_cache;',
    )]
