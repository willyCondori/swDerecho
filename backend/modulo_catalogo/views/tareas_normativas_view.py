import logging
import threading
import uuid
from django.core.cache import cache
from django.db import close_old_connections
from rest_framework import serializers
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from core.permissions.roles_permission import EsOperativo
from .revision_carga_view import RevisionCargaPDFView

logger = logging.getLogger(__name__)

PREFIJO = 'tarea_normativa:'
_gaceta_lock = threading.Lock()

def iniciar(usuario, trabajo, final=None):
    task_id = str(uuid.uuid4())
    def guardar(estado, **campos):
        cache.set(PREFIJO + task_id, {'usuario_id': usuario.pk, 'estado': estado, **campos}, 7200)
    guardar('PENDING')
    def ejecutar():
        close_old_connections()
        try:
            guardar('STARTED')
            resultado = trabajo(lambda resumen: guardar('STARTED', resumen=resumen))
            guardar('SUCCESS', resultado=resultado)
        except Exception as exc:
            guardar('FAILURE', error=str(exc))
        finally:
            close_old_connections()
            if final: final()
    threading.Thread(target=ejecutar, name='normativa-' + task_id, daemon=True).start()
    return task_id

class RevisionAsincronaView(APIView):
    permission_classes = [EsOperativo]
    parser_classes = [MultiPartParser, FormParser]
    def post(self, request):
        # Copiar archivo a memoria antes de cerrar el upload temporal.
        from django.core.files.uploadedfile import SimpleUploadedFile
        from modulo_catalogo.serializers.carga_pdf_serializer import CargaArticulosPDFSerializer
        validacion = CargaArticulosPDFSerializer(data=request.data, context={'request': request, 'solo_revision': True})
        if not validacion.is_valid():
            logger.warning('Revisión PDF rechazada antes de iniciar. usuario=%s errores=%s',
                           request.user.pk, validacion.errors)
            raise serializers.ValidationError(validacion.errors)
        original = request.data.copy()
        archivo = request.FILES['archivo']
        archivo.seek(0)
        original['archivo'] = SimpleUploadedFile(archivo.name, archivo.read(), content_type='application/pdf')
        class Peticion:
            data = original
            user = request.user
        def trabajo(progreso):
            peticion = Peticion()
            peticion.progreso_normativo = progreso
            return RevisionCargaPDFView().post(peticion).data
        return Response({'task_id': iniciar(request.user, trabajo)}, status=202)

class SincronizarGacetaView(APIView):
    permission_classes = [EsOperativo]
    def post(self, request):
        class Opciones(serializers.Serializer):
            max_paginas = serializers.IntegerField(min_value=0, max_value=100000, default=1)
            desde = serializers.DateField(required=False)
            hasta = serializers.DateField(required=False)
        opciones = Opciones(data=request.data)
        opciones.is_valid(raise_exception=True)
        datos = opciones.validated_data
        if datos.get('desde') and datos.get('hasta') and datos['desde'] > datos['hasta']:
            return Response({'detail': 'El inicio debe ser anterior al fin.'}, status=400)
        if not _gaceta_lock.acquire(blocking=False):
            return Response({'detail': 'Ya hay una sincronización de Gaceta en curso.'}, status=409)
        from modulo_catalogo.services.gaceta_service import recolectar
        try:
            tarea = iniciar(request.user, lambda progreso: recolectar(**datos, progreso=progreso), _gaceta_lock.release)
        except Exception:
            _gaceta_lock.release()
            raise
        return Response({'task_id': tarea}, status=202)

class EstadoNormativoView(APIView):
    permission_classes = [EsOperativo]
    def get(self, request, task_id):
        dato = cache.get(PREFIJO + task_id)
        if not dato or dato['usuario_id'] != request.user.pk:
            return Response({'detail': 'Tarea no encontrada o expirada.'}, status=404)
        return Response({k: v for k, v in dato.items() if k != 'usuario_id'})
