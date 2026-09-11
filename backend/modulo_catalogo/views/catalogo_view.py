from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.permissions.auditoria_mixin import AuditoriaMixin
from core.permissions.roles_permission import EsAbogado, EsAdmin, EsUsuarioAutenticado
from modulo_catalogo.models.articulo import Articulo
from modulo_catalogo.models.entidad import EntidadJuridica
from modulo_catalogo.models.jerarquia import jerarquia as Jerarquia
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama import RamaDerecho
from modulo_catalogo.serializers.catalogo_serializer import (
    ArticuloListSerializer,
    ArticuloReadSerializer,
    ArticuloWriteSerializer,
    EntidadJuridicaListSerializer,
    EntidadJuridicaSerializer,
    JerarquiaListSerializer,
    JerarquiaSerializer,
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
    GET    /api/ramas/              — lista ramas activas (o filtradas por ?estado=)
    POST   /api/ramas/              — crear  [admin]
    GET    /api/ramas/{id}/         — detalle (incluye inactivas)  [admin]
    PATCH  /api/ramas/{id}/         — editar [admin]
    DELETE /api/ramas/{id}/         — soft-delete [admin]
    POST   /api/ramas/{id}/activar/ — reactivar rama desactivada [admin]
    GET    /api/ramas/lista/        — compacto para selects (solo activas)
    """
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields   = ["nombre", "descripcion"]
    ordering_fields = ["nombre"]
    auditoria_tabla = "ramas_derecho"

    # Acciones de detalle en las que un admin necesita poder ver/operar
    # sobre una rama inactiva (para poder inspeccionarla o reactivarla).
    _ACCIONES_VEN_INACTIVAS = ("retrieve", "update", "partial_update", "destroy", "activar")

    def get_queryset(self):
        qs = RamaDerecho.objects.order_by("nombre")

        # ?estado=true|false — usado por el panel de administración
        # para alternar entre pestañas "Activas" / "Eliminadas".
        estado = self.request.query_params.get("estado")
        if estado is not None:
            return qs.filter(estado=estado.lower() in ["true", "1"])

        if self.action in self._ACCIONES_VEN_INACTIVAS:
            return qs

        # list / lista sin filtro explícito: comportamiento seguro por
        # defecto, solo ramas activas.
        return qs.filter(estado=True)

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

    @action(detail=True, methods=["post"], url_path="activar")
    def activar(self, request, pk=None):
        """POST /api/ramas/{id}/activar/ — reactiva una rama desactivada."""
        instance        = self.get_object()
        instance.estado = True
        instance.save(update_fields=["estado"])
        self._auditar("UPDATE", registro_id=instance.pk, metadata={"campo": "estado", "valor": True})
        return Response({"detail": "Rama de derecho reactivada."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def debug(self, request):
        return Response({
            "is_authenticated": request.user.is_authenticated,
            "usuario": str(request.user),
            "estado": getattr(request.user, "estado", None),
            "rol": getattr(getattr(request.user, "rol", None), "nombre", None),
        })

# ---------------------------------------------------------------------------
# Jerarquia
# ---------------------------------------------------------------------------

class JerarquiaViewSet(AuditoriaMixin, ModelViewSet):
    """
    GET    /api/jerarquias/              — lista jerarquías activas (o filtradas por ?estado=)
    POST   /api/jerarquias/              — crear  [admin]
    GET    /api/jerarquias/{id}/         — detalle (incluye inactivas)  [admin]
    PATCH  /api/jerarquias/{id}/         — editar [admin]
    DELETE /api/jerarquias/{id}/         — soft-delete [admin]
    POST   /api/jerarquias/{id}/activar/ — reactivar jerarquía desactivada [admin]
    GET    /api/jerarquias/lista/        — compacto para selects (al crear/editar una Norma)
    """
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields   = ["nombre"]
    ordering_fields = ["nivel", "nombre"]
    auditoria_tabla = "jerarquias"

    # Acciones de detalle en las que un admin necesita poder ver/operar
    # sobre una jerarquía inactiva (para poder inspeccionarla o reactivarla).
    _ACCIONES_VEN_INACTIVAS = ("retrieve", "update", "partial_update", "destroy", "activar")

    def get_queryset(self):
        qs = Jerarquia.objects.order_by("nivel")

        # ?estado=true|false — usado por el panel de administración
        # para alternar entre pestañas "Activas" / "Eliminadas".
        estado = self.request.query_params.get("estado")
        if estado is not None:
            return qs.filter(estado=estado.lower() in ["true", "1"])

        if self.action in self._ACCIONES_VEN_INACTIVAS:
            return qs

        # list / lista sin filtro explícito: comportamiento seguro por
        # defecto, solo jerarquías activas.
        return qs.filter(estado=True)

    def get_serializer_class(self):
        if self.action == "lista":
            return JerarquiaListSerializer
        return JerarquiaSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve", "lista"]:
            return [EsUsuarioAutenticado()]
        return [EsAdmin()]

    @staticmethod
    def _conflicto_response(nivel, existente):
        return Response(
            {
                "conflicto": True,
                "nivel": nivel,
                "existente": {"id": existente.id, "nombre": existente.nombre},
                "detail": f'Esta jerarquía es mayor que "{existente.nombre}".',
            },
            status=status.HTTP_409_CONFLICT,
        )

    def create(self, request, *args, **kwargs):
        """
        Al crear una jerarquía con un nivel ya ocupado por otra activa,
        se responde 409 con los datos de la jerarquía existente para que
        el cliente confirme el reemplazo ("Esta jerarquía es mayor que
        xxxx"). Si el cliente reenvía la petición con
        confirmar_reemplazo=true, se corren hacia abajo (nivel + 1) la
        jerarquía existente y todas las que tengan un nivel mayor o igual
        al nuevo (guardando en nivel_anterior el nivel que tenían antes
        del corrimiento), y luego se crea la jerarquía en el nivel
        solicitado.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        nivel     = serializer.validated_data["nivel"]
        confirmar = serializer.validated_data.get("confirmar_reemplazo", False)

        existente = Jerarquia.objects.filter(nivel=nivel, estado=True).first()
        if existente and not confirmar:
            return self._conflicto_response(nivel, existente)

        with transaction.atomic():
            if existente:
                Jerarquia.objects.filter(nivel__gte=nivel, estado=True).update(
                    nivel_anterior=F("nivel"), nivel=F("nivel") + 1
                )
            self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """
        Misma lógica de confirmación/cascada que create(), aplicada cuando
        se edita el nivel de una jerarquía existente hacia uno ya ocupado
        por otra jerarquía activa. Antes de aplicar el nuevo nivel (propio
        o de las jerarquías corridas en cascada) se guarda el nivel
        anterior en nivel_anterior, para poder revertir el cambio desde
        "Editar" más adelante.
        """
        partial  = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        nuevo_nivel = serializer.validated_data.get("nivel", instance.nivel)
        confirmar   = serializer.validated_data.get("confirmar_reemplazo", False)

        if nuevo_nivel != instance.nivel:
            nivel_anterior_propio = instance.nivel
            existente = (
                Jerarquia.objects.filter(nivel=nuevo_nivel, estado=True)
                .exclude(pk=instance.pk)
                .first()
            )
            if existente and not confirmar:
                return self._conflicto_response(nuevo_nivel, existente)

            with transaction.atomic():
                if existente:
                    (
                        Jerarquia.objects
                        .filter(nivel__gte=nuevo_nivel, estado=True)
                        .exclude(pk=instance.pk)
                        .update(nivel_anterior=F("nivel"), nivel=F("nivel") + 1)
                    )
                instance_actualizada = serializer.save(nivel_anterior=nivel_anterior_propio)
                self._auditar("UPDATE", registro_id=instance_actualizada.pk)
        else:
            self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Soft-delete + cascada: al eliminar una jerarquía de nivel N, todas
        las jerarquías activas con nivel > N bajan un puesto (N+1 pasa a
        ser N, N+2 pasa a ser N+1, etc.), guardando en nivel_anterior el
        nivel que tenían antes de correrse. La jerarquía eliminada NO
        cambia su propio nivel: lo conserva tal cual para poder
        reactivarse correctamente más adelante (ver `activar`).
        """
        instance        = self.get_object()
        nivel_eliminado = instance.nivel
        with transaction.atomic():
            instance.estado = False
            instance.save(update_fields=["estado"])
            Jerarquia.objects.filter(nivel__gt=nivel_eliminado, estado=True).update(
                nivel_anterior=F("nivel"), nivel=F("nivel") - 1
            )
        self._auditar("DELETE", registro_id=instance.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="lista")
    def lista(self, request):
        qs = self.get_queryset()
        return Response(JerarquiaListSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="activar")
    def activar(self, request, pk=None):
        """
        POST /api/jerarquias/{id}/activar/ — reactiva una jerarquía
        desactivada, en el nivel original que conservaba desde que fue
        eliminada. Si ese nivel ya está ocupado por otra jerarquía activa
        (por ejemplo, porque los niveles se corrieron mientras estaba
        eliminada), se aplica la misma lógica de confirmación/cascada que
        create()/update(): responde 409 pidiendo confirmar_reemplazo=true
        para correr hacia abajo a la jerarquía existente y a las
        siguientes antes de reactivar.
        """
        instance  = self.get_object()
        nivel     = instance.nivel
        confirmar = bool(request.data.get("confirmar_reemplazo", False))

        existente = (
            Jerarquia.objects.filter(nivel=nivel, estado=True)
            .exclude(pk=instance.pk)
            .first()
        )
        if existente and not confirmar:
            return self._conflicto_response(nivel, existente)

        with transaction.atomic():
            if existente:
                (
                    Jerarquia.objects
                    .filter(nivel__gte=nivel, estado=True)
                    .exclude(pk=instance.pk)
                    .update(nivel_anterior=F("nivel"), nivel=F("nivel") + 1)
                )
            instance.estado = True
            instance.save(update_fields=["estado"])

        self._auditar("UPDATE", registro_id=instance.pk, metadata={"campo": "estado", "valor": True})
        return Response({"detail": "Jerarquía reactivada."}, status=status.HTTP_200_OK)


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
    queryset        = (
        Norma.objects
        .filter(estado=True)
        .select_related("jerarquia")
        .order_by("nombre")
    )
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields   = ["nombre", "sigla"]
    ordering_fields = ["nombre", "sigla", "jerarquia__nivel"]
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
    GET    /api/entidades/              — lista entidades activas (o filtradas por ?estado=)
    POST   /api/entidades/              — crear  [admin]
    GET    /api/entidades/{id}/         — detalle (incluye inactivas)  [admin]
    PATCH  /api/entidades/{id}/         — editar [admin]
    DELETE /api/entidades/{id}/         — soft-delete [admin]
    POST   /api/entidades/{id}/activar/ — reactivar entidad desactivada [admin]
    GET    /api/entidades/lista/        — compacto para selects (solo activas)
    """
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields   = ["nombre", "descripcion"]
    ordering_fields = ["nombre"]
    auditoria_tabla = "entidades_juridicas"

    # Acciones de detalle en las que un admin necesita poder ver/operar
    # sobre una entidad inactiva (para poder inspeccionarla o reactivarla).
    _ACCIONES_VEN_INACTIVAS = ("retrieve", "update", "partial_update", "destroy", "activar")

    def get_queryset(self):
        qs = EntidadJuridica.objects.order_by("nombre")

        # ?estado=true|false — usado por el panel de administración
        # para alternar entre pestañas "Activas" / "Eliminadas".
        estado = self.request.query_params.get("estado")
        if estado is not None:
            return qs.filter(estado=estado.lower() in ["true", "1"])

        if self.action in self._ACCIONES_VEN_INACTIVAS:
            return qs

        # list / lista sin filtro explícito: comportamiento seguro por
        # defecto, solo entidades activas.
        return qs.filter(estado=True)

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
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["estado", "deleted_at"])
        self._auditar("DELETE", registro_id=instance.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="lista")
    def lista(self, request):
        qs = self.get_queryset()
        return Response(EntidadJuridicaListSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="activar")
    def activar(self, request, pk=None):
        """POST /api/entidades/{id}/activar/ — reactiva una entidad desactivada."""
        instance            = self.get_object()
        instance.estado     = True
        instance.deleted_at = None
        instance.save(update_fields=["estado", "deleted_at"])
        self._auditar("UPDATE", registro_id=instance.pk, metadata={"campo": "estado", "valor": True})
        return Response({"detail": "Entidad jurídica reactivada."}, status=status.HTTP_200_OK)


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
        .select_related("norma", "norma__jerarquia", "rama")
        .prefetch_related("entidades")
        .order_by("norma", "numero_articulo")
    )
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields   = ["numero_articulo", "titulo", "contenido"]
    ordering_fields = ["numero_articulo", "norma__jerarquia__nivel", "frecuencia_historica"]
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