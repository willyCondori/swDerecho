from django.db import models
from modulo_usuarios.models.usuario import Usuario


class Auditoria(models.Model):
    """
    Registro inmutable de acciones de usuario sobre cualquier tabla.
    Se genera automáticamente desde el middleware AuditoriaMiddleware
    o manualmente en los servicios críticos.

    accion: CREATE | READ | UPDATE | DELETE | LOGIN | LOGOUT | EXPORT
    metadata: JSON con valores anteriores/nuevos u otros datos de contexto.
    """
    ACCION_CHOICES = [
        ("CREATE",  "Creación"),
        ("READ",    "Lectura"),
        ("UPDATE",  "Actualización"),
        ("DELETE",  "Eliminación"),
        ("LOGIN",   "Inicio de sesión"),
        ("LOGOUT",  "Cierre de sesión"),
        ("EXPORT",  "Exportación"),
        ("ANALYZE", "Análisis IA"),
    ]

    usuario     = models.ForeignKey(
                      Usuario,
                      on_delete=models.PROTECT,
                      related_name="auditoria",
                      null=True,
                      blank=True,
                  )
    tabla       = models.CharField(max_length=100)
    accion      = models.CharField(max_length=50, choices=ACCION_CHOICES)
    registro_id = models.BigIntegerField(null=True, blank=True,
                      help_text="ID del registro afectado.")
    ip          = models.CharField(max_length=100, blank=True, null=True)
    metadata    = models.JSONField(
                      default=dict,
                      blank=True,
                      help_text="Contexto adicional: valores anteriores, payload, etc.",
                  )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "auditoria"
        ordering = ["-created_at"]
        indexes  = [
            models.Index(fields=["usuario"],              name="idx_auditoria_usuario"),
            models.Index(fields=["tabla"],                name="idx_auditoria_tabla"),
            models.Index(fields=["accion"],               name="idx_auditoria_accion"),
            models.Index(fields=["-created_at"],          name="idx_auditoria_created"),
            models.Index(fields=["tabla","registro_id"],  name="idx_auditoria_registro"),
        ]

    def __str__(self):
        return f"[{self.accion}] {self.tabla}#{self.registro_id} — {self.created_at:%Y-%m-%d %H:%M}"
