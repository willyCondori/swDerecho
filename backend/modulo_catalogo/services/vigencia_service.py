import hashlib
import json
import re
import unicodedata
from datetime import date

from django.db import transaction
from django.utils import timezone
from modulo_catalogo.models import Articulo, Norma, CambioNormativo, VersionArticulo


def clave(texto):
    texto = ''.join(c for c in unicodedata.normalize('NFKD', str(texto)) if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', texto.casefold()).strip()


def fecha(valor):
    try:
        return date.fromisoformat(str(valor)) if valor else None
    except ValueError:
        return None


def resolver_norma(referencia):
    buscada = clave(referencia)
    buscada = re.sub(r'(?<=[a-z])(?=\d)', ' ', buscada)
    if not buscada:
        return None
    candidatas = []
    for norma in Norma.objects.all():
        identidades = {re.sub(r'(?<=[a-z])(?=\d)', ' ', clave(v)) for v in [norma.nombre, norma.sigla or '']}
        for identidad in list(identidades):
            legal = re.match(r'^(ley|decreto supremo|decreto ley|decreto presidencial|resolucion suprema|resolucion ministerial) (?:n |no |numero )?(\d+)\b', identidad)
            if legal: identidades.add(' '.join(legal.groups()))
        for etiqueta in ['codigo penal', 'codigo de procedimiento penal']:
            if clave(norma.nombre).startswith(etiqueta): identidades.add(etiqueta)
        if norma.tipo_norma and norma.numero_norma:
            identidades.add(clave(f'{norma.tipo_norma} {norma.numero_norma}'))
        # El número legal es identidad, no el ID interno de la Gaceta.
        buscada_identidad = re.sub(r'\b(?:n|no|numero)\b', '', buscada)
        buscada_identidad = ' '.join(buscada_identidad.split())
        if buscada in identidades or buscada_identidad in identidades:
            candidatas.append(norma)
    return candidatas[0] if len(candidatas) == 1 else None


def resolver_unidad(norma, numero):
    if not norma or not numero:
        return None
    filas = list(Articulo.objects.filter(norma=norma, numero_articulo__iexact=numero)[:2])
    return filas[0] if len(filas) == 1 else None


def describir_unidad_fuente(numero):
    prefijos = {'DF': 'disposición final', 'DT': 'disposición transitoria',
                'DD': 'disposición derogatoria', 'DA': 'disposición abrogatoria',
                'DAD': 'disposición adicional'}
    partes = str(numero or '').split(maxsplit=1)
    if partes and partes[0] in prefijos:
        return prefijos[partes[0]] + (' ' + partes[1].lower() if len(partes) > 1 else '')
    return 'artículo ' + str(numero) if numero else 'unidad por verificar'


def evaluar_destino(cambio, norma_fuente=None):
    """Solo aplicar a un destino inequívoco cuyo contenido esté en el catálogo."""
    norma = (norma_fuente if cambio.get('origen') == 'nota_editorial' and not cambio.get('norma')
             else resolver_norma(cambio.get('norma', '')))
    numero = cambio.get('unidad', '')
    articulo = resolver_unidad(norma, numero)
    concreto = cambio.get('operacion') not in ['general', 'temporal']
    encontrado = bool(concreto and norma and (articulo if numero else
                      (norma.articulos.exists() or norma.documentos.exists())))
    return {'encontrado': encontrado,
            'norma_id': norma.pk if encontrado else None,
            'articulo_id': articulo.pk if encontrado and articulo else None,
            'mensaje': ('Destino encontrado en el sistema. El cambio requiere confirmación del usuario.'
                        if encontrado else 'Solo aviso: no se encontró una norma o artículo cargado que coincida inequívocamente. No se aplicará ningún cambio.')}


def preparar_avisos_revision(cambios, metadatos, norma_fuente=None, nombre_fuente=''):
    causante = f"{metadatos.get('tipo_norma', '')} {metadatos.get('numero_norma', '')}".strip() or nombre_fuente
    resultado = []
    for cambio in cambios:
        fuente = cambio.get('causante') if cambio.get('origen') == 'nota_editorial' else causante
        resultado.append({**cambio, 'norma_causante': fuente,
                          'disposicion_fuente': describir_unidad_fuente(cambio.get('unidad_fuente')),
                          'destino_catalogo': evaluar_destino(cambio, norma_fuente)})
    return resultado


def conservar_version(articulo):
    digest = hashlib.sha256((str(articulo.documento_norma_id) + '\n' +
                            (articulo.titulo or '') + '\n' + articulo.contenido).encode()).hexdigest()
    VersionArticulo.objects.get_or_create(articulo=articulo, huella=digest, defaults={
        'documento': articulo.documento_norma, 'titulo': articulo.titulo or '', 'contenido': articulo.contenido})


def aviso(cambio):
    ref = cambio.referencia
    parcial = ref.get('alcance', '')
    sujeto = 'Esta norma' if not cambio.articulo_afectado_id else (
        f"Esta disposición ({cambio.articulo_afectado.numero_articulo})"
        if cambio.articulo_afectado.tipo_unidad != 'articulo' else 'Este artículo')
    if not cambio.norma_afectada_id:
        sujeto = f"Artículo o disposición {ref.get('unidad')} de {ref.get('norma') or 'la norma del documento'}" if ref.get('unidad') else f"La norma {ref.get('norma') or 'referida en la fuente'}"
    verbos = {'abroga': 'abrogada', 'deroga': 'derogado', 'modifica': 'modificado', 'incorpora': 'ampliado'}
    causante = cambio.norma_causante or cambio.fuente.norma.nombre
    fecha_norma = cambio.fecha_norma_causante
    if parcial and clave(parcial) not in ['total', 'completo', 'articulo completo', 'norma completa']:
        sujeto = f'Afectación parcial del artículo o disposición {ref.get("unidad", "")}'
    verbo = verbos.get(cambio.operacion, cambio.operacion)
    if not cambio.articulo_afectado_id and verbo.endswith('o'): verbo = verbo[:-1] + 'a'
    if cambio.articulo_afectado_id and cambio.articulo_afectado.tipo_unidad != 'articulo' and verbo.endswith('o'): verbo = verbo[:-1] + 'a'
    descripcion = f"{sujeto}: {verbo} por {causante}"
    if parcial and clave(parcial) not in ['total', 'completo', 'articulo completo', 'norma completa']:
        descripcion += f'. Alcance: {parcial}'
    descripcion += f". Fuente: {describir_unidad_fuente(cambio.unidad_fuente)}"
    descripcion += f". Fecha de la norma: {fecha_norma.strftime('%d/%m/%Y') if fecha_norma else 'por verificar'}."
    if cambio.estado_revision != 'confirmado':
        descripcion = 'Afectación detectada, pendiente de verificación. ' + descripcion
    if cambio.operacion in ['modifica', 'incorpora']:
        descripcion += ' Consulte la fuente modificatoria; el texto mostrado puede requerir consolidación.'
    return {'id': cambio.pk, 'operacion': cambio.operacion, 'estado': cambio.estado_revision,
            'mensaje': descripcion, 'norma_causante': causante,
            'unidad_fuente': cambio.unidad_fuente, 'disposicion_fuente': describir_unidad_fuente(cambio.unidad_fuente),
            'fecha': fecha_norma.isoformat() if fecha_norma else None,
            'fecha_efecto': cambio.fecha_efecto.isoformat() if cambio.fecha_efecto else None,
            'alcance': parcial, 'parte_afectada': ref.get('parte_afectada', {}), 'cita': cambio.cita,
            'url_fuente': cambio.fuente.url_fuente, 'documento_id': cambio.fuente_id}


def actualizar_avisos(norma):
    eventos = list(CambioNormativo.objects.filter(norma_afectada=norma).exclude(estado_revision='descartado')
                   .select_related('articulo_afectado', 'fuente__norma').order_by('created_at'))
    Norma.objects.filter(pk=norma.pk).update(avisos_vigencia=[aviso(e) for e in eventos if not e.articulo_afectado_id])
    por_articulo = {}
    for evento in eventos:
        if evento.articulo_afectado_id:
            por_articulo.setdefault(evento.articulo_afectado_id, []).append(aviso(evento))
    for articulo in Articulo.objects.filter(norma=norma).only('pk'):
        Articulo.objects.filter(pk=articulo.pk).update(avisos_vigencia=por_articulo.get(articulo.pk, []))


@transaction.atomic
def registrar_cambios(documento, unidades, cambios, metadatos):
    documento.analisis_normativo = {**documento.analisis_normativo, 'cambios_aplicados': cambios}
    documento.metadatos = metadatos or {}
    documento.url_fuente = (metadatos or {}).get('url_fuente', '')
    documento.save(update_fields=['analisis_normativo', 'metadatos', 'url_fuente'])
    norma = documento.norma
    # Solo completar identidades ausentes. Una carga posterior no cambia la identidad.
    for campo, valor in [('tipo_norma', metadatos.get('tipo_norma', '')),
                         ('numero_norma', metadatos.get('numero_norma', '')),
                         ('fecha_norma', fecha(metadatos.get('fecha_norma'))),
                         ('fecha_publicacion', fecha(metadatos.get('fecha_publicacion')))]:
        if valor and not getattr(norma, campo):
            setattr(norma, campo, valor)
            norma.save(update_fields=[campo])
    for c in cambios:
        objetivo = documento.norma if c['origen'] == 'nota_editorial' and not c['norma'] else resolver_norma(c['norma'])
        numero = c.get('unidad', '')
        if c['origen'] == 'nota_editorial' and not numero:
            numero = c['unidad_fuente']
        articulo = resolver_unidad(objetivo, numero)
        # Una referencia a un artículo no resuelto nunca se degrada a afectación de toda la norma.
        if numero and not articulo:
            objetivo = None
        if c['operacion'] in ['general', 'temporal']:
            objetivo, articulo = None, None
        causante = c.get('causante') if c['origen'] == 'nota_editorial' else (
            f"{metadatos.get('tipo_norma', '')} {metadatos.get('numero_norma', '')}".strip() or documento.norma.nombre)
        fechac = fecha(c.get('fecha_causante')) if c['origen'] == 'nota_editorial' else fecha(metadatos.get('fecha_norma'))
        from .alcance_normativo_service import identificar_parte
        parte = identificar_parte(c['cita'], c['alcance'], articulo, c['operacion'], numero)
        referencia = {'norma': c['norma'], 'unidad': numero, 'alcance': parte['descripcion'] if parte['tipo'] == 'parcial' else c['alcance'], 'parte_afectada': parte}
        digest = hashlib.sha256(json.dumps([documento.pk, c], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        CambioNormativo.objects.get_or_create(huella=digest, defaults={
            'fuente': documento, 'norma_afectada': objetivo, 'articulo_afectado': articulo,
            'operacion': c['operacion'], 'unidad_fuente': c['unidad_fuente'], 'referencia': referencia,
            'cita': c['cita'], 'origen': c['origen'], 'norma_causante': causante,
            'fecha_norma_causante': fechac})
    # Resolver también eventos importados antes que la norma afectada.
    afectadas = {norma.pk}
    for evento in CambioNormativo.objects.filter(estado_revision='pendiente', norma_afectada__isnull=True):
        ref = evento.referencia
        if evento.operacion in ['general', 'temporal']:
            continue
        objetivo = resolver_norma(ref.get('norma', ''))
        articulo = resolver_unidad(objetivo, ref.get('unidad'))
        if objetivo and (not ref.get('unidad') or articulo):
            evento.norma_afectada = objetivo
            evento.articulo_afectado = articulo
            from .alcance_normativo_service import identificar_parte
            evento.referencia = {**ref, 'parte_afectada': identificar_parte(evento.cita, ref.get('alcance', ''), articulo, evento.operacion, ref.get('unidad', ''))}
            evento.save(update_fields=['norma_afectada', 'articulo_afectado', 'referencia'])
            afectadas.add(objetivo.pk)
    afectadas.update(CambioNormativo.objects.filter(fuente=documento, norma_afectada__isnull=False)
                     .values_list('norma_afectada_id', flat=True))
    for objetivo in Norma.objects.filter(pk__in=afectadas):
        actualizar_avisos(objetivo)


@transaction.atomic
def confirmar(cambio, datos, usuario):
    cambio = CambioNormativo.objects.select_for_update(of=('self',)).select_related('fuente__norma__jerarquia',
        'norma_afectada__jerarquia', 'articulo_afectado').get(pk=cambio.pk)
    if cambio.estado_revision != 'pendiente':
        raise ValueError('El cambio ya fue revisado. Recarga la lista.')
    if datos.get('descartar'):
        cambio.estado_revision = 'descartado'
    else:
        if cambio.operacion not in ['general', 'temporal']:
            destino_actual = evaluar_destino({**cambio.referencia, 'operacion': cambio.operacion,
                                              'origen': cambio.origen}, cambio.fuente.norma)
            if not destino_actual['encontrado']:
                raise ValueError(destino_actual['mensaje'])
            if datos.get('norma_afectada_id') and datos['norma_afectada_id'] != destino_actual['norma_id']:
                raise ValueError('La norma seleccionada no coincide con la referencia de la disposición.')
            if datos.get('articulo_afectado_id') and datos['articulo_afectado_id'] != destino_actual['articulo_id']:
                raise ValueError('El artículo seleccionado no coincide con la referencia de la disposición.')
            cambio.norma_afectada_id = destino_actual['norma_id']
            cambio.articulo_afectado_id = destino_actual['articulo_id']
            # Vaciar las relaciones cacheadas al actualizar sus IDs.
            cambio._state.fields_cache.pop('norma_afectada', None)
            cambio._state.fields_cache.pop('articulo_afectado', None)
        if datos.get('fecha_norma_causante'):
            cambio.fecha_norma_causante = fecha(datos['fecha_norma_causante'])
        if datos.get('norma_afectada_id'):
            objetivo = Norma.objects.get(pk=datos['norma_afectada_id'])
            if cambio.norma_afectada_id and cambio.norma_afectada_id != objetivo.pk:
                raise ValueError('La detección ya tiene un destino. Descártala si el destino es incorrecto.')
            articulo = resolver_unidad(objetivo, cambio.referencia.get('unidad'))
            if datos.get('articulo_afectado_id'):
                articulo = Articulo.objects.filter(pk=datos['articulo_afectado_id'], norma=objetivo).first()
                if not articulo: raise ValueError('El artículo seleccionado no pertenece a la norma afectada.')
            if cambio.referencia.get('unidad') and not articulo:
                raise ValueError('Debes identificar el artículo o disposición concretos.')
            cambio.norma_afectada, cambio.articulo_afectado = objetivo, articulo
        if cambio.operacion in ['general', 'temporal']:
            raise ValueError('Una cláusula general o temporal no confirma una derogación concreta.')
        if not cambio.norma_afectada:
            raise ValueError('La norma o unidad afectada todavía no tiene una coincidencia inequívoca en el catálogo.')
        from .alcance_normativo_service import identificar_parte, fragmento_literal
        ref = dict(cambio.referencia)
        parte = identificar_parte(cambio.cita, ref.get('alcance', ''), cambio.articulo_afectado, cambio.operacion, ref.get('unidad', ''))
        if parte['tipo'] == 'parcial' and datos.get('fragmento_afectado'):
            fragmento = fragmento_literal(cambio.articulo_afectado.contenido if cambio.articulo_afectado else '', datos['fragmento_afectado'])
            if fragmento and fragmento.strip() == cambio.articulo_afectado.contenido.strip():
                raise ValueError('Una derogación parcial no puede marcar todo el artículo como derogado.')
            if not fragmento:
                raise ValueError('El fragmento debe coincidir una sola vez con el texto original del artículo afectado.')
            parte.update(localizado=True, partes=[{'descripcion': ref.get('alcance', 'Fragmento verificado'),
                'fragmento': fragmento, 'localizado': True, 'verificado_manualmente': True}])
        if cambio.operacion == 'deroga' and parte['tipo'] == 'parcial' and not parte['localizado']:
            raise ValueError('No se identificó inequívocamente la parte derogada. Selecciona el fragmento exacto del artículo antes de confirmar.')
        cambio.referencia = {**ref, 'parte_afectada': parte}
        efecto = fecha(datos.get('fecha_efecto'))
        if not efecto:
            raise ValueError('Indica la fecha de efecto verificada en la fuente oficial.')
        if not cambio.fecha_norma_causante:
            raise ValueError('Falta la fecha verificada de la norma causante. Completa los metadatos al cargar el documento.')
        if efecto < cambio.fecha_norma_causante:
            raise ValueError('La fecha de efecto es anterior a la norma causante.')
        anterior = cambio.norma_afectada.fecha_norma or cambio.norma_afectada.fecha_publicacion
        if not anterior:
            raise ValueError('Falta la fecha de la norma afectada. Complétala en su ficha antes de confirmar la cronología.')
        if anterior and cambio.fecha_norma_causante <= anterior:
            raise ValueError('La norma causante debe ser posterior a la norma afectada; la misma fecha requiere estudiar la prioridad jurídica.')
        fuente = cambio.fuente.norma
        destino = cambio.norma_afectada
        if (cambio.origen != 'nota_editorial' and fuente.jerarquia_id and destino.jerarquia_id
                and fuente.jerarquia.nivel > destino.jerarquia.nivel
                and cambio.operacion in ['abroga', 'deroga', 'modifica', 'incorpora']):
            raise ValueError('La fuente tiene menor jerarquía; requiere evaluar el efecto jurídico, no una derogación automática.')
        if not datos.get('observacion', '').strip():
            raise ValueError('Registra el fundamento de la verificación de alcance, competencia y vigencia.')
        cambio.estado_revision = 'confirmado'
        cambio.fecha_efecto = efecto
        cambio.observacion = datos['observacion'].strip()
    cambio.revisado_por = usuario
    cambio.revisado_at = timezone.now()
    cambio.save()
    if cambio.norma_afectada:
        actualizar_avisos(cambio.norma_afectada)
    return cambio


def avisos_visibles(avisos):
    from zoneinfo import ZoneInfo
    hoy = timezone.now().astimezone(ZoneInfo('America/La_Paz')).date()
    resultado = []
    for original in avisos:
        dato = dict(original)
        efecto = fecha(dato.get('fecha_efecto'))
        if dato.get('estado') == 'confirmado' and efecto and efecto > hoy:
            dato['mensaje'] = 'Cambio confirmado con efecto futuro (' + efecto.isoformat() + '). ' + dato['mensaje']
            dato['estado'] = 'futuro'
        resultado.append(dato)
    return resultado


def estado_vigencia(avisos, es_articulo=False):
    """Estado jurídico confirmado, separado del estado administrativo del catálogo."""
    confirmados = [a for a in avisos_visibles(avisos) if a.get('estado') == 'confirmado']
    totales = [a for a in confirmados if a.get('parte_afectada', {}).get('tipo') != 'parcial'
               and clave(a.get('alcance', '')) in ['total', 'completo', 'articulo completo', 'norma completa']]
    if any(a.get('operacion') == 'abroga' for a in totales):
        return 'abrogado' if es_articulo else 'abrogada'
    if any(a.get('operacion') == 'deroga' for a in totales):
        return 'derogado' if es_articulo else 'derogada'
    if any(a.get('operacion') in ['deroga', 'abroga'] for a in confirmados):
        return 'derogado_parcialmente' if es_articulo else 'derogada_parcialmente'
    return 'sin_derogacion_confirmada'
