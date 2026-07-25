from django.db import models


class Cliente(models.Model):
    """
    Datos personales del cliente atendido.
    Todos los datos personales se almacenan cifrados (AES-256).
    """

    # ----- Campos cifrados -----
    nombres = models.TextField()
    apellidos = models.TextField()
    telefono = models.TextField(blank=True, null=True)
    # ----------------------------

    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "clientes"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["estado"], name="idx_clientes_estado"),
        ]

    def __str__(self):
        return f"Cliente #{self.id}"