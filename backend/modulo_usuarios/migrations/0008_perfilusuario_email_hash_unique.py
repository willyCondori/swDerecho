from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Aplicar SOLO después de resolver los duplicados que reportó
    0006_perfilusuario_email_hash (correr primero:
    `python manage.py verificar_emails_duplicados` para confirmar que
    ya no queda ninguno). Si todavía hay dos perfiles con el mismo
    email real, esta migración va a fallar con el mismo
    UniqueViolation que falló antes — es la señal de que falta
    limpiar datos, no un bug de la migración.
    """

    dependencies = [
        ("modulo_usuarios", "0007_passwordresettoken"),
    ]

    operations = [
        migrations.AlterField(
            model_name="perfilusuario",
            name="email_hash",
            field=models.CharField(max_length=64, null=True, blank=True, unique=True),
        ),
    ]
