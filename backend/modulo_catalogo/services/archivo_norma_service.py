"""Nombres de registro y almacenamiento de los PDF normativos."""
import os
import re
import unicodedata
from zoneinfo import ZoneInfo
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


def guardar_pdf_norma(archivo, norma):
    registro = timezone.now().astimezone(ZoneInfo('America/La_Paz'))
    titulo = unicodedata.normalize('NFC', norma.nombre or 'Norma')
    titulo = re.sub(r'[<>:"/\\|?*\x00-\x1f]', ' ', titulo)
    titulo = re.sub(r'\s+', ' ', titulo).strip(' .')[:120].rstrip(' .') or 'Norma'
    carpeta = f'{norma.pk}-' + (slugify(norma.sigla or norma.nombre)[:50] or 'norma')
    relativa = os.path.join('documentos_normativas', carpeta)
    absoluta = os.path.join(settings.MEDIA_ROOT, relativa)
    os.makedirs(absoluta, exist_ok=True)
    base = f'{titulo} - {registro:%Y-%m-%d}'
    numero = 1
    while True:
        nombre = f'{base}{f" ({numero})" if numero > 1 else ""}.pdf'
        ruta = os.path.join(absoluta, nombre)
        try:
            destino = open(ruta, 'xb')
        except FileExistsError:
            numero += 1
            continue
        try:
            with destino:
                for chunk in archivo.chunks():
                    destino.write(chunk)
        except Exception:
            os.remove(ruta)
            raise
        return {'nombre': nombre, 'ruta': ruta, 'ruta_relativa': os.path.join(relativa, nombre),
                'metadatos': {'nombre_archivo_subido': archivo.name, 'fecha_registro': registro.isoformat()}}
