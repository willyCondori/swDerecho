from django.db import models
from .caso import Caso


class ResultadoCaso(models.Model):
    """
    Resultado del análisis completo generado por GPT4All.
    Se genera una sola vez por caso (OneToOne).
    """
    caso          = models.OneToOneField(
                        Caso,
                        on_delete=models.CASCADE,
                        related_name="resultado",
                    )
    resumen       = models.TextField(blank=True, null=True)
    fortalezas    = models.TextField(blank=True, null=True)
    debilidades   = models.TextField(blank=True, null=True)
    estrategias   = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "resultados_caso"

    def __str__(self):
        return f"Resultado del caso {self.caso.codigo}"
