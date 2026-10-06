"""Texto activo y evidencia inmutable de efectos confirmados."""
from django.db import transaction
from django.utils import timezone
from modulo_catalogo.models import Articulo, HistorialArticulo
from .alcance_normativo_service import fragmento_literal


def texto_sin_partes(texto, parte):
    rangos = []
    for item in parte.get('partes', []):
        fragmento = fragmento_literal(texto, item.get('fragmento', ''))
        if not fragmento:
            raise ValueError('La parte derogada ya no coincide inequívocamente con el texto activo. Revisa el artículo.')
        inicio = texto.index(fragmento)
        rangos.append((inicio, inicio + len(fragmento)))
    if not rangos:
        raise ValueError('Falta el fragmento exacto que debe retirarse del artículo.')
    rangos.sort()
    salida = []; fin = 0
    for inicio, hasta in rangos:
        if inicio < fin:
            raise ValueError('Las partes derogadas se superponen. Revisa el alcance antes de confirmar.')
        salida.append(texto[fin:inicio]); fin = hasta
    salida.append(texto[fin:])
    despues = ''.join(salida).strip()
    if not despues:
        raise ValueError('Una derogación parcial no puede eliminar todo el artículo.')
    return despues


def actualizar_busqueda(articulo):
    from modulo_ia.models.embedding import EmbeddingArticulo
    from .articulo_entidad_service import ArticuloEntidadService
    if EmbeddingArticulo.objects.filter(articulo=articulo).exists():
        from .carga_pdf_service import _obtener_modelo, construir_texto_embedding
        from modulo_ia.services.vectorizacion_service import vectorizar_textos
        from modulo_ia.services.model_loader import version_activa
        vector = vectorizar_textos([construir_texto_embedding(articulo.titulo, articulo.contenido)], _obtener_modelo())[0]
        EmbeddingArticulo.objects.filter(articulo=articulo).delete()
        EmbeddingArticulo.objects.create(articulo=articulo, modelo_version=version_activa(), vector=vector)
    articulo.entidades.clear()
    ArticuloEntidadService.vincular(articulo)


@transaction.atomic
def aplicar_texto_confirmado(cambio):
    from modulo_catalogo.models import CambioNormativo
    from .vigencia_service import conservar_version
    cambio = CambioNormativo.objects.select_for_update().get(pk=cambio.pk)
    if cambio.estado_revision != 'confirmado' or cambio.operacion not in ['deroga', 'abroga']:
        return
    parte = cambio.referencia.get('parte_afectada', {})
    parcial = cambio.operacion == 'deroga' and parte.get('tipo') == 'parcial'
    articulos = Articulo.objects.select_for_update().filter(pk=cambio.articulo_afectado_id) if cambio.articulo_afectado_id else Articulo.objects.select_for_update().filter(norma_id=cambio.norma_afectada_id)
    vigente = bool(cambio.fecha_efecto and cambio.fecha_efecto <= timezone.localdate())
    for articulo in articulos.order_by('pk'):
        previo = HistorialArticulo.objects.filter(cambio=cambio, articulo=articulo).first()
        if previo and previo.aplicado and (not parcial or articulo.contenido == previo.texto_despues):
            continue
        if previo and previo.aplicado and parcial and all(not fragmento_literal(articulo.contenido, p.get('fragmento', '')) for p in parte.get('partes', [])):
            continue
        antes = articulo.contenido
        despues = texto_sin_partes(antes, parte) if parcial else antes
        historial, _ = HistorialArticulo.objects.get_or_create(cambio=cambio, articulo=articulo, defaults={
            'titulo': articulo.titulo or '', 'texto_antes': antes, 'texto_despues': despues,
            'parte_afectada': parte, 'aplicado': False})
        if not vigente:
            continue
        if previo and not previo.aplicado:
            historial.texto_antes = antes
            historial.texto_despues = despues
        if parcial:
            conservar_version(articulo)
            articulo.contenido = despues
            articulo.save(update_fields=['contenido'])
            conservar_version(articulo)
            actualizar_busqueda(articulo)
        historial.aplicado = True
        historial.save(update_fields=['aplicado', 'texto_antes', 'texto_despues'])


def comprobar_restauracion(cambio, historiales):
    if cambio.estado_revision != 'confirmado':
        raise ValueError('Solo se puede restaurar una confirmación que aún no fue revertida.')
    if cambio.operacion not in ['deroga', 'abroga']:
        raise ValueError('Esta sección restaura derogaciones y abrogaciones confirmadas.')
    if not historiales:
        raise ValueError('Falta el historial anterior. No se puede restaurar de forma segura.')
    for historial in historiales:
        if historial.aplicado and historial.texto_antes != historial.texto_despues and historial.articulo.contenido != historial.texto_despues:
            raise ValueError(f'El artículo {historial.articulo.numero_articulo} cambió después de la derogación. La restauración automática no puede sobrescribirlo.')


@transaction.atomic
def restaurar_confirmacion(cambio, usuario):
    from modulo_catalogo.models import CambioNormativo
    from .vigencia_service import conservar_version, actualizar_avisos
    cambio = CambioNormativo.objects.select_for_update(of=('self',)).get(pk=cambio.pk)
    historiales = list(HistorialArticulo.objects.filter(cambio=cambio).select_related('articulo').order_by('articulo_id'))
    articulos = {a.pk: a for a in Articulo.objects.select_for_update().filter(pk__in=[h.articulo_id for h in historiales]).order_by('pk')}
    for h in historiales:
        h.articulo = articulos[h.articulo_id]
    comprobar_restauracion(cambio, historiales)
    for h in historiales:
        if h.aplicado and h.texto_antes != h.texto_despues:
            articulo = h.articulo
            conservar_version(articulo)
            articulo.contenido = h.texto_antes
            articulo.save(update_fields=['contenido'])
            conservar_version(articulo)
            actualizar_busqueda(articulo)
    cambio.estado_revision = 'revertido'
    cambio.restaurado_por = usuario
    cambio.restaurado_at = timezone.now()
    cambio.save(update_fields=['estado_revision', 'restaurado_por', 'restaurado_at'])
    if cambio.norma_afectada_id:
        actualizar_avisos(cambio.norma_afectada)
    return cambio
