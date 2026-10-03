"""Reconoce unidades con IA y las reconstruye desde offsets del texto fuente."""
import re
import unicodedata

from django.conf import settings
from .ollama_normativo import consultar, RespuestaIncompleta

TIPOS = ['articulo', 'transitoria', 'final', 'derogatoria', 'abrogatoria', 'adicional']
ORDINALES = r'PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA|SEXTA|S[EÉ]PTIMA|OCTAVA|NOVENA|D[EÉ]CIMA|[UÚ]NICA'
SECCION = re.compile(r'^\s*DISPOSICI[OÓ]N(?:ES)?\s+(TRANSITORIA|FINAL|DEROGATORIA|ABROGATORIA|ADICIONAL)(?:S|ES)?\b', re.I)
ORDINAL = re.compile(r'^\s*(' + ORDINALES + r')\s*(?:[.\-–:(]|$)', re.I)
ARTICULO = re.compile(r'^\s*(?:ART[IÍ]CULO|ART\.)\s+([UÚ]NICO|\d+(?:\s*(?:bis|ter|quater|quinquies|sexies|septies))?)\s*(?:[°º.\-–:(]|$)', re.I)
ESTRUCTURA = {'type': 'object', 'additionalProperties': False, 'required': ['unidades'], 'properties': {
    'unidades': {'type': 'array', 'maxItems': 24, 'items': {'type': 'object', 'additionalProperties': False,
        'required': ['linea', 'tipo', 'numero'], 'properties': {
            'linea': {'type': 'integer', 'minimum': 0}, 'tipo': {'enum': TIPOS},
            'numero': {'type': 'string', 'maxLength': 35}}}}}}


def normalizar(texto):
    return ' '.join(unicodedata.normalize('NFKC', texto).split())


def bloques_lineas(lineas, limite=2400):
    bloque, largo = [], 0
    for numero, linea in enumerate(lineas):
        # El modelo solo localiza cabeceras: una línea muy larga se representa
        # por su comienzo. El cuerpo íntegro se conserva fuera del prompt.
        entrada = f'{numero}: {linea[:550]}'
        if bloque and largo + len(entrada) > limite:
            yield '\n'.join(bloque)
            bloque, largo = [], 0
        bloque.append(entrada)
        largo += len(entrada) + 1
    if bloque:
        yield '\n'.join(bloque)


def consultar_fragmentado(instruccion, texto, esquema, campo, profundidad=0):
    """Reintentar únicamente truncamientos, conservando índices y evidencia.

    No ampliar el contexto ni la memoria del servidor; cada reintento es
    serial y descarta por completo la respuesta incompleta anterior.
    """
    try:
        return consultar(instruccion, texto, esquema)[campo]
    except RespuestaIncompleta:
        if profundidad >= 3 or len(texto) < 600:
            raise RespuestaIncompleta('Qwen no logró completar este fragmento después de dividirlo. '
                                     'La revisión no se guardó; vuelve a intentarlo.')
        mitad = len(texto) // 2
        patron_corte = r'\n' if campo == 'unidades' else r'\n|[.;]\s+'
        limites = [m.end() for m in re.finditer(patron_corte, texto)
                   if len(texto) // 4 <= m.end() <= 3 * len(texto) // 4]
        if not limites:
            # No cortar palabras o una línea de estructura por la mitad.
            raise RespuestaIncompleta('Qwen no completó una línea indivisible. La revisión no se guardó.')
        corte = min(limites, key=lambda pos: abs(pos - mitad))
        resultados = []
        for fragmento in (texto[:corte], texto[corte:]):
            resultados.extend(consultar_fragmentado(instruccion, fragmento, esquema, campo, profundidad + 1))
        return resultados


def destinos_sustituidos(prefijo):
    cabecera = ARTICULO.match(prefijo)
    if cabecera: prefijo = prefijo[cabecera.end():]
    prefijo = re.sub(r'(?m)^\s*\d+[.)]\s*(?=(?:El|La|Los|Las)\b)', '', prefijo, flags=re.I)
    numero = r'\d+(?:\s+(?:bis|ter|quater|quinquies|sexies|septies))?'
    patron_lista = numero + r'(?:\s*(?:,\s*(?:y\s+)?|y\s+)(?:Art[ií]culos?\s+)?' + numero + r')*'
    numeros = set()
    for referencia in re.finditer(r'\bArt[ií]culos?\s+', prefijo, re.I):
        lista = re.match(patron_lista, prefijo[referencia.end():], re.I)
        if lista:
            numeros.update(normalizar(m).upper() for m in re.findall(numero, lista.group(), re.I))
    return numeros


def localizar_clasico(lineas, excluidas=None):
    unidades, seccion, comillas = [], 'articulo', 0
    objetivos, inicio_actual = set(), 0
    for i, linea in enumerate(lineas):
        art = ARTICULO.match(linea)
        if art and objetivos:
            if normalizar(art.group(1)).upper() in objetivos:
                if excluidas is not None: excluidas.add(i)
                continue
            # Un artículo principal distinto termina la sustitución incluso
            # si el PDF omite la comilla de cierre (Ley 1636, artículo 5).
            objetivos, comillas = set(), 0
        if art and not comillas: inicio_actual = i
        if re.search(r'siguiente(?:s)?\s+texto(?:s)?\s*:', linea, re.I):
            objetivos = destinos_sustituidos('\n'.join(lineas[inicio_actual:i + 1]))
        citada = comillas > 0 or linea.lstrip().startswith(('“', '«', '"'))
        comillas = max(0, comillas + linea.count('“') + linea.count('«') - linea.count('”') - linea.count('»'))
        if citada:
            if excluidas is not None: excluidas.add(i)
            continue
        cabecera = SECCION.match(linea)
        if cabecera:
            seccion = cabecera.group(1).lower()
            if seccion == 'transitoria': seccion = 'transitoria'
            if seccion == 'final': seccion = 'final'
            inline = ORDINAL.match(linea[cabecera.end():])
            if inline:
                unidades.append({'linea': i, 'tipo': seccion, 'numero': inline.group(1)})
            continue
        art = ARTICULO.match(linea)
        ordinal = ORDINAL.match(linea) if seccion != 'articulo' else None
        if art:
            unidades.append({'linea': i, 'tipo': 'articulo', 'numero': art.group(1)})
            inicio_actual = i
        elif ordinal:
            unidades.append({'linea': i, 'tipo': seccion, 'numero': ordinal.group(1)})
    return unidades


def extraer_unidades(texto, motor=None, advertencias=None, progreso=None):
    from .carga_pdf_service import dividir_por_articulos, extraer_titulo_articulo as extraer_titulo
    motor = motor or settings.LECTURA_NORMATIVA_MOTOR
    lineas = texto.splitlines()
    if motor == 'qwen':
        unidades = []
        for i, bloque in enumerate(bloques_lineas(lineas)):
            if progreso: progreso({'paso': f'Identificando unidades del PDF, bloque {i + 1}'})
            unidades.extend(consultar_fragmentado(
                'Localiza inicios de artículos y disposiciones de la norma PRINCIPAL. '
                'Los números antes de : son índices de línea globales. '
                'No incluyas referencias, índices ni artículos dentro de citas de modificaciones. '
                'PRIMERA transitoria y PRIMERA final son unidades diferentes. '
                'ARTÍCULO ÚNICO es un artículo. Devuelve el número literal, sin prefijos.',
                bloque, ESTRUCTURA, 'unidades'))
        # Los índices numéricos no son fiables en modelos pequeños. Las
        # cabeceras literales verificables completan el mapa sin generar texto.
        excluidas = set()
        conocidos = localizar_clasico(lineas, excluidas)
        mapa = {u['linea']: u for u in conocidos}
        corregidas = 0
        for u in unidades:
            pos = u['linea']
            if pos in mapa:
                if u != mapa[pos]: corregidas += 1
                continue
            numero = re.sub(r'^(?:ART[IÍ]CULO|ART\.)\s*', '', u['numero'], flags=re.I).strip()
            if not 0 <= pos < len(lineas) or pos in excluidas or SECCION.match(lineas[pos]):
                corregidas += 1
                continue
            # Un inicio adicional tiene que ser una cabecera literal, no
            # una referencia del cuerpo ni una cifra encontrada más adelante.
            if lineas[pos].lstrip().startswith(('“', '«', '"')):
                corregidas += 1
                continue
            anteriores = '\n'.join(lineas[:pos])
            if anteriores.count('“') + anteriores.count('«') > anteriores.count('”') + anteriores.count('»'):
                corregidas += 1
                continue
            if u['tipo'] != 'articulo':
                encabezado = next((SECCION.match(l) for l in reversed(lineas[:pos]) if SECCION.match(l)), None)
                if not encabezado or encabezado.group(1).lower() != u['tipo']:
                    corregidas += 1
                    continue
            elif not ARTICULO.match(lineas[pos]) and not re.match(r'^\s*\d+\s*[.:-]\s*\(', lineas[pos]):
                # Una definición numerada del cuerpo no es un artículo.
                corregidas += 1
                continue
            if u['tipo'] != 'articulo' and numero.isdigit():
                seccion_inicio = max((i for i, l in enumerate(lineas[:pos]) if SECCION.match(l)), default=-1)
                if any(v['tipo'] != 'articulo' and not v['numero'].isdigit() and seccion_inicio < v['linea'] < pos for v in conocidos):
                    corregidas += 1
                    continue
            linea = normalizar(lineas[pos])
            patron = r'^(?:(?:ART[IÍ]CULO|ART\.)\s+)?' + re.escape(numero) + r'(?:[.\s:()°º–-]|$)'
            if not numero or not re.match(patron, linea, re.I):
                corregidas += 1
                continue
            mapa[pos] = {**u, 'numero': numero}
        faltantes = [u for u in conocidos if not any(v['linea'] == u['linea'] and v['tipo'] == u['tipo'] for v in unidades)]
        if advertencias is not None and (faltantes or corregidas):
            advertencias.append('Se completó la estructura usando cabeceras literales del PDF. Verifica la lista de unidades y su texto antes de confirmar.')
        unidades = list(mapa.values())
    elif motor == 'clasico':
        articulos = dividir_por_articulos(texto)
        unidades = [u for u in localizar_clasico(lineas) if u['tipo'] != 'articulo'
                    or u['numero'].upper() in ['ÚNICO', 'UNICO']]
        if not unidades:
            return articulos
        # Mezclar solo las disposiciones con los artículos del extractor anterior.
        return articulos + reconstruir(unidades, lineas, extraer_titulo)
    else:
        raise ValueError('Motor de lectura inválido.')
    return reconstruir(unidades, lineas, extraer_titulo)


def reconstruir(unidades, lineas, extraer_titulo):
    unidades = sorted(unidades, key=lambda u: u['linea'])
    resultados, numeros, posiciones = [], set(), set()
    prefijos = {'transitoria': 'DT', 'final': 'DF', 'derogatoria': 'DD', 'abrogatoria': 'DA', 'adicional': 'DAD'}
    for i, unidad in enumerate(unidades):
        pos = unidad['linea']
        numero = unidad['numero'].strip()
        if not 0 <= pos < len(lineas) or pos in posiciones or not numero:
            raise ValueError('Qwen devolvió una ubicación duplicada o inexistente.')
        # Validar la identidad contra la cabecera, no contra cualquier cifra del cuerpo.
        cabecera = normalizar(lineas[pos]).upper()
        if not re.search(r'(?<!\w)' + re.escape(normalizar(numero).upper()) + r'(?!\w)', cabecera):
            raise ValueError('El número extraído no coincide con la cabecera original.')
        posiciones.add(pos)
        clave = (f"{prefijos[unidad['tipo']]} {numero.upper()}"
                 if unidad['tipo'] != 'articulo' else numero)
        if clave.casefold() in numeros:
            raise ValueError('El documento contiene unidades repetidas; separa las normas de la compilación.')
        numeros.add(clave.casefold())
        fin = unidades[i + 1]['linea'] if i + 1 < len(unidades) else len(lineas)
        cuerpo = '\n'.join(lineas[pos:fin])
        primera, separador, resto = cuerpo.partition('\n')
        resto = re.split(r'(?im)^\s*(?:DISPOSICI[OÓ]N(?:ES)?\s+|Rem[íi]tase\s+|Por\s+tanto,?\s+la\s+promulgo)', resto)[0]
        cuerpo = (primera + separador + resto).strip()
        resultados.append({'numero': clave, 'tipo_unidad': unidad['tipo'],
                           'titulo': extraer_titulo(numero, cuerpo) if unidad['tipo'] == 'articulo' else lineas[pos].strip()[:500],
                           'texto': cuerpo})
    return resultados


CAMBIOS = {'type': 'object', 'additionalProperties': False, 'required': ['cambios'], 'properties': {
    'cambios': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
        'required': ['operacion', 'norma', 'unidad', 'alcance', 'cita', 'origen', 'causante', 'fecha_causante'],
        'properties': {
            'operacion': {'enum': ['abroga', 'deroga', 'modifica', 'incorpora', 'general', 'temporal']},
            'norma': {'type': 'string', 'maxLength': 200},
            'unidad': {'type': 'string', 'maxLength': 50},
            'alcance': {'type': 'string', 'maxLength': 150},
            'cita': {'type': 'string', 'minLength': 10},
            'origen': {'enum': ['clausula', 'nota_editorial']},
            'causante': {'type': 'string', 'maxLength': 200},
            'fecha_causante': {'type': 'string', 'description': 'YYYY-MM-DD o vacío; solo fechas expresas'}
        }}}}}


def bloques_efectos(texto, limite=1800):
    if len(texto) <= limite:
        return [texto]
    partes, inicio = [], 0
    while inicio < len(texto):
        fin = min(inicio + limite, len(texto))
        if fin < len(texto):
            corte = max(texto.rfind('\n', inicio + limite // 2, fin),
                        texto.rfind('. ', inicio + limite // 2, fin))
            if corte > inicio: fin = corte + 1
        partes.append(texto[inicio:fin])
        if fin == len(texto): break
        # Un pequeño solapamiento mantiene referencias de una cláusula
        # partida. Cada cita se verifica contra el fragmento de origen.
        inicio = max(inicio + 1, fin - 600)
    return partes


def detectar_cambios(unidades, progreso=None):
    cambios = []
    for i, u in enumerate(unidades):
        if progreso: progreso({'paso': f'Analizando efectos normativos: {i + 1}/{len(unidades)}'})
        if not re.search(r'\b(?:abrog(?:a(?:da|do|das|dos|n)?|ar|aci[oó]n)|derog(?:a(?:da|do|das|dos|n)?|ar|aci[oó]n)|'
                         r'modific(?:a(?:da|do|das|dos|n)?|ar)|incorpor(?:a(?:da|do|das|dos|n)?|ar)|'
                         r'sustituy\w*|vigencia|publicaci[oó]n|plazos?)\b', texto_operativo(u['texto']), re.I):
            continue
        # Evitar truncamiento silencioso de cláusulas que exceden el contexto.
        partes = bloques_efectos(texto_operativo(u['texto']))
        for parte in partes:
            import copy
            esquema = copy.deepcopy(CAMBIOS)
            # La cita se añade desde el original. Hacerla generar una vez por
            # destino agotaba la respuesta en listas de reformas/derogaciones.
            del esquema['properties']['cambios']['items']['properties']['cita']
            esquema['properties']['cambios']['items']['required'].remove('cita')
            datos = consultar_fragmentado(
                'Extrae todos los efectos normativos EXPRESOS. No interpretes incompatibilidades. '
                'Todas las disposiciones contrarias = general, norma y unidad vacías. '
                'Abrogación completa = norma afectada, unidad vacía, alcance total. '
                'Derogación parcial = párrafo/inciso afectado, nunca todo el artículo. '
                'Plazos y reglas de vigencia = temporal; vencimiento no significa derogación. '
                'DEROGADO por Ley X en una cabecera = nota_editorial: causante Ley X y unidad afectada la actual. '
                'Para esa nota, norma vacía significa la norma del documento. '
                'Para cláusulas, causante y fecha_causante vacíos; provienen de los metadatos de la fuente. '
                'Devuelve solo los campos del esquema. La cita la adjunta el sistema desde el original. '
                'Cada artículo de una lista recibe su propio registro. '
                'Unidad destino: número de artículo sin prefijo o DT TERCERA / DF TERCERA.',
                f"Unidad actual: {u['numero']}\n{parte}", esquema, 'cambios')
            for c in datos:
                c = {**c, 'cita': c.get('cita', parte)}
                prefijo = f"Unidad actual: {u['numero']}\n"
                if c['cita'].startswith(prefijo):
                    c['cita'] = c['cita'][len(prefijo):]
                if normalizar(c['cita']) not in normalizar(parte):
                    raise ValueError('La evidencia del cambio no coincide con el texto fuente.')
                c = ajustar_cambio_literal(c, u)
                verbos = {'abroga': r'abrog', 'deroga': r'derog', 'modifica': r'modific|sustit',
                          'incorpora': r'incorpor|a[nñ]ad', 'general': r'contrari', 'temporal': r'vigencia|publicaci[oó]n|plazo'}
                if not re.search(verbos[c['operacion']], c['cita'], re.I):
                    raise ValueError('La operación extraída carece de evidencia literal.')
                for destino in completar_destinos_literales(c, u):
                    destino['unidad_fuente'] = u['numero']
                    cambios.append(destino)
    vistos = set()
    unicos = []
    import json
    for cambio in cambios:
        identidad = json.dumps(cambio, sort_keys=True, ensure_ascii=False)
        if identidad not in vistos:
            unicos.append(cambio); vistos.add(identidad)
    return unicos



METADATOS = {'type': 'object', 'additionalProperties': False,
    'required': ['tipo_norma', 'numero_norma', 'fecha_norma'], 'properties': {
    'tipo_norma': {'type': 'string', 'maxLength': 80},
    'numero_norma': {'type': 'string', 'maxLength': 50},
    'fecha_norma': {'type': 'string'},
    }}

def extraer_metadatos(texto):
    from .vigencia_service import fecha
    datos = consultar('Identifica la norma PRINCIPAL del documento: tipo (Ley, Decreto Supremo, etc.), '
        'número legal y fecha de promulgación YYYY-MM-DD. No uses normas citadas, fechas de modificaciones '
        'ni fechas editoriales. Si no es inequívoco devuelve vacío en ese campo.',
        texto[:2000] + '\n[FINAL DEL DOCUMENTO]\n' + texto[-2200:], METADATOS)
    if datos['fecha_norma'] and not fecha(datos['fecha_norma']):
        raise ValueError('La fecha identificada por Qwen no es válida.')
    if datos['numero_norma'] and not re.search(r'(?<!\w)' + re.escape(datos['numero_norma']) + r'(?!\w)', texto[:2000]):
        raise ValueError('La identidad de la norma no está respaldada por su encabezado.')
    datos['numero_norma'] = re.sub(r'^N(?:[°ºoO.]|ro\.)?\s*', '', datos['numero_norma'], flags=re.I).strip()
    return {k: v for k, v in datos.items() if v}



def fecha_literal(texto):
    from .vigencia_service import fecha
    iso = re.search(r'\b\d{4}-\d{2}-\d{2}\b', texto)
    if iso and fecha(iso.group()): return iso.group()
    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
             'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    dato = re.search(r'\b(\d{1,2})\s+de\s+(' + '|'.join(meses) + r')\s+(?:de|del)\s+(\d{4})\b', texto, re.I)
    if dato:
        valor = f'{dato.group(3)}-{meses.index(dato.group(2).lower())+1:02d}-{int(dato.group(1)):02d}'
        if fecha(valor): return valor
    return ''

def identidades_literales(texto):
    return list(dict.fromkeys(' '.join(m) for m in re.findall(
        r'\b(Decreto\s+Ley|Decreto\s+Supremo|Decreto\s+Presidencial|Resoluci[oó]n\s+Suprema|'
        r'Resoluci[oó]n\s+Ministerial|Ley)\s+(?:N(?:[°ºoO.]|ro\.)?\s*)?(\d+)\b', texto, re.I)))

def ajustar_cambio_literal(cambio, unidad):
    """Corregir salidas del 2B solo cuando una cláusula literal lo permite.

    El destino y el efecto jurídico siguen pendientes. Nunca inferir una
    incompatibilidad ni tomar una mención a una norma como derogación.
    """
    c = dict(cambio)
    cita = c['cita']
    numero_propio = re.sub(r'^(?:DT|DF|DD|DA|DAD)\s+', '', unidad['numero'])
    nota = re.match(r'^\s*(?:(?:ART[IÍ]CULO|ART\.)\s+)?' + re.escape(numero_propio) +
                    r'\s*[°º.\-–:]*\s*\(?\s*(DEROGAD[OA]|ABROGAD[OA])\b', unidad['texto'], re.I)
    # Las notas solo califican como tales si están en la cabecera propia.
    if nota and re.search(r'\bpor\b', unidad['texto'][:350], re.I):
        c.update(origen='nota_editorial', norma='', unidad=unidad['numero'], alcance='total',
                 operacion='deroga' if nota.group(1).upper().startswith('DEROG') else 'abroga')
        identidades = identidades_literales(cita)
        c['causante'] = identidades[0] if len(identidades) == 1 else c['causante']
        c['fecha_causante'] = fecha_literal(cita)
    elif re.search(r'todas\s+las\s+disposiciones\s+contrarias', cita, re.I):
        c.update(operacion='general', norma='', unidad='', alcance='indeterminado', origen='clausula', causante='', fecha_causante='')
    else:
        # La nota editorial exige una cabecera literal, nunca la etiqueta de IA.
        c.update(origen='clausula', causante='', fecha_causante='')
        # Verbo expreso de afectación, separado de palabras como
        # «modificaciones» que forman parte del objeto de la abrogación.
        operaciones = []
        for op, patron in [('abroga', r'\babrog(?:a(?:da|do|das|dos|n)?|ar|aci[oó]n)\b'),
                            ('deroga', r'\bderog(?:a(?:da|do|das|dos|n)?|ar|aci[oó]n)\b'),
                            ('modifica', r'\b(?:modific(?:a(?:da|do|das|dos|n)?|ar)|sustituy\w*)\b'),
                            ('incorpora', r'\b(?:incorpor(?:a(?:da|do|das|dos|n)?|ar)|a[nñ]ade\w*)\b')]:
            if re.search(patron, cita, re.I): operaciones.append(op)
        if len(operaciones) == 1: c['operacion'] = operaciones[0]
        if not operaciones and re.search(r'vigencia|publicaci[oó]n|plazo', cita, re.I):
            c.update(operacion='temporal', norma='', unidad='', alcance='Regla de vigencia o plazo; no implica derogación', origen='clausula')
        if c['origen'] == 'clausula':
            c.update(causante='', fecha_causante='')
            objetivo = cita_sin_cabecera(cita)
            objetivo = re.split(r'\bmodificad[ao]\s+por\b', objetivo, maxsplit=1, flags=re.I)[0]
            identidades = identidades_literales(objetivo)
            codigos = list(dict.fromkeys('Código de Procedimiento Penal' if 'procedimiento' in m.lower() else 'Código Penal' for m in re.findall(
                r'\bC[oó]digo\s+(?:de\s+Procedimiento\s+)?Penal\b', objetivo, re.I)))
            if len(identidades) == 1 and c['operacion'] in ['abroga', 'deroga', 'modifica', 'incorpora']:
                c['norma'] = identidades[0]
            if len(codigos) == 1 and len(identidades) <= 1 and c['operacion'] in ['abroga', 'deroga', 'modifica', 'incorpora']:
                c['norma'] = 'Código de Procedimiento Penal' if 'procedimiento' in codigos[0].lower() else 'Código Penal'
            articulos = list(dict.fromkeys(re.findall(r'\bArt[ií]culo\s+(\d+(?:\s+(?:bis|ter|quater|quinquies|sexies|septies))?)\b', objetivo, re.I)))
            if len(articulos) == 1 and c['operacion'] in ['deroga', 'modifica', 'incorpora']:
                c['unidad'] = articulos[0]
            if c['operacion'] == 'abroga' and not articulos:
                c.update(unidad='', alcance='total')
    if c['operacion'] in ['deroga', 'modifica', 'incorpora']:
        from .alcance_normativo_service import identificar_parte
        parte = identificar_parte(cita, '', None, c['operacion'], c['unidad'])
        if parte['tipo'] == 'parcial': c['alcance'] = parte['descripcion']
        elif c['unidad']: c['alcance'] = 'total'
    return c



def cita_sin_cabecera(cita):
    cabecera = ARTICULO.match(cita)
    return cita[cabecera.end():] if cabecera else cita


def completar_destinos_literales(cambio, unidad):
    """Expandir listas expresas de un mismo destino normativo, sin inferir.

    El 2B puede devolver el número de la unidad fuente o solo el primer
    artículo de una lista. Las referencias del texto operativo lo corrigen.
    Una lista con varias normas conserva la revisión individual pendiente.
    """
    if cambio['origen'] != 'clausula' or cambio['operacion'] not in ['deroga', 'modifica', 'incorpora']:
        return [cambio]
    cita = cambio['cita']
    operaciones = [patron for patron in [r'\babrog(?:a(?:da|do|das|dos|n)?|ar)\b',
        r'\bderog(?:a(?:da|do|das|dos|n)?|ar)\b',
        r'\b(?:modific(?:a(?:da|do|das|dos|n)?|ar)|sustituy\w*)\b',
        r'\b(?:incorpor(?:a(?:da|do|das|dos|n)?|ar)|a[nñ]ade\w*)\b'] if re.search(patron, cita, re.I)]
    if len(operaciones) != 1:
        return [cambio]
    objetivo = re.split(r'\bmodificad[ao]\s+por\b', cita_sin_cabecera(cita), maxsplit=1, flags=re.I)[0]
    if len(identidades_literales(objetivo)) > 1:
        return [cambio]
    destinos = destinos_sustituidos(objetivo)
    if not destinos:
        return [cambio]
    from .alcance_normativo_service import identificar_parte
    resultado = []
    for numero in sorted(destinos):
        c = {**cambio, 'unidad': numero}
        parte = identificar_parte(cita, '', None, c['operacion'], numero)
        c['alcance'] = parte['descripcion'] if parte['tipo'] == 'parcial' else 'total'
        resultado.append(c)
    return resultado


def texto_operativo(texto):
    # En una reforma, «con el siguiente texto» introduce el contenido
    # sustitutivo citado. Las referencias dentro de ese contenido no son
    # otros destinos de la modificación de la norma principal.
    introduccion = re.search(r'(?:con\s+)?(?:el|los|la|las)\s+siguiente(?:s)?\s+(?:texto(?:s)?|redacci[oó]n)\s*:', texto, re.I)
    if not introduccion: return texto
    apertura = re.search(r'[“«"]', texto[introduccion.end():])
    if not apertura: return texto
    inicio = introduccion.end() + apertura.start()
    antes = texto[:inicio].rstrip()
    # Solo reducir la cita cuando existe una instrucción de reforma.
    if not re.search(r'\b(?:incorporan?|modifican?|sustituy(?:e|en))\b', antes, re.I): return texto
    caracter = texto[inicio]
    cierre = {'“': '”', '«': '»', '"': '"'}[caracter]
    final = texto.rfind(cierre, inicio + 1)
    if final < 0: return antes
    despues = texto[final + 1:].strip()
    return antes + ('\n' + despues if despues else '')
