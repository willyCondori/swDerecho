import re
import unicodedata


def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto or '')
                   if unicodedata.category(c) != 'Mn').lower()


class ContextoTentativaService:
    """Regla conservadora para la tentativa de secuestro expresada en el relato.

    No infiere una calificación jurídica ni cambia las valoraciones manuales.
    La tentativa se vincula al secuestro, no a todos los delitos del caso.
    """

    @staticmethod
    def motivo(articulo, texto):
        texto = normalizar(texto)
        clausulas = re.split(r'[.;!?\n]', texto)
        patrones = (
            r'\b(?:intento|tentativa)\s+(?:de\s+)?secuestro\b',
            r'\b(?:intento|intentaron|intentaba|intentaban|trate|trataron|trato)'
            r'\s+(?:de\s+)?secuestr\w*',
            r'\bno\s+(?:lograron|consiguieron|pudieron)\s+secuestr\w*',
        )
        tentativa = any(
            re.search(patron, clausula)
            and not re.search(r'\b(?:no hubo|sin|descarto|descartaron)\s+'
                              r'(?:un\s+)?(?:intento|tentativa)', clausula)
            and not re.search(r'\bno\s+(?:intentaron|intentaba|intentaban|intento|trataron|trato)\b', clausula)
            for clausula in clausulas for patron in patrones
        )
        if not tentativa:
            return ''
        titulo = normalizar(articulo.titulo)
        encabezado = re.search(r'\(([^)]+)\)', articulo.contenido or '')
        if encabezado:
            titulo += ' ' + normalizar(encabezado.group(1))
        if re.search(r'\bsecuestro\b', titulo):
            if re.search(r'\b(?:procedimiento|objetos|documentos|bienes)\b', titulo):
                return ('Este artículo trata del secuestro de objetos o documentos; '
                        'no acredita su relación con el intento de secuestro de una persona. '
                        'Revisar su pertinencia por separado.')
            return ('El relato menciona un intento de secuestro. Se recomienda revisar '
                    'este artículo junto con las disposiciones sobre tentativa, '
                    'sin asumir que el delito se consumó.')
        if 'trata de personas' in titulo:
            return ('El intento de secuestro mencionado no basta para establecer trata '
                    'de personas. Revisar si existen hechos adicionales que justifiquen '
                    'esta recomendación.')
        return ''
