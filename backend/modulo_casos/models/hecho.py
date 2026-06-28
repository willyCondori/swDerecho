from django.db import models
from .caso import Caso


class Hecho(models.Model):
    """
    Hecho jurídico generado por GPT4All (resumir_chunk).
    Se redacta en tercera persona, breve y sin interpretación legal.
    """
    descripcion = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hechos"
        ordering = ["id"]

    def __str__(self):
        return self.descripcion[:80]


class HechoCaso(models.Model):
    """Relación N:M entre Caso y Hecho (mantiene el orden de inserción)."""
    caso   = models.ForeignKey(Caso,  on_delete=models.CASCADE, related_name="hechos_caso")
    hecho  = models.ForeignKey(Hecho, on_delete=models.CASCADE, related_name="casos_hecho")
    orden  = models.PositiveIntegerField(default=0, help_text="Orden del hecho dentro del caso.")

    class Meta:
        db_table        = "hechos_casos"
        ordering        = ["orden"]
        unique_together = [("caso", "hecho")]
        indexes         = [
            models.Index(fields=["caso"],  name="idx_hechos_casos_caso"),
            models.Index(fields=["hecho"], name="idx_hechos_casos_hecho"),
        ]
