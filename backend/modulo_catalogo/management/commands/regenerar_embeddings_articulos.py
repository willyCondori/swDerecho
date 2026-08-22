# modulo_catalogo/services/carga_pdf_service.py

"""
Servicio de carga masiva de artículos desde PDF.

Flujo:
    PDF
      ↓
    Extraer texto
      ↓
    Limpiar texto
      ↓
    Dividir por artículos
      ↓
    Extraer título
      ↓
    Guardar Articulo
      ↓
    Generar embedding normalizado
      ↓
    Guardar EmbeddingArticulo 1:1

Características:
    - Soporta Civil, Penal, Laboral y CPE.
    - Extrae y guarda el título del artículo.
    - Genera embeddings usando el mismo modelo configurado
      en settings.SENTENCE_TRANSFORMER_MODEL.
    - Normaliza los embeddings.
    - Verifica que tengan 768 dimensiones.
    - Cada embedding se guarda directamente asociado a su articulo_id.
    - No depende de posiciones de listas.
    - Evita duplicados.
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

DIMENSION_VECTOR = 768


# ---------------------------------------------------------------------------
# Modelo SentenceTransformer
# ---------------------------------------------------------------------------

_modelo_cache = None


def _obtener_modelo():
    """
    Carga el modelo SentenceTransformer una sola vez.

    Esto evita volver a cargar el modelo para cada artículo.
    """
    global _modelo_cache

    if _modelo_cache is None:
        from sentence_transformers import SentenceTransformer

        logger.info(
            "Cargando modelo de embeddings: %s",
            settings.SENTENCE_TRANSFORMER_MODEL,
        )

        _modelo_cache = SentenceTransformer(
            settings.SENTENCE_TRANSFORMER_MODEL
        )

    return _modelo_cache


def _generar_vector(texto: str) -> list[float]:
    """
    Genera un embedding normalizado para un artículo.

    El vector se genera directamente con el modelo configurado
    en settings.SENTENCE_TRANSFORMER_MODEL.

    Se verifica que tenga la dimensión esperada.
    """
    if not texto or not texto.strip():
        raise ValueError("No se puede generar un embedding de texto vacío.")

    modelo = _obtener_modelo()

    vector = modelo.encode(
        texto,
        normalize_embeddings=True,
    ).tolist()

    if len(vector) != DIMENSION_VECTOR:
        raise ValueError(
            f"El embedding generado tiene {len(vector)} dimensiones; "
            f"se esperaban {DIMENSION_VECTOR}."
        )

    return vector


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
    """
    Extrae texto de todas las páginas de un PDF.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError(
            "Instala pypdf: pip install pypdf --break-system-packages"
        )

    reader = PdfReader(ruta)

    partes = []

    for page in reader.pages:
        texto = page.extract_text()

        if texto:
            partes.append(texto)

    return "\n".join(partes)


def extraer_texto_pdf_bytes(contenido: bytes) -> str:
    """
    Extrae texto directamente desde bytes.
    """
    import io

    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError(
            "Instala pypdf: pip install pypdf --break-system-packages"
        )

    reader = PdfReader(io.BytesIO(contenido))

    partes = []

    for page in reader.pages:
        texto = page.extract_text()

        if texto:
            partes.append(texto)

    return "\n".join(partes)


# ---------------------------------------------------------------------------
# Limpieza de texto
# ---------------------------------------------------------------------------

def limpiar_texto(texto: str) -> str:
    """
    Elimina URLs, headers/footers y metadata de InfoLeyes.
    """

    # URLs
    texto = re.sub(
        r"http[s]?://[^\s\]]+(?:\[[^\]]+\])?",
        "",
        texto,
    )

    # Headers InfoLeyes
    texto = re.sub(
        r"CODIGO\s+(?:CIVIL|PENAL|LABORAL|DE TRABAJO)"
        r"\s*-\s*Código\s+\w+\s*-\s*Bolivia\s*-\s*InfoLeyes[^\n]*",
        "",
        texto,
        flags=re.IGNORECASE,
    )

    texto = re.sub(
        r"Constitución\s+Política\s+del\s+Estado\s+\(CPE\)"
        r"\s*-\s*Bolivia\s*-\s*InfoLeyes[^\n]*",
        "",
        texto,
        flags=re.IGNORECASE,
    )

    texto = re.sub(
        r"Legislación\s+online[^\n]*",
        "",
        texto,
        flags=re.IGNORECASE,
    )

    # Timestamps
    texto = re.sub(
        r"\[\d{1,2}/\d{1,2}/\d{4}\s+"
        r"\d{1,2}:\d{2}:\d{2}\s+[AP]M\]",
        "",
        texto,
    )

    return texto


# ---------------------------------------------------------------------------
# Patrones por fuente
# ---------------------------------------------------------------------------

PATRONES_POR_FUENTE = {
    "Civil": [
        r"(?:^|\n)\s*ARTÍCULO\s+(\d+)\.",
        r"(?:^|\n)\s*ARTÍCULO\s+(\d+)-",
        r"(?:^|\n)\s*ARTICULO\s+(\d+)\.",
        r"(?:^|\n)\s*ARTICULO\s+(\d+)-",
    ],

    "Penal": [
        r"(?:^|\n)\s*Art\.\s+(\d+)°\.-",
        r"(?:^|\n)\s*Art\.\s+(\d+)º\.-",
        r"(?:^|\n)\s*Art\.\s+(\d+)°\s*\.-",
        r"(?:^|\n)\s*ART\.\s+(\d+)°\.-",
        r"(?:^|\n)\s*Art\.\s+(\d+)\.-",
        r"(?:^|\n)\s*ARTICULO\s+(\d+)°\.-",
        r"(?:^|\n)\s*ARTICULO\s+(\d+)º\.-",
    ],

    "Laboral": [
        r"(?:^|\n)\s*ARTICULO\s+(\d+)º",
        r"(?:^|\n)\s*ARTICULO\s+(\d+)°",
        r"(?:^|\n)\s*ARTICULO\s+(\d+)\.",
        r"(?:^|\n)\s*ARTICULO\s+(\d+)\s",
        r"(?:^|\n)\s*ARTÍCULO\.\s+(\d+)\s*º",
        r"(?:^|\n)\s*ARTÍCULO\s+(\d+)\s*º",
        r"(?:^|\n)\s*Art\.\s*(\d+)º",
    ],

    "CPE": [
        r"(?:^|\n)\s*Artículo\s+(\d+)\.",
        r"(?:^|\n)\s*Artículo\.\s+(\d+)\.",
        r"(?:^|\n)\s*Artículo\s+(\d+)\s",
        r"(?:^|\n)\s*Articulo\s+(\d+)\.",
    ],
}


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
# Extracción del título
# ---------------------------------------------------------------------------

# Ejemplos:
#
# Art. 332°.- (ROBO AGRAVADO).
# Art. 251°.- (HOMICIDIO).
# Art. 308°.- (VIOLACIÓN).
#
# El título debe estar entre paréntesis y normalmente en mayúsculas.

PATRON_TITULO = re.compile(
    r"\(\s*"
    r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-&,/"
    r"0-9\.]*?)"
    r"\s*\)",
)


def extraer_titulo_articulo(contenido: str) -> str | None:
    """
    Extrae el encabezado completo del artículo:

        Art. 332°.- (ROBO AGRAVADO)

    No devuelve solamente:
        ROBO AGRAVADO

    sino todo el encabezado.
    """

    if not contenido:
        return None

    match = re.search(
        r"^([^\n]*?\([^)]+\))",
        contenido.strip(),
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    titulo = match.group(1).strip()

    # Elimina puntuación que aparezca después del paréntesis.
    titulo = re.sub(r"\)\s*\.", ")", titulo)

    # Normaliza espacios.
    titulo = re.sub(r"\s+", " ", titulo)

    return titulo

# ---------------------------------------------------------------------------
# Limpieza del contenido del artículo
# ---------------------------------------------------------------------------

def _limpiar_contenido_articulo(contenido: str, fuente: str) -> str:
    """
    Elimina encabezados de sección pero conserva decretos
    y sub-artículos.
    """

    lineas = contenido.split("\n")
    lineas_limpias = []

    for linea in lineas:
        ls = linea.strip()

        if not ls:
            continue

        es_encabezado = False

        if re.match(
            r"^(?:CAP[ÍI]TULO|TITULO|T[ÍI]TULO|"
            r"SECCI[ÓO]N|PARTE)\s+[IVX\d]+\s*$",
            ls,
            re.IGNORECASE,
        ):
            es_encabezado = True

        if re.match(
            r"^(?:DE\s+LA|DEL|DE\s+LOS|DE\s+LAS)"
            r"\s+[A-ZÁÉÍÓÚÑ\s]+$",
            ls,
        ):
            if (
                len(ls) < 100
                and ls.isupper()
                and ls.count(" ") <= 6
            ):
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
# División por artículos
# ---------------------------------------------------------------------------

def dividir_por_articulos(texto: str, fuente: str) -> list[dict]:
    """
    Divide el texto en artículos.

    Devuelve:

        [
            {
                "numero": 332,
                "titulo": "ROBO AGRAVADO",
                "texto": "Art. 332°.- (ROBO AGRAVADO)..."
            }
        ]
    """

    texto = limpiar_texto(texto)

    patrones = PATRONES_POR_FUENTE.get(
        fuente,
        PATRONES_POR_FUENTE["Civil"],
    )

    todos_matches = []

    for patron in patrones:
        matches = list(
            re.finditer(
                patron,
                texto,
                re.MULTILINE,
            )
        )

        todos_matches.extend(matches)

    todos_matches.sort(key=lambda m: m.start())

    # ---------------------------------------------------------------
    # Deduplicar coincidencias producidas por distintos patrones
    # ---------------------------------------------------------------

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
        logger.warning(
            "No se encontraron artículos en el PDF para fuente=%s",
            fuente,
        )
        return []

    articulos = []
    numeros_vistos = set()

    # ---------------------------------------------------------------
    # Crear cada artículo
    # ---------------------------------------------------------------

    for i, match in enumerate(matches_unicos):

        numero = int(match.group(1))

        if numero in numeros_vistos:
            continue

        numeros_vistos.add(numero)

        inicio = match.start()

        fin = (
            matches_unicos[i + 1].start()
            if i + 1 < len(matches_unicos)
            else len(texto)
        )

        contenido = _limpiar_contenido_articulo(
            texto[inicio:fin].strip(),
            fuente,
        )

        if len(contenido) < 20:
            continue

        titulo = extraer_titulo_articulo(contenido)

        articulos.append(
            {
                "numero": numero,
                "titulo": titulo,
                "texto": contenido,
            }
        )

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
    Procesa un PDF en memoria y guarda los artículos + embeddings.

    Args:
        contenido_pdf:
            Contenido del PDF en bytes.

        fuente:
            Civil | Penal | Laboral | CPE.

        norma_id:
            ID de la Norma.

        rama_id:
            ID de la RamaDerecho.

        task:
            Tarea Celery opcional.

        sobrescribir:
            Si True elimina los artículos anteriores
            de esa norma y rama.
    """

    from modulo_catalogo.models.norma import Norma
    from modulo_catalogo.models.rama import RamaDerecho
    from modulo_catalogo.models.articulo import Articulo
    from modulo_ia.models.embedding import EmbeddingArticulo

    # ---------------------------------------------------------------
    # Obtener objetos relacionados
    # ---------------------------------------------------------------

    try:
        norma = Norma.objects.get(
            pk=norma_id,
            estado=True,
        )

        rama = RamaDerecho.objects.get(
            pk=rama_id,
            estado=True,
        )

    except Norma.DoesNotExist:
        raise ValueError(
            f"No existe la norma con ID {norma_id}."
        )

    except RamaDerecho.DoesNotExist:
        raise ValueError(
            f"No existe la rama con ID {rama_id}."
        )

    resultado = ResultadoCarga(
        fuente=fuente,
        norma_nombre=norma.nombre,
        rama_nombre=rama.nombre,
    )

    # ---------------------------------------------------------------
    # Sobrescribir
    # ---------------------------------------------------------------

    if sobrescribir:

        Articulo.objects.filter(
            norma=norma,
            rama=rama,
        ).delete()

        logger.info(
            "Artículos previos eliminados. norma=%s rama=%s",
            norma,
            rama,
        )

    # ---------------------------------------------------------------
    # Extraer texto
    # ---------------------------------------------------------------

    _update_task(
        task,
        5,
        "Extrayendo texto del PDF...",
    )

    try:
        texto = extraer_texto_pdf_bytes(
            contenido_pdf
        )

    except Exception as e:
        raise RuntimeError(
            f"No se pudo extraer el texto del PDF: {e}"
        )

    # ---------------------------------------------------------------
    # Dividir en artículos
    # ---------------------------------------------------------------

    _update_task(
        task,
        15,
        "Dividiendo en artículos...",
    )

    lista_articulos = dividir_por_articulos(
        texto,
        fuente,
    )

    resultado.total_encontrados = len(
        lista_articulos
    )

    if not lista_articulos:

        logger.warning(
            "PDF no produjo artículos. fuente=%s norma=%s",
            fuente,
            norma,
        )

        return resultado

    jerarquia = JERARQUIA_POR_FUENTE.get(
        fuente,
        0.8,
    )

    # ---------------------------------------------------------------
    # Cargar modelo UNA SOLA VEZ
    # ---------------------------------------------------------------

    _update_task(
        task,
        18,
        "Cargando modelo de embeddings...",
    )

    modelo = _obtener_modelo()

    total = len(lista_articulos)

    # ---------------------------------------------------------------
    # Procesar artículos
    # ---------------------------------------------------------------

    for idx, art_dict in enumerate(
        lista_articulos,
        start=1,
    ):

        numero = art_dict["numero"]
        titulo = art_dict["titulo"]
        texto_articulo = art_dict["texto"]

        # -----------------------------------------------------------
        # Progreso
        # -----------------------------------------------------------

        if idx % 10 == 0 or idx == total:

            pct = int(
                18 + (idx / total) * 80
            )

            _update_task(
                task,
                pct,
                f"Procesando artículo {idx}/{total}...",
            )

        # -----------------------------------------------------------
        # Evitar duplicados
        # -----------------------------------------------------------

        if Articulo.objects.filter(
            norma=norma,
            rama=rama,
            numero_articulo=str(numero),
        ).exists():

            resultado.duplicados += 1
            continue

        # -----------------------------------------------------------
        # Validar contenido
        # -----------------------------------------------------------

        if (
            not texto_articulo
            or len(texto_articulo.strip()) < 20
        ):

            resultado.errores += 1

            resultado.errores_detalle.append(
                f"Art. {numero}: texto muy corto"
            )

            continue

        # -----------------------------------------------------------
        # Guardar artículo
        # -----------------------------------------------------------

        try:

            articulo = Articulo.objects.create(
                numero_articulo=str(numero),

                # Ahora sí se guarda el título
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

            resultado.errores_detalle.append(
                f"Art. {numero}: "
                f"error al guardar — {e}"
            )

            logger.error(
                "Error guardando Art.%s: %s",
                numero,
                e,
            )

            continue

        # -----------------------------------------------------------
        # Generar embedding
        # -----------------------------------------------------------

        try:

            vector = modelo.encode(
                texto_articulo,
                normalize_embeddings=True,
            ).tolist()

            # Validar dimensión
            if len(vector) != DIMENSION_VECTOR:

                raise ValueError(
                    f"El embedding del Art. {numero} "
                    f"tiene {len(vector)} dimensiones; "
                    f"se esperaban {DIMENSION_VECTOR}."
                )

            # -------------------------------------------------------
            # Guardar inmediatamente asociado al artículo
            # -------------------------------------------------------

            EmbeddingArticulo.objects.update_or_create(
                articulo=articulo,
                defaults={
                    "vector": vector,
                },
            )

        except Exception as e:

            resultado.errores += 1

            resultado.errores_detalle.append(
                f"Art. {numero}: "
                f"error en embedding — {e}"
            )

            logger.error(
                "Error generando embedding Art.%s: %s",
                numero,
                e,
                exc_info=True,
            )

            # Si no existe embedding, el artículo queda guardado
            # pero se informa claramente del problema.
            continue

        resultado.guardados += 1

    # ---------------------------------------------------------------
    # Finalización
    # ---------------------------------------------------------------

    _update_task(
        task,
        100,
        "Carga completada.",
    )

    logger.info(
        "Carga finalizada. Norma=%s "
        "Guardados=%s Duplicados=%s Errores=%s",
        norma,
        resultado.guardados,
        resultado.duplicados,
        resultado.errores,
    )

    return resultado


# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------

def _update_task(
    task,
    progreso: int,
    paso: str,
):
    """
    Actualiza el estado de Celery si existe.
    """

    if task is None:
        return

    try:

        task.update_state(
            state="STARTED",
            meta={
                "progreso": progreso,
                "paso": paso,
            },
        )

    except Exception:
        # Un error mostrando progreso nunca debe
        # romper la carga de legislación.
        pass
