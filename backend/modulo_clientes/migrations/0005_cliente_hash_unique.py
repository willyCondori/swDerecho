from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Aplicar SOLO después de resolver los duplicados que reportó
    0004_cliente_hash_duplicados (revisar la salida de esa migración).
    Si todavía hay dos clientes con el mismo teléfono o nombre
    completo reales, esta migración va a fallar con un
    UniqueViolation — es la señal de que falta limpiar datos, no un
    bug de la migración.
    """

    dependencies = [
        ("modulo_clientes", "0004_cliente_hash_duplicados"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cliente",
            name="telefono_hash",
            field=models.CharField(max_length=64, null=True, blank=True, unique=True),
        ),
        migrations.AlterField(
            model_name="cliente",
            name="nombre_completo_hash",
            field=models.CharField(max_length=64, null=True, blank=True, unique=True),
        ),
    ]
