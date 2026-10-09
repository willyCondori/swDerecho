import re


class ContextoArticuloService:
    """Comprueba el objeto especializado de un artículo candidato."""

    @staticmethod
    def compatible(articulo, texto):
        titulo = (articulo.titulo or "").lower()
        encabezado = re.match(r"[^()]*\(([^)]+)\)", articulo.contenido or "")
        if encabezado:
            titulo += " " + encabezado.group(1).lower()
        if "minerales" in titulo:
            return bool(re.search(
                r"\b(?:mineral(?:es)?|miner[ií]a|minera?s?|yacimientos?|"
                r"mena|concentrados?|estaño|zinc|wolfram|litio|cobre|plata|oro)\b",
                texto, re.I,
            ))
        return True
