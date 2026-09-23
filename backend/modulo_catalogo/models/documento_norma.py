from django.conf import settings
from django.db import models

from .norma import Norma
from .rama import RamaDerecho


class DocumentoNorma(models.Model):
    """
    PDF fuente que se subió para extraer los artículos de una Norma
    (CargaArticulosView). Antes ese archivo se guardaba en
    MEDIA_ROOT/documentos_normativas/... sin quedar registrado en ningún
    lado; este modelo lo deja consultable, descargable y eliminable desde
    Catálogo → Normas, igual que ya pasa con los documentos de un caso.

    Una misma Norma puede tener varios documentos (p. ej. se cargó en más
    de una tanda, o se volvió a subir tras una corrección).
    ruta_archivo almacena la ruta relativa dentro de MEDIA_ROOT.
    """
    norma           = models.ForeignKey(
                          Norma,
                          on_delete=models.CASCADE,
                          related_name="documentos",
                      )
    rama            = models.ForeignKey(
                          RamaDerecho,
                          on_delete=models.SET_NULL,
                          related_name="documentos_norma",
                          null=True,
                          blank=True,
                          help_text="Rama de derecho con la que se cargó este PDF.",
                      )
    nombre_original = models.CharField(max_length=500)
    ruta_archivo    = models.CharField(max_length=1000)
    tamano          = models.BigIntegerField(help_text="Tamaño en bytes.")
    subido_por      = models.ForeignKey(
                          settings.AUTH_USER_MODEL,
                          on_delete=models.SET_NULL,
                          related_name="documentos_norma_subidos",
                          null=True,
                          blank=True,
                      )
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documentos_norma"
        ordering = ["-created_at"]
        indexes  = [
            models.Index(fields=["norma"],        name="idx_docs_norma_norma"),
            models.Index(fields=["-created_at"],  name="idx_docs_norma_created"),
        ]

    def __str__(self):
        return f"{self.nombre_original} ({self.norma.nombre})"
