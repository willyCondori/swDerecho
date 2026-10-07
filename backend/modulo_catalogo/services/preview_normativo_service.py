"""Vista previa sin modificar artículos, normas ni avisos."""
from modulo_catalogo.models import Articulo
from .vigencia_service import evaluar_destino, evidencia_de_alcance
from .alcance_normativo_service import identificar_parte, fragmento_literal
from .historial_articulos_service import texto_sin_partes


def preparar_revision(cambio, datos):
    if cambio.estado_revision != 'pendiente' or cambio.operacion not in ['deroga', 'abroga']:
        raise ValueError('Solo se pueden previsualizar derogaciones y abrogaciones pendientes.')
    destino = evaluar_destino({**cambio.referencia, 'operacion': cambio.operacion,
                              'origen': cambio.origen}, cambio.fuente.norma)
    if not destino['encontrado']:
        raise ValueError(destino['mensaje'])
    articulos = Articulo.objects.filter(pk=destino['articulo_id']) if destino['articulo_id'] else Articulo.objects.filter(norma_id=destino['norma_id'])
    resultados = []
    for articulo in articulos.order_by('pk'):
        ref = cambio.referencia
        parte = identificar_parte(evidencia_de_alcance(cambio.cita, cambio.origen, cambio.operacion),
                                 ref.get('alcance', ''), articulo, cambio.operacion, ref.get('unidad', ''))
        parcial = cambio.operacion == 'deroga' and parte['tipo'] == 'parcial'
        if parcial and datos.get('fragmento_afectado'):
            fragmento = fragmento_literal(articulo.contenido, datos['fragmento_afectado'])
            if not fragmento or fragmento.strip() == articulo.contenido.strip():
                raise ValueError('El fragmento parcial debe coincidir una sola vez y no puede abarcar todo el artículo.')
            parte.update(localizado=True, partes=[{'fragmento': fragmento, 'descripcion': ref.get('alcance', 'Fragmento verificado')}])
        if parcial and not parte['localizado']:
            raise ValueError('Identifica el fragmento exacto para ver el cambio antes de confirmar.')
        resultados.append({'articulo_id': articulo.pk, 'numero_articulo': articulo.numero_articulo,
            'norma': articulo.norma.nombre, 'texto_antes': articulo.contenido,
            'texto_despues': texto_sin_partes(articulo.contenido, parte) if parcial else articulo.contenido,
            'parte_afectada': parte, 'operacion': cambio.operacion, 'aplicado': False})
    return {'articulos': resultados, 'norma_id': destino['norma_id']}
