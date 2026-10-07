"""OCR local de una página a la vez; no utiliza Ollama ni carga modelos en GPU."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from django.conf import settings


def transcribir_pagina(pagina, numero):
    configurado = getattr(settings, 'PDF_TESSERACT_CMD', '')
    ejecutable = configurado or shutil.which('tesseract')
    if not ejecutable and os.name == 'nt':
        candidato = Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Tesseract-OCR' / 'tesseract.exe'
        if candidato.is_file():
            ejecutable = str(candidato)
    if not ejecutable:
        raise ValueError(f'La página {numero} está escaneada. Para leerla sin Qwen instala Tesseract '
                         'con español o configura PDF_TESSERACT_CMD. También puedes elegir Qwen manualmente.')
    import fitz
    with tempfile.TemporaryDirectory(prefix='ocr_normativo_') as carpeta:
        archivo = Path(carpeta) / 'pagina.png'
        escala = min(2.5, 2000 / max(pagina.rect.width, pagina.rect.height))
        pagina.get_pixmap(matrix=fitz.Matrix(escala, escala), alpha=False).save(str(archivo))
        opciones = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        try:
            resultado = subprocess.run([ejecutable, str(archivo), 'stdout', '-l',
                                        getattr(settings, 'PDF_OCR_IDIOMA', 'spa'), '--psm', '3'],
                                       capture_output=True, text=True, encoding='utf-8',
                                       timeout=90, env={**os.environ, 'OMP_THREAD_LIMIT': '1'}, **opciones)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError(f'No se pudo transcribir la página {numero} con OCR local. Revisa Tesseract.') from exc
    if resultado.returncode != 0 or len(resultado.stdout.strip()) < 15:
        raise ValueError(f'No se obtuvo texto legible de la página {numero}. Verifica la imagen y el idioma del OCR local.')
    return resultado.stdout.strip()
