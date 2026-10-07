from django.http import FileResponse
from django.db.models import Q
from django.core.files.storage import default_storage
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from core.permissions.roles_permission import EsAdmin, EsOperativo
from modulo_catalogo.models import CambioNormativo, DocumentoOficial, VersionArticulo, Norma, DisposicionNormativa, HistorialArticulo
from modulo_catalogo.services.vigencia_service import confirmar, evaluar_destino, describir_unidad_fuente, aviso

class CambioSerializer(serializers.ModelSerializer):
    destino_catalogo = serializers.SerializerMethodField()
    disposicion_fuente = serializers.SerializerMethodField()
    aviso = serializers.SerializerMethodField()

    def get_destino_catalogo(self, obj):
        return evaluar_destino({**obj.referencia, 'operacion': obj.operacion, 'origen': obj.origen}, obj.fuente.norma)

    def get_disposicion_fuente(self, obj):
        return describir_unidad_fuente(obj.unidad_fuente)

    def get_aviso(self, obj):
        return aviso(obj)

    fuente_nombre = serializers.CharField(source='fuente.norma.nombre', read_only=True)
    url_fuente = serializers.CharField(source='fuente.url_fuente', read_only=True)
    class Meta:
        model = CambioNormativo
        fields = '__all__'

class CambioNormativoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CambioSerializer
    queryset = CambioNormativo.objects.select_related('fuente__norma').all()
    def get_permissions(self):
        return [EsAdmin()] if self.action in ['revisar', 'restaurar', 'preparar_restauracion', 'preparar_revision'] else [EsOperativo()]
    def get_queryset(self):
        qs = super().get_queryset().exclude(unidad_fuente__startswith='DT ')
        if self.action in ['list', 'grupos']:
            from modulo_catalogo.services.vigencia_service import afectaciones_unicas
            ids = [e.pk for e in afectaciones_unicas(qs)]
            qs = qs.filter(pk__in=ids)
        for campo in ['estado_revision', 'norma_afectada', 'fuente']:
            valor = self.request.query_params.get(campo)
            if valor:
                qs = qs.filter(**{campo: valor})
        operaciones = [o for o in self.request.query_params.get('operaciones', '').split(',') if o in ['deroga', 'abroga']]
        if operaciones:
            qs = qs.filter(operacion__in=operaciones)
        buscar = self.request.query_params.get('buscar', '').strip()
        if buscar:
            qs = qs.filter(Q(norma_causante__icontains=buscar) | Q(cita__icontains=buscar)
                | Q(unidad_fuente__icontains=buscar) | Q(referencia__norma__icontains=buscar)
                | Q(referencia__unidad__icontains=buscar) | Q(referencia__alcance__icontains=buscar)
                | Q(fuente__norma__nombre__icontains=buscar))
        norma = self.request.query_params.get('norma')
        if norma:
            qs = qs.filter(Q(norma_afectada_id=norma) | Q(fuente__norma_id=norma))
        articulo = self.request.query_params.get('articulo')
        if articulo:
            from modulo_catalogo.models import Articulo
            norma_id = Articulo.objects.filter(pk=articulo).values_list('norma_id', flat=True).first()
            qs = qs.filter(Q(articulo_afectado_id=articulo) | Q(articulo_afectado__isnull=True, norma_afectada_id=norma_id)) if norma_id else qs.none()
        if self.request.query_params.get('fuente_norma'):
            qs = qs.filter(fuente__norma_id=self.request.query_params['fuente_norma'])
        return qs

    @action(detail=False, methods=['get'])
    def grupos(self, request):
        from modulo_catalogo.services.vigencia_service import afectaciones_unicas
        # Paginar disposiciones completas: sus destinos no se dividen entre páginas.
        grupos = {}
        tipo = request.query_params.get('tipo')
        qs = self.get_queryset().select_related('articulo_afectado', 'norma_afectada')
        if tipo in ['deroga', 'abroga', 'temporal']:
            qs = qs.filter(operacion=tipo)
        for cambio in afectaciones_unicas(qs):
            if tipo and aviso(cambio)['categoria_aviso'] != tipo:
                continue
            key = (cambio.fuente.norma_id, cambio.norma_causante, cambio.fecha_norma_causante,
                   cambio.unidad_fuente, ' '.join(cambio.cita.split()))
            grupos.setdefault(key, []).append(cambio)
        lista = list(grupos.values())
        pagina = self.paginate_queryset(lista)
        def serializar(grupo):
            primero = grupo[0]
            return {'id': primero.pk, 'norma_causante': primero.norma_causante or primero.fuente.norma.nombre,
                    'fecha': primero.fecha_norma_causante, 'disposicion_fuente': describir_unidad_fuente(primero.unidad_fuente),
                    'cita': primero.cita, 'url_fuente': primero.fuente.url_fuente, 'documento_id': primero.fuente_id,
                    'afectaciones': CambioSerializer(grupo, many=True).data}
        datos = [serializar(g) for g in (pagina if pagina is not None else lista)]
        return self.get_paginated_response(datos) if pagina is not None else Response(datos)

    @action(detail=True, methods=['post'], url_path='preparar-revision')
    def preparar_revision(self, request, pk=None):
        from modulo_catalogo.services.preview_normativo_service import preparar_revision
        try:
            return Response(preparar_revision(self.get_object(), request.data))
        except ValueError as error:
            return Response({'detail': str(error)}, status=400)

    @action(detail=True, methods=['get'], url_path='preparar-restauracion')
    def preparar_restauracion(self, request, pk=None):
        from modulo_catalogo.services.historial_articulos_service import comprobar_restauracion
        cambio = self.get_object()
        historiales = list(cambio.historial_articulos.select_related('articulo__norma', 'cambio__fuente', 'cambio__revisado_por', 'cambio__restaurado_por'))
        error = ''
        try:
            comprobar_restauracion(cambio, historiales)
        except ValueError as exc:
            error = str(exc)
        return Response({'cambio': CambioSerializer(cambio).data, 'historial': HistorialArticuloSerializer(historiales, many=True).data,
                         'restaurable': not error, 'detalle': error})

    @action(detail=True, methods=['post'])
    def restaurar(self, request, pk=None):
        from modulo_catalogo.services.historial_articulos_service import restaurar_confirmacion
        if request.data.get('confirmar') is not True:
            return Response({'detail': 'Confirma expresamente la restauración antes de continuar.'}, status=400)
        try:
            cambio = restaurar_confirmacion(self.get_object(), request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=400)
        return Response(CambioSerializer(cambio).data)

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


class DisposicionSerializer(serializers.ModelSerializer):
    norma_nombre = serializers.CharField(source='documento.norma.nombre', read_only=True)
    norma_id = serializers.IntegerField(source='documento.norma_id', read_only=True)
    avisos = serializers.SerializerMethodField()

    class Meta:
        model = DisposicionNormativa
        fields = ['id', 'documento', 'norma_id', 'norma_nombre', 'numero', 'tipo', 'titulo', 'contenido', 'avisos']

    def get_avisos(self, obj):
        return [aviso(c) for c in obj.documento.cambios_detectados.all()
                if c.unidad_fuente == obj.numero and c.estado_revision != 'descartado']


class DisposicionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DisposicionSerializer
    permission_classes = [EsOperativo]
    queryset = DisposicionNormativa.objects.filter(documento__vigente=True, documento__norma__estado=True).select_related(
        'documento__norma').prefetch_related('documento__cambios_detectados__articulo_afectado')

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('norma_id'):
            qs = qs.filter(documento__norma_id=self.request.query_params['norma_id'])
        if self.request.query_params.get('rama_id'):
            qs = qs.filter(documento__rama_id=self.request.query_params['rama_id'])
        return qs


class HistorialArticuloSerializer(serializers.ModelSerializer):
    numero_articulo = serializers.CharField(source='articulo.numero_articulo', read_only=True)
    norma = serializers.CharField(source='articulo.norma.nombre', read_only=True)
    operacion = serializers.CharField(source='cambio.operacion', read_only=True)
    norma_causante = serializers.CharField(source='cambio.norma_causante', read_only=True)
    fecha_efecto = serializers.DateField(source='cambio.fecha_efecto', read_only=True)
    revisado_at = serializers.DateTimeField(source='cambio.revisado_at', read_only=True)
    revisado_por = serializers.SerializerMethodField()
    estado_revision = serializers.CharField(source='cambio.estado_revision', read_only=True)
    restaurado_at = serializers.DateTimeField(source='cambio.restaurado_at', read_only=True)
    restaurado_por = serializers.SerializerMethodField()
    cita = serializers.CharField(source='cambio.cita', read_only=True)
    documento_id = serializers.IntegerField(source='cambio.fuente_id', read_only=True)
    disposicion_fuente = serializers.SerializerMethodField()

    class Meta:
        model = HistorialArticulo
        fields = ['id', 'articulo', 'numero_articulo', 'norma', 'titulo', 'operacion', 'norma_causante',
                  'fecha_efecto', 'revisado_at', 'revisado_por', 'cita', 'documento_id', 'disposicion_fuente',
                  'texto_antes', 'texto_despues', 'parte_afectada', 'aplicado', 'estado_revision', 'restaurado_at', 'restaurado_por']

    def get_restaurado_por(self, obj):
        return str(obj.cambio.restaurado_por) if obj.cambio.restaurado_por else None

    def get_revisado_por(self, obj):
        return str(obj.cambio.revisado_por) if obj.cambio.revisado_por else 'Usuario no disponible'

    def get_disposicion_fuente(self, obj):
        return describir_unidad_fuente(obj.cambio.unidad_fuente)


class HistorialArticuloViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [EsOperativo]
    serializer_class = HistorialArticuloSerializer
    queryset = HistorialArticulo.objects.select_related('articulo__norma', 'cambio__fuente', 'cambio__revisado_por', 'cambio__restaurado_por')

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('norma'):
            qs = qs.filter(articulo__norma_id=self.request.query_params['norma'])
        if self.request.query_params.get('articulo'):
            qs = qs.filter(articulo_id=self.request.query_params['articulo'])
        if self.request.query_params.get('operacion') in ['deroga', 'abroga']:
            qs = qs.filter(cambio__operacion=self.request.query_params['operacion'])
        return qs
