"""Etiquetas explicables; no determinan la aplicación jurídica del artículo."""
import re

from .contexto_tentativa_service import normalizar
from .jurisprudencia_relevancia import contexto_busqueda, robo_relacionado, secuestro_personas


def relaciones_articulo(articulo, contexto):
    texto_caso = ' '.join([contexto.get('descripcion', ''), *contexto.get('fragmentos', [])])
    grupos, figuras = contexto_busqueda(texto_caso)
    texto_articulo = normalizar(f'{articulo.titulo or ""} {articulo.contenido or ""}')
    coincidencias = []
    for nombre, patron in grupos.items():
        if not re.search(patron, texto_articulo):
            continue
        if nombre == 'Secuestro de personas' and not secuestro_personas(texto_articulo):
            continue
        if nombre == 'Robo' and not robo_relacionado(texto_articulo):
            continue
        coincidencias.append(nombre)
    for nombre, patron in figuras.items():
        if nombre == 'Tentativa':
            # Mencionar la consumación en una disposición no equivale a regular tentativa.
            patron = r'\b(?:tentativa|intento|intentaron|intentar\w*|desistimiento)\b'
        if re.search(patron, texto_articulo):
            coincidencias.append(nombre)
    return coincidencias
