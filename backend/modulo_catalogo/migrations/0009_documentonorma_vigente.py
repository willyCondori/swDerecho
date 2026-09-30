from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_catalogo", "0008_documento_norma"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentonorma",
            name="vigente",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "False cuando una carga posterior con sobrescribir=True "
                    "reemplazó este PDF. Se conserva como historial "
                    "(trazabilidad, ley penal más benigna); no se borra."
                ),
            ),
        ),
    ]
