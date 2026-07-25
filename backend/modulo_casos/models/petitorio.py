from django.db import models
from .caso import Caso


class Petitorio(models.Model):
    """
    Petitorio jurídico formal generado por GPT4All (generar_petitorio_rag).
    Estructura en 3 puntos, basado en delitos identificados y artículos de respaldo.
    """
    descripcion = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "petitorios"
        ordering = ["id"]

    def __str__(self):
        return self.descripcion[:80]


class PetitorioCaso(models.Model):
    """Relación N:M entre Caso y Petitorio."""
    caso      = models.ForeignKey(Caso,      on_delete=models.CASCADE, related_name="petitorios_caso")
    petitorio = models.ForeignKey(Petitorio, on_delete=models.CASCADE, related_name="casos_petitorio")

    class Meta:
        db_table        = "petitorios_casos"
        unique_together = [("caso", "petitorio")]
        indexes         = [
            models.Index(fields=["caso"],      name="idx_petitorios_casos_caso"),
            models.Index(fields=["petitorio"], name="idx_petitorios_casos_pet"),
        ]
