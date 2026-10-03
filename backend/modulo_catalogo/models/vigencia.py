from django.conf import settings
from django.db import models


class CambioNormativo(models.Model):
    """Evidencia de una afectación; nunca confundir detección con confirmación."""
    fuente = models.ForeignKey('DocumentoNorma', on_delete=models.PROTECT, related_name='cambios_detectados')
    norma_afectada = models.ForeignKey('Norma', on_delete=models.PROTECT, null=True, blank=True,
                                       related_name='cambios_recibidos')
    articulo_afectado = models.ForeignKey('Articulo', on_delete=models.PROTECT, null=True, blank=True,
                                          related_name='cambios_recibidos')
    operacion = models.CharField(max_length=20, choices=[(x, x) for x in
        ['abroga', 'deroga', 'modifica', 'incorpora', 'general', 'temporal']])
    estado_revision = models.CharField(max_length=20, default='pendiente', choices=[
        ('pendiente', 'Pendiente'), ('confirmado', 'Confirmado'), ('descartado', 'Descartado')])
    unidad_fuente = models.CharField(max_length=80, blank=True)
    referencia = models.JSONField(default=dict)
    cita = models.TextField()
    origen = models.CharField(max_length=30, default='clausula')
    norma_causante = models.CharField(max_length=200, blank=True)
    fecha_norma_causante = models.DateField(null=True, blank=True)
    fecha_efecto = models.DateField(null=True, blank=True)
    observacion = models.TextField(blank=True)
    huella = models.CharField(max_length=64, unique=True)
    revisado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    revisado_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['estado_revision'], name='idx_cambio_revision')]


class VersionArticulo(models.Model):
    articulo = models.ForeignKey('Articulo', on_delete=models.CASCADE, related_name='versiones')
    documento = models.ForeignKey('DocumentoNorma', on_delete=models.PROTECT, null=True, blank=True)
    titulo = models.CharField(max_length=500, blank=True)
    contenido = models.TextField()
    huella = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['articulo', 'huella'], name='version_articulo_unica')]
        ordering = ['-created_at']


class DocumentoOficial(models.Model):
    """Archivo descargado de la Gaceta, antes de incorporarlo al catálogo."""
    url_fuente = models.URLField(max_length=1000, unique=True)
    url_pdf = models.URLField(max_length=1000)
    identificador = models.CharField(max_length=80)
    titulo = models.CharField(max_length=500)
    tipo = models.CharField(max_length=80, blank=True)
    numero = models.CharField(max_length=50, blank=True)
    fecha_publicacion = models.DateField(null=True, blank=True)
    texto = models.TextField(blank=True)
    ruta_archivo = models.CharField(max_length=1000, blank=True)
    hash_pdf = models.CharField(max_length=64, blank=True)
    penal = models.BooleanField(default=False)
    estado_descarga = models.CharField(max_length=20, default='pendiente')
    error = models.TextField(blank=True)
    ultima_consulta = models.DateTimeField(auto_now=True)
    documento_catalogo = models.ForeignKey('DocumentoNorma', null=True, blank=True,
                                           on_delete=models.SET_NULL, related_name='origenes_oficiales')

    class Meta:
        ordering = ['-fecha_publicacion', '-pk']
