import hashlib
import uuid

from django.core.cache import cache
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from core.permissions.roles_permission import EsOperativo
from modulo_catalogo.serializers.carga_pdf_serializer import CargaArticulosPDFSerializer
from modulo_catalogo.services.carga_pdf_service import extraer_texto_pdf_bytes, dividir_por_articulos
from modulo_catalogo.services.revision_carga_service import comparar_articulos, filas_actuales, huella_catalogo, numero_clave

PREFIJO = 'revision_carga_pdf:'


def datos_destino(data):
    return {'norma_id': data['norma'].pk if data.get('norma') else None,
            'rama_id': data['rama'].pk,
            'nombre': data.get('nombre_documento', ''), 'sigla': data.get('sigla', ''),
            'jerarquia_id': data['jerarquia'].pk if data.get('jerarquia') else None,
            'motor': data.get('motor_lectura', ''), 'metadatos': data.get('metadatos', {}),
            'documento_oficial_id': data.get('documento_oficial_id')}


def validar_revision(data, usuario_id):
    token = data.get('revision_token')
    revision = cache.get(PREFIJO + (token or ''))
    archivo = data['archivo']
    contenido = archivo.read()
    archivo.seek(0)
    if not revision or revision['usuario_id'] != usuario_id:
        raise ValidationError({'revision_token': 'La revisión expiró. Vuelve a revisar el PDF.'})
    if revision['destino'] != datos_destino(data) or revision['sha'] != hashlib.sha256(contenido).hexdigest():
        raise ValidationError({'revision_token': 'Cambió el archivo o su destino. Vuelve a revisarlo.'})
    if huella_catalogo(filas_actuales(data['norma'].pk if data.get('norma') else None,
                                    data['rama'].pk)) != revision['huella']:
        raise ValidationError({'revision_token': 'El catálogo cambió. Vuelve a revisar el PDF.'})
    seleccion = data.get('articulos_seleccionados', [])
    numeros = {numero_clave(a['numero']) for a in revision['articulos']}
    if data.get('modo_actualizacion') == 'articulos' and (
            not isinstance(seleccion, list) or (not seleccion and not any(a.get('tipo_unidad') in ['final', 'derogatoria', 'abrogatoria'] for a in revision['articulos']))
            or any(not isinstance(n, str) or numero_clave(n) not in numeros for n in seleccion)):
        raise ValidationError({'articulos_seleccionados': 'Selecciona artículos presentes en el PDF revisado.'})
    return revision


class RevisionCargaPDFView(APIView):
    permission_classes = [EsOperativo]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = CargaArticulosPDFSerializer(data=request.data, context={'request': request, 'solo_revision': True})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        archivo = data['archivo']
        contenido = archivo.read()
        archivo.seek(0)
        try:
            from django.conf import settings
            from modulo_catalogo.services.lectura_normativa_service import extraer_unidades, detectar_cambios, extraer_metadatos
            motor = data.get('motor_lectura', settings.LECTURA_NORMATIVA_MOTOR)
            from modulo_catalogo.services.pdf_normativo_service import leer_pdf
            texto, advertencias = leer_pdf(contenido, motor, extraer_texto_pdf_bytes)
            progreso = getattr(request, 'progreso_normativo', None)
            articulos = extraer_unidades(texto, motor, advertencias, progreso)
            from modulo_catalogo.services.disposiciones_service import separar_unidades
            from modulo_catalogo.services.lectura_normativa_service import detectar_derogaciones_expresas
            articulos, disposiciones = separar_unidades(articulos)
            unidades_importadas = articulos + disposiciones
            cambios = detectar_cambios(unidades_importadas, progreso) if motor == 'qwen' else detectar_derogaciones_expresas(disposiciones)
            metadatos = {**(extraer_metadatos(texto) if motor == 'qwen' else {}), **data.get('metadatos', {})}
            oficial_id = data.get('documento_oficial_id')
            if oficial_id:
                from modulo_catalogo.models import DocumentoOficial
                oficial = DocumentoOficial.objects.filter(pk=oficial_id, estado_descarga='descargado').first()
                if not oficial or oficial.hash_pdf != hashlib.sha256(contenido).hexdigest():
                    raise ValueError('El PDF no coincide con el archivo oficial seleccionado.')
                metadatos.update({'url_fuente': oficial.url_fuente, 'tipo_norma': oficial.tipo,
                                 'numero_norma': oficial.numero})
                if oficial.fecha_publicacion:
                    metadatos['fecha_publicacion'] = oficial.fecha_publicacion.isoformat()
            destino = data.get('norma')
            if destino and destino.numero_norma and metadatos.get('numero_norma') and destino.numero_norma != metadatos['numero_norma']:
                raise ValueError('Este PDF pertenece a otra norma. Cárgalo como norma nueva; sus efectos se vincularán a la norma afectada.')
        except (ValueError, RuntimeError) as exc:
            raise ValidationError({'archivo': str(exc)})
        if not articulos and not disposiciones:
            raise ValidationError({'archivo': 'No se encontraron artículos. Revisa la capa de texto del PDF.'})
        filas = filas_actuales(data['norma'].pk if data.get('norma') else None, data['rama'].pk)
        if len({numero_clave(a['numero_articulo']) for a in filas}) != len(filas):
            raise ValidationError({'norma_id': 'Hay números duplicados en el catálogo. Corrígelos antes de actualizar.'})
        token = str(uuid.uuid4())
        cache.set(PREFIJO + token, {'usuario_id': request.user.pk, 'sha': hashlib.sha256(contenido).hexdigest(),
                                  'destino': datos_destino(data), 'huella': huella_catalogo(filas),
                                  'articulos': unidades_importadas, 'cambios': cambios, 'metadatos': metadatos,
                                  'motor': motor, 'documento_oficial_id': data.get('documento_oficial_id')}, timeout=7200)
        from modulo_catalogo.services.vigencia_service import preparar_avisos_revision
        avisos_revision = preparar_avisos_revision(cambios, metadatos, data.get('norma'),
            data['norma'].nombre if data.get('norma') else data['nombre_documento'])
        return Response({'revision_token': token, 'norma': data['norma'].nombre if data.get('norma') else data['nombre_documento'],
                         'disposiciones': disposiciones, 'motor': motor, 'cambios_normativos': avisos_revision, 'metadatos': metadatos, 'advertencias_lectura': advertencias,
                         **comparar_articulos(articulos, filas)})
