import re

from modulo_catalogo.models.articulo import Articulo

# ---------------------------------------------------------------------------
# Figuras jurídicas transversales: no son "tipos de delito" (no tienen
# categoría propia para ClasificadorDelitoService), pero modifican o
# complementan la aplicación de cualquier delito y deberían sugerirse
# junto al artículo principal cuando el relato de hechos las menciona.
#
# Ej: "intento de robo" -> Art. 8 (TENTATIVA), aunque TENTATIVA no
# aparezca en GRUPOS_PENAL porque no es un delito en sí mismo.
#
# Extensible por rama igual que GRUPOS_POR_RAMA en clasificador_delito_service.
# ---------------------------------------------------------------------------
FIGURAS_PENAL = {
    "TENTATIVA": {
        "titulos": ["TENTATIVA", "DESISTIMIENTO"],
        "keywords": [
            "intento", "intentó", "intentaron", "tentativa", "trató de",
            "no logró consumar", "no consumó", "no se consumó",
            "fue frustrado", "frustrad",
        ],
    },
    "LEGITIMA_DEFENSA": {
        "titulos": ["LEGITIMA DEFENSA", "LEGÍTIMA DEFENSA", "CAUSAS DE JUSTIFICACIÓN"],
        "keywords": [
            "defensa personal", "legítima defensa", "legitima defensa",
            "se defendió", "en defensa propia", "para defenderse",
            "repeler la agresión", "acto de defensa",
        ],
    },
    "COMPLICIDAD": {
        "titulos": ["COMPLICIDAD"],
        "keywords": [
            "cómplice", "complice", "ayudó a", "colaboró en", "facilitó",
            "encubrió", "encubrimiento",
        ],
    },
    "AUTORIA_COAUTORIA": {
        "titulos": ["AUTORÍA Y PARTICIPACIÓN", "COAUTORÍA", "AUTORIA MEDIATA"],
        "keywords": [
            "junto con", "en compañía de", "entre varios", "los dos",
            "actuaron conjuntamente",
        ],
    },
    "ATENUANTES": {
        "titulos": ["CIRCUNSTANCIAS ATENUANTES", "ATENUANTES"],
        "keywords": [
            "primera vez", "sin antecedentes", "arrepentido", "se entregó",
            "colaboró con la investigación", "confesó",
        ],
    },
    "AGRAVANTES": {
        "titulos": ["CIRCUNSTANCIAS AGRAVANTES", "AGRAVANTES"],
        "keywords": [
            "con alevosía", "premeditación", "en banda", "varios sujetos",
            "aprovechando la noche", "indefensión de la víctima",
        ],
    },
    "IMPUTABILIDAD": {
        "titulos": ["IMPUTABILIDAD", "INIMPUTABILIDAD"],
        "keywords": [
            "menor de edad", "estado de ebriedad", "bajo efectos de",
            "trastorno mental", "inconsciente",
        ],
    },
}

FIGURAS_POR_RAMA = {
    "Penal": FIGURAS_PENAL,
}

_PATRON_TITULO_ARTICULO = re.compile(r"\(([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-,]+)\)")


class FiguraTransversalService:
    """
    Detecta figuras jurídicas transversales mencionadas en el texto de un
    caso (tentativa, legítima defensa, complicidad, etc.) y devuelve los
    artículos del catálogo que corresponden a esas figuras, para que el
    ranking pueda incluirlos aunque no destaquen por similitud semántica
    ni tengan un score_delito propio (no son "tipos de delito").
    """

    @classmethod
    def _figuras_para_rama(cls, nombre_rama: str | None) -> dict:
        return FIGURAS_POR_RAMA.get(nombre_rama, FIGURAS_PENAL)

    @staticmethod
    def _titulo_articulo(articulo) -> str | None:
        match = _PATRON_TITULO_ARTICULO.search(articulo.contenido or "")
        if not match:
            return None
        return match.group(1).strip().upper()

    @classmethod
    def detectar_figuras(cls, texto_caso: str, nombre_rama: str | None = None) -> set:
        """
        Devuelve el conjunto de nombres de figura (ej. {"TENTATIVA"})
        cuyas keywords aparecen en el texto del caso.
        """
        figuras = cls._figuras_para_rama(nombre_rama)
        texto = (texto_caso or "").lower()
        detectadas = set()
        for nombre_figura, datos in figuras.items():
            if any(kw in texto for kw in datos["keywords"]):
                detectadas.add(nombre_figura)
        return detectadas

    @classmethod
    def articulos_por_figuras(cls, figuras_detectadas: set, rama_id=None, nombre_rama: str | None = None):
        """
        Devuelve los Articulo activos cuyo título (extraído del texto)
        coincide con alguna de las figuras detectadas. Escanea el
        catálogo activo (filtrado por rama si corresponde) porque el
        título vive dentro de `contenido`, no en una columna indexada.
        """
        if not figuras_detectadas:
            return []

        figuras = cls._figuras_para_rama(nombre_rama)
        titulos_buscados = {
            titulo
            for nombre_figura in figuras_detectadas
            for titulo in figuras.get(nombre_figura, {}).get("titulos", [])
        }
        if not titulos_buscados:
            return []

        qs = Articulo.objects.filter(estado=True).select_related("norma", "rama").prefetch_related("entidades")
        if rama_id:
            qs = qs.filter(rama_id=rama_id)

        encontrados = []
        for articulo in qs.only("id", "contenido", "jerarquia_normativa", "frecuencia_historica", "rama", "norma", "estado"):
            titulo_extraido = cls._titulo_articulo(articulo)
            if titulo_extraido in titulos_buscados:
                encontrados.append(articulo)
        return encontrados