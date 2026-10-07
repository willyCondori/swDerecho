"""Localización conservadora de la parte afectada, sobre texto original.

No asumir que una derogación parcial elimina el artículo entero. Cuando
la fuente no da una ubicación inequívoca, exigir identificar el fragmento.
"""
import re

def etiquetas(cita, singular, plural, patron):
    encontrados = []
    for match in re.finditer(r'\b(?:' + singular + '|' + plural + r')\s+(' + patron +
                            r'(?:\s*(?:,|y)\s*' + patron + r')*)', cita, re.I):
        encontrados.extend(re.findall(patron, match.group(1), re.I))
    return list(dict.fromkeys(e.strip('(). ').upper() for e in encontrados))

def seccion(texto, etiqueta, patron):
    marcas = list(re.finditer(r'(?m)^\s*(' + patron + r')\s*[.)\-–:]\s*', texto))
    coincidencias = [i for i, m in enumerate(marcas) if m.group(1).upper() == etiqueta.upper()]
    if len(coincidencias) != 1:
        return None
    i = coincidencias[0]
    fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
    return texto[marcas[i].start():fin].strip()

def fragmento_literal(texto, propuesta):
    if not propuesta or not propuesta.strip(): return None
    patron = r'\s+'.join(re.escape(p) for p in propuesta.split())
    matches = list(re.finditer(patron, texto))
    return matches[0].group() if len(matches) == 1 else None

def cita_del_destino(cita, unidad):
    """Separar destinos de una enumeración sin compartir alcances parciales.

    Si una cláusula no permite asociar el alcance a un único destino,
    conservarla como ambigua para impedir una confirmación automática.
    """
    patron = (r'\bArt[ií]culos?\s+(?P<art>\d+(?:\s+(?:bis|ter|quater|quinquies|sexies|septies))?)\b|'
              r'\bDisposici[oó]n\s+(?P<tipo>Transitoria|Final|Derogatoria|Abrogatoria)'
              r'\s+(?P<ordinal>\w+)\b')
    cita = re.sub(r'\b(Art[ií]culos?)(?=\d)', r'\1 ', cita, flags=re.I)
    cita = re.sub(r'(?<=\d)(?=(?:bis|ter|quater|quinquies|sexies|septies)\b)', ' ', cita, flags=re.I)
    referencias = list(re.finditer(patron, cita, re.I))
    if len(referencias) < 2 or not unidad:
        return cita, False
    prefijos = {'transitoria': 'DT', 'final': 'DF', 'derogatoria': 'DD', 'abrogatoria': 'DA'}
    def destino(m):
        return (m.group('art') or prefijos[m.group('tipo').lower()] + ' ' + m.group('ordinal')).upper()
    matches = [m for m in referencias if destino(m) == unidad.strip().upper()]
    if len(matches) != 1:
        return cita, True
    match = matches[0]
    limites = list(re.finditer(r'[,;]|\n\s*\d+[.)]\s*|(?<!\w)\d+[.)]\s+(?=(?:El|La|Los|Las)\b)', cita, re.I))
    inicio = max([m.end() for m in limites if m.end() <= match.start()] or [0])
    fin = min([m.start() for m in limites if m.start() >= match.end()] or [len(cita)])
    segmento = cita[inicio:fin]
    if len(list(re.finditer(patron, segmento, re.I))) != 1:
        return cita, True
    return segmento, False


def identificar_parte(cita, alcance, articulo=None, operacion='deroga', unidad=''):
    destino = unidad or getattr(articulo, 'numero_articulo', '')
    cita_original = cita
    cita, destino_ambiguo = cita_del_destino(cita, destino)
    if cita != cita_original:
        # El alcance sugerido por IA puede pertenecer a otro destino.
        alcance = ''
    parrafos = etiquetas(cita, r'Par[aá]grafo', r'Par[aá]grafos', r'[IVXLCDM]+(?![A-Za-zÀ-ÿ])')
    incisos = etiquetas(cita, 'inciso', 'incisos', r'[a-z]\)?(?![A-Za-zÀ-ÿ])')
    numerales = etiquetas(cita, 'numeral', 'numerales', r'\d+\)?')
    ultimo = bool(re.search(r'\b[úu]ltimo\s+p[aá]rrafo\b', cita, re.I))
    frase = re.search(r'\b(?:frase|expresi[oó]n)\s+[“«"]([^”»"]+)[”»"]', cita, re.I)
    parcial_indicado = bool(re.search(r'parcial|par[aá]grafo|inciso|numeral|p[aá]rrafo|frase|expresi[oó]n', alcance + ' ' + cita, re.I))
    partes = []
    combinaciones = [(p, i, n) for p in parrafos or [''] for i in incisos or [''] for n in numerales or ['']]
    for paragrafo, inciso, numeral in combinaciones:
        if not any([paragrafo, inciso, numeral, ultimo, frase, parcial_indicado]): continue
        etiquetas_parte = ([f'Parágrafo {paragrafo}'] if paragrafo else []) + ([f'Inciso {inciso.lower()}'] if inciso else []) + ([f'Numeral {numeral}'] if numeral else [])
        descripcion = ', '.join(etiquetas_parte) or ('Último párrafo' if ultimo else ('Frase citada' if frase else alcance or 'Parte por identificar'))
        texto = articulo.contenido if articulo else None
        if texto is not None and paragrafo: texto = seccion(texto, paragrafo, r'[IVXLCDM]+')
        if texto is not None and inciso: texto = seccion(texto, inciso, r'[a-zA-Z]')
        if texto is not None and numeral: texto = seccion(texto, numeral, r'\d+')
        if texto is not None and ultimo:
            bloques = [b.strip() for b in re.split(r'\n\s*\n', texto) if b.strip()]
            # Saltos de línea de PDF no garantizan límites de párrafo.
            texto = bloques[-1] if len(bloques) > 1 else None
        if texto is not None and frase: texto = fragmento_literal(texto, frase.group(1))
        if parcial_indicado and not any([paragrafo, inciso, numeral, ultimo, frase]): texto = None
        partes.append({'descripcion': descripcion, 'paragrafo': paragrafo, 'inciso': inciso.lower(),
            'numeral': numeral, 'fragmento': texto or '', 'localizado': bool(texto),
            'es_nueva_parte': operacion == 'incorpora' and not texto})
    # No inferir cómo se distribuyen varias referencias de distinto nivel.
    ambiguo = sum(bool(v) for v in [parrafos, incisos, numerales]) > 1 and any(len(v) > 1 for v in [parrafos, incisos, numerales])
    if ambiguo or destino_ambiguo:
        for parte in partes: parte.update(fragmento='', localizado=False)
    if destino_ambiguo and parcial_indicado:
        partes = [{'descripcion': 'Alcance parcial por verificar para este destino', 'paragrafo': '',
                   'inciso': '', 'numeral': '', 'fragmento': '', 'localizado': False, 'es_nueva_parte': False}]
    if not partes:
        return {'tipo': 'total', 'descripcion': 'Artículo o disposición completos' if articulo else 'Norma completa',
                'partes': [], 'localizado': bool(articulo) or not parcial_indicado}
    return {'tipo': 'parcial', 'descripcion': '; '.join(p['descripcion'] for p in partes), 'partes': partes,
            'localizado': all(p['localizado'] for p in partes)}
