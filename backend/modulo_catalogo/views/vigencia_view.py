from django.http import FileResponse
from django.core.files.storage import default_storage
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from core.permissions.roles_permission import EsAdmin, EsOperativo
from modulo_catalogo.models import CambioNormativo, DocumentoOficial, VersionArticulo, Norma
from modulo_catalogo.services.vigencia_service import confirmar

class CambioSerializer(serializers.ModelSerializer):
    fuente_nombre = serializers.CharField(source='fuente.norma.nombre', read_only=True)
    url_fuente = serializers.CharField(source='fuente.url_fuente', read_only=True)
    class Meta:
        model = CambioNormativo
        fields = '__all__'

class CambioNormativoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CambioSerializer
    queryset = CambioNormativo.objects.select_related('fuente__norma').all()
    def get_permissions(self):
        return [EsAdmin()] if self.action == 'revisar' else [EsOperativo()]
    def get_queryset(self):
        qs = super().get_queryset()
        for campo in ['estado_revision', 'norma_afectada', 'fuente']:
            valor = self.request.query_params.get(campo)
            if valor:
                qs = qs.filter(**{campo: valor})
        return qs
    @action(detail=True, methods=['post'])
    def revisar(self, request, pk=None):
        class Revision(serializers.Serializer):
            descartar = serializers.BooleanField(default=False)
            fecha_norma_causante = serializers.DateField(required=False)
            norma_afectada_id = serializers.PrimaryKeyRelatedField(queryset=Norma.objects.all(), required=False)
            fragmento_afectado = serializers.CharField(required=False, allow_blank=True, max_length=50000)
            articulo_afectado_id = serializers.IntegerField(required=False, min_value=1)
            fecha_efecto = serializers.DateField(required=False)
            observacion = serializers.CharField(required=False, allow_blank=True, max_length=3000)
        datos = Revision(data=request.data)
        datos.is_valid(raise_exception=True)
        try:
            valores = dict(datos.validated_data)
            if valores.get('norma_afectada_id'): valores['norma_afectada_id'] = valores['norma_afectada_id'].pk
            cambio = confirmar(self.get_object(), valores, request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=400)
        return Response(CambioSerializer(cambio).data)

class DocumentoOficialSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoOficial
        exclude = ['texto', 'ruta_archivo']

class DocumentoOficialViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DocumentoOficialSerializer
    permission_classes = [EsOperativo]
    queryset = DocumentoOficial.objects.filter(penal=True).order_by('-fecha_publicacion', '-pk')
    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('buscar'):
            qs = qs.filter(titulo__icontains=self.request.query_params['buscar'])
        return qs
    @action(detail=True, methods=['get'])
    def descargar(self, request, pk=None):
        documento = self.get_object()
        if documento.estado_descarga != 'descargado' or not default_storage.exists(documento.ruta_archivo):
            return Response({'detail': 'El PDF no está disponible; consulta la fuente o reintenta la sincronización.'}, status=404)
        return FileResponse(default_storage.open(documento.ruta_archivo, 'rb'), as_attachment=True,
                            filename=f'{documento.tipo}-{documento.numero or documento.identificador}.pdf')

class VersionArticuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = VersionArticulo
        fields = ['id', 'articulo', 'documento', 'titulo', 'contenido', 'created_at']

class VersionArticuloViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [EsOperativo]
    serializer_class = VersionArticuloSerializer
    queryset = VersionArticulo.objects.all()
    def get_queryset(self):
        qs = super().get_queryset()
        articulo = self.request.query_params.get('articulo')
        return qs.filter(articulo_id=articulo) if articulo else qs.none()
