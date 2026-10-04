"""Revisión y publicación de todas las normas de una compilación."""
from types import SimpleNamespace
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from rest_framework.exceptions import ValidationError
from modulo_catalogo.models import Norma, DocumentoNorma
from .revision_carga_service import filas_actuales, huella_catalogo, aplicar_carga_revisada


def destino_anexo(titulo, metadatos):
    candidatos = list(Norma.objects.filter(nombre__iexact=titulo))
    if not candidatos and metadatos.get('numero_norma') and metadatos.get('tipo_norma'):
        numero = str(metadatos['numero_norma'])
        candidatos = [n for n in Norma.objects.filter(tipo_norma__iexact=metadatos['tipo_norma'])
                      if n.numero_norma == numero or n.numero_norma.isdigit() and numero.isdigit() and int(n.numero_norma) == int(numero)]
    if len(candidatos) > 1 or any(not n.estado for n in candidatos):
        raise ValidationError({'anexos': f'Revisa el destino duplicado o inactivo: {titulo}.'})
    return candidatos[0] if candidatos else None


def revisar_anexos(request, data, contenido, principal, secciones):
    from modulo_catalogo.views.revision_carga_view import RevisionCargaPDFView, PREFIJO
    from .lectura_normativa_service import identidades_literales
    anexos, planes = [], []
    for seccion in secciones:
        if seccion['id'] == principal['seccion_activa']:
            continue
        identidad = data.get('identidades_secciones', {}).get(seccion['id'], {})
        titulo = identidad.get('nombre') or seccion['titulo']
        legales = identidades_literales(titulo)
        meta = {k: v for k, v in identidad.items() if k != 'nombre'}
        if not identidad and len(legales) == 1:
            partes = legales[0].rsplit(' ', 1)
            destino = destino_anexo(titulo, {'tipo_norma': partes[0], 'numero_norma': partes[1]})
        else:
            destino = destino_anexo(titulo, meta)
        params = {'archivo': SimpleUploadedFile(data['archivo'].name, contenido, content_type='application/pdf'),
                  'incluir_anexos': False, 'seccion_documento': seccion['id'], 'nombre_documento': titulo,
                  'rama_id': data['rama'].pk, 'motor_lectura': data.get('motor_lectura', principal['motor']),
                  'metadatos': meta, 'variantes_unidades': data.get('variantes_secciones', {}).get(seccion['id'], {})}
        from modulo_catalogo.models.jerarquia import jerarquia
        tipo_anexo = meta.get('tipo_norma') or (legales[0].rsplit(' ', 1)[0] if len(legales) == 1 else '')
        jerarquia_anexo = jerarquia.objects.filter(estado=True, nombre__iexact=tipo_anexo).first() if tipo_anexo else None
        jerarquia_anexo = jerarquia_anexo or data.get('jerarquia') or getattr(data.get('norma'), 'jerarquia', None)
        if jerarquia_anexo:
            params['jerarquia_id'] = jerarquia_anexo.pk
        if destino and destino.numero_norma and meta.get('numero_norma'):
            params['metadatos'] = {**meta, 'numero_norma': destino.numero_norma}
        if destino:
            params['norma_id'] = str(destino.pk)
        progreso = getattr(request, 'progreso_normativo', None)
        if progreso:
            progreso({'paso': f'Revisando norma {seccion["id"]}: {titulo}…'})
        peticion = SimpleNamespace(data=params, user=request.user, progreso_normativo=progreso, _compilacion_normativa=getattr(request, '_compilacion_normativa', None))
        respuesta = RevisionCargaPDFView().post(peticion).data
        plan = cache.get(PREFIJO + respuesta['revision_token'])
        if not plan:
            raise ValidationError({'anexos': 'La revisión del anexo expiró.'})
        plan['norma_id'] = destino.pk if destino else None
        plan['nombre'] = titulo
        # Resolver también normas conocidas por sus metadatos, sin crear nada.
        if not destino and not respuesta['identidad_por_verificar']:
            encontrado = destino_anexo(titulo, respuesta['metadatos'])
            if encontrado:
                params['norma_id'] = str(encontrado.pk)
                respuesta = RevisionCargaPDFView().post(SimpleNamespace(data=params, user=request.user, progreso_normativo=progreso, _compilacion_normativa=getattr(request, '_compilacion_normativa', None))).data
                plan = cache.get(PREFIJO + respuesta['revision_token'])
                plan.update(norma_id=encontrado.pk, nombre=titulo)
        anexos.append(respuesta)
        planes.append(plan)
    return anexos, planes


def validar_anexos(planes, rama):
    destinos = set()
    for plan in planes:
        if plan.get('identidad_por_verificar') or plan.get('ambiguedades_pendientes'):
            raise ValidationError({'anexos': f'Resuelve la identidad y las alternativas de {plan["nombre"]} antes de cargar todas las normas.'})
        if not plan['articulos']:
            raise ValidationError({'anexos': f'No hay unidades para cargar en {plan["nombre"]}.'})
        identidad = ('id', plan['norma_id']) if plan.get('norma_id') else ('nombre', plan['nombre'].casefold())
        if identidad in destinos:
            raise ValidationError({'anexos': 'Varias secciones tienen el mismo destino. Revisa su identidad antes de cargar.'})
        destinos.add(identidad)
        if huella_catalogo(filas_actuales(plan.get('norma_id'), rama.pk)) != plan['huella']:
            raise ValidationError({'anexos': f'El catálogo cambió: {plan["nombre"]}. Revisa nuevamente.'})


def progreso_norma(task, indice, total, nombre):
    if task is None:
        return None
    class ProgresoNorma:
        def update_state(self, state, meta):
            porcentaje = min(99, int((indice * 100 + meta.get('progreso', 0)) / total))
            task.update_state(state=state, meta={**meta, 'progreso': porcentaje,
                'paso': f'Norma {indice + 1}/{total} · {nombre} · {meta.get("paso", "")}'} )
    return ProgresoNorma()


@transaction.atomic
def aplicar_compilacion(norma, rama, revision, modo, seleccion, documento_id, task=None):
    validar_anexos(revision['anexos'], rama)
    resultado = aplicar_carga_revisada(norma, rama, revision['articulos'], modo, seleccion, revision['huella'], documento_id, progreso_norma(task, 0, 1 + len(revision['anexos']), norma.nombre))
    principal = DocumentoNorma.objects.get(pk=documento_id)
    creadas, reutilizadas = [], []
    destinos = {norma.pk}
    for indice, plan in enumerate(revision['anexos'], 1):
        if plan.get('norma_id'):
            destino = Norma.objects.select_for_update().get(pk=plan['norma_id'], estado=True)
            creada = False
        else:
            if destino_anexo(plan['nombre'], plan['metadatos']):
                raise ValueError('Se creó otra norma durante la revisión. Revisa el PDF nuevamente.')
            destino = Norma.objects.create(nombre=plan['nombre'], jerarquia_id=plan['destino'].get('jerarquia_id') or norma.jerarquia_id, estado=True)
            creada = True
        if destino.pk in destinos:
            raise ValueError('Un anexo coincide con la norma principal. Revisa las identidades.')
        destinos.add(destino.pk)
        doc = DocumentoNorma.objects.create(norma=destino, rama=rama, nombre_original=principal.nombre_original,
            ruta_archivo=principal.ruta_archivo, tamano=principal.tamano, subido_por=principal.subido_por, vigente=False,
            metadatos=plan['metadatos'], url_fuente=principal.url_fuente,
            analisis_normativo={'motor': plan['motor'], 'seccion': plan['seccion'], 'secciones': plan['secciones'],
                               'cambios': plan['cambios'], 'variantes_unidades': plan['destino'].get('variantes_unidades', {})})
        elegidos = [a['numero'] for a in plan['articulos'] if a.get('tipo_unidad', 'articulo') == 'articulo']
        parcial = aplicar_carga_revisada(destino, rama, plan['articulos'], 'articulos', elegidos, plan['huella'], doc.pk, progreso_norma(task, indice, 1 + len(revision['anexos']), destino.nombre))
        resultado.total_encontrados += parcial.total_encontrados
        resultado.guardados += parcial.guardados
        for campo in ['nuevo', 'actualizar', 'sin_cambios', 'retirados', 'disposiciones', 'avisos_normativos', 'derogados_indicados']:
            resultado.revision[campo] = resultado.revision.get(campo, 0) + parcial.revision.get(campo, 0)
        resultado.revision['avisos'].extend(parcial.revision.get('avisos', []))
        (creadas if creada else reutilizadas).append({'id': destino.pk, 'nombre': destino.nombre})
    resultado.revision.update(normas_guardadas=len(destinos), normas_creadas=creadas, normas_reutilizadas=reutilizadas)
    return resultado
