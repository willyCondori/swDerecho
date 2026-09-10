from django.db import models


class jerarquia(models.Model):
    """
    Modelo para representar la jerarquía normativa de las normas jurídicas.
    Se utiliza para establecer la prioridad de las normas en el sistema.
    """
    nombre = models.CharField(max_length=200, unique=True)
    nivel = models.PositiveIntegerField()
    # Guarda el nivel que tenía la jerarquía justo antes del último cambio
    # (ya sea una edición manual o un corrimiento en cascada provocado por
    # crear/editar/eliminar/reactivar otra jerarquía). Permite ofrecer la
    # opción de "volver al nivel anterior" y también preserva el nivel
    # original de una jerarquía eliminada para poder reactivarla en el
    # lugar correcto de la escala.
    nivel_anterior = models.PositiveIntegerField(null=True, blank=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = "jerarquias"
        ordering = ["nivel"]

    def __str__(self):
        return f"{self.nombre} (nivel {self.nivel})"