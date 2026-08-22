# modulo_catalogo/services/carga_pdf_service.py
"""
Servicio de carga masiva de artículos desde PDF.

Flujo:
    PDF
      ↓
    Extraer texto
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
    - Soporta Civil, Penal, Laboral y CPE.
    - El título se CONSTRUYE (no se extrae tal cual) como "Art. {numero} - {paréntesis}".
      Si el artículo no trae paréntesis, el título queda como "Art. {numero}".
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

import re
import logging
from dataclasses import dataclass, field

from django.conf import settings


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuración de embeddings
# ---------------------------------------------------------------------------

DIMENSION_VECTOR = 768   # Ajustar si EmbeddingArticulo.vector usa otra dimensión


# ---------------------------------------------------------------------------
# Modelo SentenceTransformer (cache global, se carga una sola vez)
# ---------------------------------------------------------------------------

_modelo_cache = None


def _obtener_modelo():
    """Carga el modelo SentenceTransformer una sola vez por proceso."""
    global _modelo_cache

    if _modelo_cache is None:
        from sentence_transformers import SentenceTransformer

        logger.info(
            "Cargando modelo de embeddings: %s",
            settings.SENTENCE_TRANSFORMER_MODEL,
        )

        _modelo_cache = SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL)

    return _modelo_cache


# ---------------------------------------------------------------------------
# Resultado de carga
# ---------------------------------------------------------------------------

@dataclass
class ResultadoCarga:
    fuente: str
    norma_nombre: str
    rama_nombre: str

    total_encontrados: int = 0
    guardados: int = 0
    duplicados: int = 0
    errores: int = 0

    errores_detalle: list = field(default_factory=list)

    def resumen(self) -> dict:
        return {
            "fuente": self.fuente,
            "norma": self.norma_nombre,
            "rama": self.rama_nombre,
            "total_encontrados": self.total_encontrados,
            "guardados": self.guardados,
            "duplicados": self.duplicados,
            "errores": self.errores,
            "errores_detalle": self.errores_detalle[:20],
        }


# ---------------------------------------------------------------------------
# Extracción de texto del PDF
# ---------------------------------------------------------------------------

def extraer_texto_pdf(ruta: str) -> str:
    """Extrae texto de todas las páginas de un PDF (desde archivo en disco)."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("Instala pypdf: pip install pypdf --break-system-packages")

    reader = PdfReader(ruta)
    partes = []
    for page in reader.pages:
        texto = page.extract_text()
        if texto:
            partes.append(texto)
    return "\n".join(partes)


def extraer_texto_pdf_bytes(contenido: bytes) -> str:
    """Extrae texto directamente desde bytes (archivo en memoria)."""
    import io

    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("Instala pypdf: pip install pypdf --break-system-packages")

    reader = PdfReader(io.BytesIO(contenido))
    partes = []
    for page in reader.pages:
        texto = page.extract_text()
        if texto:
            partes.append(texto)
    return "\n".join(partes)


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
# Patrones por fuente
# ---------------------------------------------------------------------------

PATRONES_POR_FUENTE = {
    "Civil": [
        r"ARTÍCULO\s+(\d+)\.",
        r"ARTÍCULO\s+(\d+)-",
        r"ARTICULO\s+(\d+)\.",
        r"ARTICULO\s+(\d+)-",
    ],
    "Penal": [
        r"Art\.\s+(\d+)°\.-",
        r"Art\.\s+(\d+)º\.-",
        r"Art\.\s+(\d+)°\s*\.-",
        r"ART\.\s+(\d+)°\.-",
        r"Art\.\s+(\d+)\.-",
        r"ARTICULO\s+(\d+)°\.-",
        r"ARTICULO\s+(\d+)º\.-",
    ],
    "Laboral": [
        r"ARTICULO\s+(\d+)º",
        r"ARTICULO\s+(\d+)°",
        r"ARTICULO\s+(\d+)\.",
        r"ARTICULO\s+(\d+)\s",
        r"ARTÍCULO\.\s+(\d+)\s*º",
        r"ARTÍCULO\s+(\d+)\s*º",
        r"Art\.\s*(\d+)º",
    ],
    "CPE": [
        r"Artículo\s+(\d+)\.",
        r"Artículo\.\s+(\d+)\.",
        r"Artículo\s+(\d+)\s",
        r"Articulo\s+(\d+)\.",
    ],
}

# IMPORTANTE — cómo se detecta un encabezado de artículo:
#
# Los patrones YA NO anclan a inicio de línea (?:^|\n). Algunos PDFs
# extraídos con pypdf conservan saltos de línea reales entre elementos
# (títulos, capítulos, artículos); otros — sobre todo si el PDF viene de
# un visor/navegador o de una exportación distinta — devuelven el texto
# como un bloque corrido sin \n. Anclar a \n rompe la detección por
# completo en ese segundo caso (0 matches), así que se sacó el anclaje.
#
# Para no confundir una referencia DENTRO de una oración (ej. "...conforme
# al Artículo 5 de esta Constitución...") con el INICIO real de un
# artículo nuevo, cada coincidencia se valida con _es_inicio_valido():
# solo se acepta si el carácter no-espacio inmediatamente anterior NO es
# una letra minúscula (es decir: inicio de texto, un punto, dos puntos, o
# una palabra en MAYÚSCULAS de un título de capítulo/sección).
#
# Si tu PDF sí conserva \n reales, esto sigue funcionando igual (el
# carácter antes de un \n normalmente es un punto o mayúscula de todos
# modos). Si notás falsos positivos o artículos que igual se pierden,
# mandame ese tramo puntual del texto crudo (con repr(), para ver los \n
# reales) y se ajusta la validación.


def _es_inicio_valido(texto: str, pos: int) -> bool:
    """
    True si el match de un encabezado de artículo en `pos` es el INICIO
    real de un artículo nuevo, y no una referencia dentro del cuerpo de
    otro artículo (ej. "...conforme al Artículo 5 de esta Constitución...").

    Reglas, en orden:
      1. Si el carácter no-espacio-horizontal inmediatamente anterior es
         un salto de línea real (\\n) -> VÁLIDO. El encabezado empieza en
         su propia línea, que es como vienen casi siempre los "Art. N" /
         "Artículo N" en el PDF real, con o sin línea en blanco antes
         (la CPE separa artículos con un solo \\n; el Código Penal usa
         línea en blanco — ambos casos quedan cubiertos acá).
      2. Si no hay \\n real inmediato (texto corrido, sin saltos de línea
         — puede pasar según cómo se haya extraído/pegado el texto), se
         mira el último carácter no-espacio antes de `pos`:
           - Si es una letra minúscula -> casi seguro es una referencia
             en medio de una oración -> INVÁLIDO.
           - Si es inicio de texto, un punto, dos puntos, o una letra
             mayúscula (título de capítulo en mayúsculas) -> VÁLIDO.
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
        return False
    return True


# ---------------------------------------------------------------------------
# Jerarquía normativa
# ---------------------------------------------------------------------------

JERARQUIA_POR_FUENTE = {
    "CPE": 1.0,
    "Civil": 0.8,
    "Penal": 0.8,
    "Laboral": 0.8,
}


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


def _limpiar_contenido_articulo(contenido: str, fuente: str) -> str:
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

        if fuente == "Laboral" and re.match(r"^\d+$", ls):
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
    r"[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s,\-]{2,90})$"
)


def _quitar_encabezado_colgante(contenido: str) -> str:
    """
    Quita un título de capítulo/sección/título que haya quedado pegado al
    final del artículo por cómo el PDF concatena texto sin saltos de línea
    reales entre el cierre de un artículo y el encabezado del siguiente
    capítulo.

    Ejemplo:
        "...formas del anatocismo. DELITOS CONTRA EL DERECHO DE AUTOR"
        → "...formas del anatocismo."

    Solo corta si el tramo final, después del último punto, no tiene
    minúsculas ni dígitos y es razonablemente corto (heurística de
    "esto es un título, no una oración").
    """
    contenido = contenido.rstrip()
    match = PATRON_COLA_ENCABEZADO.search(contenido)

    if not match:
        return contenido

    cola = match.group(1)

    tiene_minuscula_o_digito = re.search(r"[a-záéíóúñ0-9]", cola)
    palabras = cola.split()

    if not tiene_minuscula_o_digito and len(palabras) <= 12:
        contenido = contenido[: match.start(1)].rstrip()
        # el punto que quedó suelto antes del título se conserva,
        # es el punto final legítimo del artículo.

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

def dividir_por_articulos(texto: str, fuente: str) -> list[dict]:
    """
    Divide el texto en artículos.

    Devuelve:
        [
            {"numero": 361, "titulo": "Art. 361 - USURA AGRAVADA", "texto": "..."},
            ...
        ]
    """
    texto = limpiar_texto(texto)
    patrones = PATRONES_POR_FUENTE.get(fuente, PATRONES_POR_FUENTE["Civil"])

    todos_matches = []
    for patron in patrones:
        matches = list(re.finditer(patron, texto, re.MULTILINE))
        # Filtra referencias en medio de una oración (ver _es_inicio_valido)
        matches = [m for m in matches if _es_inicio_valido(texto, m.start())]
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
        logger.warning("No se encontraron artículos en el PDF para fuente=%s", fuente)
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
        contenido = _limpiar_contenido_articulo(contenido, fuente)
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
    fuente: str,
    norma_id: int,
    rama_id: int,
    task=None,
    sobrescribir: bool = False,
) -> ResultadoCarga:
    """
    Procesa un PDF en memoria y guarda los artículos + embeddings en la BD.

    Args:
        contenido_pdf: bytes del archivo PDF
        fuente: "Civil" | "Penal" | "Laboral" | "CPE"
        norma_id: ID de la Norma (ya debe existir)
        rama_id: ID de la RamaDerecho (ya debe existir)
        task: tarea Celery para reportar progreso (puede ser None)
        sobrescribir: si True elimina artículos previos de esa norma+rama
    """
    from modulo_catalogo.models.norma import Norma
    from modulo_catalogo.models.rama import RamaDerecho
    from modulo_catalogo.models.articulo import Articulo
    from modulo_ia.models.embedding import EmbeddingArticulo

    try:
        norma = Norma.objects.get(pk=norma_id, estado=True)
        rama = RamaDerecho.objects.get(pk=rama_id, estado=True)
    except Norma.DoesNotExist:
        raise ValueError(f"No existe la norma con ID {norma_id}.")
    except RamaDerecho.DoesNotExist:
        raise ValueError(f"No existe la rama con ID {rama_id}.")

    resultado = ResultadoCarga(
        fuente=fuente,
        norma_nombre=norma.nombre,
        rama_nombre=rama.nombre,
    )

    if sobrescribir:
        Articulo.objects.filter(norma=norma, rama=rama).delete()
        logger.info("Artículos previos eliminados. norma=%s rama=%s", norma, rama)

    _update_task(task, 5, "Extrayendo texto del PDF...")
    try:
        texto = extraer_texto_pdf_bytes(contenido_pdf)
    except Exception as e:
        raise RuntimeError(f"No se pudo extraer el texto del PDF: {e}")

    _update_task(task, 15, "Dividiendo en artículos...")
    lista_articulos = dividir_por_articulos(texto, fuente)
    resultado.total_encontrados = len(lista_articulos)

    if not lista_articulos:
        logger.warning("PDF no produjo artículos. fuente=%s norma=%s", fuente, norma)
        return resultado

    jerarquia = JERARQUIA_POR_FUENTE.get(fuente, 0.8)

    _update_task(task, 18, "Cargando modelo de embeddings...")
    modelo = _obtener_modelo()

    total = len(lista_articulos)

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
            articulo = Articulo.objects.create(
                numero_articulo=str(numero),
                titulo=titulo,
                contenido=texto_articulo,
                norma=norma,
                rama=rama,
                jerarquia_normativa=jerarquia,
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
                defaults={"vector": vector},
            )
        except Exception as e:
            resultado.errores_detalle.append(f"Art. {numero}: error en embedding — {e}")
            logger.error("Error generando embedding Art.%s: %s", numero, e, exc_info=True)
            # El artículo ya está guardado; se informa el problema pero no se
            # cuenta dos veces como error total del artículo.

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