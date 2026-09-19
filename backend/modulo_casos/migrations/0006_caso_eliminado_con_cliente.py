from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_casos", "0005_papelera_casos"),
    ]

    operations = [
        migrations.AddField(
            model_name="caso",
            name="eliminado_con_cliente",
            field=models.BooleanField(default=False, help_text="True si el caso se envió a la papelera junto con su cliente (al restaurar al cliente se restauran solo estos casos)."),
        ),
    ]
