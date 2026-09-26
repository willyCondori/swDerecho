from datetime import timedelta

from django.db import models
from django.utils import timezone
from modulo_usuarios.models.usuario import Usuario
from modulo_clientes.models.cliente import Cliente
from modulo_catalogo.models.rama import RamaDerecho
from modulo_casos.models.etapas import EtapaCaso


class EstadoAnalisis(models.TextChoices):
    """
    Estado persistido del pipeline IA de un caso (chunking → embeddings →
    entidades → ranking → ResultadoCaso). Reemplaza al patrón anterior, que
    corría todo dentro del propio request HTTP: sin este campo, la barra
    de progreso se perdía al recargar la página y no había forma de saber
    si un análisis ya estaba en curso (permitiendo lanzar dos al mismo
    tiempo sobre el mismo caso con un doble clic).
    """
    PENDIENTE   = "pendiente",   "Pendiente"
    PROCESANDO  = "procesando",  "Procesando"
    COMPLETADO  = "completado",  "Completado"
    ERROR       = "error",       "Con error"


class Caso(models.Model):
    """
    Expediente legal principal.
    Puede tener texto redactado (descripcion) o un PDF subido
    (se gestiona en modulo_documentos). Ambas opciones son excluyentes
    pero opcionales individualmente; la validación ocurre en el serializer.
    """
    # Un análisis "procesando" hace más de este tiempo se considera
    # huérfano (el hilo murió sin poder actualizar el estado, ej. por un
    # reinicio del servidor a mitad de análisis) y se permite lanzar uno
    # nuevo en su lugar, en vez de bloquear el caso para siempre.
    ANALISIS_TIMEOUT_MINUTOS = 20

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
    eliminado_con_cliente = models.BooleanField(
                           default=False,
                           help_text=(
                               "True si el caso se envió a la papelera junto con su cliente "
                               "(al restaurar al cliente se restauran solo estos casos)."
                           ),
                       )
    created_at       = models.DateTimeField(auto_now_add=True)

    # --- Estado del análisis IA (async, ver EstadoAnalisis arriba) ---
    estado_analisis        = models.CharField(
                                 max_length=20,
                                 choices=EstadoAnalisis.choices,
                                 default=EstadoAnalisis.PENDIENTE,
                             )
    analisis_paso          = models.CharField(
                                 max_length=40, null=True, blank=True,
                                 help_text="Paso actual del pipeline (chunking, embeddings, "
                                           "entidades, ranking...), solo informativo para la UI.",
                             )
    analisis_iniciado_en   = models.DateTimeField(null=True, blank=True)
    analisis_iniciado_por  = models.ForeignKey(
                                 Usuario,
                                 on_delete=models.SET_NULL,
                                 null=True, blank=True,
                                 related_name="analisis_iniciados",
                                 help_text="Quién disparó la corrida más reciente del análisis.",
                             )
    analisis_completado_en = models.DateTimeField(null=True, blank=True)
    analisis_error         = models.TextField(
                                 null=True, blank=True,
                                 help_text="Mensaje de la última corrida fallida. Se limpia al "
                                           "iniciar una nueva.",
                             )

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
            models.Index(fields=["estado_analisis"], name="idx_casos_estado_analisis"),
        ]

    def __str__(self):
        return f"[{self.codigo}] {self.titulo}"

    def analisis_en_curso(self) -> bool:
        """
        True si hay un análisis corriendo ahora mismo. Un "procesando" que
        lleva más de ANALISIS_TIMEOUT_MINUTOS sin completarse se considera
        huérfano y ya no bloquea un nuevo intento (ver comentario en la
        constante de arriba).
        """
        if self.estado_analisis != EstadoAnalisis.PROCESANDO:
            return False
        if self.analisis_iniciado_en is None:
            return False
        limite = timezone.now() - timedelta(minutes=self.ANALISIS_TIMEOUT_MINUTOS)
        return self.analisis_iniciado_en >= limite
