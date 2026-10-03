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
    from .lectura_normativa_service import extraer_unidades, detectar_derogaciones_expresas
    from .vigencia_service import registrar_cambios, aviso
    _, disposiciones = separar_unidades(extraer_unidades(texto, 'clasico'))
    cambios = detectar_derogaciones_expresas(disposiciones)
    guardar_disposiciones(documento, disposiciones)
    registrar_cambios(documento, disposiciones, cambios, documento.metadatos)
    return {'actualizar': 0, 'nuevo': 0, 'retirados': 0, 'derogados_indicados': 0,
            'disposiciones': len(disposiciones), 'avisos_normativos': len(cambios),
            'avisos': [aviso(c) for c in documento.cambios_detectados.select_related('fuente__norma',
                      'articulo_afectado').exclude(estado_revision='descartado')]}
