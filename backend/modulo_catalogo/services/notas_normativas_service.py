"""Separar notas de edición, reglas temporales y contenido penal ordinario."""
import re


def regla_temporal(unidad, texto):
    if re.search(r'\b(?:entrar[aá]n?|entrar[aá]|entra|entran)\s+en\s+vigencia\b|'
                 r'\bregir[aá]\s+a\s+partir\b', texto, re.I):
        return True
    if re.search(r'^\s*(?:ART[IÍ]CULO|ART\.)[^\n]{0,45}\(Vigencia\)', texto, re.I):
        return True
    disposicion = unidad.get('tipo_unidad') in ['final', 'derogatoria', 'abrogatoria'] or re.match(r'^(?:DF|DD|DA)\s', unidad.get('numero', ''))
    return bool((disposicion or re.search(r'\breglament\w*\b', texto, re.I)) and
                re.search(r'\b(?:vigencia|publicaci[oó]n|plazos?)\b', texto, re.I))


def nota_editorial(unidad):
    from .lectura_normativa_service import identidades_literales, fecha_literal
    texto = unidad['texto']
    base = {'norma': '', 'unidad': unidad.get('numero', ''), 'alcance': 'total', 'cita': texto,
            'origen': 'nota_editorial', 'causante': '', 'fecha_causante': '', 'unidad_fuente': unidad.get('numero', '')}
    # Una cabecera propia o la primera línea después del título puede indicar derogación.
    from .lectura_normativa_service import ARTICULO
    propia = ARTICULO.match(texto)
    fragmento = texto[propia.end():].lstrip() if propia else texto
    titulo = re.match(r'^\((?!DEROGAD[OA]|ABROGAD[OA])[^)]+\)[.\s]*', fragmento, re.I)
    if titulo:
        fragmento = fragmento[titulo.end():]
    cabecera = re.match(r'^\s*\(?\s*(DEROGAD[OA]|ABROGAD[OA])\s+por\b', fragmento, re.I)
    if cabecera:
        nota = fragmento[:900]
        identidades = identidades_literales(nota)
        return {**base, 'operacion': 'deroga' if cabecera.group(1).upper().startswith('DEROG') else 'abroga',
                'causante': identidades[0] if len(identidades) == 1 else '', 'fecha_causante': fecha_literal(nota)}
    # Las notas judiciales requieren contrastar la decisión y sus aclaraciones.
    if re.search(r'\b(?:declarad[oa]\s+inconstitucional|(?:sentencia|auto)\s+constitucional\s+(?:SC[P]?|AC)?\s*\d)\b', texto, re.I):
        return {**base, 'operacion': 'general', 'unidad': '',
                'causante': 'la decisión constitucional citada en el PDF',
                'alcance': 'Referencia judicial: revisar la sentencia, sus aclaraciones y la parte afectada; no equivale a una derogación legislativa.'}
    nota = re.search(r'(?im)^\s*(modificad[oa]|incorporad[oa])\s+por\b', texto)
    if nota:
        evidencia = texto[nota.start():]
        identidades = identidades_literales(evidencia)
        return {**base, 'operacion': 'modifica' if nota.group(1).lower().startswith('modific') else 'incorpora',
                'causante': identidades[0] if len(identidades) == 1 else '', 'fecha_causante': fecha_literal(evidencia)}
    # Estas notas pueden corresponder al capítulo siguiente o a varios artículos.
    nota = re.search(r'(?im)^.*\bse\s+incorporan?\s+por\b', texto)
    if nota:
        evidencia = texto[nota.start():]
        identidades = identidades_literales(evidencia)
        return {**base, 'operacion': 'general', 'unidad': '',
                'causante': identidades[0] if len(identidades) == 1 else '', 'fecha_causante': fecha_literal(evidencia),
                'alcance': 'Nota histórica de incorporación: puede referirse a varios artículos o al capítulo siguiente. Verifique los destinos en la ley citada.'}
    return None
