from django.db import models


class EntidadJuridica(models.Model):
    """
    Entidades reconocidas en el análisis jurídico:
    menor de edad, funcionario público, mujer, víctima, Estado, etc.
    Se usan para calcular el factor 'Entidades Jurídicas' del ranking.
    """
    nombre      = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    estado      = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    deleted_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "entidades_juridicas"
        ordering = ["nombre"]
        indexes  = [
            models.Index(fields=["estado"], name="idx_entidades_estado"),
        ]

    def __str__(self):
        return self.nombre
