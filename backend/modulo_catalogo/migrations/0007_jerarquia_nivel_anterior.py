from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_catalogo", "0006_corregir_niveles_duplicados_jerarquia"),
    ]

    operations = [
        migrations.AddField(
            model_name="jerarquia",
            name="nivel_anterior",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
