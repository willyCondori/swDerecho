import hashlib
import os

from django.conf import settings
from django.http import FileResponse
from backend.core.permissions.roles import ve_todo
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView

from core.permissions.auditoria_mixin import AuditoriaMixin, registrar_auditoria
from core.permissions.roles_permission import EsAbogado, EsAdmin, EsUsuarioAutenticado
from modulo_documentos.models.documento import (
    DocumentoCaso,
    DocumentoGenerado,
    PlantillaDocumento,
    TipoDoc,
)
from modulo_documentos.serializers.documento_serializer import (
    DocumentoCasoReadSerializer,
    DocumentoCasoWriteSerializer,
    DocumentoGeneradoSerializer,
    GenerarDocumentoSerializer,
    PlantillaDocumentoReadSerializer,
    PlantillaDocumentoWriteSerializer,
    TipoDocSerializer,
)

ROLES_VEN_TODOS = ["Administrador", "Abogado"]
    
# ---------------------------------------------------------------------------
# TipoDoc
# ---------------------------------------------------------------------------

class TipoDocViewSet(AuditoriaMixin, ModelViewSet):
    """
    GET    /api/tipo-doc/       — lista.
    POST   /api/tipo-doc/       — crear [admin]
    PATCH  /api/tipo-doc/{id}/  — editar [admin]
    DELETE /api/tipo-doc/{id}/  — eliminar [admin]
    """
    queryset        = TipoDoc.objects.all().order_by("tipo")
    serializer_class= TipoDocSerializer
    auditoria_tabla = "tipo_doc"

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [EsUsuarioAutenticado()]
        return [EsAdmin()]


# ---------------------------------------------------------------------------
# DocumentoCaso
# ---------------------------------------------------------------------------

class DocumentoCasoViewSet(AuditoriaMixin, ModelViewSet):
    """
    GET    /api/documentos/            — lista [abogado, admin]
    POST   /api/documentos/            — subir documento
    GET    /api/documentos/{id}/       — detalle
    DELETE /api/documentos/{id}/       — eliminar físicamente [admin]
    GET    /api/documentos/{id}/descargar/ — descarga del archivo
    GET    /api/documentos/por_caso/   — filtrar por caso_id
    """
    queryset        = DocumentoCaso.objects.select_related("caso", "tipo_documento").order_by("-created_at")
    filter_backends = [OrderingFilter]
    ordering_fields = ["created_at", "nombre_original"]
    auditoria_tabla = "documentos_caso"
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return DocumentoCasoWriteSerializer
        return DocumentoCasoReadSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [EsAdmin()]
        return [EsAbogado()]

    def get_queryset(self):
        qs      = super().get_queryset()
        user    = self.request.user
        rol     = getattr(user.rol, "nombre", "") if user.rol else ""
        caso_id = self.request.query_params.get("caso_id")

        if not ve_todo(user):
            qs = qs.filter(caso__usuario=user)
        if caso_id:
            qs = qs.filter(caso_id=caso_id)
        return qs

    def destroy(self, request, *args, **kwargs):
        """Elimina registro y archivo físico."""
        instance     = self.get_object()
        ruta_absoluta= os.path.join(settings.MEDIA_ROOT, instance.ruta_archivo)
        if os.path.exists(ruta_absoluta):
            os.remove(ruta_absoluta)
        pk = instance.pk
        instance.delete()
        self._auditar("DELETE", registro_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="descargar")
    def descargar(self, request, pk=None):
        """GET /api/documentos/{id}/descargar/ — descarga directa del archivo."""
        documento     = self.get_object()
        ruta_absoluta = os.path.join(settings.MEDIA_ROOT, documento.ruta_archivo)

        if not os.path.exists(ruta_absoluta):
            return Response(
                {"detail": "Archivo no encontrado en el servidor."},
                status=status.HTTP_404_NOT_FOUND,
            )

        registrar_auditoria(
            usuario=request.user,
            tabla="documentos_caso",
            accion="EXPORT",
            registro_id=documento.pk,
            request=request,
        )
        return FileResponse(
            open(ruta_absoluta, "rb"),
            as_attachment=True,
            filename=documento.nombre_original,
        )

    @action(detail=False, methods=["get"], url_path="por_caso")
    def por_caso(self, request):
        """GET /api/documentos/por_caso/?caso_id=X"""
        caso_id = request.query_params.get("caso_id")
        if not caso_id:
            return Response(
                {"detail": "Parámetro caso_id requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs         = self.get_queryset().filter(caso_id=caso_id)
        serializer = DocumentoCasoReadSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# PlantillaDocumento
# ---------------------------------------------------------------------------

class PlantillaDocumentoViewSet(AuditoriaMixin, ModelViewSet):
    """
    GET    /api/plantillas/        — lista [abogado, admin]
    POST   /api/plantillas/        — subir plantilla [admin]
    GET    /api/plantillas/{id}/   — detalle
    DELETE /api/plantillas/{id}/   — eliminar [admin]
    GET    /api/plantillas/{id}/descargar/ — descarga la plantilla
    """
    queryset         = PlantillaDocumento.objects.select_related("tipo_documento").order_by("nombre")
    filter_backends  = [SearchFilter, OrderingFilter]
    search_fields    = ["nombre", "descripcion"]
    ordering_fields  = ["nombre"]
    auditoria_tabla  = "plantillas_documento"
    http_method_names= ["get", "post", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return PlantillaDocumentoWriteSerializer
        return PlantillaDocumentoReadSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve", "descargar"]:
            return [EsAbogado()]
        return [EsAdmin()]

    def destroy(self, request, *args, **kwargs):
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
        """GET /api/plantillas/{id}/descargar/"""
        plantilla     = self.get_object()
        ruta_absoluta = os.path.join(settings.MEDIA_ROOT, plantilla.ruta_archivo)

        if not os.path.exists(ruta_absoluta):
            return Response(
                {"detail": "Archivo de plantilla no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return FileResponse(
            open(ruta_absoluta, "rb"),
            as_attachment=True,
            filename=os.path.basename(plantilla.ruta_archivo),
        )


# ---------------------------------------------------------------------------
# DocumentoGenerado
# ---------------------------------------------------------------------------

class DocumentoGeneradoViewSet(ModelViewSet):
    """
    GET    /api/documentos-generados/              — lista
    GET    /api/documentos-generados/{id}/         — detalle
    POST   /api/documentos-generados/generar/      — generar nuevo documento
    GET    /api/documentos-generados/{id}/descargar/ — descarga
    GET    /api/documentos-generados/por_caso/     — filtrar por caso_id
    """
    queryset         = (
        DocumentoGenerado.objects
        .select_related("caso", "plantilla")
        .order_by("-created_at")
    )
    serializer_class = DocumentoGeneradoSerializer
    http_method_names= ["get", "post", "head", "options"]

    def get_permissions(self):
        return [EsAbogado()]

    def get_queryset(self):
        qs   = super().get_queryset()
        user = self.request.user
        rol  = getattr(user.rol, "nombre", "") if user.rol else ""
        if not ve_todo(user):
            qs = qs.filter(caso__usuario=user)
        caso_id = self.request.query_params.get("caso_id")
        if caso_id:
            qs = qs.filter(caso_id=caso_id)
        return qs

    @action(detail=False, methods=["post"], url_path="generar")
    def generar(self, request):
        """
        POST /api/documentos-generados/generar/
        Body: { "caso_id": X, "plantilla_id": Y }
        Genera el .docx usando docxtpl y la plantilla indicada.
        """
        serializer = GenerarDocumentoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        caso_id      = serializer.validated_data["caso_id"]
        plantilla_id = serializer.validated_data["plantilla_id"]

        try:
            from modulo_documentos.services.generador_docx_service import GeneradorDocxService
            doc_generado = GeneradorDocxService.generar(caso_id, plantilla_id)

            registrar_auditoria(
                usuario=request.user,
                tabla="documentos_generados",
                accion="CREATE",
                registro_id=doc_generado.pk,
                request=request,
                metadata={"caso_id": caso_id, "plantilla_id": plantilla_id},
            )

            return Response(
                DocumentoGeneradoSerializer(doc_generado, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"detail": f"Error al generar el documento: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], url_path="descargar")
    def descargar(self, request, pk=None):
        """GET /api/documentos-generados/{id}/descargar/"""
        documento     = self.get_object()
        ruta_absoluta = os.path.join(settings.MEDIA_ROOT, documento.ruta_archivo)

        if not os.path.exists(ruta_absoluta):
            return Response(
                {"detail": "Documento generado no encontrado en el servidor."},
                status=status.HTTP_404_NOT_FOUND,
            )

        registrar_auditoria(
            usuario=request.user,
            tabla="documentos_generados",
            accion="EXPORT",
            registro_id=documento.pk,
            request=request,
        )

        nombre = f"jurisprudencia_{documento.caso.codigo}.docx"
        return FileResponse(
            open(ruta_absoluta, "rb"),
            as_attachment=True,
            filename=nombre,
        )

    @action(detail=False, methods=["get"], url_path="por_caso")
    def por_caso(self, request):
        """GET /api/documentos-generados/por_caso/?caso_id=X"""
        caso_id = request.query_params.get("caso_id")
        if not caso_id:
            return Response(
                {"detail": "Parámetro caso_id requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = self.get_queryset().filter(caso_id=caso_id)
        return Response(
            DocumentoGeneradoSerializer(qs, many=True, context={"request": request}).data
        )
