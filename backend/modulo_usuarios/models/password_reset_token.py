from django.conf import settings
from django.db import models
from django.utils import timezone

from .usuario import Usuario


class PasswordResetToken(models.Model):
    """
    Bitácora de solicitudes de recuperación de contraseña, usada para
    auditoría y para el límite anti-abuso (PASSWORD_RESET_MAX_SOLICITUDES
    por PASSWORD_RESET_VENTANA_MINUTOS) en SolicitarRecuperacionView.

    Nota histórica: el nombre y los campos (token_hash, expira_en,
    usado_en) vienen de un primer diseño basado en enlace de un solo
    uso. El flujo actual no usa enlaces — al pedir la recuperación se
    genera directamente una contraseña temporal nueva y se manda por
    correo (ver core.utils.passwords.generar_password_aleatoria), y
    esa contraseña es la que prueba identidad en ConfirmarRecuperacionView
    (con check_password, como un login). Cada fila que se crea acá
    queda con usado_en=creado_en de una: no hay nada que "confirmar"
    contra este modelo, solo se usa para contar cuántas solicitudes
    hizo un usuario en la ventana de tiempo.
    """

    @staticmethod
    def vigencia_minutos() -> int:
        return getattr(settings, "PASSWORD_RESET_VIGENCIA_MINUTOS", 30)

    usuario      = models.ForeignKey(
                       Usuario,
                       on_delete=models.CASCADE,
                       related_name="tokens_recuperacion",
                   )
    token_hash   = models.CharField(max_length=64, unique=True)
    creado_en    = models.DateTimeField(auto_now_add=True)
    expira_en    = models.DateTimeField()
    usado_en     = models.DateTimeField(null=True, blank=True)
    ip_solicitud = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "password_reset_tokens"
        ordering = ["-creado_en"]
        indexes  = [
            models.Index(fields=["usuario"],    name="idx_pwreset_usuario"),
            models.Index(fields=["token_hash"], name="idx_pwreset_hash"),
        ]

    def __str__(self):
        return f"Token de recuperación para {self.usuario} ({self.creado_en:%Y-%m-%d %H:%M})"

    @property
    def esta_vigente(self) -> bool:
        return self.usado_en is None and timezone.now() < self.expira_en

    def marcar_usado(self):
        self.usado_en = timezone.now()
        self.save(update_fields=["usado_en"])