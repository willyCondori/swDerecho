import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_usuarios", "0006_perfilusuario_email_hash"),
    ]

    operations = [
        migrations.CreateModel(
            name="PasswordResetToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token_hash", models.CharField(max_length=64, unique=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("expira_en", models.DateTimeField()),
                ("usado_en", models.DateTimeField(blank=True, null=True)),
                ("ip_solicitud", models.GenericIPAddressField(blank=True, null=True)),
                ("usuario", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="tokens_recuperacion",
                    to="modulo_usuarios.usuario",
                )),
            ],
            options={
                "db_table": "password_reset_tokens",
                "ordering": ["-creado_en"],
            },
        ),
        migrations.AddIndex(
            model_name="passwordresettoken",
            index=models.Index(fields=["usuario"], name="idx_pwreset_usuario"),
        ),
        migrations.AddIndex(
            model_name="passwordresettoken",
            index=models.Index(fields=["token_hash"], name="idx_pwreset_hash"),
        ),
    ]
