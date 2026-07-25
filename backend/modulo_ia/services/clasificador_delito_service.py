import re

# ---------------------------------------------------------------------------
# Clasificación de delitos penales por palabras clave (sin LLM).
#
# Cada grupo agrupa variantes del mismo delito que aparecen en los títulos
# entre paréntesis de los artículos del CP (ej. "(ROBO)" y "(ROBO AGRAVADO)"
# comparten el mismo vocabulario narrativo), y una lista de términos
# coloquiales/legales que suelen aparecer en el relato de hechos de ese
# tipo de caso.
#
# Extensible por rama: si en el futuro se agregan otras normas (Civil,
# Familia, Laboral, etc.), se puede crear un diccionario nuevo en este
# mismo archivo (ej. GRUPOS_CIVIL) y registrarlo en GRUPOS_POR_RAMA,
# sin tocar ranking_service.py.
# ---------------------------------------------------------------------------
GRUPOS_PENAL = {
    "ROBO": {
        "titulos": ["ROBO", "ROBO AGRAVADO"],
        "keywords": [
            "robo", "asalt", "arrebat", "sustra", "apoder", "desposei",
            "cuchillo", "arma", "amenaz", "intimid", "violencia",
            "pertenencias", "billetera", "celular", "despojo", "atracar",
        ],
    },
    "HURTO": {
        "titulos": ["HURTO", "HURTO AGRAVADO", "HURTO DE USO"],
        "keywords": [
            "hurto", "sustra", "apoder", "sin violencia", "descuido",
            "aprovechando", "distracción", "bolsillo", "sin darse cuenta",
        ],
    },
    "HOMICIDIO": {
        "titulos": [
            "ASESINATO", "HOMICIDIO",
            "HOMICIDIO EN RIÑA O A CONSECUENCIA DE AGRESIÓN",
            "HOMICIDIO - SUICIDIO", "PARRICIDIO",
        ],
        "keywords": [
            "murió", "falleció", "muerte", "matar", "homicidio", "asesinato",
            "cadáver", "riña", "pelea", "occiso", "deceso",
        ],
    },
    "LESIONES": {
        "titulos": [
            "LESIONES GRAVES Y GRAVISIMAS", "LESIONES LEVES",
            "HOMICIDIO Y LESIONES GRAVES Y GRAVISIMAS EN ACCIDENTES DE TRANSITO",
        ],
        "keywords": [
            "lesión", "lesiones", "herida", "golpe", "golpeó", "fractura",
            "incapacidad médico legal", "certificado médico", "pómulo",
            "labio", "contusión",
        ],
    },
    "VIOLACION": {
        "titulos": [
            "VIOLACIÓN", "VIOLACION", "ESTUPRO",
            "VIOLACIÓN DE INFANTE, NIÑA, NIÑO O ADOLESCENTE",
        ],
        "keywords": [
            "violación", "acceso carnal", "abuso sexual", "violó",
            "agresión sexual",
        ],
    },
    "SECUESTRO": {
        "titulos": ["SECUESTRO", "TRATA DE PERSONAS"],
        "keywords": [
            "secuestr", "rescate", "retuvo", "privó de libertad",
            "cautiverio", "rehén",
        ],
    },
    "ESTAFA": {
        "titulos": ["ESTAFA", "ESTELIONATO"],
        "keywords": [
            "estafa", "engaño", "defraud", "artificio", "timó",
            "falsa promesa", "fraude",
        ],
    },
    "AMENAZAS": {
        "titulos": ["AMENAZAS", "COACCIÓN"],
        "keywords": [
            "amenaz", "coaccion", "intimidó", "conminó",
        ],
    },
    "TRANSITO": {
        "titulos": [
            "HOMICIDIO Y LESIONES GRAVES Y GRAVISIMAS EN ACCIDENTES DE TRANSITO",
            "OMISIÓN DE SOCORRO",
        ],
        "keywords": [
            "atropell", "conductor", "vehículo", "vehiculo", "tránsito", "transito",
            "alcohol", "estupefaciente", "fuga", "se dio a la fuga", "auxilio",
            "socorro", "accidente",
        ],
},
}

# Mapeo rama -> diccionario de grupos correspondiente. Agregar acá cuando
# se sumen más ramas/normas, ej. GRUPOS_POR_RAMA["Civil"] = GRUPOS_CIVIL.
GRUPOS_POR_RAMA = {
    "Penal": GRUPOS_PENAL,
}

_PATRON_TITULO_ARTICULO = re.compile(r"\(([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-,]+)\)")


class ClasificadorDelitoService:
    """
    Clasifica el texto de un caso contra grupos de delitos por palabras
    clave, y extrae la categoría de un artículo a partir de su título
    entre paréntesis (ej. "(ROBO AGRAVADO)"). No usa IA/LLM: es un
    clasificador de reglas, pensado como paso intermedio hasta integrar
    un modelo real de clasificación.
    """

    @classmethod
    def _grupos_para_rama(cls, nombre_rama: str | None) -> dict:
        return GRUPOS_POR_RAMA.get(nombre_rama, GRUPOS_PENAL)

    @classmethod
    def _titulo_a_grupo(cls, nombre_rama: str | None) -> dict:
        grupos = cls._grupos_para_rama(nombre_rama)
        return {
            titulo: grupo
            for grupo, datos in grupos.items()
            for titulo in datos["titulos"]
        }

    @staticmethod
    def titulo_articulo(articulo) -> str | None:
        """
        Extrae el título entre paréntesis del artículo, ej. de
        'Art. 332°.- (ROBO AGRAVADO). La pena...' devuelve 'ROBO AGRAVADO'.
        """
        match = _PATRON_TITULO_ARTICULO.search(articulo.contenido or "")
        if not match:
            return None
        return match.group(1).strip().upper()

    @classmethod
    def clasificar_texto(cls, texto_caso: str, nombre_rama: str | None = None) -> dict:
        """
        Cuenta coincidencias de palabras clave por grupo de delito en el
        texto del caso, y normaliza contra el grupo con más coincidencias
        para obtener un score relativo 0-1 por grupo.
        """
        grupos = cls._grupos_para_rama(nombre_rama)
        texto = texto_caso.lower()

        conteos = {
            grupo: sum(1 for kw in datos["keywords"] if kw in texto)
            for grupo, datos in grupos.items()
        }
        maximo = max(conteos.values(), default=0)
        if maximo == 0:
            return {}
        return {grupo: cuenta / maximo for grupo, cuenta in conteos.items() if cuenta > 0}

    @classmethod
    def score_delito_articulo(cls, articulo, categorias_caso: dict, nombre_rama: str | None = None) -> float:
        if not categorias_caso:
            return 0.0
        titulo_articulo = cls.titulo_articulo(articulo)
        if not titulo_articulo:
            return 0.0
        titulo_a_grupo = cls._titulo_a_grupo(nombre_rama)
        grupo = titulo_a_grupo.get(titulo_articulo)
        if not grupo:
            return 0.0
        return categorias_caso.get(grupo, 0.0)