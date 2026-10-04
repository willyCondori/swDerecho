"""Segmentación asistida por Qwen con límites contrastados en el texto fuente."""
import hashlib
import re

from django.core.cache import cache


SECCIONES = {'type': 'object', 'additionalProperties': False, 'required': ['secciones'],
             'properties': {'secciones': {'type': 'array', 'maxItems': 80, 'items': {
                 'type': 'object', 'additionalProperties': False, 'required': ['linea', 'titulo'],
                 'properties': {'linea': {'type': 'integer', 'minimum': 0},
                                'titulo': {'type': 'string', 'maxLength': 200}}}}}}


def segmentar_normas(texto, progreso=None, motor='qwen'):
    from .lectura_normativa_service import ARTICULO, localizar_clasico, normalizar, consultar
    lineas = texto.splitlines()
    excluidas = set()
    unidades = localizar_clasico(lineas, excluidas)
    primera = next((u['linea'] for u in unidades if u['tipo'] == 'articulo'), len(lineas))
    # Candidatos solamente: el modelo decide si son otra norma, cita o pie de página.
    patron = re.compile(r'^\s*(?:LEY\s+(?:N[°ºoO.]*\s*)?\d+\b|DECRETO\s+(?:LEY|SUPREMO|PRESIDENCIAL)\b|'
                        r'RESOLUCI[ÓO]N\s+(?:SUPREMA|MINISTERIAL|ADMINISTRATIVA)\b|C[ÓO]DIGO\s+)', re.I)
    anteriores = {normalizar(s).casefold() for s in lineas[:primera] if patron.match(s)}
    candidatos = [i for i, s in enumerate(lineas) if i > primera and i not in excluidas
                  and len(s.strip()) < 210 and patron.match(s)
                  and normalizar(s).casefold() not in anteriores]
    principal = next((s.strip()[:200] for s in lineas[:primera] if patron.match(s)), '')
    if not candidatos:
        return [{'id': '0', 'titulo': principal, 'inicio': 0, 'fin': len(lineas)}]
    if motor != 'qwen':
        inicios = [(0, principal)]
        for i in candidatos:
            titulo = lineas[i].strip()
            # Una cabecera independiente ocupa una línea y antecede a unidades propias.
            legal = re.match(r'^(?:LEY|DECRETO (?:LEY|SUPREMO|PRESIDENCIAL)|RESOLUCI[ÓO]N (?:SUPREMA|MINISTERIAL|ADMINISTRATIVA))\s+(?:N[°ºoO.]*\s*)?\d+(?:\s*[-,.]?\s*(?:DE|DEL)\s+.+)?$', titulo, re.I)
            codigo = re.match(r'^C[ÓO]DIGO\s+[A-ZÁÉÍÓÚÜÑ ]+$', titulo)
            proximas = [u for u in unidades if i < u['linea'] < i + 45]
            if not (legal or codigo) or not proximas:
                continue
            # Ley y nombre del código contiguos son la portada de la misma norma.
            if i - inicios[-1][0] < 15 and not any(inicios[-1][0] < u['linea'] < i for u in unidades):
                continue
            inicios.append((i, titulo))
        return [{'id': str(k), 'titulo': titulo, 'inicio': inicio,
                 'fin': inicios[k + 1][0] if k + 1 < len(inicios) else len(lineas)}
                for k, (inicio, titulo) in enumerate(inicios)]
    clave = 'compilacion:qwen:v1:' + hashlib.sha256(texto.encode()).hexdigest()
    previo = cache.get(clave)
    if previo is not None:
        return previo
    if progreso:
        progreso({'paso': 'Identificando normas, anexos y referencias del PDF…'})
    posiciones = sorted(set([0] + candidatos))
    entradas = []
    for i in posiciones:
        entorno = '\n'.join(f'{j}: {lineas[j][:220]}' for j in range(max(0, i - 3), min(len(lineas), i + 9)))
        entradas.append(f'CANDIDATO {i}\n{entorno}')
    # Mantener contexto de candidatos individuales y número reducido de resultados.
    grupos, grupo, largo = [], [], 0
    for entrada in entradas:
        if grupo and largo + len(entrada) > 6500:
            grupos.append('\n\n'.join(grupo)); grupo, largo = [], 0
        grupo.append(entrada); largo += len(entrada)
    if grupo:
        grupos.append('\n\n'.join(grupo))
    halladas = {}
    for grupo in grupos:
        datos = consultar(
            'Identifica SOLO los candidatos que inician una norma independiente dentro de una compilación. '
            'Un código y las leyes que lo elevan o modifican en su portada son UNA norma. '
            'No son inicios: referencias dentro de artículos, notas de modificación, títulos de capítulos, '
            'encabezados y pies repetidos. Una lista de leyes especiales NO incorporadas al código sí '
            'inicia normas independientes. Usa exactamente el número CANDIDATO como linea y un título '
            'literal del contexto. Incluye el candidato 0 como norma principal si está presente.',
            grupo, SECCIONES)['secciones']
        for s in datos:
            pos = s['linea']
            if pos not in posiciones:
                raise ValueError('Qwen identificó un límite de norma que no existe en el PDF.')
            contexto = normalizar('\n'.join(lineas[max(0, pos - 3):pos + 9])).casefold()
            if not s['titulo'].strip() or normalizar(s['titulo']).casefold() not in contexto:
                raise ValueError('El título identificado por Qwen no coincide con el PDF original.')
            halladas[pos] = s['titulo'].strip()
    halladas.setdefault(0, principal)
    inicios = sorted(halladas)
    secciones = [{'id': str(i), 'titulo': halladas[pos], 'inicio': pos,
                  'fin': inicios[i + 1] if i + 1 < len(inicios) else len(lineas)}
                 for i, pos in enumerate(inicios)]
    cache.set(clave, secciones, 7200)
    return secciones


def elegir_seccion(texto, secciones, seleccion=None, destino=None):
    from .vigencia_service import clave
    seleccionada = None
    if seleccion is not None:
        seleccionada = next((s for s in secciones if s['id'] == str(seleccion)), None)
        if not seleccionada:
            raise ValueError('La norma seleccionada no pertenece a este PDF.')
    elif destino:
        identidades = [clave(getattr(destino, 'nombre', '')), clave(getattr(destino, 'sigla', ''))]
        identidades += [clave(f'{getattr(destino, "tipo_norma", "")} {getattr(destino, "numero_norma", "")}')]
        matches = [s for s in secciones if any(v and (v == clave(s['titulo']) or
                   clave(s['titulo']) == 'codigo penal' and v.startswith('codigo penal')) for v in identidades)]
        if len(matches) == 1:
            seleccionada = matches[0]
    seleccionada = seleccionada or secciones[0]
    lineas = texto.splitlines()
    return '\n'.join(lineas[seleccionada['inicio']:seleccionada['fin']]), seleccionada


def resolver_alternativas(unidades, elecciones=None):
    from .lectura_normativa_service import normalizar
    elecciones = {} if elecciones is None else elecciones
    if not isinstance(elecciones, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                              for k, v in elecciones.items()):
        raise ValueError('Las alternativas seleccionadas deben ser un objeto de identificadores.')
    grupos = {}
    for u in unidades:
        key = u.get('tipo_unidad', 'articulo') + ':' + normalizar(u['numero']).casefold()
        grupos.setdefault(key, []).append(u)
    ambiguas, resueltas = [], []
    validas = set()
    for key, filas in grupos.items():
        if len(filas) == 1:
            resueltas.extend(filas)
            continue
        # Solo textos íntegros idénticos permiten eliminar una repetición de impresión.
        por_texto = {}
        for u in filas:
            por_texto.setdefault(normalizar(u['texto']), u)
        filas = list(por_texto.values())
        if len(filas) == 1:
            resueltas.extend(filas)
            continue
        validas.add(key)
        alternativas = [{**u, 'id_unidad': u.get('id_unidad') or hashlib.sha256(
            (key + '\n' + u['texto']).encode()).hexdigest()[:24]} for u in filas]
        elegida = elecciones.get(key, '')
        if elegida and elegida not in [u['id_unidad'] for u in alternativas] + ['ignorar']:
            raise ValueError('La alternativa seleccionada no coincide con el texto de este PDF.')
        ambiguas.append({'clave': key, 'numero': filas[0]['numero'],
                         'tipo_unidad': filas[0].get('tipo_unidad', 'articulo'),
                         'alternativas': alternativas, 'seleccionada': elegida})
        resueltas.extend(u for u in alternativas if u['id_unidad'] == elegida)
    if set(elecciones) - validas:
        raise ValueError('Una selección de alternativas no pertenece a las unidades del PDF.')
    return resueltas, ambiguas
