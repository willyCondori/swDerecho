"""Disposiciones separadas: no producen artículos ni embeddings."""
from modulo_catalogo.models import DisposicionNormativa

TIPOS_IMPORTADOS = {'final', 'derogatoria', 'abrogatoria'}


def separar_unidades(unidades):
    return ([u for u in unidades if u.get('tipo_unidad', 'articulo') == 'articulo'],
            [u for u in unidades if u.get('tipo_unidad') in TIPOS_IMPORTADOS])


def guardar_disposiciones(documento, disposiciones):
    for unidad in disposiciones:
        DisposicionNormativa.objects.update_or_create(documento=documento, numero=unidad['numero'], defaults={
            'tipo': unidad['tipo_unidad'], 'titulo': unidad.get('titulo', ''), 'contenido': unidad['texto']})


def importar_disposiciones_expresas(documento, texto):
    from .lectura_normativa_service import detectar_derogaciones_expresas
    from .vigencia_service import registrar_cambios, aviso
    _, disposiciones = separar_unidades(recuperar_unidades_seleccionadas(documento, texto))
    cambios = detectar_derogaciones_expresas(disposiciones)
    guardar_disposiciones(documento, disposiciones)
    registrar_cambios(documento, disposiciones, cambios, documento.metadatos)
    return {'actualizar': 0, 'nuevo': 0, 'retirados': 0, 'derogados_indicados': 0,
            'disposiciones': len(disposiciones), 'avisos_normativos': len(cambios),
            'avisos': [aviso(c) for c in documento.cambios_detectados.select_related('fuente__norma',
                      'articulo_afectado').exclude(estado_revision='descartado')]}


def recuperar_unidades_seleccionadas(documento, texto):
    """Recuperar sin mezclar anexos ni elegir versiones ambiguas por defecto."""
    from .compilaciones_service import segmentar_normas, elegir_seccion, resolver_alternativas
    from .lectura_normativa_service import extraer_unidades
    from .vigencia_service import clave
    secciones = segmentar_normas(texto, motor='clasico')
    analisis = documento.analisis_normativo or {}
    guardada = analisis.get('seccion') or {}
    seleccion = None
    if guardada:
        candidatas = [s for s in secciones if clave(s['titulo']) == clave(guardada.get('titulo', ''))]
        if len(candidatas) != 1:
            raise ValueError('No se pudo recuperar inequívocamente la sección seleccionada; revisa el PDF nuevamente.')
        seleccion = candidatas[0]['id']
    texto, _ = elegir_seccion(texto, secciones, seleccion, documento.norma)
    unidades = [u for u in extraer_unidades(texto, 'clasico')
                if u.get('tipo_unidad', 'articulo') in {'articulo', *TIPOS_IMPORTADOS}]
    # Una cabecera corregida puede dejar de requerir alternativas.
    _, ambiguas = resolver_alternativas(unidades)
    claves = {u['clave'] for u in ambiguas}
    elecciones = {k: v for k, v in analisis.get('variantes_unidades', {}).items() if k in claves}
    unidades, _ = resolver_alternativas(unidades, elecciones)
    return unidades
