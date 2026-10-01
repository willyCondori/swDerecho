import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_catalogo", "0007_jerarquia_nivel_anterior"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentoNorma",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre_original", models.CharField(max_length=500)),
                ("ruta_archivo", models.CharField(max_length=1000)),
                ("tamano", models.BigIntegerField(help_text="Tamaño en bytes.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("norma", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documentos", to="modulo_catalogo.norma")),
                ("rama", models.ForeignKey(blank=True, help_text="Rama de derecho con la que se cargó este PDF.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="documentos_norma", to="modulo_catalogo.ramaderecho")),
                ("subido_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="documentos_norma_subidos", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "documentos_norma",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="documentonorma",
            index=models.Index(fields=["norma"], name="idx_docs_norma_norma"),
        ),
        migrations.AddIndex(
            model_name="documentonorma",
            index=models.Index(fields=["-created_at"], name="idx_docs_norma_created"),
        ),
    ]
