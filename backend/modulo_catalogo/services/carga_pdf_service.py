# modulo_catalogo/services/carga_pdf_service.py
"""
Servicio de carga masiva de artículos desde PDF.

Flujo:
    PDF
      ↓
    Extraer texto (página por página; se quitan encabezados y pies repetidos)
      ↓
    Limpiar texto (URLs, headers InfoLeyes, timestamps)
      ↓
    Dividir por artículos
      ↓
    Extraer título → "Art. {numero} - {TEXTO ENTRE PARÉNTESIS}"
      ↓
    Limpiar encabezados de capítulo/sección colgantes al final del artículo
      ↓
    Guardar Articulo
      ↓
    Generar embedding (título + cuerpo, sin el prefijo "Art. N°.- (TITULO)." repetido)
      ↓
    Guardar EmbeddingArticulo 1:1

Características:
    - Los patrones de detección de artículos son GENÉRICOS (no dependen de
      un "tipo de norma" fijo): cubren todas las formas de numeración que
      se usan en la legislación boliviana (Código Civil, Penal, Laboral,
      CPE, CPP, y en general cualquier código/ley/decreto nuevo que se
      cargue), así que cargar una norma nueva (ej. Código de Procedimiento
      Penal) no requiere tocar este archivo.
    - El título se CONSTRUYE (no se extrae tal cual) como "Art. {numero} - {paréntesis}".
      Si el artículo no trae paréntesis, el título queda como "Art. {numero}".
    - Quita los encabezados y pies de página que se repiten en las páginas del
      PDF (ej. "Caja de herramientas para la atención de la violencia en
      servicios de salud 8"), ignorando el número de página; si no, quedan
      pegados en medio del artículo que cruza el salto de página.
    - Quita títulos de capítulo/sección/título que quedan pegados al final del
      artículo por cómo el PDF concatena texto sin saltos de línea reales
      (ej. "...del anatocismo. DELITOS CONTRA EL DERECHO DE AUTOR" → se corta
      antes de "DELITOS CONTRA...").
    - Genera embeddings usando el modelo configurado en
      settings.SENTENCE_TRANSFORMER_MODEL, cargado una sola vez por carga.
    - El texto usado para el embedding es distinto del texto guardado como
      "contenido": incluye el título y quita el prefijo redundante
      "Art. N°.- (TITULO)." para no duplicar información en el vector.
    - Normaliza los embeddings y verifica que tengan la dimensión esperada.
    - Evita duplicados por (norma, rama, numero_articulo).
    - Permite sobrescribir artículos de una norma/rama.
    - Reporta progreso mediante Celery.
"""

import math
import re
import logging
from dataclasses import dataclass, field

from django.conf import settings
from django.db import transaction


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuración de embeddings — módulo único, compartido con embedding_service.py
# y regenerar_embeddings_articulos.py (ver modulo_ia/services/model_loader.py).
# ---------------------------------------------------------------------------

from modulo_ia.services.model_loader import DIMENSION_VECTOR, obtener_modelo as _obtener_modelo, version_activa  # noqa: E402


# ---------------------------------------------------------------------------
# Resultado de carga
# ---------------------------------------------------------------------------

@dataclass
class ResultadoCarga:
    norma_nombre: str
    rama_nombre: str
    jerarquia_nombre: str = None

    total_encontrados: int = 0
    guardados: int = 0
    duplicados: int = 0
    errores: int = 0

    errores_detalle: list = field(default_factory=list)

    def resumen(self) -> dict:
        return {
            "norma": self.norma_nombre,
            "rama": self.rama_nombre,
            "jerarquia": self.jerarquia_nombre,
            "total_encontrados": self.total_encontrados,
            "guardados": self.guardados,
            "duplicados": self.duplicados,
            "errores": self.errores,
            "errores_detalle": self.errores_detalle[:20],
        }


# ---------------------------------------------------------------------------
# Extracción de texto del PDF
# ---------------------------------------------------------------------------

# Cuántas líneas del borde de cada página se consideran candidatas a ser
# encabezado o pie de página, y en qué fracción de las páginas tiene que
# repetirse una línea (ignorando los números) para tratarla como tal.
LINEAS_BORDE_PAGINA = 3
MIN_PAGINAS_REPETICION = 3
FRACCION_PAGINAS_REPETICION = 0.3
MAX_LARGO_LINEA_BORDE = 160

_PATRON_LINEA_ARTICULO = re.compile(r"^\s*(?:art[íi]culo|art\.)\s*\d", re.IGNORECASE)


def _clave_linea_borde(linea: str) -> str:
    """
    Clave para comparar líneas de encabezado/pie entre páginas: minúsculas,
    espacios colapsados y cualquier número reemplazado por '#', para que
    "…servicios de salud 8" y "…servicios de salud 9" sean la misma línea.
    """
    clave = re.sub(r"\d+", "#", linea.lower())
    return re.sub(r"\s+", " ", clave).strip()


def _indices_borde(lineas: list[str]) -> list[int]:
    """Índices de las primeras y últimas líneas NO vacías de una página."""
    no_vacias = [i for i, linea in enumerate(lineas) if linea.strip()]
    if len(no_vacias) <= 2 * LINEAS_BORDE_PAGINA:
        return no_vacias
    return no_vacias[:LINEAS_BORDE_PAGINA] + no_vacias[-LINEAS_BORDE_PAGINA:]


def _es_linea_borde_candidata(linea: str, clave: str) -> bool:
    if len(linea.strip()) > MAX_LARGO_LINEA_BORDE:
        return False
    # Nunca tocar el inicio de un artículo, aunque se repita.
    if _PATRON_LINEA_ARTICULO.match(linea):
        return False
    # Exige texto real: un número de página suelto lo maneja la limpieza por línea.
    return len(re.sub(r"[^a-záéíóúñü]", "", clave)) >= 3


def quitar_encabezados_y_pies(paginas: list[str]) -> list[str]:
    """
    Quita los encabezados y pies de página que se repiten en las páginas del
    PDF (ej. "Caja de herramientas para la atención de la violencia en
    servicios de salud 8"). Si no se quitan, terminan pegados en medio del
    artículo que cruza el salto de página y contaminan su contenido y su
    embedding.

    Solo mira las primeras y últimas líneas de cada página y solo quita una
    línea si, ignorando los números, aparece en el borde de al menos el 30 %
    de las páginas (mínimo 3). Así una línea legítima que aparece una vez no
    se toca.
    """
    if len(paginas) < MIN_PAGINAS_REPETICION:
        return paginas

    paginas_lineas = [pagina.split("\n") for pagina in paginas]

    conteo: dict[str, int] = {}
    for lineas in paginas_lineas:
        claves_pagina = set()
        for i in _indices_borde(lineas):
            clave = _clave_linea_borde(lineas[i])
            if _es_linea_borde_candidata(lineas[i], clave):
                claves_pagina.add(clave)
        for clave in claves_pagina:
            conteo[clave] = conteo.get(clave, 0) + 1

    minimo = max(MIN_PAGINAS_REPETICION, math.ceil(len(paginas) * FRACCION_PAGINAS_REPETICION))
    repetidas = {clave for clave, veces in conteo.items() if veces >= minimo}
    if not repetidas:
        return paginas

    limpias = []
    quitadas = 0
    for lineas in paginas_lineas:
        a_quitar = {
            i for i in _indices_borde(lineas)
            if _clave_linea_borde(lineas[i]) in repetidas
            and _es_linea_borde_candidata(lineas[i], _clave_linea_borde(lineas[i]))
        }
        quitadas += len(a_quitar)
        limpias.append("\n".join(l for i, l in enumerate(lineas) if i not in a_quitar))

    logger.info(
        "Encabezados/pies de página repetidos quitados: %d línea(s), %d patrón(es) distintos",
        quitadas, len(repetidas),
    )
    return limpias


def _texto_desde_reader(reader) -> str:
    paginas = []
    for page in reader.pages:
        texto = page.extract_text()
        if texto:
            paginas.append(texto)
    return "\n".join(quitar_encabezados_y_pies(paginas))


def extraer_texto_pdf(ruta: str) -> str:
    """Extrae texto de todas las páginas de un PDF (desde archivo en disco)."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("Instala pypdf: pip install pypdf --break-system-packages")

    return _texto_desde_reader(PdfReader(ruta))


def extraer_texto_pdf_bytes(contenido: bytes) -> str:
    """Extrae texto directamente desde bytes (archivo en memoria)."""
    import io

    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("Instala pypdf: pip install pypdf --break-system-packages")

    return _texto_desde_reader(PdfReader(io.BytesIO(contenido)))


# ---------------------------------------------------------------------------
# Limpieza de texto general
# ---------------------------------------------------------------------------

def limpiar_texto(texto: str) -> str:
    """Elimina URLs, headers/footers y metadata de InfoLeyes."""
    texto = re.sub(r"http[s]?://[^\s\]]+(?:\[[^\]]+\])?", "", texto)

    texto = re.sub(
        r"CODIGO\s+(?:CIVIL|PENAL|LABORAL|DE TRABAJO)"
        r"\s*-\s*Código\s+\w+\s*-\s*Bolivia\s*-\s*InfoLeyes[^\n]*",
        "", texto, flags=re.IGNORECASE,
    )

    texto = re.sub(
        r"Constitución\s+Política\s+del\s+Estado\s+\(CPE\)"
        r"\s*-\s*Bolivia\s*-\s*InfoLeyes[^\n]*",
        "", texto, flags=re.IGNORECASE,
    )

    texto = re.sub(r"Legislación\s+online[^\n]*", "", texto, flags=re.IGNORECASE)

    texto = re.sub(
        r"\[\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M\]", "", texto,
    )

    return texto


# ---------------------------------------------------------------------------
# Patrones de detección de artículos (genéricos, no atados a una norma)
# ---------------------------------------------------------------------------

PATRONES_ARTICULO = [
    r"ARTÍCULO\s+(\d+)\.",
    r"ARTÍCULO\s+(\d+)-",
    r"ARTÍCULO\.\s+(\d+)\s*º",
    r"ARTÍCULO\s+(\d+)\s*º",
    r"ARTICULO\s+(\d+)\.",
    r"ARTICULO\s+(\d+)-",
    r"ARTICULO\s+(\d+)º",
    r"ARTICULO\s+(\d+)°",
    r"ARTICULO\s+(\d+)°\.-",
    r"ARTICULO\s+(\d+)º\.-",
    r"ARTICULO\s+(\d+)\s",
    r"Artículo\s+(\d+)\.",
    r"Artículo\.\s+(\d+)\.",
    r"Artículo\s+(\d+)\s",
    r"Articulo\s+(\d+)\.",
    r"Art\.\s+(\d+)°\.-",
    r"Art\.\s+(\d+)º\.-",
    r"Art\.\s+(\d+)°\s*\.-",
    r"Art\.\s+(\d+)\.-",
    r"Art\.\s*(\d+)º",
    r"ART\.\s+(\d+)°\.-",
]


# Palabras en minúscula que, justo antes de "ARTÍCULO N", indican que es una
# referencia dentro de una oración ("...según el ARTÍCULO 5.") y no el inicio
# de un artículo.
_CONECTORES_REFERENCIA = {
    "el", "del", "al", "lo", "los", "las", "este", "ese", "dicho", "dicha",
    "presente", "citado", "mencionado", "según", "conforme", "en", "por",
    "con", "de", "a", "y", "e", "o", "u",
}


def _es_mayuscula(texto: str) -> bool:
    letras = re.sub(r"[^A-Za-zÁÉÍÓÚÑáéíóúñ]", "", texto)
    return bool(letras) and letras == letras.upper()


def _es_inicio_valido(texto: str, pos: int, es_mayuscula: bool = False) -> bool:
    """
    Filtra referencias en medio de una oración ("...conforme al Artículo 5.").

    Un "Artículo N" precedido por una letra minúscula se considera referencia.
    Excepción: si el patrón está escrito TODO EN MAYÚSCULAS ("ARTÍCULO 6."),
    lo normal es que sea un encabezado; en texto corrido sin saltos de línea
    puede venir justo después de un título sin punto ("Capítulo II Derechos de
    las mujeres ARTÍCULO 6.") y descartarlo haría perder el artículo entero.
    Solo se descarta si la palabra anterior es un conector de referencia
    ("el", "del", "según"...).
    """
    anterior = texto[:pos]
    i = len(anterior)
    while i > 0 and anterior[i - 1] in " \t":
        i -= 1
    sin_espacios_horizontales = anterior[:i]

    if not sin_espacios_horizontales:
        return True
    if sin_espacios_horizontales[-1] == "\n":
        return True

    anterior_strip = sin_espacios_horizontales.rstrip()
    if not anterior_strip:
        return True
    ultimo = anterior_strip[-1]
    if ultimo.isalpha() and ultimo.islower():
        if not es_mayuscula:
            return False
        palabra = re.search(r"([^\W\d_]+)$", anterior_strip)
        return not (palabra and palabra.group(1).lower() in _CONECTORES_REFERENCIA)
    return True


def _es_referencia_en_oracion(texto: str, coincidencia) -> bool:
    """
    "Artículo 5 de la presente Ley..." al inicio de una oración no es un
    encabezado: en los patrones que terminan en espacio (sin punto ni guion
    tras el número), un encabezado real continúa con mayúscula o "(" y una
    referencia continúa con minúscula ("de", "y", "del"...).
    """
    if not coincidencia.group(0)[-1].isspace():
        return False
    siguiente = texto[coincidencia.end():coincidencia.end() + 1]
    return siguiente.isalpha() and siguiente.islower()


# ---------------------------------------------------------------------------
# Jerarquía normativa
# ---------------------------------------------------------------------------
#
# Antes el nivel se adivinaba a partir de una "fuente" fija (CPE=1,
# Civil/Penal/Laboral=2), lo que era incorrecto en general (un Decreto
# Supremo, una Ley Orgánica o una Ordenanza Municipal no son "nivel 2") y
# además obligaba a extender ese dict cada vez que se quería cargar una
# norma distinta. Ahora el nivel de jerarquía es un campo que el usuario
# elige explícitamente en el formulario de carga (rama, tipo de norma /
# jerarquía, nombre del documento), y se asigna directamente a la Norma.

def _asegurar_jerarquia_norma(norma, jerarquia_id=None):
    """
    Si la norma aún no tiene jerarquía asignada y se indicó una
    `jerarquia_id` en la carga, se la asigna.

    No sobrescribe una jerarquía ya configurada manualmente en la Norma
    (por ejemplo, desde la pantalla de administración de normas), para no
    pisar una corrección manual previa.
    """
    if norma.jerarquia_id:
        return
    if not jerarquia_id:
        return

    from modulo_catalogo.models.jerarquia import jerarquia as Jerarquia

    try:
        jerarquia_obj = Jerarquia.objects.get(pk=jerarquia_id, estado=True)
    except Jerarquia.DoesNotExist:
        logger.warning(
            "jerarquia_id=%s no existe o está inactiva; la norma '%s' "
            "queda sin jerarquía hasta que se configure manualmente.",
            jerarquia_id, norma,
        )
        return

    norma.jerarquia = jerarquia_obj
    norma.save(update_fields=["jerarquia"])


# ---------------------------------------------------------------------------
# Título del artículo: "Art. {numero} - {TEXTO ENTRE PARÉNTESIS}"
# ---------------------------------------------------------------------------

PATRON_PARENTESIS = re.compile(r"\(\s*([^()]+?)\s*\)")


def extraer_titulo_articulo(numero: int, contenido: str) -> str:
    """
    Construye el título como "Art. {numero} - {TEXTO ENTRE PARÉNTESIS}".

    Ejemplo:
        numero=361, contenido="Art. 361°.- (USURA AGRAVADA). La sanción..."
        → "Art. 361 - USURA AGRAVADA"

    Busca el paréntesis solo cerca del inicio del artículo (primeros ~200
    caracteres) para no capturar por error un paréntesis que aparezca más
    adelante en el cuerpo (una cita, un inciso, etc.)

    Si el artículo no trae paréntesis al inicio (pasa seguido en Civil,
    Laboral y CPE), el título queda solo como "Art. {numero}".
    """
    base = f"Art. {numero}"

    if not contenido:
        return base

    inicio = contenido.strip()[:200]
    match = PATRON_PARENTESIS.search(inicio)

    if not match:
        return base

    texto_parentesis = re.sub(r"\s+", " ", match.group(1).strip())
    if not texto_parentesis:
        return base

    return f"{base} - {texto_parentesis}"


# ---------------------------------------------------------------------------
# Prefijo crudo al inicio del artículo (para armar el texto de embedding
# sin duplicar "Art. N°.- (TITULO)." que ya está representado en `titulo`)
# ---------------------------------------------------------------------------

PATRON_PREFIJO_ARTICULO = re.compile(
    r"^\s*(?:Art(?:[íi]culo)?\.?\s*\d+\s*[°º]?\s*\.?-?\s*)"
    r"(?:\([^()]*\)\s*\.?\s*)?",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Limpieza del contenido del artículo — por línea (cuando el PDF sí trae \n)
# ---------------------------------------------------------------------------

def _es_encabezado_seccion(ls: str) -> bool:
    """
    Detecta una línea completa que es título de capítulo/sección
    (no cuerpo del artículo): sin dígitos, toda en mayúsculas.
    Sin límite de palabras — títulos de capítulo pueden ser largos
    (ej. "FUNCIONES DE CONTROL, DE DEFENSA DE LA SOCIEDAD Y DE DEFENSA
    DEL ESTADO" en la CPE, 13 palabras). Lo que los distingue del cuerpo
    del artículo no es el largo, sino que NO tienen minúsculas ni dígitos
    en toda la línea — algo prácticamente inexistente en el texto de un
    artículo real.
    """
    if not ls or len(ls) > 110:
        return False
    letras = re.sub(r"[^A-ZÁÉÍÓÚÑ]", "", ls.upper())
    if len(letras) < 4:
        return False
    es_mayuscula_total = ls == ls.upper()
    sin_digitos = not re.search(r"\d", ls)
    return es_mayuscula_total and sin_digitos


def _limpiar_contenido_articulo(contenido: str) -> str:
    """Elimina encabezados de sección línea por línea (cuando hay \\n reales)."""
    lineas = contenido.split("\n")
    lineas_limpias = []

    for linea in lineas:
        ls = linea.strip()
        if not ls:
            continue

        es_encabezado = False

        if re.match(
            r"^(?:CAP[ÍI]TULO|TITULO|T[ÍI]TULO|SECCI[ÓO]N|PARTE)\s+[IVX\d]+\s*$",
            ls, re.IGNORECASE,
        ):
            es_encabezado = True
        elif _es_encabezado_seccion(ls):
            es_encabezado = True

        # Una línea que es solo un número (sin nada más) es casi siempre un
        # número de página u otro artefacto de la extracción del PDF, sin
        # importar de qué norma se trate — antes esto solo se aplicaba a
        # "Laboral", pero el mismo ruido aparece en cualquier PDF.
        if re.match(r"^\d+$", ls):
            es_encabezado = True

        if not es_encabezado:
            lineas_limpias.append(linea)

    resultado = "\n".join(lineas_limpias)
    resultado = re.sub(r" +", " ", resultado)
    resultado = re.sub(r"\n{3,}", "\n\n", resultado)
    return resultado.strip()


# ---------------------------------------------------------------------------
# Limpieza de encabezado colgante al FINAL del artículo (texto corrido,
# sin \n real) — es el filtro que faltaba y resuelve el caso
# "...del anatocismo. DELITOS CONTRA EL DERECHO DE AUTOR"
# ---------------------------------------------------------------------------

PATRON_COLA_ENCABEZADO = re.compile(
    r"\.\s+((?:(?:CAP[ÍI]TULO|T[ÍI]TULO|SECCI[ÓO]N|PARTE)\s+[IVXLCDM\d]+\s*)?"
    r"[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s,\-]{2,300})$"
)
# Encabezados largos: p. ej. un TÍTULO y un CAPÍTULO seguidos, cada uno con
# su nombre, pueden sumar más de 100 caracteres.
MAX_PALABRAS_ENCABEZADO_MAYUSCULAS = 40

# Encabezado con mayúsculas y minúsculas ("Capítulo II Derechos de las
# mujeres"): empieza con la palabra de la división y su número (romano,
# arábigo u ordinal), y NO lleva punto: una oración sí.
_ORDINALES_DIVISION = (
    r"ÚNICO|UNICO|PRIMER[OA]?|SEGUND[OA]|TERCER[OA]?|CUART[OA]|QUINT[OA]|SEXT[OA]|"
    r"S[ÉE]PTIM[OA]|OCTAV[OA]|NOVEN[OA]|D[ÉE]CIM[OA]"
)
PATRON_COLA_ENCABEZADO_MIXTO = re.compile(
    r"\.\s+((?:CAP[ÍI]TULO|T[ÍI]TULO|SECCI[ÓO]N|PARTE|LIBRO)\s+"
    r"(?:(?-i:[IVXLCDM]+)|\d+|" + _ORDINALES_DIVISION + r")\b[^.]*)$",
    re.IGNORECASE,
)
MAX_LARGO_ENCABEZADO_MIXTO = 200
MAX_PALABRAS_ENCABEZADO_MIXTO = 30


def _quitar_encabezado_colgante_una_vez(contenido: str) -> str:
    match = PATRON_COLA_ENCABEZADO.search(contenido)
    if match:
        cola = match.group(1)
        tiene_minuscula_o_digito = re.search(r"[a-záéíóúñ0-9]", cola)
        if not tiene_minuscula_o_digito and len(cola.split()) <= MAX_PALABRAS_ENCABEZADO_MAYUSCULAS:
            # el punto que quedó suelto antes del título se conserva,
            # es el punto final legítimo del artículo.
            return contenido[: match.start(1)].rstrip()

    match = PATRON_COLA_ENCABEZADO_MIXTO.search(contenido)
    if match:
        cola = match.group(1)
        if (
            len(cola) <= MAX_LARGO_ENCABEZADO_MIXTO
            and len(cola.split()) <= MAX_PALABRAS_ENCABEZADO_MIXTO
        ):
            return contenido[: match.start(1)].rstrip()

    return contenido


def _quitar_encabezado_colgante(contenido: str) -> str:
    """
    Quita títulos de capítulo/sección/título que hayan quedado pegados al
    final del artículo por cómo el PDF concatena texto sin saltos de línea
    reales entre el cierre de un artículo y el encabezado del siguiente
    capítulo.

    Ejemplos:
        "...formas del anatocismo. DELITOS CONTRA EL DERECHO DE AUTOR"
        → "...formas del anatocismo."
        "...las mujeres. Capítulo II Derechos de las mujeres"
        → "...las mujeres."

    Solo corta si el tramo final, después del último punto, es un encabezado:
    todo en mayúsculas y sin dígitos (aunque sean varios seguidos, como
    "TÍTULO II ... CAPÍTULO I ..."), o que empieza con "Capítulo/Título/
    Sección/Parte/Libro" + número y no tiene punto (una oración sí lo tiene).
    Se repite mientras siga habiendo encabezados apilados al final.
    """
    contenido = contenido.rstrip()
    for _ in range(3):
        siguiente = _quitar_encabezado_colgante_una_vez(contenido)
        if siguiente == contenido:
            break
        contenido = siguiente
    return contenido


# ---------------------------------------------------------------------------
# Texto para el embedding: título + cuerpo, sin el prefijo redundante
# ---------------------------------------------------------------------------

def construir_texto_embedding(titulo: str, contenido: str) -> str:
    """
    Arma el texto que se vectoriza: título primero (más peso semántico
    para búsquedas por tema), seguido del cuerpo del artículo SIN el
    prefijo "Art. N°.- (TITULO)." que ya está representado en `titulo`
    y solo agregaría ruido/redundancia al embedding.
    """
    cuerpo = PATRON_PREFIJO_ARTICULO.sub("", contenido, count=1).strip()
    partes = [p for p in (titulo, cuerpo) if p]
    return "\n".join(partes)


# ---------------------------------------------------------------------------
# División por artículos
# ---------------------------------------------------------------------------

def dividir_por_articulos(texto: str) -> list[dict]:
    """
    Divide el texto en artículos.

    Devuelve:
        [
            {"numero": 361, "titulo": "Art. 361 - USURA AGRAVADA", "texto": "..."},
            ...
        ]

    Usa la lista genérica PATRONES_ARTICULO — funciona para cualquier norma
    (Civil, Penal, Laboral, CPE, CPP, o una nueva), no depende de que el
    usuario elija un "tipo de norma" predefinido.
    """
    texto = limpiar_texto(texto)

    todos_matches = []
    for patron in PATRONES_ARTICULO:
        matches = list(re.finditer(patron, texto, re.MULTILINE))
        # Filtra referencias en medio de una oración (ver _es_inicio_valido
        # y _es_referencia_en_oracion)
        matches = [
            m for m in matches
            if _es_inicio_valido(texto, m.start(), _es_mayuscula(m.group(0)))
            and not _es_referencia_en_oracion(texto, m)
        ]
        todos_matches.extend(matches)

    todos_matches.sort(key=lambda m: m.start())

    # Deduplicar coincidencias producidas por distintos patrones
    matches_unicos = []
    ultima_pos = -100
    ultimo_num = -1
    for match in todos_matches:
        num = int(match.group(1))
        pos = match.start()
        if num == ultimo_num and pos - ultima_pos < 50:
            continue
        matches_unicos.append(match)
        ultima_pos = pos
        ultimo_num = num

    if not matches_unicos:
        logger.warning("No se encontraron artículos en el PDF (ningún patrón hizo match).")
        return []

    articulos = []
    numeros_vistos = set()

    for i, match in enumerate(matches_unicos):
        numero = int(match.group(1))
        if numero in numeros_vistos:
            continue
        numeros_vistos.add(numero)

        inicio = match.start()
        fin = matches_unicos[i + 1].start() if i + 1 < len(matches_unicos) else len(texto)

        contenido = texto[inicio:fin].strip()
        contenido = _limpiar_contenido_articulo(contenido)
        contenido = _quitar_encabezado_colgante(contenido)

        if len(contenido) < 20:
            continue

        titulo = extraer_titulo_articulo(numero, contenido)

        articulos.append({"numero": numero, "titulo": titulo, "texto": contenido})

    return articulos


# ---------------------------------------------------------------------------
# Carga principal
# ---------------------------------------------------------------------------

def cargar_articulos_desde_bytes(
    contenido_pdf: bytes,
    norma_id: int,
    rama_id: int,
    jerarquia_id: int = None,
    task=None,
    sobrescribir: bool = False,
) -> ResultadoCarga:
   
    from modulo_catalogo.models.norma import Norma
    from modulo_catalogo.models.rama import RamaDerecho
    from modulo_catalogo.models.articulo import Articulo
    from modulo_ia.models.embedding import EmbeddingArticulo
    from modulo_catalogo.services.articulo_entidad_service import ArticuloEntidadService

    try:
        norma = Norma.objects.get(pk=norma_id, estado=True)
        rama = RamaDerecho.objects.get(pk=rama_id, estado=True)
    except Norma.DoesNotExist:
        raise ValueError(f"No existe la norma con ID {norma_id}.")
    except RamaDerecho.DoesNotExist:
        raise ValueError(f"No existe la rama con ID {rama_id}.")

    _asegurar_jerarquia_norma(norma, jerarquia_id)

    resultado = ResultadoCarga(
        norma_nombre=norma.nombre,
        rama_nombre=rama.nombre,
        jerarquia_nombre=norma.jerarquia.nombre if norma.jerarquia_id else None,
    )

    _update_task(task, 5, "Extrayendo texto del PDF...")
    try:
        texto = extraer_texto_pdf_bytes(contenido_pdf)
    except Exception as e:
        raise RuntimeError(f"No se pudo extraer el texto del PDF: {e}")

    _update_task(task, 15, "Dividiendo en artículos...")
    lista_articulos = dividir_por_articulos(texto)
    resultado.total_encontrados = len(lista_articulos)

    if not lista_articulos:
        logger.warning("PDF no produjo artículos. norma=%s", norma)
        return resultado

    _update_task(task, 18, "Cargando modelo de embeddings...")
    modelo = _obtener_modelo()
    catalogo_entidades = ArticuloEntidadService.obtener_catalogo()

    total = len(lista_articulos)

    # ------------------------------------------------------------------
    # Todo lo que escribe en la base de datos (borrado por "sobrescribir",
    # creación de artículos, embeddings y vínculos con entidades) queda
    # dentro de una única transacción atómica. Si algo revienta a mitad
    # de la carga con una excepción NO controlada (ej. se cae la conexión
    # a la BD, un bug inesperado, el proceso se interrumpe de forma
    # anómala), Django revierte TODO lo hecho en esta llamada — no deja
    # la norma con artículos a medias. Los errores "esperables" de un
    # artículo puntual (texto muy corto, embedding con dimensión
    # incorrecta, fallo al vincular entidades) se siguen capturando por
    # artículo dentro del try/except correspondiente y NO disparan un
    # rollback: ese artículo se cuenta como error y se sigue con el
    # resto, que es el comportamiento que ya se quería mantener.
    # ------------------------------------------------------------------
    with transaction.atomic():
        if sobrescribir:
            Articulo.objects.filter(norma=norma, rama=rama).delete()
            logger.info("Artículos previos eliminados. norma=%s rama=%s", norma, rama)

        for idx, art_dict in enumerate(lista_articulos, start=1):
            numero = art_dict["numero"]
            titulo = art_dict["titulo"]
            texto_articulo = art_dict["texto"]

            if idx % 10 == 0 or idx == total:
                pct = int(18 + (idx / total) * 80)
                _update_task(task, pct, f"Procesando artículo {idx}/{total}...")

            if Articulo.objects.filter(
                norma=norma, rama=rama, numero_articulo=str(numero)
            ).exists():
                resultado.duplicados += 1
                continue

            if not texto_articulo or len(texto_articulo.strip()) < 20:
                resultado.errores += 1
                resultado.errores_detalle.append(f"Art. {numero}: texto muy corto")
                continue

            try:
                # savepoint por artículo: si el guardado del artículo en
                # sí falla, solo se descarta ese savepoint (no toda la
                # transacción), y se sigue con el resto del documento.
                with transaction.atomic():
                    articulo = Articulo.objects.create(
                        numero_articulo=str(numero),
                        titulo=titulo,
                        contenido=texto_articulo,
                        norma=norma,
                        rama=rama,
                        frecuencia_historica=0,
                        estado=True,
                    )
            except Exception as e:
                resultado.errores += 1
                resultado.errores_detalle.append(f"Art. {numero}: error al guardar — {e}")
                logger.error("Error guardando Art.%s: %s", numero, e)
                continue

            try:
                texto_embed = construir_texto_embedding(titulo, texto_articulo)
                vector = modelo.encode(texto_embed, normalize_embeddings=True).tolist()

                if len(vector) != DIMENSION_VECTOR:
                    raise ValueError(
                        f"El embedding del Art. {numero} tiene {len(vector)} "
                        f"dimensiones; se esperaban {DIMENSION_VECTOR}."
                    )

                EmbeddingArticulo.objects.update_or_create(
                    articulo=articulo,
                    modelo_version=version_activa(),
                    defaults={"vector": vector},
                )
            except Exception as e:
                resultado.errores_detalle.append(f"Art. {numero}: error en embedding — {e}")
                logger.error("Error generando embedding Art.%s: %s", numero, e, exc_info=True)
                # El artículo ya está guardado; se informa el problema pero no se
                # cuenta dos veces como error total del artículo.

            try:
                ArticuloEntidadService.vincular(articulo, catalogo=catalogo_entidades)
            except Exception as e:
                resultado.errores_detalle.append(f"Art. {numero}: error vinculando entidades — {e}")
                logger.error("Error vinculando entidades Art.%s: %s", numero, e, exc_info=True)
                # Igual que el embedding: no bloquea el artículo ya guardado.

            resultado.guardados += 1

    _update_task(task, 100, "Carga completada.")
    logger.info(
        "Carga finalizada. Norma=%s Guardados=%s Duplicados=%s Errores=%s",
        norma, resultado.guardados, resultado.duplicados, resultado.errores,
    )
    return resultado


# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------

def _update_task(task, progreso: int, paso: str):
    """Actualiza el estado de Celery si existe. Nunca rompe la carga."""
    if task is None:
        return
    try:
        task.update_state(state="STARTED", meta={"progreso": progreso, "paso": paso})
    except Exception:
        pass