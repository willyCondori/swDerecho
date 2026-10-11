import hashlib
import json
import re
import unicodedata

from modulo_ia.models.valoracion import ValoracionArticulo


def contexto_caso(caso):
    return {
        "descripcion": caso.descripcion or "",
        "fragmentos": list(caso.chunks.order_by("orden", "id").values_list("contenido", flat=True)),
    }


def huella(contexto, articulo):
    contenido = json.dumps([contexto, articulo.contenido], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def texto_normalizado(texto):
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto or '')
                    if unicodedata.category(c) != 'Mn').lower()
    return ' '.join(re.findall(r'\w+', texto))


def conserva_relato(anterior, actual):
    anterior, actual = texto_normalizado(anterior), texto_normalizado(actual)
    if anterior == actual:
        return True
    if not anterior:
        return True
    if f' {anterior} ' not in f' {actual} ':
        return False
    # No basta con conservar el texto si luego se rectifica o niega ese hecho.
    agregado = actual.replace(anterior, '', 1)
    if re.search(r'\b(?:rectifico|corrijo|en realidad|era falso|no ocurrio)\b', agregado):
        return False
    raices = {palabra[:5] for palabra in anterior.split() if len(palabra) >= 4}
    if raices and re.search(r'\b(?:no|sin|nunca)\s+(?:\w+\s+){0,3}(?:'
                            + '|'.join(re.escape(r) + r'\w*' for r in raices) + r')\b', agregado):
        return False
    return True


def valoracion_desactualizada(decision, contexto, articulo):
    if decision.contexto_hash == huella(contexto, articulo):
        return False
    muestra = decision.muestra
    if not all(k in muestra for k in ('descripcion', 'fragmentos', 'articulo_texto')):
        return True  # No hay evidencia suficiente para comparar una valoración antigua.
    return not (
        texto_normalizado(muestra['articulo_texto']) == texto_normalizado(articulo.contenido)
        and conserva_relato(muestra['descripcion'], contexto['descripcion'])
        and conserva_relato(' '.join(muestra['fragmentos']), ' '.join(contexto['fragmentos']))
    )


def decisiones_caso(caso):
    """La última decisión por artículo se comparte dentro del caso.

    El historial y el contexto de cada envío se conservan para auditoría.
    Cambiar la descripción, el PDF o el modelo no revoca una decisión manual.
    """
    return dict(ValoracionArticulo.objects.filter(caso=caso)
                .order_by("articulo_id", "-id").distinct("articulo_id")
                .values_list("articulo_id", "valor"))


def articulos_excluidos(caso):
    return {articulo_id for articulo_id, valor in decisiones_caso(caso).items()
            if valor == "no_util"}


def valoraciones_actuales(caso, resultados):
    ultimas = decisiones_caso(caso)
    return {r.id: ultimas.get(r.articulo_id, "sin_valorar") for r in resultados}


def articulos_con_seleccion(caso, resultados):
    """Unir el ranking actual con las selecciones manuales, sin alterar el ranking."""
    from modulo_ia.serializers.ia_serializer import ResultadoArticuloSerializer
    from modulo_catalogo.serializers.catalogo_serializer import ArticuloListSerializer
    from .contexto_tentativa_service import ContextoTentativaService
    from .relacion_articulos_service import relaciones_articulo
    decisiones = {v.articulo_id: v for v in ValoracionArticulo.objects.filter(caso=caso)
                  .select_related('articulo__norma', 'articulo__rama')
                  .order_by('articulo_id', '-id').distinct('articulo_id')}
    contexto = contexto_caso(caso)
    # Los fragmentos pueden pertenecer a un análisis anterior si se editó el relato.
    texto = contexto['descripcion'] or ' '.join(contexto['fragmentos'])
    data = list(ResultadoArticuloSerializer(resultados, many=True).data)
    presentes = set()
    for item, resultado in zip(data, resultados):
        presentes.add(resultado.articulo_id)
        decision = decisiones.get(resultado.articulo_id)
        item['valoracion'] = decision.valor if decision else 'sin_valorar'
        item['valoracion_desactualizada'] = bool(decision and decision.valor == 'util'
            and valoracion_desactualizada(decision, contexto, resultado.articulo))
        item['seleccion_historica'] = False
        item['coincidencias'] = relaciones_articulo(resultado.articulo, resultado.contexto_evaluado or contexto)
        motivo = ContextoTentativaService.motivo(resultado.articulo, texto)
        if motivo:
            item.update(es_sugerencia=True, motivo_recomendacion=motivo)
    for articulo_id, decision in decisiones.items():
        if decision.valor != 'util' or articulo_id in presentes:
            continue
        data.append({
            'id': f'valoracion-{decision.pk}', 'valoracion_id': decision.pk,
            'articulo': ArticuloListSerializer(decision.articulo).data,
            'valoracion': 'util', 'es_sugerencia': decision.muestra.get('es_sugerencia', False),
            'seleccion_historica': True,
            'valoracion_desactualizada': valoracion_desactualizada(decision, contexto, decision.articulo),
            'coincidencias': relaciones_articulo(decision.articulo, decision.muestra),
        })
        motivo = ContextoTentativaService.motivo(decision.articulo, texto)
        if motivo:
            data[-1].update(es_sugerencia=True, motivo_recomendacion=motivo)
    return data


def registrar(caso, resultado, usuario, valor):
    from .contexto_tentativa_service import ContextoTentativaService
    contexto = resultado.contexto_evaluado or contexto_caso(caso)
    articulo = resultado.articulo
    texto = contexto['descripcion'] or ' '.join(contexto['fragmentos'])
    motivo = ContextoTentativaService.motivo(articulo, texto)
    return ValoracionArticulo.objects.create(
        caso=caso, articulo=articulo, usuario=usuario, valor=valor,
        contexto_hash=huella(contexto, articulo), modelo_version=resultado.modelo_version,
        muestra={
            **contexto, "articulo_texto": articulo.contenido,
            "norma": articulo.norma.sigla, "numero_articulo": articulo.numero_articulo,
            "posicion": resultado.posicion, "score_total": str(resultado.score_total),
            "es_sugerencia": bool(resultado.es_sugerencia or motivo),
            "motivo_recomendacion": motivo,
        },
    )
