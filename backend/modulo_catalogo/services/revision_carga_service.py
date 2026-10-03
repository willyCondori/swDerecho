"""Comparación y publicación atómica de una carga revisada por el usuario."""
import hashlib
import json
import re

from django.db import transaction

from modulo_catalogo.models.articulo import Articulo
from modulo_catalogo.models.documento_norma import DocumentoNorma


def numero_clave(numero):
    return re.sub(r'\s+', ' ', str(numero).strip()).casefold()


def indica_derogacion(articulo):
    # Solo una indicación en la cabecera propia, nunca una cita en el cuerpo.
    from .carga_pdf_service import PATRON_CABECERA
    texto = articulo['texto'].strip()
    cabecera = PATRON_CABECERA.match(texto)
    cuerpo = texto[cabecera.end():].lstrip() if cabecera else ''
    if articulo.get('tipo_unidad', 'articulo') != 'articulo':
        return bool(re.match(r'^\s*[^.\n]+[.\-–:\s]+\(?\s*(?:DEROGAD[OA]|ABROGAD[OA])\b', texto, re.I))
    return bool(re.match(r'\(?\s*(?:DEROGAD[OA]|ABROGAD[OA])\b', cuerpo, re.I))


def filas_actuales(norma_id, rama_id):
    return list(Articulo.objects.filter(norma_id=norma_id, rama_id=rama_id)
                .order_by('pk').values('id', 'numero_articulo', 'titulo', 'contenido', 'estado',
                                       'documento_norma_id')) if norma_id else []


def huella_catalogo(filas):
    return hashlib.sha256(json.dumps(filas, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def comparar_articulos(articulos, filas):
    existentes = {numero_clave(a['numero_articulo']): a for a in filas}
    entrantes = {numero_clave(a['numero']) for a in articulos}
    revision = []
    for articulo in articulos:
        previo = existentes.get(numero_clave(articulo['numero']))
        derogado = indica_derogacion(articulo)
        igual = previo and previo['estado'] and previo['contenido'] == articulo['texto'] and previo['titulo'] == articulo['titulo']
        revision.append({
            'numero': articulo['numero'], 'titulo': articulo['titulo'],
            'tipo_unidad': articulo.get('tipo_unidad', 'articulo'),
            'accion': 'sin_cambios' if igual else ('actualizar' if previo else 'nuevo'),
            'derogado_en_pdf': derogado,
            'texto_anterior': (previo['contenido'][:240] if previo else None),
            'texto_nuevo': articulo['texto'][:240],
        })
    sobrantes = [{'numero': a['numero_articulo'], 'titulo': a['titulo']} for a in filas
                 if a['estado'] and numero_clave(a['numero_articulo']) not in entrantes]
    return {'articulos': revision, 'sobrantes': sobrantes,
            'conteos': {accion: sum(a['accion'] == accion for a in revision)
                        for accion in ['nuevo', 'actualizar', 'sin_cambios']},
            'derogados_en_pdf': sum(a['derogado_en_pdf'] for a in revision)}


def aplicar_carga_revisada(norma, rama, articulos, modo, seleccion, huella, documento_id, task=None):
    from .carga_pdf_service import ResultadoCarga, _update_task, _obtener_modelo, construir_texto_embedding
    from .articulo_entidad_service import ArticuloEntidadService
    from modulo_ia.services.vectorizacion_service import vectorizar_textos
    from modulo_ia.services.model_loader import version_activa
    from modulo_ia.models.embedding import EmbeddingArticulo

    claves = {numero_clave(n) for n in seleccion or []}
    elegidos = articulos if modo == 'completo' else [a for a in articulos if numero_clave(a['numero']) in claves]
    if not elegidos:
        raise ValueError('Selecciona al menos un artículo para actualizar.')
    if modo not in ['completo', 'articulos']:
        raise ValueError('Modo de actualización inválido.')
    actuales = filas_actuales(norma.pk, rama.pk)
    if huella_catalogo(actuales) != huella:
        raise ValueError('El catálogo cambió desde la revisión. Vuelve a revisar el PDF.')
    existentes = {numero_clave(a['numero_articulo']): a for a in actuales}
    if len(existentes) != len(actuales):
        raise ValueError('Hay números duplicados en esta norma y rama. Corrígelos antes de reemplazarla.')
    # Preparar todos los vectores antes de modificar el catálogo. Un fallo
    # impide publicar una versión parcial o retirar artículos anteriores.
    _update_task(task, 18, 'Generando embeddings de los artículos seleccionados...')
    modelo = _obtener_modelo()
    vectores = vectorizar_textos([construir_texto_embedding(a['titulo'], a['texto']) for a in elegidos], modelo)
    entidades = ArticuloEntidadService.obtener_catalogo()
    resultado = ResultadoCarga(norma_nombre=norma.nombre, rama_nombre=rama.nombre,
                              jerarquia_nombre=norma.jerarquia.nombre if norma.jerarquia_id else None)
    resultado.total_encontrados = len(articulos)
    resultado.revision = {**comparar_articulos(elegidos, actuales)['conteos'], 'retirados': 0,
                          'derogados_indicados': sum(indica_derogacion(a) for a in elegidos)}
    from .vigencia_service import conservar_version, registrar_cambios
    with transaction.atomic():
        # Las cargas revisadas de una misma norma se publican en serie.
        type(norma).objects.select_for_update().get(pk=norma.pk)
        if huella_catalogo(filas_actuales(norma.pk, rama.pk)) != huella:
            raise ValueError('El catálogo cambió durante la carga. Vuelve a revisar el PDF.')
        fuente = DocumentoNorma.objects.get(pk=documento_id, norma=norma, rama=rama)
        fuente.vigente = True
        fuente.save(update_fields=['vigente'])
        ids_publicados = []
        for articulo_pdf, vector in zip(elegidos, vectores):
            previo = existentes.get(numero_clave(articulo_pdf['numero']))
            campos = {'titulo': articulo_pdf['titulo'], 'contenido': articulo_pdf['texto'],
                      'estado': True, 'documento_norma': fuente,
                      'tipo_unidad': articulo_pdf.get('tipo_unidad', 'articulo')}
            if previo:
                articulo = Articulo.objects.get(pk=previo['id'])
                conservar_version(articulo)
                for nombre, valor in campos.items():
                    setattr(articulo, nombre, valor)
                articulo.save(update_fields=list(campos))
            else:
                articulo = Articulo.objects.create(numero_articulo=articulo_pdf['numero'],
                                                    norma=norma, rama=rama, **campos)
            conservar_version(articulo)
            # Ningún embedding de otra versión debe representar el texto anterior.
            EmbeddingArticulo.objects.filter(articulo=articulo).delete()
            EmbeddingArticulo.objects.create(articulo=articulo, modelo_version=version_activa(), vector=vector)
            articulo.entidades.clear()
            ArticuloEntidadService.vincular(articulo, catalogo=entidades)
            resultado.guardados += 1
            ids_publicados.append(articulo.pk)
        if modo == 'completo':
            resultado.revision['retirados'] = Articulo.objects.filter(norma=norma, rama=rama, estado=True).exclude(
                pk__in=ids_publicados).update(estado=False)
            DocumentoNorma.objects.filter(norma=norma, rama=rama, vigente=True).exclude(pk=fuente.pk).update(vigente=False)
        analisis = fuente.analisis_normativo
        cambios = [c for c in analisis.get('cambios', [])
                   if numero_clave(c['unidad_fuente']) in {numero_clave(a['numero']) for a in elegidos}]
        registrar_cambios(fuente, elegidos, cambios, fuente.metadatos)
        _update_task(task, 98, 'Publicando la versión revisada...')
    return resultado
