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
            'jerarquia_id': data['jerarquia'].pk if data.get('jerarquia') else None}


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
            not isinstance(seleccion, list) or not seleccion
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
            articulos = dividir_por_articulos(extraer_texto_pdf_bytes(contenido))
        except (ValueError, RuntimeError) as exc:
            raise ValidationError({'archivo': str(exc)})
        if not articulos:
            raise ValidationError({'archivo': 'No se encontraron artículos. Revisa la capa de texto del PDF.'})
        filas = filas_actuales(data['norma'].pk if data.get('norma') else None, data['rama'].pk)
        if len({numero_clave(a['numero_articulo']) for a in filas}) != len(filas):
            raise ValidationError({'norma_id': 'Hay números duplicados en el catálogo. Corrígelos antes de actualizar.'})
        token = str(uuid.uuid4())
        cache.set(PREFIJO + token, {'usuario_id': request.user.pk, 'sha': hashlib.sha256(contenido).hexdigest(),
                                  'destino': datos_destino(data), 'huella': huella_catalogo(filas),
                                  'articulos': articulos}, timeout=1800)
        return Response({'revision_token': token, 'norma': data['norma'].nombre if data.get('norma') else data['nombre_documento'],
                         **comparar_articulos(articulos, filas)})
