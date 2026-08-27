from django.db import models


class jerarquia(models.Model):
    """
    Modelo para representar la jerarquía normativa de las normas jurídicas.
    Se utiliza para establecer la prioridad de las normas en el sistema.
    """
    nombre = models.CharField(max_length=200, unique=True)
    nivel = models.PositiveIntegerField()
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = "jerarquias"
        ordering = ["nivel"]

    def __str__(self):
        return f"{self.nombre} (nivel {self.nivel})"