from django.db import models


class Cliente(models.Model):
    """
    Datos personales del cliente atendido.
    nombres y apellidos se cifran en reposo (AES-256 / ISO 27001).
    fecha_nacimiento también es dato sensible → cifrado como TextField.
    """
    # --- campos cifrados en reposo ---
    nombres          = models.TextField()           # AES-256
    apellidos        = models.TextField()           # AES-256
    fecha_nacimiento = models.TextField(blank=True, null=True)  # AES-256
    # ---------------------------------
    estado     = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "clientes"
        ordering = ["id"]
        indexes  = [
            models.Index(fields=["estado"], name="idx_clientes_estado"),
        ]

    def __str__(self):
        return f"Cliente #{self.id}"
