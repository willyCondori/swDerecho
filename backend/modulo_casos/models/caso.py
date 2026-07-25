from django.db import models
from modulo_usuarios.models.usuario import Usuario
from modulo_clientes.models.cliente import Cliente
from modulo_catalogo.models.rama import RamaDerecho


class Caso(models.Model):
    """
    Expediente legal principal.
    Puede tener texto redactado (descripcion) o un PDF subido
    (se gestiona en modulo_documentos). Ambas opciones son excluyentes
    pero opcionales individualmente; la validación ocurre en el serializer.
    """
    codigo           = models.CharField(max_length=100, unique=True)
    titulo           = models.CharField(max_length=500)
    descripcion      = models.TextField(
                           blank=True,
                           null=True,
                           help_text="Texto redactado del caso. Vacío si se subió PDF.",
                       )
    usuario          = models.ForeignKey(
                           Usuario,
                           on_delete=models.PROTECT,
                           related_name="casos",
                       )
    cliente          = models.ForeignKey(
                           Cliente,
                           on_delete=models.PROTECT,
                           related_name="casos",
                       )
    rama_detectada   = models.ForeignKey(
                           RamaDerecho,
                           on_delete=models.SET_NULL,
                           null=True,
                           blank=True,
                           related_name="casos",
                           help_text="Rama jurídica detectada por el análisis IA.",
                       )
    estado           = models.BooleanField(default=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "casos"
        ordering = ["-created_at"]
        indexes  = [
            models.Index(fields=["usuario"],    name="idx_casos_usuario"),
            models.Index(fields=["cliente"],    name="idx_casos_cliente"),
            models.Index(fields=["rama_detectada"], name="idx_casos_rama"),
            models.Index(fields=["estado"],     name="idx_casos_estado"),
            models.Index(fields=["codigo"],     name="idx_casos_codigo"),
            models.Index(fields=["-created_at"],name="idx_casos_created"),
        ]

    def __str__(self):
        return f"[{self.codigo}] {self.titulo}"
