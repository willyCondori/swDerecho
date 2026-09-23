import os

from django.conf import settings
from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.permissions.auditoria_mixin import AuditoriaMixin, registrar_auditoria
from core.permissions.roles_permission import EsAdmin, EsOperativo
from modulo_catalogo.models.documento_norma import DocumentoNorma
from modulo_catalogo.serializers.documento_norma_serializer import DocumentoNormaSerializer


class DocumentoNormaViewSet(AuditoriaMixin, ModelViewSet):
    """
    GET    /api/catalogo/documentos-norma/            — lista [abogado, admin]
    GET    /api/catalogo/documentos-norma/{id}/        — detalle
    DELETE /api/catalogo/documentos-norma/{id}/        — eliminar físicamente [admin]
    GET    /api/catalogo/documentos-norma/{id}/descargar/ — descarga del archivo
    GET    /api/catalogo/documentos-norma/por_norma/   — filtrar por norma_id

    Son los PDF que se subieron para extraer artículos (ver
    CargaArticulosView): no hay endpoint de creación acá, ese registro lo
    crea la propia carga. Esta vista solo sirve para consultarlos,
    descargarlos o borrarlos — p. ej. si se cargó el archivo equivocado o
    ya no hace falta conservarlo.
    """
    queryset        = DocumentoNorma.objects.select_related("norma", "rama", "subido_por").order_by("-created_at")
    serializer_class= DocumentoNormaSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ["created_at", "nombre_original"]
    auditoria_tabla = "documentos_norma"
    http_method_names = ["get", "delete", "head", "options"]

    def get_permissions(self):
        if self.action == "destroy":
            return [EsAdmin()]
        return [EsOperativo()]

    def get_queryset(self):
        qs       = super().get_queryset()
        norma_id = self.request.query_params.get("norma_id")
        if norma_id:
            qs = qs.filter(norma_id=norma_id)
        return qs

    def destroy(self, request, *args, **kwargs):
        """Elimina registro y archivo físico. No toca los artículos ya extraídos."""
        instance      = self.get_object()
        ruta_absoluta = os.path.join(settings.MEDIA_ROOT, instance.ruta_archivo)
        if os.path.exists(ruta_absoluta):
            os.remove(ruta_absoluta)
        pk = instance.pk
        instance.delete()
        self._auditar("DELETE", registro_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="descargar")
    def descargar(self, request, pk=None):
        """GET /api/catalogo/documentos-norma/{id}/descargar/"""
        documento     = self.get_object()
        ruta_absoluta = os.path.join(settings.MEDIA_ROOT, documento.ruta_archivo)

        if not os.path.exists(ruta_absoluta):
            return Response(
                {"detail": "Archivo no encontrado en el servidor."},
                status=status.HTTP_404_NOT_FOUND,
            )

        registrar_auditoria(
            usuario=request.user,
            tabla="documentos_norma",
            accion="EXPORT",
            registro_id=documento.pk,
            request=request,
        )
        return FileResponse(
            open(ruta_absoluta, "rb"),
            as_attachment=True,
            filename=documento.nombre_original,
        )

    @action(detail=False, methods=["get"], url_path="por_norma")
    def por_norma(self, request):
        """GET /api/catalogo/documentos-norma/por_norma/?norma_id=X"""
        norma_id = request.query_params.get("norma_id")
        if not norma_id:
            return Response(
                {"detail": "Parámetro norma_id requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = self.get_queryset().filter(norma_id=norma_id)
        serializer = DocumentoNormaSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)
