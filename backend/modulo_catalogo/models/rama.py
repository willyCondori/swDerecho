from django.db import models


class RamaDerecho(models.Model):
    nombre      = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    estado      = models.BooleanField(default=True)

    class Meta:
        db_table = "ramas_derecho"
        ordering = ["nombre"]
        indexes  = [
            models.Index(fields=["estado"], name="idx_ramas_estado"),
        ]

    def __str__(self):
        return self.nombre
