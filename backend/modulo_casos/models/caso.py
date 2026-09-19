from django.db import models
from modulo_usuarios.models.usuario import Usuario
from modulo_clientes.models.cliente import Cliente
from modulo_catalogo.models.rama import RamaDerecho
from modulo_casos.models.etapas import EtapaCaso


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
                           help_text=(
                               "Rama jurídica del caso, seleccionada por el usuario al "
                               "registrarlo (penal, civil, etc.). Nullable a nivel de BD "
                               "solo para sobrevivir a on_delete=SET_NULL si la rama se "
                               "elimina del catálogo más adelante; la creación de casos "
                               "la exige (ver CasoCreateSerializer)."
                           ),
                       )
    etapa            = models.CharField(
                           max_length=40,
                           choices=EtapaCaso.choices,
                           default=EtapaCaso.REGISTRADO,
                           help_text=(
                               "Etapa actual del proceso legal. Solo se modifica a través "
                               "de seguimiento_service.registrar_seguimiento, que deja el "
                               "historial en SeguimientoCaso. No confundir con 'estado' "
                               "(activo/inactivo)."
                           ),
                       )
    etapa_actualizada_at = models.DateTimeField(null=True, blank=True)
    estado           = models.BooleanField(
                           default=True,
                           help_text=(
                               "True = caso activo. False = caso en la papelera "
                               "(soft-delete; se recupera con papelera_service.restaurar_desde_papelera)."
                           ),
                       )
    eliminado_at     = models.DateTimeField(
                           null=True,
                           blank=True,
                           help_text="Cuándo se envió el caso a la papelera. Nulo si está activo.",
                       )
    eliminado_por    = models.ForeignKey(
                           Usuario,
                           on_delete=models.SET_NULL,
                           null=True,
                           blank=True,
                           related_name="casos_eliminados",
                           help_text="Quién envió el caso a la papelera. Nulo si está activo.",
                       )
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "casos"
        ordering = ["-created_at"]
        indexes  = [
            models.Index(fields=["usuario"],    name="idx_casos_usuario"),
            models.Index(fields=["cliente"],    name="idx_casos_cliente"),
            models.Index(fields=["rama_detectada"], name="idx_casos_rama"),
            models.Index(fields=["estado"],     name="idx_casos_estado"),
            models.Index(fields=["etapa"],      name="idx_casos_etapa"),
            models.Index(fields=["codigo"],     name="idx_casos_codigo"),
            models.Index(fields=["-created_at"],name="idx_casos_created"),
        ]

    def __str__(self):
        return f"[{self.codigo}] {self.titulo}"
