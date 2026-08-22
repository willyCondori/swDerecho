from django.db import models
from modulo_casos.models.caso import Caso
from modulo_catalogo.models.articulo import Articulo


class ResultadoArticulo(models.Model):
    """
    Ranking jurídico final de un artículo para un caso específico.

    Fórmula de puntuación:
        score_total = 0.60 × score_semantico
                    + 0.15 × score_delito
                    + 0.10 × score_entidades
                    + 0.10 × score_jerarquia
                    + 0.05 × score_frecuencia

    posicion: lugar en el ranking (1 = más relevante).
    Al seleccionarse, se incrementa articulo.frecuencia_historica.
    """
    caso             = models.ForeignKey(
                           Caso,
                           on_delete=models.CASCADE,
                           related_name="resultado_articulos",
                       )
    articulo         = models.ForeignKey(
                           Articulo,
                           on_delete=models.PROTECT,
                           related_name="resultados",
                       )
    score_total      = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    score_semantico  = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    score_delito     = models.DecimalField(
                           max_digits=10, decimal_places=6, default=0,
                           help_text="Coincidencia de delito/derecho identificado.",
                       )
    score_entidades  = models.DecimalField(
                           max_digits=10, decimal_places=6, default=0,
                           help_text="Coincidencia de entidades jurídicas.",
                       )
    score_jerarquia  = models.DecimalField(
                           max_digits=10, decimal_places=6, default=0,
                           help_text="Jerarquía normativa del artículo.",
                       )
    score_frecuencia = models.DecimalField(
                           max_digits=10, decimal_places=6, default=0,
                           help_text="Frecuencia histórica normalizada.",
                       )
    posicion         = models.PositiveIntegerField(help_text="Posición en el ranking.")
    es_sugerencia    = models.BooleanField(
                           default=False,
                           help_text=(
                               "True si el artículo se incluyó como sugerencia "
                               "complementaria (ej. figura transversal como "
                               "tentativa, legítima defensa) en vez de haber "
                               "superado el umbral principal de relevancia por "
                               "mérito propio."
                           ),
                       )

    class Meta:
        db_table        = "resultado_articulos"
        ordering        = ["caso", "posicion"]
        unique_together = [("caso", "articulo")]
        indexes         = [
            models.Index(fields=["caso"],               name="idx_resultado_caso"),
            models.Index(fields=["articulo"],           name="idx_resultado_articulo"),
            models.Index(fields=["caso", "-score_total"],name="idx_resultado_score"),
            models.Index(fields=["caso", "posicion"],   name="idx_resultado_posicion"),
        ]

    def __str__(self):
        return (
            f"Caso {self.caso.codigo} — {self.articulo.numero_articulo} "
            f"(pos={self.posicion}, score={self.score_total})"
        )