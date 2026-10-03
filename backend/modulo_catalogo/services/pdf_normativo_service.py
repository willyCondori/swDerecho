import base64
from .ollama_normativo import consultar

OCR = {'type': 'object', 'additionalProperties': False, 'required': ['texto'],
       'properties': {'texto': {'type': 'string'}}}

def leer_pdf(contenido, motor, extractor):
    if motor != 'qwen':
        return extractor(contenido), []
    import fitz
    textos, escaneadas = [], []
    with fitz.open(stream=contenido, filetype='pdf') as documento:
        if documento.is_encrypted:
            raise ValueError('El PDF está protegido. Sube una copia legible.')
        for numero, pagina in enumerate(documento):
            texto = pagina.get_text(sort=True).strip()
            if len(texto) < 35:
                # Página aislada, sin cargar todas las imágenes en RAM.
                escala = min(1.8, 1200 / max(pagina.rect.width, pagina.rect.height))
                pixmap = pagina.get_pixmap(matrix=fitz.Matrix(escala, escala), alpha=False)
                imagen = base64.b64encode(pixmap.tobytes('png')).decode()
                texto = consultar('Transcribe literalmente esta página jurídica en español. '
                    'Respeta artículos, encabezados y saltos de línea. No resumas, no completes '
                    'contenido cortado. Si no es legible escribe [ILEGIBLE].',
                    'Transcripción de la página del PDF.', OCR, [imagen])['texto']
                if '[ILEGIBLE]' in texto.upper():
                    raise ValueError(f'La página {numero + 1} no es legible. Revisa el PDF.')
                escaneadas.append(numero + 1)
            textos.append(texto)
    avisos = [f'Se transcribieron páginas escaneadas con Qwen: {escaneadas}. Contrasta el texto con el PDF original.'] if escaneadas else []
    return '\n'.join(textos), avisos
