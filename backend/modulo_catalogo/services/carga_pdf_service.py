# modulo_catalogo/services/carga_pdf_service.py
"""
Servicio de carga masiva de artículos desde PDF.

Adapta la lógica del script cargar_articulos.py al modelo del proyecto:
  - Usa modulo_catalogo.models → Articulo, Norma, RamaDerecho
  - Usa modulo_ia.services.embedding_service para generar y guardar vectores
  - Reporta progreso vía Celery task state (meta) para que el frontend
    pueda consultarlo en GET /api/ia/tarea/{task_id}/

Flujo:
  PDF → extraer texto → dividir por artículos → limpiar
      → guardar Articulo → generar embedding → guardar EmbeddingArticulo
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Dataclass de resultado
# ─────────────────────────────────────────────────────────────

@dataclass
class ResultadoCarga:
    fuente:         str
    norma_nombre:   str
    rama_nombre:    str
    total_encontrados: int = 0
    guardados:      int = 0
    duplicados:     int = 0
    errores:        int = 0
    errores_detalle: list = field(default_factory=list)

    def resumen(self) -> dict:
        return {
            "fuente"          : self.fuente,
            "norma"           : self.norma_nombre,
            "rama"            : self.rama_nombre,
            "total_encontrados": self.total_encontrados,
            "guardados"       : self.guardados,
            "duplicados"      : self.duplicados,
            "errores"         : self.errores,
            "errores_detalle" : self.errores_detalle[:20],   # máximo 20
        }


# ─────────────────────────────────────────────────────────────
# Extracción de texto del PDF
# ─────────────────────────────────────────────────────────────

def extraer_texto_pdf(ruta: str) -> str:
    """Extrae texto de todas las páginas del PDF."""
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


# ─────────────────────────────────────────────────────────────
# Limpieza de texto
# ─────────────────────────────────────────────────────────────

def limpiar_texto(texto: str) -> str:
    """Elimina URLs, headers/footers y metadata de InfoLeyes."""
    # URLs
    texto = re.sub(r'http[s]?://[^\s\]]+(?:\[[^\]]+\])?', '', texto)
    # Headers InfoLeyes
    texto = re.sub(
        r'CODIGO\s+(?:CIVIL|PENAL|LABORAL|DE TRABAJO)\s*-\s*Código\s+\w+\s*-\s*Bolivia\s*-\s*InfoLeyes[^\n]*',
        '', texto, flags=re.IGNORECASE
    )
    texto = re.sub(
        r'Constitución\s+Política\s+del\s+Estado\s+\(CPE\)\s*-\s*Bolivia\s*-\s*InfoLeyes[^\n]*',
        '', texto, flags=re.IGNORECASE
    )
    texto = re.sub(r'Legislación\s+online[^\n]*', '', texto, flags=re.IGNORECASE)
    # Timestamps
    texto = re.sub(r'\[\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M\]', '', texto)
    return texto


# ─────────────────────────────────────────────────────────────
# Patrones por fuente
# ─────────────────────────────────────────────────────────────

PATRONES_POR_FUENTE = {
    "Civil": [
        r'(?:^|\n)\s*ARTÍCULO\s+(\d+)\.',
        r'(?:^|\n)\s*ARTÍCULO\s+(\d+)-',
        r'(?:^|\n)\s*ARTICULO\s+(\d+)\.',
        r'(?:^|\n)\s*ARTICULO\s+(\d+)-',
    ],
    "Penal": [
        r'(?:^|\n)\s*Art\.\s+(\d+)°\.-',
        r'(?:^|\n)\s*Art\.\s+(\d+)º\.-',
        r'(?:^|\n)\s*Art\.\s+(\d+)°\s*\.-',
        r'(?:^|\n)\s*ART\.\s+(\d+)°\.-',
        r'(?:^|\n)\s*Art\.\s+(\d+)\.-',
        r'(?:^|\n)\s*ARTICULO\s+(\d+)°\.-',
        r'(?:^|\n)\s*ARTICULO\s+(\d+)º\.-',
    ],
    "Laboral": [
        r'(?:^|\n)\s*ARTICULO\s+(\d+)º',
        r'(?:^|\n)\s*ARTICULO\s+(\d+)°',
        r'(?:^|\n)\s*ARTICULO\s+(\d+)\.',
        r'(?:^|\n)\s*ARTICULO\s+(\d+)\s',
        r'(?:^|\n)\s*ARTÍCULO\.\s+(\d+)\s*º',
        r'(?:^|\n)\s*ARTÍCULO\s+(\d+)\s*º',
        r'(?:^|\n)\s*Art\.\s*(\d+)º',
    ],
    "CPE": [
        r'(?:^|\n)\s*Artículo\s+(\d+)\.',
        r'(?:^|\n)\s*Artículo\.\s+(\d+)\.',
        r'(?:^|\n)\s*Artículo\s+(\d+)\s',
        r'(?:^|\n)\s*Articulo\s+(\d+)\.',
    ],
}

# Mapa fuente → jerarquía normativa (usado al crear Articulo)
JERARQUIA_POR_FUENTE = {
    "CPE"    : 1.0,   # Constitución
    "Civil"  : 0.8,   # Código Civil
    "Penal"  : 0.8,   # Código Penal
    "Laboral": 0.8,   # Código Laboral
}


# ─────────────────────────────────────────────────────────────
# División en artículos
# ─────────────────────────────────────────────────────────────

def _limpiar_contenido_articulo(contenido: str, fuente: str) -> str:
    """Elimina encabezados de sección pero conserva decretos y sub-artículos."""
    lineas = contenido.split('\n')
    lineas_limpias = []
    for linea in lineas:
        ls = linea.strip()
        if not ls:
            continue
        es_encabezado = False
        if re.match(
            r'^(?:CAP[ÍI]TULO|TITULO|T[ÍI]TULO|SECCI[ÓO]N|PARTE)\s+[IVX\d]+\s*$',
            ls, re.IGNORECASE
        ):
            es_encabezado = True
        if re.match(r'^(?:DE\s+LA|DEL|DE\s+LOS|DE\s+LAS)\s+[A-ZÁÉÍÓÚÑ\s]+$', ls):
            if len(ls) < 100 and ls.isupper() and ls.count(' ') <= 6:
                es_encabezado = True
        if fuente == "Laboral" and re.match(r'^\d+$', ls):
            es_encabezado = True
        if not es_encabezado:
            lineas_limpias.append(linea)

    resultado = '\n'.join(lineas_limpias)
    resultado = re.sub(r' +', ' ', resultado)
    resultado = re.sub(r'\n{3,}', '\n\n', resultado)
    return resultado.strip()


def dividir_por_articulos(texto: str, fuente: str) -> list[dict]:
    """
    Divide el texto en artículos usando los patrones de la fuente.
    Devuelve lista de {"numero": int, "texto": str}.
    """
    texto   = limpiar_texto(texto)
    patrones= PATRONES_POR_FUENTE.get(fuente, PATRONES_POR_FUENTE["Civil"])

    todos_matches = []
    for patron in patrones:
        matches = list(re.finditer(patron, texto, re.MULTILINE))
        todos_matches.extend(matches)

    todos_matches.sort(key=lambda m: m.start())

    # Deduplicar: mismo número muy cerca → tomar primero
    matches_unicos = []
    ultima_pos  = -100
    ultimo_num  = -1
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

    articulos        = []
    numeros_vistos   = set()

    for i, match in enumerate(matches_unicos):
        numero = int(match.group(1))
        if numero in numeros_vistos:
            continue
        numeros_vistos.add(numero)

        inicio   = match.start()
        fin      = matches_unicos[i + 1].start() if i + 1 < len(matches_unicos) else len(texto)
        contenido= _limpiar_contenido_articulo(texto[inicio:fin].strip(), fuente)

        if len(contenido) >= 20:
            articulos.append({"numero": numero, "texto": contenido})

    return articulos


# ─────────────────────────────────────────────────────────────
# Carga principal
# ─────────────────────────────────────────────────────────────

def cargar_articulos_desde_bytes(
    contenido_pdf: bytes,
    fuente: str,
    norma_id: int,
    rama_id: int,
    task=None,           # instancia de la tarea Celery (opcional, para progreso)
    sobrescribir: bool = False,
) -> ResultadoCarga:
    """
    Procesa un PDF en memoria y guarda los artículos + embeddings en la BD.

    Args:
        contenido_pdf : bytes del archivo PDF
        fuente        : "Civil" | "Penal" | "Laboral" | "CPE" | custom
        norma_id      : ID de la Norma (ya debe existir)
        rama_id       : ID de la RamaDerecho (ya debe existir)
        task          : tarea Celery para reportar progreso (puede ser None)
        sobrescribir  : si True elimina artículos previos de esa norma+rama

    Returns:
        ResultadoCarga con el resumen de la operación
    """
    from modulo_catalogo.models.norma   import Norma
    from modulo_catalogo.models.rama    import RamaDerecho
    from modulo_catalogo.models.articulo import Articulo
    from modulo_ia.models.embedding     import EmbeddingArticulo

    # ── Obtener objetos de BD ──────────────────────────────
    try:
        norma = Norma.objects.get(pk=norma_id, estado=True)
        rama  = RamaDerecho.objects.get(pk=rama_id, estado=True)
    except Norma.DoesNotExist:
        raise ValueError(f"No existe la norma con ID {norma_id}.")
    except RamaDerecho.DoesNotExist:
        raise ValueError(f"No existe la rama con ID {rama_id}.")

    resultado = ResultadoCarga(
        fuente       = fuente,
        norma_nombre = norma.nombre,
        rama_nombre  = rama.nombre,
    )

    # ── Borrar existentes si se pide ───────────────────────
    if sobrescribir:
        Articulo.objects.filter(norma=norma, rama=rama).delete()
        logger.info("Artículos previos de norma=%s rama=%s eliminados.", norma, rama)

    # ── Extraer texto ──────────────────────────────────────
    _update_task(task, 5, "Extrayendo texto del PDF...")
    try:
        texto = extraer_texto_pdf_bytes(contenido_pdf)
    except Exception as e:
        raise RuntimeError(f"No se pudo extraer el texto del PDF: {e}")

    # ── Dividir en artículos ───────────────────────────────
    _update_task(task, 15, "Dividiendo en artículos...")
    lista_articulos = dividir_por_articulos(texto, fuente)
    resultado.total_encontrados = len(lista_articulos)

    if not lista_articulos:
        logger.warning("PDF no produjo artículos. fuente=%s norma=%s", fuente, norma)
        return resultado

    jerarquia = JERARQUIA_POR_FUENTE.get(fuente, 0.8)

    # ── Guardar artículos + embeddings ─────────────────────
    total   = len(lista_articulos)
    for idx, art_dict in enumerate(lista_articulos, start=1):
        numero        = art_dict["numero"]
        texto_articulo= art_dict["texto"]

        # Reportar progreso cada 10 artículos
        if idx % 10 == 0 or idx == total:
            pct = int(15 + (idx / total) * 80)
            _update_task(task, pct, f"Procesando artículo {idx}/{total}...")

        # Saltar duplicados
        if Articulo.objects.filter(norma=norma, rama=rama, numero_articulo=str(numero)).exists():
            resultado.duplicados += 1
            continue

        if not texto_articulo or len(texto_articulo.strip()) < 20:
            resultado.errores += 1
            resultado.errores_detalle.append(f"Art. {numero}: texto muy corto")
            continue

        # Guardar artículo
        try:
            articulo = Articulo.objects.create(
                numero_articulo     = str(numero),
                titulo              = None,
                contenido           = texto_articulo,
                norma               = norma,
                rama                = rama,
                jerarquia_normativa = jerarquia,
                frecuencia_historica= 0,
                estado              = True,
            )
        except Exception as e:
            resultado.errores += 1
            resultado.errores_detalle.append(f"Art. {numero}: error al guardar — {e}")
            logger.error("Error guardando Art.%s: %s", numero, e)
            continue

        # Generar y guardar embedding
        try:
            vector = _generar_vector(texto_articulo)
            EmbeddingArticulo.objects.update_or_create(
                articulo=articulo,
                defaults={"vector": vector},
            )
        except Exception as e:
            # El artículo ya está guardado; solo logueamos el error de embedding
            resultado.errores_detalle.append(f"Art. {numero}: error en embedding — {e}")
            logger.error("Error embedding Art.%s: %s", numero, e)

        resultado.guardados += 1

    _update_task(task, 100, "Carga completada.")
    logger.info(
        "Carga finalizada. Norma=%s Guardados=%s Duplicados=%s Errores=%s",
        norma, resultado.guardados, resultado.duplicados, resultado.errores,
    )
    return resultado


# ─────────────────────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────────────────────

def _generar_vector(texto: str) -> list[float]:
    """
    Genera el vector de embedding usando el servicio IA del proyecto.
    Importación diferida para evitar cargar el modelo al importar el módulo.
    """
    try:
        from modulo_ia.services.embedding_service import EmbeddingService
        return EmbeddingService.generar_vector(texto)
    except ImportError:
        # Fallback: intentar con sentence_transformers directamente
        from django.conf import settings
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL)
        return model.encode(texto, normalize_embeddings=True).tolist()


def _update_task(task, progreso: int, paso: str):
    """Actualiza el estado de la tarea Celery si existe."""
    if task is None:
        return
    try:
        task.update_state(
            state="STARTED",
            meta={"progreso": progreso, "paso": paso},
        )
    except Exception:
        pass   # nunca romper el flujo por un error de reporte