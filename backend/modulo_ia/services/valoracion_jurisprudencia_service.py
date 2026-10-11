import hashlib
import json
from modulo_ia.models.valoracion import ValoracionJurisprudencia
from .valoracion_service import contexto_caso, conserva_relato


def decisiones(caso):
    return {v.resolucion_id: v for v in ValoracionJurisprudencia.objects.filter(caso=caso)
            .select_related('resolucion').order_by('resolucion_id', '-id').distinct('resolucion_id')}


def excluidas(caso):
    valores = (ValoracionJurisprudencia.objects.filter(caso=caso)
                .order_by('resolucion_id', '-id').distinct('resolucion_id')
                .values_list('resolucion_id', 'valor'))
    return [rid for rid, valor in valores if valor == 'no_util']


def huella(contexto, huella_fuente):
    return hashlib.sha256(json.dumps([contexto, huella_fuente], sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def desactualizada(decision, contexto):
    muestra = decision.muestra
    if not decision.resolucion.activa or muestra.get('huella_fuente') != decision.resolucion.huella:
        return True
    if decision.contexto_hash == huella(contexto, decision.resolucion.huella):
        return False
    return not (all(k in muestra for k in ('descripcion', 'fragmentos'))
                and conserva_relato(muestra['descripcion'], contexto['descripcion'])
                and conserva_relato(' '.join(muestra['fragmentos']), ' '.join(contexto['fragmentos'])))


def con_seleccion(caso, resultados):
    from modulo_ia.serializers.jurisprudencia_serializer import ResultadoJurisprudenciaSerializer
    ultimas = decisiones(caso)
    contexto = contexto_caso(caso)
    data = list(ResultadoJurisprudenciaSerializer(resultados, many=True).data)
    presentes = set()
    for item, resultado in zip(data, resultados):
        presentes.add(resultado.resolucion_id)
        decision = ultimas.get(resultado.resolucion_id)
        item.update(valoracion=decision.valor if decision else 'sin_valorar',
                    valoracion_desactualizada=bool(decision and decision.valor == 'util' and desactualizada(decision, contexto)),
                    seleccion_historica=False)
    for rid, decision in ultimas.items():
        if rid in presentes:
            continue
        r = decision.resolucion
        data.append({**decision.muestra['resultado'],
                     'id': f'valoracion-juris-{decision.pk}', 'valoracion_id': decision.pk,
                     'registro_id': rid, 'numero': r.numero, 'fuente_id': r.fuente_id,
                     'fecha': r.fecha.isoformat() if r.fecha else None, 'sala': r.sala,
                     'expediente': r.expediente, 'url_fuente': r.url_fuente, 'url_pdf': r.url_pdf,
                     'valoracion': decision.valor, 'seleccion_historica': True,
                     'desactualizada': not r.activa or decision.muestra.get('huella_fuente') != r.huella,
                     'valoracion_desactualizada': decision.valor == 'util' and desactualizada(decision, contexto)})
    return data


def registrar(caso, resultado, usuario, valor, contexto):
    from modulo_ia.serializers.jurisprudencia_serializer import ResultadoJurisprudenciaSerializer
    # Los metadatos ya serializados son una instantánea del fragmento valorado.
    muestra_resultado = dict(ResultadoJurisprudenciaSerializer(resultado).data)
    return ValoracionJurisprudencia.objects.create(caso=caso, resolucion=resultado.resolucion,
        usuario=usuario, valor=valor, contexto_hash=huella(contexto, resultado.huella_fuente),
        modelo_version=resultado.modelo_version,
        muestra={**contexto, 'huella_fuente': resultado.huella_fuente, 'resultado': muestra_resultado})
