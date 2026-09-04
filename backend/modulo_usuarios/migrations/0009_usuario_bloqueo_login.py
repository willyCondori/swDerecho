from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_usuarios", "0008_perfilusuario_email_hash_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="intentos_fallidos",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="usuario",
            name="bloqueado_hasta",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]