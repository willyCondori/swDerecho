from django.db import models
from .jerarquia import jerarquia

class Norma(models.Model):
    nombre = models.CharField(max_length=200)
    sigla  = models.CharField(max_length=50, blank=True, null=True)
    jerarquia = models.ForeignKey(
        jerarquia,
        on_delete=models.PROTECT,
        related_name="normas",
        null=True,
        blank=True,
    )

    estado = models.BooleanField(default=True)

    class Meta:
        db_table = "normas"
        ordering = ["nombre"]
        indexes  = [
            models.Index(fields=["estado"], name="idx_normas_estado"),
            models.Index(fields=["sigla"],  name="idx_normas_sigla"),
            models.Index(fields=["jerarquia"], name="idx_normas_jerarquia"),
        ]

    def __str__(self):
        return f"{self.sigla} — {self.nombre}" if self.sigla else self.nombre
