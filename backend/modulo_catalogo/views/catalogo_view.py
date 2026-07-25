from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.permissions.auditoria_mixin import AuditoriaMixin
from core.permissions.roles_permission import EsAbogado, EsAdmin, EsUsuarioAutenticado
from modulo_catalogo.models.articulo import Articulo
from modulo_catalogo.models.entidad import EntidadJuridica
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama import RamaDerecho
from modulo_catalogo.serializers.catalogo_serializer import (
    ArticuloListSerializer,
    ArticuloReadSerializer,
    ArticuloWriteSerializer,
    EntidadJuridicaListSerializer,
    EntidadJuridicaSerializer,
    NormaListSerializer,
    NormaSerializer,
    RamaDerechoListSerializer,
    RamaDerechoSerializer,
)

from rest_framework.decorators import action
from rest_framework.response import Response
# ---------------------------------------------------------------------------
# RamaDerecho
# ---------------------------------------------------------------------------

class RamaDerechoViewSet(AuditoriaMixin, ModelViewSet):
    """
    GET    /api/ramas/        — lista
    POST   /api/ramas/        — crear  [admin]
    GET    /api/ramas/{id}/   — detalle
    PATCH  /api/ramas/{id}/   — editar [admin]
    DELETE /api/ramas/{id}/   — soft-delete [admin]
    GET    /api/ramas/lista/  — compacto para selects
    """
    queryset        = RamaDerecho.objects.filter(estado=True).order_by("nombre")
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields   = ["nombre", "descripcion"]
    ordering_fields = ["nombre"]
    auditoria_tabla = "ramas_derecho"

    def get_serializer_class(self):
        if self.action == "lista":
            return RamaDerechoListSerializer
        return RamaDerechoSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve", "lista"]:
            return [EsUsuarioAutenticado()]
        return [EsAdmin()]

    def destroy(self, request, *args, **kwargs):
        instance        = self.get_object()
        instance.estado = False
        instance.save(update_fields=["estado"])
        self._auditar("DELETE", registro_id=instance.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="lista")
    def lista(self, request):
        qs = self.get_queryset()
        return Response(RamaDerechoListSerializer(qs, many=True).data)


    @action(detail=False, methods=["get"])
    def debug(self, request):
        return Response({
            "is_authenticated": request.user.is_authenticated,
            "usuario": str(request.user),
            "estado": getattr(request.user, "estado", None),
            "rol": getattr(getattr(request.user, "rol", None), "nombre", None),
        })

# ---------------------------------------------------------------------------
# Norma
# ---------------------------------------------------------------------------

class NormaViewSet(AuditoriaMixin, ModelViewSet):
    """
    GET    /api/normas/        — lista
    POST   /api/normas/        — crear  [admin]
    GET    /api/normas/{id}/   — detalle
    PATCH  /api/normas/{id}/   — editar [admin]
    DELETE /api/normas/{id}/   — soft-delete [admin]
    GET    /api/normas/lista/  — compacto para selects
    """
    queryset        = Norma.objects.filter(estado=True).order_by("nombre")
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields   = ["nombre", "sigla"]
    ordering_fields = ["nombre", "sigla"]
    auditoria_tabla = "normas"

    def get_serializer_class(self):
        if self.action == "lista":
            return NormaListSerializer
        return NormaSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve", "lista"]:
            return [EsUsuarioAutenticado()]
        return [EsAdmin()]

    def destroy(self, request, *args, **kwargs):
        instance        = self.get_object()
        instance.estado = False
        instance.save(update_fields=["estado"])
        self._auditar("DELETE", registro_id=instance.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="lista")
    def lista(self, request):
        qs = self.get_queryset()
        return Response(NormaListSerializer(qs, many=True).data)
    
    @action(detail=False, methods=["get"])
    def debug(self, request):
        return Response({
            "is_authenticated": request.user.is_authenticated,
            "usuario": str(request.user),
            "estado": getattr(request.user, "estado", None),
            "rol": getattr(getattr(request.user, "rol", None), "nombre", None),
        })


# ---------------------------------------------------------------------------
# EntidadJuridica
# ---------------------------------------------------------------------------

class EntidadJuridicaViewSet(AuditoriaMixin, ModelViewSet):
    """
    GET    /api/entidades/        — lista
    POST   /api/entidades/        — crear  [admin]
    GET    /api/entidades/{id}/   — detalle
    PATCH  /api/entidades/{id}/   — editar [admin]
    DELETE /api/entidades/{id}/   — soft-delete [admin]
    GET    /api/entidades/lista/  — compacto para selects
    """
    queryset        = EntidadJuridica.objects.filter(estado=True).order_by("nombre")
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields   = ["nombre", "descripcion"]
    ordering_fields = ["nombre"]
    auditoria_tabla = "entidades_juridicas"

    def get_serializer_class(self):
        if self.action == "lista":
            return EntidadJuridicaListSerializer
        return EntidadJuridicaSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve", "lista"]:
            return [EsUsuarioAutenticado()]
        return [EsAdmin()]

    def destroy(self, request, *args, **kwargs):
        instance            = self.get_object()
        instance.estado     = False
        instance.deleted_at = __import__("django.utils.timezone", fromlist=["now"]).now()
        instance.save(update_fields=["estado", "deleted_at"])
        self._auditar("DELETE", registro_id=instance.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="lista")
    def lista(self, request):
        qs = self.get_queryset()
        return Response(EntidadJuridicaListSerializer(qs, many=True).data)


# ---------------------------------------------------------------------------
# Articulo
# ---------------------------------------------------------------------------

class ArticuloViewSet(AuditoriaMixin, ModelViewSet):
    """
    GET    /api/articulos/                — lista con filtros
    POST   /api/articulos/                — crear [admin]
    GET    /api/articulos/{id}/           — detalle
    PATCH  /api/articulos/{id}/           — editar [admin]
    DELETE /api/articulos/{id}/           — soft-delete [admin]
    GET    /api/articulos/por_norma/      — filtrar por norma_id
    GET    /api/articulos/por_rama/       — filtrar por rama_id
    GET    /api/articulos/{id}/entidades/ — entidades del artículo
    """
    queryset        = (
        Articulo.objects
        .filter(estado=True)
        .select_related("norma", "rama")
        .prefetch_related("entidades")
        .order_by("norma", "numero_articulo")
    )
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields   = ["numero_articulo", "titulo", "contenido"]
    ordering_fields = ["numero_articulo", "jerarquia_normativa", "frecuencia_historica"]
    auditoria_tabla = "articulos"

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return ArticuloWriteSerializer
        if self.action == "list":
            return ArticuloListSerializer
        return ArticuloReadSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve", "por_norma", "por_rama", "entidades"]:
            return [EsUsuarioAutenticado()]
        return [EsAdmin()]

    def get_queryset(self):
        qs      = super().get_queryset()
        norma   = self.request.query_params.get("norma_id")
        rama    = self.request.query_params.get("rama_id")
        if norma:
            qs  = qs.filter(norma_id=norma)
        if rama:
            qs  = qs.filter(rama_id=rama)
        return qs

    def destroy(self, request, *args, **kwargs):
        instance        = self.get_object()
        instance.estado = False
        instance.save(update_fields=["estado"])
        self._auditar("DELETE", registro_id=instance.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="por_norma")
    def por_norma(self, request):
        """GET /api/articulos/por_norma/?norma_id=X"""
        norma_id = request.query_params.get("norma_id")
        if not norma_id:
            return Response(
                {"detail": "Parámetro norma_id requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs         = self.get_queryset().filter(norma_id=norma_id)
        serializer = ArticuloListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="por_rama")
    def por_rama(self, request):
        """GET /api/articulos/por_rama/?rama_id=X"""
        rama_id = request.query_params.get("rama_id")
        if not rama_id:
            return Response(
                {"detail": "Parámetro rama_id requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs         = self.get_queryset().filter(rama_id=rama_id)
        serializer = ArticuloListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="entidades")
    def entidades(self, request, pk=None):
        """GET /api/articulos/{id}/entidades/ — entidades jurídicas del artículo."""
        articulo  = self.get_object()
        from modulo_catalogo.serializers.catalogo_serializer import EntidadJuridicaListSerializer
        serializer = EntidadJuridicaListSerializer(
            articulo.entidades.filter(estado=True), many=True
        )
        return Response(serializer.data)
