from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_usuarios", "0004_seed_usuario_inicial"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="debe_cambiar_password",
            field=models.BooleanField(default=False),
        ),
    ]