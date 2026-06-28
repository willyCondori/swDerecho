from django.db import models
from .usuario import Usuario


class PerfilUsuario(models.Model):
    """
    Datos personales del usuario.
    Los campos sensibles (nombres, apellidos, email, telefono, ci)
    se cifran en la capa de servicio con AES-256 (ISO 27001)
    antes de persistirse. Aquí se almacenan como TextField para
    soportar el texto cifrado en base64.
    """
    usuario   = models.OneToOneField(
                    Usuario,
                    on_delete=models.CASCADE,
                    related_name="perfil",
                )
    # --- campos cifrados en reposo ---
    nombres   = models.TextField()           # AES-256
    apellidos = models.TextField()           # AES-256
    email     = models.TextField(unique=True)# AES-256
    telefono  = models.TextField(blank=True, null=True)  # AES-256
    ci        = models.TextField(unique=True)             # AES-256
    # ---------------------------------
    estado    = models.BooleanField(default=True)
    created_at= models.DateTimeField(auto_now_add=True)
    updated_at= models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "perfil_usuarios"
        indexes  = [
            models.Index(fields=["usuario"], name="idx_perfil_usuario"),
            models.Index(fields=["email"],   name="idx_perfil_email"),
            models.Index(fields=["ci"],      name="idx_perfil_ci"),
        ]

    def __str__(self):
        return f"Perfil de {self.usuario}"
