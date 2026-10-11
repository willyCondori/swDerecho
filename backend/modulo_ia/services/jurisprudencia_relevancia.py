"""Reglas explicables de recuperación; no determinan aplicabilidad jurídica."""
import re
from .contexto_tentativa_service import normalizar

DELITOS = {
    'Robo': r'\b(?:robo|robar\w*|robaron|robado|asalt\w*|apoder\w*)\b',
    'Hurto': r'\b(?:hurto|hurtar\w*)\b',
    'Secuestro de personas': r'\bsecuestr\w*\b',
    'Homicidio': r'\b(?:homicidio|asesinat\w*|matar\w*|mataron)\b',
    'Lesiones': r'\b(?:lesion\w*|herida\w*|golpe\w*|fractur\w*)\b',
    'Violencia sexual': r'\b(?:violacion|violo|abuso sexual|agresion sexual|estupro)\b',
    'Estafa': r'\b(?:estafa\w*|defraud\w*|fraude)\b',
    'Amenazas': r'\b(?:amenaz\w*|coaccion\w*)\b',
    'Trata de personas': r'\btrata de personas\b',
}
FIGURAS = {
    'Tentativa': r'\b(?:tentativa|intento|intentaron|intentar\w*|desistimiento|consum\w*)\b',
    'Legítima defensa': r'\b(?:legitima defensa|defensa propia)\b',
    'Complicidad': r'\b(?:complic\w*|complice\w*)\b',
    'Coautoría': r'\b(?:coautori\w*|coautor\w*|actuaron conjuntamente)\b',
}
CRITERIO = r'\b(?:examin\w*|considerando|doctrina|fundament\w*|conclu\w*|establec\w*|previsto|conforme|corresponde|inaplicable|configur\w*|valoracion|elementos|tipicidad)\b'


def secuestro_personas(texto):
    for m in re.finditer(r'\bsecuestr\w*\b', texto):
        alrededor = texto[max(0, m.start()-120):m.end()+120]
        if re.search(r'\b(?:victimas?|personas?|menor(?:es)?|ninos?|ninas?|rehen|rescate|cautiverio)\b|tentativa de secuestro|delitos? de secuestro', alrededor):
            objetos = r'(?:objetos?|dinero|dolares|bolivianos|efectivo|divisas|vehiculos?|motos?|hoja|coca|bienes|documentos?|telefonos?|celulares?|sustancias)'
            if not re.search(r'secuestr\w*\s+(?:de |del |de la |de las |de los )?' + objetos
                             + '|' + objetos + r'(?:\s+americanos)?[\s,;:]+secuestr\w*', alrededor):
                return True
    return False


def robo_relacionado(texto):
    for coincidencia in re.finditer(DELITOS['Robo'], texto):
        # «Ser asaltada» como amenaza futura no acredita un relato de asalto.
        # Conservar referencias expresas a robo y sus elementos; descartar el
        # sinónimo aislado cuando depende de una condición o posibilidad.
        if coincidencia.group().startswith('asalt'):
            antes = texto[max(0, coincidencia.start()-160):coincidencia.start()]
            antes = re.split(r'[.!?;]\s+', antes)[-1]
            eventual = re.search(r'\b(?:podria\w*|podra\w*|amenaz\w*|temor|miedo|posibilidad|riesgo)\b.{0,120}$', antes)
            realizado = re.search(r'\b(?:fue|fueron|fui|habia sido|habian sido)\s+(?:\w+\s+){0,2}$', antes)
            eventual_asalto = re.fullmatch(r'asaltad[oa]s?|asaltar(?:le|les|lo|la|los|las|me|nos)?', coincidencia.group())
            if eventual and eventual_asalto and not realizado:
                continue
        return True
    return False


def fragmento_sustantivo(contenido):
    # Si el segmento incluye carátula y fundamento, mostrar desde el fundamento.
    inicio = re.search(r'\bCONSIDERANDO\s*:', contenido, re.I)
    if inicio and re.search(r'SALA PENAL|AUTO SUPREMO|PARTES:', contenido[:inicio.start()], re.I):
        return contenido[inicio.start():].strip()
    return contenido


def contexto_busqueda(texto):
    texto = normalizar(texto)
    grupos = {k: v for k, v in DELITOS.items() if re.search(v, texto)}
    # Un relato abreviado de secuestro se refiere a personas, salvo objeto expreso.
    if 'Secuestro de personas' in grupos and re.search(r'secuestro de (?:objetos|bienes|documentos|vehiculos)', texto):
        grupos.pop('Secuestro de personas')
    figuras = {k: v for k, v in FIGURAS.items() if re.search(v, texto)}
    if 'Tentativa' in figuras and not re.search(r'\b(?:tentativa|intento|intentaron|intentar\w*|desistimiento)\b|no (?:se )?consum\w*', texto):
        figuras.pop('Tentativa')  # Consumación afirmada no es tentativa.
    return grupos, figuras


def patron_sql(grupos, figuras):
    patron = '|'.join([*grupos.values(), *figuras.values()]) or r'(?!)'
    # PostgreSQL usa límites de palabra distintos a Python.
    patron = patron.replace(r'\b', r'\y').replace(r'\w', '[[:alnum:]_]')
    for vocal, opciones in [('a', '[aá]'), ('e', '[eé]'), ('i', '[ií]'), ('o', '[oó]'), ('u', '[uú]')]:
        # Solo los literales, preservando las clases POSIX del patrón.
        partes = re.split(r'(\[.*?\])', patron)
        patron = ''.join(p if p.startswith('[') else p.replace(vocal, opciones) for p in partes)
    return patron


def evaluar_fragmento(contenido, score, grupos, figuras, umbral_fuerte, umbral_recomendacion):
    texto = normalizar(contenido)
    if len(texto.split()) < 15 or not re.search(CRITERIO, texto):
        return None  # No publicar únicamente encabezados o carátulas.
    if texto.lstrip().startswith('vistos:') and not re.search(r'\b(?:doctrina|conclu\w*|establec\w*|corresponde|inaplicable|configur\w*|tipicidad)\b', texto):
        return None  # La presentación del recurso no explica el criterio jurídico.
    coincidencias = [k for k, p in grupos.items() if re.search(p, texto)
                     and (k != 'Secuestro de personas' or secuestro_personas(texto))
                     and (k != 'Robo' or robo_relacionado(texto))]
    # Incluso una similitud vectorial alta necesita una relación identificable
    # con los delitos detectados. La fundamentación procesal genérica no basta.
    if grupos and not coincidencias:
        return None
    # La mera incautación no sostiene una coincidencia sobre secuestro de personas.
    if 'Secuestro de personas' in grupos and re.search(r'\bsecuestr\w*\b', texto) and not coincidencias:
        return None
    figuras_coincidentes = [k for k, p in figuras.items() if re.search(p, texto)]
    if 'Tentativa' in figuras_coincidentes and 'Secuestro de personas' in grupos:
        if not re.search(r'tentativa de secuestro|secuestr\w*.{0,160}(?:tentativa|consum\w*|desistimiento)|(?:tentativa|consum\w*|desistimiento).{0,160}secuestr\w*', texto, re.S):
            figuras_coincidentes.remove('Tentativa')
    if score < umbral_fuerte and (score < umbral_recomendacion or not coincidencias):
        return None
    score_terminos = len(coincidencias) / max(1, len(grupos))
    score_figuras = len(figuras_coincidentes) / max(1, len(figuras))
    hibrido = .75 * score + .20 * score_terminos + .05 * score_figuras
    recomendacion = score < umbral_fuerte or ('Tentativa' in figuras and 'Secuestro de personas' in coincidencias)
    motivo = ('Coincidencia de menor confianza; revisar su pertinencia.' if score < umbral_fuerte
              else 'Coincidencia semántica con contenido sustantivo para revisión.')
    if 'Tentativa' in figuras and 'Secuestro de personas' in coincidencias:
        motivo += ' El caso menciona tentativa; la resolución puede abordar consumación o desistimiento.'
    return hibrido, recomendacion, coincidencias + figuras_coincidentes, motivo


TERMINOS_BUSQUEDA = {
    'Robo': ['robo', 'robar', 'asaltar', 'asalto', 'apoderar'],
    'Hurto': ['hurto', 'hurtar'],
    'Secuestro de personas': ['secuestro', 'secuestrar'],
    'Homicidio': ['homicidio', 'asesinato', 'matar'],
    'Lesiones': ['lesion', 'herida', 'golpe', 'fractura'],
    'Violencia sexual': ['violacion', 'violar', 'abuso', 'estupro'],
    'Estafa': ['estafa', 'defraudar', 'fraude'],
    'Amenazas': ['amenaza', 'coaccion'],
    'Trata de personas': ['trata'],
    'Tentativa': ['tentativa', 'intento', 'intentar', 'desistimiento'],
    'Legítima defensa': ['legitima', 'defensa'],
    'Complicidad': ['complicidad', 'complice'],
    'Coautoría': ['coautoria', 'coautor'],
}

def consulta_lexica(grupos, figuras):
    # Términos controlados del catálogo; nunca SQL ni texto libre del usuario.
    terminos = {termino for grupo in [*grupos, *figuras]
                for termino in TERMINOS_BUSQUEDA.get(grupo, [])}
    return ' | '.join(sorted(terminos))
