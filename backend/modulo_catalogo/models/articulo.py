from django.db import models
from .norma import Norma
from .rama import RamaDerecho
from .entidad import EntidadJuridica


class Articulo(models.Model):

    numero_articulo      = models.CharField(max_length=50)
    titulo               = models.CharField(max_length=500, blank=True, null=True)
    contenido            = models.TextField()
    norma                = models.ForeignKey(
                               Norma,
                               on_delete=models.PROTECT,
                               related_name="articulos",
                           )
    rama                 = models.ForeignKey(
                               RamaDerecho,
                               on_delete=models.PROTECT,
                               related_name="articulos",
                           )
    frecuencia_historica = models.IntegerField(
                               default=0,
                               help_text="Veces seleccionado en casos anteriores",
                           )
    entidades            = models.ManyToManyField(
                               EntidadJuridica,
                               through="ArticuloEntidad",
                               related_name="articulos",
                               blank=True,
                           )
    estado               = models.BooleanField(default=True)
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "articulos"
        ordering = ["norma", "numero_articulo"]
        indexes  = [
            models.Index(fields=["norma"],               name="idx_articulos_norma"),
            models.Index(fields=["rama"],                name="idx_articulos_rama"),
            models.Index(fields=["estado"],              name="idx_articulos_estado"),
            models.Index(fields=["-frecuencia_historica"],name="idx_articulos_frecuencia"),
            models.Index(fields=["numero_articulo"],     name="idx_articulos_numero"),
        ]

    def __str__(self):
        return f"Art. {self.numero_articulo} — {self.titulo or '(sin título)'}"


class ArticuloEntidad(models.Model):
    """Tabla intermedia artículo ↔ entidad jurídica."""
    articulo = models.ForeignKey(Articulo,       on_delete=models.CASCADE)
    entidad  = models.ForeignKey(EntidadJuridica, on_delete=models.CASCADE)

    class Meta:
        db_table        = "articulo_entidades"
        unique_together = [("articulo", "entidad")]
        indexes         = [
            models.Index(fields=["articulo"], name="idx_art_entidades_art"),
            models.Index(fields=["entidad"],  name="idx_art_entidades_entid"),
        ]
