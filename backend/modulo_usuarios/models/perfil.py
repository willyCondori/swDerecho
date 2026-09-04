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
    # ---------------------------------
    # HMAC-SHA256 determinístico del email (ver core.encryption
    # .aes_encryption.hash_lookup). No es información sensible en sí
    # misma (no es reversible a texto plano), así que no hace falta
    # cifrarla: sirve para buscar/comparar por email sin descifrar
    # toda la tabla (validación de unicidad, recuperación de
    # contraseña por correo). Se mantiene sincronizada con `email`
    # en PerfilUsuarioWriteSerializer.
    email_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    estado    = models.BooleanField(default=True)
    created_at= models.DateTimeField(auto_now_add=True)
    updated_at= models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "perfil_usuarios"
        indexes  = [
            models.Index(fields=["usuario"],    name="idx_perfil_usuario"),
            models.Index(fields=["email"],      name="idx_perfil_email"),
            models.Index(fields=["email_hash"], name="idx_perfil_email_hash"),
        ]

    def __str__(self):
        return f"Perfil de {self.usuario}"