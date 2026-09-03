from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.permissions.auditoria_mixin import AuditoriaMixin
from core.permissions.roles_permission import EsAdmin, EsUsuarioAutenticado
from core.permissions.roles import ROL_ADMINISTRADOR
from modulo_usuarios.models.rol import Rol
from modulo_usuarios.serializers.rol_serializer import RolListSerializer, RolSerializer

# Acciones de detalle en las que un admin necesita poder ver/operar
# sobre un rol inactivo (para poder inspeccionarlo o reactivarlo).
_ROL_ACCIONES_VEN_INACTIVOS = ("retrieve", "update", "partial_update", "destroy", "activar")

class RolViewSet(AuditoriaMixin, ModelViewSet):
    """
    GET    /api/roles/           — lista roles activos (o filtrados por ?estado=)
    POST   /api/roles/           — crear rol  [admin]
    GET    /api/roles/{id}/      — detalle (incluye inactivos)  [admin]
    PATCH  /api/roles/{id}/      — actualizar [admin]
    DELETE /api/roles/{id}/      — soft-delete (estado=False) [admin]
    POST   /api/roles/{id}/activar/ — reactivar rol desactivado [admin]
    GET    /api/roles/lista/     — compacto para selects (solo activos)
    """
    serializer_class = RolSerializer
    filter_backends  = [SearchFilter, OrderingFilter]
    search_fields    = ["nombre", "descripcion"]
    ordering_fields  = ["nombre", "created_at"]
    auditoria_tabla  = "roles"

    def get_queryset(self):
        qs = Rol.objects.order_by("nombre")

        # ?estado=true|false — usado por el panel de administración
        # para alternar entre pestañas "Activos" / "Eliminados".
        estado = self.request.query_params.get("estado")
        if estado is not None:
            return qs.filter(estado=estado.lower() in ["true", "1"])

        # Acciones de detalle: un admin debe poder ver/operar sobre
        # un rol inactivo (por ejemplo, para reactivarlo).
        if self.action in _ROL_ACCIONES_VEN_INACTIVOS:
            return qs

        # list / lista sin filtro explícito: comportamiento seguro por
        # defecto, solo roles activos.
        return qs.filter(estado=True)

    def get_serializer_class(self):
        if self.action == "lista":
            return RolListSerializer
        return RolSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve", "lista"]:
            return [EsUsuarioAutenticado()]
        return [EsAdmin()]

    def destroy(self, request, *args, **kwargs):
        """Soft-delete: marca estado=False en lugar de eliminar."""
        instance = self.get_object()

        # El rol Administrador es un rol del sistema: nunca se desactiva,
        # sin importar si tiene usuarios asignados o no. Desactivarlo
        # dejaría al sistema sin forma de asignar administradores nuevos.
        if instance.nombre.strip().lower() == ROL_ADMINISTRADOR:
            return Response(
                {"detail": "El rol Administrador es un rol del sistema y no puede desactivarse."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if instance.usuarios.filter(estado=True).exists():
            return Response(
                {"detail": "No se puede desactivar un rol con usuarios activos asignados."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.estado = False
        instance.save(update_fields=["estado"])
        self._auditar("DELETE", registro_id=instance.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="lista")
    def lista(self, request):
        """Lista compacta para selects/desplegables (solo roles activos)."""
        qs         = self.get_queryset()
        serializer = RolListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="activar")
    def activar(self, request, pk=None):
        """POST /api/roles/{id}/activar/ — reactiva un rol desactivado."""
        instance        = self.get_object()
        instance.estado = True
        instance.save(update_fields=["estado"])
        self._auditar("UPDATE", registro_id=instance.pk, metadata={"campo": "estado", "valor": True})
        return Response({"detail": "Rol reactivado."}, status=status.HTTP_200_OK)