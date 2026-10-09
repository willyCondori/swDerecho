"""Importación idempotente de los JSON originales guardados por tsj_scraper."""
import hashlib
import json
import re
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urlparse

from django.db import transaction

from modulo_ia.models.jurisprudencia import (
    ResolucionJurisprudencia, FragmentoJurisprudencia, EmbeddingJurisprudencia,
)
from modulo_ia.services.chunking_service import ChunkingService
from modulo_ia.services.model_loader import version_activa
from modulo_ia.services.vectorizacion_service import vectorizar_textos


class _TextoHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes = []
        self.oculto = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.oculto += 1
        if not self.oculto and tag in ("p", "div", "br", "li", "h1", "h2", "h3", "tr"):
            self.partes.append("\n\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.oculto = max(0, self.oculto - 1)
        if not self.oculto and tag in ("p", "div", "li", "tr"):
            self.partes.append("\n\n")

    def handle_data(self, data):
        if not self.oculto:
            self.partes.append(data)


def limpiar_contenido(contenido):
    if not isinstance(contenido, str):
        raise ValueError("La resolución no tiene contenido textual.")
    parser = _TextoHTML()
    parser.feed(contenido)
    texto = "".join(parser.partes)
    texto = re.sub(r"[^\S\n]+", " ", texto)
    return re.sub(r"\n\s*\n", "\n\n", texto).strip()


def _etiqueta(valor):
    if isinstance(valor, dict):
        valor = valor.get("nombre") or valor.get("descripcion") or ""
    return str(valor or "").strip()


def _fecha(valor):
    if not valor:
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(valor)[:10], formato).date()
        except ValueError:
            pass
    raise ValueError(f"Fecha de emisión inválida: {valor}")


def url_oficial(valor):
    valor = str(valor or "").strip()
    parsed = urlparse(valor)
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "https" and (host == "tsj.bo" or host.endswith(".tsj.bo")) and not parsed.username:
        return valor
    return ""


def importar_resolucion(datos):
    if not isinstance(datos, dict):
        raise ValueError("Se esperaba un objeto JSON de resolución.")
    # Admite también la respuesta GET /resoluciones/{id}, además del JSON crudo.
    if "id" not in datos and isinstance(datos.get("data"), dict):
        datos = datos["data"]
    fuente_id = str(datos.get("id", ""))
    if not fuente_id.isdigit() or len(fuente_id) > 40:
        raise ValueError("La resolución necesita un id numérico del TSJ.")
    texto = limpiar_contenido(datos.get("contenido"))
    if len(texto) < 80:
        raise ValueError("Texto insuficiente; los PDF sin texto requieren extracción/OCR antes de importar.")
    materia = _etiqueta(datos.get("materia")) or "Penal"
    if materia.casefold() != "penal":
        raise ValueError("Esta integración cubre las resoluciones de materia Penal de tsj_scraper.")
    campos = dict(
        numero=_etiqueta(datos.get("nro_resolucion"))[:150],
        expediente=_etiqueta(datos.get("nro_expediente"))[:255],
        fecha=_fecha(datos.get("fecha_emision")), materia=materia,
        sala=_etiqueta(datos.get("sala"))[:255],
        departamento=_etiqueta(datos.get("departamento"))[:150],
        url_fuente=f"https://apigenesis.tsj.bo/api/v1/resoluciones/{fuente_id}",
        url_pdf=url_oficial(datos.get("url_pdf_escaneado"))[:2000], texto=texto,
    )
    huella = hashlib.sha256(json.dumps(campos, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    version = version_activa()
    anterior = ResolucionJurisprudencia.objects.filter(fuente_id=fuente_id).first()
    mismo_texto = anterior is not None and anterior.texto == texto
    fragmentos = list(anterior.fragmentos.order_by("orden")) if mismo_texto else []
    if fragmentos and anterior.huella == huella and anterior.activa:
        existentes = EmbeddingJurisprudencia.objects.filter(fragmento__resolucion=anterior, modelo_version=version).count()
        if existentes == len(fragmentos):
            return "omitida"
    contenidos = [f.contenido for f in fragmentos] if fragmentos else ChunkingService._partir_en_fragmentos(texto, 900, 150)
    vectores = vectorizar_textos(contenidos)
    # Una falla de lectura o de modelo no deja la resolución a medio importar.
    with transaction.atomic():
        resolucion, _ = ResolucionJurisprudencia.objects.update_or_create(
            fuente_id=fuente_id, defaults={**campos, "huella": huella, "activa": True},
        )
        if not fragmentos:
            resolucion.fragmentos.all().delete()
            fragmentos = FragmentoJurisprudencia.objects.bulk_create([
                FragmentoJurisprudencia(resolucion=resolucion, orden=i, contenido=t)
                for i, t in enumerate(contenidos)
            ])
        EmbeddingJurisprudencia.objects.bulk_create([
            EmbeddingJurisprudencia(fragmento=f, modelo_version=version, vector=v)
            for f, v in zip(fragmentos, vectores)
        ], update_conflicts=True, unique_fields=["fragmento", "modelo_version"], update_fields=["vector"])
    return "actualizada" if anterior else "creada"
