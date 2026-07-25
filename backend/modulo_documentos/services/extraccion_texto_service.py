from pypdf import PdfReader


class ExtraccionTextoService:
    """
    Extrae el texto plano de un archivo PDF subido. El backend hace
    esta extracción al momento de guardar el documento — el frontend
    nunca envía texto extraído, solo el archivo.
    """

    @staticmethod
    def extraer(archivo) -> str:
        """
        `archivo` es un objeto file-like (ej. request.FILES['archivo_pdf']
        o el campo `archivo` de un Documento ya guardado). Devuelve el
        texto concatenado de todas las páginas.
        """
        archivo.seek(0)
        lector = PdfReader(archivo)
        paginas_texto = []
        for pagina in lector.pages:
            texto_pagina = pagina.extract_text() or ""
            if texto_pagina.strip():
                paginas_texto.append(texto_pagina)
        archivo.seek(0)  # deja el puntero al inicio por si algo más lee el archivo después
        return "\n\n".join(paginas_texto).strip()