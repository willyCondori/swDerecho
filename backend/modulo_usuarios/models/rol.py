from django.db import models

class Rol(models.Model):
    nombre      = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    estado      = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    deleted_at  = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table  = "roles"
        ordering  = ["nombre"]
        indexes   = [
            models.Index(fields=["estado"], name="idx_roles_estado"),
        ]

    def __str__(self):
        return self.nombre
