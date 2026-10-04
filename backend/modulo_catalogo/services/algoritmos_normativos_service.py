"""Reglas verificables: no deducen incompatibilidades ni efectos tácitos."""
import re


def detectar_cambios_literales(unidades, progreso=None):
    from .lectura_normativa_service import (texto_operativo, ajustar_cambio_literal,
        completar_destinos_literales, identidades_literales, destinos_sustituidos, fecha_literal)
    cambios = []
    verbos = {'abroga': r'\babrog(?:a(?:da|do|das|dos|n)?|ar)\b',
              'deroga': r'\bderog(?:a(?:da|do|das|dos|n)?|ar)\b',
              'modifica': r'\b(?:modific(?:a(?:da|do|das|dos|n)?|ar)|sustituy\w*)\b',
              'incorpora': r'\b(?:incorpor(?:a(?:da|do|das|dos|n)?|ar)|a[nñ]ade\w*)\b'}
    for i, unidad in enumerate(unidades):
        if progreso:
            progreso({'paso': f'Analizando reglas y efectos expresos: {i + 1}/{len(unidades)}'})
        cita = texto_operativo(unidad['texto'])
        base = {'norma': '', 'unidad': '', 'alcance': 'total', 'cita': cita,
                'origen': 'clausula', 'causante': '', 'fecha_causante': '',
                'unidad_fuente': unidad['numero']}
        from .notas_normativas_service import nota_editorial, regla_temporal
        historico = nota_editorial(unidad)
        if historico:
            cambios.append(historico)
            continue
        if re.search(r'todas\s+las\s+disposiciones\s+contrarias', cita, re.I):
            cambios.append({**base, 'operacion': 'general', 'alcance': 'indeterminado'})
            continue
        operaciones = [op for op, patron in verbos.items() if re.search(patron, cita, re.I)]
        # Una nota de actualización no ordena una nueva modificación de la norma actual.
        if not re.search(r'\b(?:se\s+(?:abroga|deroga|modifica|incorpora|sustituye|a[nñ]ade)|'
                         r'quedan?\s+(?:abrogad[oa]s?|derogad[oa]s?)|abrog(?:a|an)|derog(?:a|an)|'
                         r'modific(?:a|an)|incorpor(?:a|an)|sustituy(?:e|en))\b', cita, re.I):
            operaciones = []
        if not operaciones:
            if regla_temporal(unidad, cita):
                cambios.append({**base, 'operacion': 'temporal', 'alcance': 'Regla de vigencia o plazo; no implica derogación'})
            continue
        # No asignar el destino de una cláusula al verbo de otra.
        if len(operaciones) > 1:
            cambios.append({**base, 'operacion': 'general',
                            'alcance': 'Varias operaciones en la misma cláusula; requiere revisar cada destino y alcance'})
            continue
        operacion = operaciones[0]
        c = ajustar_cambio_literal({**base, 'operacion': operacion}, unidad)
        antiguo = re.search(r'\bC[oó]digo\s+(?:de\s+Procedimiento\s+)?Penal\s+(?:de|del)\s+\d{1,2}\s+de\s+\w+\s+(?:de|del)\s+\d{4}', cita, re.I)
        if antiguo:
            c['norma'] = antiguo.group()
        if not c['norma'] or (operacion in ['deroga', 'modifica', 'incorpora'] and not destinos_sustituidos(cita)):
            cambios.append({**base, 'operacion': 'general',
                            'alcance': 'Efecto expreso con destino ambiguo; requiere revisión manual'})
            continue
        for destino in completar_destinos_literales(c, unidad):
            cambios.append(destino)
    return cambios


def extraer_metadatos_literales(texto):
    from .lectura_normativa_service import identidades_literales, fecha_literal
    # Portada/cabecera únicamente: no convertir la fecha de una ley citada en la principal.
    cabecera = re.split(r'(?im)^\s*(?:ART[IÍ]CULO|ART\.)\s+', texto, maxsplit=1)[0][:2400]
    ids = identidades_literales(cabecera)
    if not ids:
        return {}
    principal = ids[0]
    tipo, numero = principal.rsplit(' ', 1)
    # La elevación del Código Penal se cita en la portada junto a su decreto original.
    coincidencia = re.search(r'\b' + re.escape(tipo) + r'\s+(?:N(?:[°ºoO.]|ro\.)?\s*)?' + re.escape(numero) + r'(?!\d)', cabecera, re.I)
    tramo = cabecera[coincidencia.start():] if coincidencia else cabecera
    siguiente = re.search(r'\b(?:LEY|DECRETO(?:\s+(?:LEY|SUPREMO))?|RESOLUCI[ÓO]N(?:\s+\w+)?)\s+(?:N[°ºoO.]*\s*)?\d+\b', tramo[len(coincidencia.group()) if coincidencia else 0:], re.I)
    if siguiente and coincidencia:
        tramo = tramo[:len(coincidencia.group()) + siguiente.start()]
    datos = {'tipo_norma': tipo, 'numero_norma': numero}
    fecha = fecha_literal(tramo)
    if fecha:
        datos['fecha_norma'] = fecha
    return datos
