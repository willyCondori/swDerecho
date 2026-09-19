from django.db import models

from modulo_casos.models.caso import Caso
from modulo_casos.models.etapas import EtapaCaso
from modulo_usuarios.models.usuario import Usuario


class SeguimientoCaso(models.Model):
    """
    Entrada del historial de seguimiento de un caso.

    Cada cambio de etapa (y cada nota de seguimiento) queda registrado
    acá de forma inmutable, con quién lo hizo y cuándo. La etapa actual
    del caso vive en Caso.etapa; este modelo es la línea de tiempo.
    """
    caso            = models.ForeignKey(
                          Caso,
                          on_delete=models.CASCADE,
                          related_name="seguimientos",
                      )
    etapa           = models.CharField(max_length=40, choices=EtapaCaso.choices)
    etapa_anterior  = models.CharField(
                          max_length=40,
                          choices=EtapaCaso.choices,
                          null=True,
                          blank=True,
                          help_text="Etapa en la que estaba el caso antes de este movimiento. Nula en la entrada inicial.",
                      )
    nota            = models.TextField(blank=True, default="")
    usuario         = models.ForeignKey(
                          Usuario,
                          on_delete=models.PROTECT,
                          related_name="seguimientos_casos",
                      )
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "seguimientos_caso"
        ordering = ["-created_at", "-id"]
        indexes  = [
            models.Index(fields=["caso", "-created_at"], name="idx_seguim_caso_fecha"),
        ]

    def __str__(self):
        return f"[{self.caso_id}] {self.etapa} ({self.created_at:%Y-%m-%d})"
