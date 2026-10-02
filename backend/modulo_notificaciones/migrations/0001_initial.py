import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("modulo_casos", "0008_backfill_estado_analisis"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Notificacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(
                    choices=[
                        ("analisis_completado", "Análisis completado"),
                        ("analisis_error", "Análisis con error"),
                        ("documento_nuevo", "Documento nuevo"),
                        ("caso_reasignado", "Caso reasignado"),
                    ],
                    max_length=30,
                )),
                ("titulo", models.CharField(max_length=200)),
                ("mensaje", models.TextField()),
                ("leida", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("caso", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="notificaciones",
                    to="modulo_casos.caso",
                )),
                ("usuario", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="notificaciones",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "db_table": "notificaciones",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="notificacion",
            index=models.Index(fields=["usuario", "leida"], name="idx_notif_usuario_leida"),
        ),
    ]
