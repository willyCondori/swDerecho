from django.db import models


class Norma(models.Model):
    nombre = models.CharField(max_length=200)
    sigla  = models.CharField(max_length=50, blank=True, null=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = "normas"
        ordering = ["nombre"]
        indexes  = [
            models.Index(fields=["estado"], name="idx_normas_estado"),
            models.Index(fields=["sigla"],  name="idx_normas_sigla"),
        ]

    def __str__(self):
        return f"{self.sigla} — {self.nombre}" if self.sigla else self.nombre
