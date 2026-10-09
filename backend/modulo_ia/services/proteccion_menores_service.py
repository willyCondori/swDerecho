import re

from modulo_catalogo.models.articulo import Articulo
from modulo_ia.services.vigencia_ranking import articulos_disponibles


class ProteccionMenoresService:
    """Recupera derechos complementarios sin inferir delitos por la edad."""

    @staticmethod
    def hay_menores(texto):
        return bool(re.search(r"\b(?:niñ[oa]s?|adolescentes?|menor(?:es)? de edad)\b", texto, re.I))

    @staticmethod
    def articulos():
        return articulos_disponibles(Articulo.objects.filter(
            norma__sigla__iexact="CPE", numero_articulo__in=["60", "61"]
        )).select_related("norma", "norma__jerarquia", "rama").prefetch_related("entidades")

    @staticmethod
    def requiere_hechos_no_mencionados(articulo, texto):
        # Se evalúa el encabezado, no todo el cuerpo: las remisiones pueden
        # mencionar otros delitos que el artículo no regula.
        titulo = (articulo.titulo or "").lower()
        encabezado = articulo.contenido.split(")", 1)[0].lower()
        titulo += " " + encabezado
        reglas = (
            (("estupro", "corrupción", "violación", "sexual"), r"sexual|violaci[oó]n|viol[oó]|estupro|pornograf|tocamiento|manose|abus"),
            (("abandono",), r"abandon|desampar"),
            (("fuga",), r"fug|escap|hu[ií]"),
            (("homicidio", "asesinato"), r"muri[oó]|muert|mat[oó]|matar|asesin|homicid"),
        )
        if any(any(p in titulo for p in palabras) and not re.search(patron, texto, re.I)
               for palabras, patron in reglas):
            return True
        # Esta ley tiene un ámbito sexual digital específico; la sola edad
        # no justifica presentar sus estadísticas o medidas especializadas.
        if str(articulo.norma.numero_norma or "") == "1636":
            return not bool(re.search(r"sexual|pornograf|grooming|sext|abus|violaci[oó]n", texto, re.I))
        return False
