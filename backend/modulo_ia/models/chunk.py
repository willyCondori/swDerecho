from django.db import models
from modulo_casos.models.caso import Caso


class ChunkCaso(models.Model):
    """
    Fragmento de texto extraído del caso (split por '.').
    Cada chunk se convierte en embedding por separado.
    tipo: 'texto' si vino del campo descripcion,
          'pdf'   si fue extraído de un documento PDF.
    """
    TIPO_CHOICES = [
        ("texto", "Texto redactado"),
        ("pdf",   "Extraído de PDF"),
    ]

    caso       = models.ForeignKey(
                     Caso,
                     on_delete=models.CASCADE,
                     related_name="chunks",
                 )
    contenido  = models.TextField()
    orden      = models.PositiveIntegerField(help_text="Posición del chunk dentro del caso.")
    tipo       = models.CharField(max_length=50, choices=TIPO_CHOICES, default="texto")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chunks_caso"
        ordering = ["caso", "orden"]
        indexes  = [
            models.Index(fields=["caso"],        name="idx_chunks_caso"),
            models.Index(fields=["caso","orden"],name="idx_chunks_orden"),
            models.Index(fields=["tipo"],        name="idx_chunks_tipo"),
        ]

    def __str__(self):
        return f"Chunk {self.orden} — {self.caso.codigo}"
