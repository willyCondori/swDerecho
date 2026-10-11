from django.conf import settings
from django.db import models


class ValoracionArticulo(models.Model):
    caso = models.ForeignKey("modulo_casos.Caso", on_delete=models.CASCADE)
    articulo = models.ForeignKey("modulo_catalogo.Articulo", on_delete=models.PROTECT)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    valor = models.CharField(max_length=12, choices=[("util", "Útil"), ("no_util", "No útil"), ("sin_valorar", "Sin valorar")])
    contexto_hash = models.CharField(max_length=64)
    modelo_version = models.CharField(max_length=100, blank=True)
    muestra = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["caso", "usuario"], name="idx_valoracion_caso_usuario"),
            models.Index(fields=["caso", "articulo", "-id"], name="idx_valoracion_caso_articulo"),
        ]


class ValoracionJurisprudencia(models.Model):
    caso = models.ForeignKey("modulo_casos.Caso", on_delete=models.CASCADE)
    resolucion = models.ForeignKey("modulo_ia.ResolucionJurisprudencia", on_delete=models.PROTECT)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    valor = models.CharField(max_length=12, choices=[("util", "Útil"), ("no_util", "No útil"), ("sin_valorar", "Sin valorar")])
    contexto_hash = models.CharField(max_length=64)
    modelo_version = models.CharField(max_length=100, blank=True)
    muestra = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        indexes = [models.Index(fields=["caso", "resolucion", "-id"], name="idx_val_juris_caso_resolucion")]
