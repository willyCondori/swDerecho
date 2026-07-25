from django.db import models
from modulo_casos.models.caso import Caso


class TipoDoc(models.Model):
    """Catálogo de tipos de documento: caso subido, plantilla, generado, etc."""
    tipo = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "tipo_doc"

    def __str__(self):
        return self.tipo


class DocumentoCaso(models.Model):
    """
    Archivo subido por el usuario asociado a un caso.
    Puede ser el PDF del caso, documentos de respaldo, etc.
    ruta_archivo almacena la ruta relativa dentro de MEDIA_ROOT.
    """
    caso            = models.ForeignKey(
                          Caso,
                          on_delete=models.CASCADE,
                          related_name="documentos",
                      )
    nombre_original = models.CharField(max_length=500)
    ruta_archivo    = models.CharField(max_length=1000)
    tipo_archivo    = models.CharField(max_length=50, help_text="pdf, docx, jpg, etc.")
    tamano          = models.BigIntegerField(help_text="Tamaño en bytes.")
    tipo_documento  = models.ForeignKey(
                          TipoDoc,
                          on_delete=models.PROTECT,
                          related_name="documentos_caso",
                      )
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documentos_caso"
        ordering = ["-created_at"]
        indexes  = [
            models.Index(fields=["caso"],           name="idx_docs_caso"),
            models.Index(fields=["tipo_documento"], name="idx_docs_tipo"),
            models.Index(fields=["-created_at"],    name="idx_docs_created"),
        ]

    def __str__(self):
        return f"{self.nombre_original} ({self.caso.codigo})"


class PlantillaDocumento(models.Model):
    """
    Plantilla .docx base cargada por el administrador.
    docxtpl usa esta plantilla para generar el documento final
    heredando estilos, fuentes y estructura.
    """
    nombre          = models.CharField(max_length=300)
    descripcion     = models.TextField(blank=True, null=True)
    ruta_archivo    = models.CharField(
                          max_length=255,
                          help_text="Ruta relativa en MEDIA_ROOT/plantillas/",
                      )
    tipo_documento  = models.ForeignKey(
                          TipoDoc,
                          on_delete=models.PROTECT,
                          related_name="plantillas",
                      )

    class Meta:
        db_table = "plantillas_documento"
        ordering = ["nombre"]
        indexes  = [
            models.Index(fields=["tipo_documento"], name="idx_plantillas_tipo"),
        ]

    def __str__(self):
        return self.nombre


class DocumentoGenerado(models.Model):
    """
    Documento .docx generado automáticamente por docxtpl
    a partir del análisis IA y la plantilla seleccionada.
    hash_archivo permite verificar integridad (SHA-256).
    """
    caso         = models.ForeignKey(
                       Caso,
                       on_delete=models.CASCADE,
                       related_name="documentos_generados",
                   )
    plantilla    = models.ForeignKey(
                       PlantillaDocumento,
                       on_delete=models.PROTECT,
                       related_name="documentos_generados",
                   )
    ruta_archivo = models.CharField(max_length=255)
    hash_archivo = models.CharField(
                       max_length=255,
                       blank=True,
                       null=True,
                       help_text="SHA-256 del archivo para verificar integridad.",
                   )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documentos_generados"
        ordering = ["-created_at"]
        indexes  = [
            models.Index(fields=["caso"],      name="idx_docs_gen_caso"),
            models.Index(fields=["plantilla"], name="idx_docs_gen_plantilla"),
            models.Index(fields=["hash_archivo"], name="idx_docs_gen_hash"),
        ]

    def __str__(self):
        return f"Doc generado — {self.caso.codigo} — {self.created_at:%Y-%m-%d}"
