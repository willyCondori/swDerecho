# modulo_notificaciones/models/notificacion.py
from django.conf import settings
from django.db import models

from modulo_casos.models.caso import Caso


class TipoNotificacion(models.TextChoices):
    ANALISIS_COMPLETADO = "analisis_completado", "Análisis completado"
    ANALISIS_ERROR       = "analisis_error", "Análisis con error"
    DOCUMENTO_NUEVO      = "documento_nuevo", "Documento nuevo"
    # Sin disparador todavía: hoy un caso no se puede reasignar a otro
    # abogado (Caso.usuario es fijo). El tipo ya queda listo para cuando
    # se implemente esa funcionalidad.
    CASO_REASIGNADO      = "caso_reasignado", "Caso reasignado"


class Notificacion(models.Model):
    """
    Notificación in-app para UN usuario puntual. A diferencia del resto
    del sistema, acá ve_todo() NO aplica: una notificación es personal,
    nadie más la ve — ni un Administrador puede leer la bandeja de otro
    usuario (ver NotificacionViewSet.get_queryset).
    """
    usuario    = models.ForeignKey(
                     settings.AUTH_USER_MODEL,
                     on_delete=models.CASCADE,
                     related_name="notificaciones",
                 )
    tipo       = models.CharField(max_length=30, choices=TipoNotificacion.choices)
    titulo     = models.CharField(max_length=200)
    mensaje    = models.TextField()
    # SET_NULL (no CASCADE): si el caso se llegara a borrar de verdad
    # (hoy solo existe soft-delete vía Caso.estado), la notificación no
    # desaparece del historial del usuario, solo pierde el enlace directo.
    caso       = models.ForeignKey(
                     Caso,
                     on_delete=models.SET_NULL,
                     null=True,
                     blank=True,
                     related_name="notificaciones",
                 )
    leida      = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notificaciones"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["usuario", "leida"], name="idx_notif_usuario_leida"),
        ]

    def __str__(self):
        estado = "leída" if self.leida else "sin leer"
        return f"[{self.tipo}] {self.titulo} → usuario {self.usuario_id} ({estado})"
