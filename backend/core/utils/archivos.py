"""
Validación de archivos subidos, más allá de la extensión y el tamaño.
"""

FIRMA_PDF = b"%PDF-"


def validar_pdf(archivo):
    """
    Comprueba que `archivo` (un UploadedFile de Django) sea realmente un
    PDF legible, no solo que se llame ".pdf": la extensión y el tamaño no
    garantizan que el contenido lo sea (un .exe renombrado a informe.pdf
    pasaría esos dos filtros sin problema).

    Dos capas:
      1. Firma: todo PDF empieza con los bytes "%PDF-". Basta con leer los
         primeros 5 bytes, sin abrir ni parsear nada.
      2. Que se pueda abrir con pypdf y tenga al menos una página. La firma
         sola no alcanza: un PDF truncado o corrupto también puede
         empezar con "%PDF-".

    Deja `archivo` reposicionado al inicio (seek(0)) para que el resto del
    flujo lo pueda seguir leyendo con normalidad (guardarlo en disco,
    extraer su texto, etc.), tanto si es válido como si no.

    Devuelve (True, "") si es válido, o (False, "motivo del rechazo") si no.
    """
    archivo.seek(0)
    cabecera = archivo.read(len(FIRMA_PDF))
    archivo.seek(0)

    if cabecera != FIRMA_PDF:
        return False, "El archivo no es un PDF válido (no tiene la firma esperada)."

    try:
        from pypdf import PdfReader
        try:
            num_paginas = len(PdfReader(archivo).pages)
        except Exception:
            return False, "El archivo está dañado o no se pudo leer como PDF."
    finally:
        archivo.seek(0)

    if num_paginas == 0:
        return False, "El PDF no tiene páginas."

    return True, ""
