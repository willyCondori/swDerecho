"""Recolector serial de fuentes oficiales: listados, texto completo y PDFs."""
import hashlib
import re
import time
import unicodedata
from io import BytesIO
from urllib.parse import urljoin, urlparse

import requests
from lxml import html
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from modulo_catalogo.models import DocumentoOficial
from .vigencia_service import fecha

FUENTES = ['/normas/listadonor/10', '/normas/listadonor/11', '/normas/listadonor/16', '/resolucions/listadomin']
PATRON_PENAL = re.compile(r'\b(?:penal|penales|penitenciari\w*|delito\w*|fiscalia\w*|fiscal general|ministerio publico|'
    r'criminal\w*|procesal penal|ejecucion de penas|redencion|narcotrafico|violencia|corrupcion|'
    r'trata|trafico de personas|seguridad ciudadana|codigo de procedimiento penal)\b', re.I)


def es_penal(texto):
    texto = ''.join(c for c in unicodedata.normalize('NFKD', texto) if not unicodedata.combining(c))
    return bool(PATRON_PENAL.search(texto))


def url_oficial(url):
    p = urlparse(url)
    if p.scheme not in ['http', 'https'] or p.hostname not in [
            'gacetaoficialdebolivia.gob.bo', 'www.gacetaoficialdebolivia.gob.bo'] or p.username or p.password or p.port:
        raise ValueError('Solo se permiten enlaces públicos de la Gaceta Oficial.')
    return url


def descargar(url, limite=50 * 1024 * 1024):
    url_oficial(url)
    # Comprobar cada redirección antes de hacer una nueva petición.
    for _ in range(5):
        with requests.get(url, stream=True, allow_redirects=False, timeout=(5, 30),
                          headers={'User-Agent': 'SW-Derecho/1.0 (consulta normativa pública)'}) as respuesta:
            if respuesta.is_redirect:
                url = url_oficial(urljoin(url, respuesta.headers['Location']))
                continue
            respuesta.raise_for_status()
            datos, largo = [], 0
            for bloque in respuesta.iter_content(65536):
                largo += len(bloque)
                if largo > limite:
                    raise ValueError('El documento excede el límite de descarga.')
                datos.append(bloque)
            return b''.join(datos)
    raise ValueError('Demasiadas redirecciones de la fuente oficial.')


def analizar_listado(contenido, url):
    tree = html.fromstring(contenido.decode('utf-8-sig') if isinstance(contenido, bytes) else contenido)
    registros, vistos = [], set()
    for enlace in tree.xpath('//a[@href]'):
        href = enlace.get('href')
        if not re.search(r'/(?:normas|resolucions)/verGratis[^/]*/\d+', href):
            continue
        # Excluir las variantes Word; solo el enlace de consulta.
        if re.search(r'verGratis_gob[12]/', href):
            continue
        fuente = url_oficial(urljoin(url, href))
        if fuente in vistos: continue
        vistos.add(fuente)
        tarjetas = enlace.xpath('ancestor::*[contains(concat(" ", normalize-space(@class), " "), " card ")]')
        contenedor = tarjetas[-1] if tarjetas else enlace.getparent().getparent()
        texto = ' '.join(contenedor.text_content().split())
        titulo = contenedor.xpath('.//h6|.//h5|.//h4')
        titulo = ' '.join(titulo[0].text_content().split()) if titulo else texto[:200]
        pdfs = [urljoin(url, a.get('href')) for a in contenedor.xpath('.//a[@href]')
                if re.search(r'/(?:normas|resolucions)/descargar(?:Nrms|Pdf|PDF)', a.get('href', ''))]
        identidad = re.search(r'(Ley|Decreto Supremo|Decreto Presidencial|Decreto Ley|Resoluci[oó]n Suprema|Sentencia Constitucional[^\d]*).*?(\d+)', titulo, re.I)
        fecha_pub = re.search(r'Fecha de Publicaci[oó]n:\s*(\d{4}-\d{2}-\d{2})', texto, re.I)
        registros.append({'url_fuente': fuente, 'url_pdf': pdfs[0] if pdfs else '',
            'identificador': href.rsplit('/', 1)[-1], 'titulo': titulo[:500],
            'tipo': identidad.group(1) if identidad else '', 'numero': identidad.group(2) if identidad else '',
            'fecha_publicacion': fecha(fecha_pub.group(1)) if fecha_pub else None,
            'descripcion': texto})
    siguientes = [urljoin(url, a.get('href')) for a in tree.xpath('//a[@href]')
                  if re.search(r'siguiente|next', a.text_content(), re.I) and 'page' in a.get('href', '')]
    return registros, siguientes[0] if siguientes else None


def texto_consulta(contenido):
    tree = html.fromstring(contenido.decode('utf-8-sig') if isinstance(contenido, bytes) else contenido)
    seleccion = tree.xpath('//*[@id="seleccion"]')
    if not seleccion:
        raise ValueError('La Gaceta cambió su estructura: no se encontró el texto de consulta.')
    # Conservar saltos de párrafos para la lectura normativa posterior.
    textos = seleccion[0].xpath('.//p|.//li')
    return '\n'.join(' '.join(n.text_content().split()) for n in textos) if textos else seleccion[0].text_content()


def recolectar(max_paginas=1, desde=None, hasta=None, fuentes=None, progreso=None):
    base = settings.GACETA_BASE_URL.rstrip('/')
    resumen = {'consultados': 0, 'penales': 0, 'descargados': 0, 'existentes': 0, 'errores': [], 'paginas': 0}
    pendientes = list(fuentes or FUENTES)
    fuentes_vistas = set()
    for ruta in pendientes:
        if ruta in fuentes_vistas: continue
        fuentes_vistas.add(ruta)
        url = url_oficial(urljoin(base, ruta))
        visitadas = set()
        paginas = 0
        while url and url not in visitadas and (not max_paginas or paginas < max_paginas):
            visitadas.add(url)
            try:
                contenido_listado = descargar(url, 5 * 1024 * 1024)
                filas, siguiente = analizar_listado(contenido_listado, url)
                tree = html.fromstring(contenido_listado.decode('utf-8-sig'))
                if '/resolucions/listadomin' in url:
                    categorias = [a.get('href') for a in tree.xpath('//a[@href]')
                                  if re.match(r'^/resolucions/listadonor1/[^/]+$', a.get('href', ''))
                                  and 'page:' not in a.get('href', '')]
                    pendientes.extend(r for r in categorias if r not in fuentes_vistas)
                elif not filas:
                    tarjetas = tree.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " card ")]')
                    if any('Resoluci' in t.text_content() for t in tarjetas):
                        resumen['errores'].append({'url': url, 'error': 'El listado de resoluciones ofrece fichas sin enlaces individuales de texto/PDF. Revisar publicaciones por edición.'})
                        # No afirmar cobertura de cientos de fichas sin archivos.
                        break
                    if '/normas/' in url:
                        raise ValueError('Listado sin enlaces normativos reconocibles; verificar estructura antes de continuar.')
            except (requests.RequestException, ValueError) as exc:
                resumen['errores'].append({'url': url, 'error': str(exc)})
                break
            paginas += 1
            resumen['paginas'] += 1
            if progreso: progreso(resumen)
            for fila in filas:
                fecha_pub = fila['fecha_publicacion']
                if fecha_pub and ((desde and fecha_pub < desde) or (hasta and fecha_pub > hasta)):
                    continue
                resumen['consultados'] += 1
                registro, nuevo = DocumentoOficial.objects.get_or_create(url_fuente=fila['url_fuente'], defaults={
                    k: v for k, v in fila.items() if k != 'descripcion'})
                if not nuevo and registro.estado_descarga in ['descargado', 'no_penal']:
                    resumen['existentes'] += 1
                    continue
                try:
                    texto = texto_consulta(descargar(fila['url_fuente'], 5 * 1024 * 1024))
                    registro.texto = texto
                    registro.penal = es_penal(fila['descripcion'] + '\n' + texto)
                    if registro.penal:
                        resumen['penales'] += 1
                        if not fila['url_pdf']:
                            raise ValueError('La publicación no ofrece un enlace PDF identificado; revisar fuente.')
                        pdf = descargar(fila['url_pdf'])
                        if not pdf.startswith(b'%PDF-'):
                            raise ValueError('El enlace devolvió un archivo que no es PDF.')
                        from pypdf import PdfReader
                        if not len(PdfReader(BytesIO(pdf)).pages):
                            raise ValueError('El PDF descargado no tiene páginas.')
                        digest = hashlib.sha256(pdf).hexdigest()
                        ruta_archivo = f'gaceta_penal/{registro.identificador}-{digest[:16]}.pdf'
                        if not default_storage.exists(ruta_archivo):
                            ruta_archivo = default_storage.save(ruta_archivo, ContentFile(pdf))
                        registro.ruta_archivo = ruta_archivo
                        registro.hash_pdf = digest
                        registro.url_pdf = fila['url_pdf']
                        registro.estado_descarga = 'descargado'
                        resumen['descargados'] += 1
                    else:
                        registro.estado_descarga = 'no_penal'
                    registro.error = ''
                except Exception as exc:
                    registro.estado_descarga = 'error'
                    registro.error = str(exc)
                    resumen['errores'].append({'url': fila['url_fuente'], 'error': str(exc)})
                registro.save()
                if progreso:
                    progreso(resumen)
                time.sleep(settings.GACETA_PAUSA_SEGUNDOS)
            # Recorrer la paginación solicitada aunque una página tenga
            # fechas antiguas: una republicación puede aparecer más adelante.
            url = siguiente
    # No confundir una búsqueda acotada o fallida con una cobertura completa.
    resumen['cobertura'] = 'parcial' if max_paginas or resumen['errores'] else 'listados_recorridos'
    return resumen
