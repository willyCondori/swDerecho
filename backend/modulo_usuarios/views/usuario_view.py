from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.permissions.auditoria_mixin import AuditoriaMixin
from core.permissions.roles_permission import EsAdmin, EsUsuarioAutenticado
from modulo_usuarios.models.usuario import Usuario
from modulo_usuarios.serializers.usuario_serializer import (
    UsuarioCreateSerializer,
    UsuarioReadSerializer,
    UsuarioUpdateSerializer,
    PerfilUsuarioWriteSerializer,
)
from core.permissions.roles import (
    ve_todo,
    rol_de,
    ROL_ADMINISTRADOR,
    administradores_activos_qs,
)


class UsuarioViewSet(AuditoriaMixin, ModelViewSet):
    """
    GET    /api/usuarios/               — lista [admin]
    POST   /api/usuarios/               — crear usuario + perfil [admin]
    GET    /api/usuarios/{id}/          — detalle [admin | propio]
    PATCH  /api/usuarios/{id}/          — actualizar rol/estado [admin]
    DELETE /api/usuarios/{id}/          — soft-delete [admin]
    PATCH  /api/usuarios/{id}/perfil/   — actualizar perfil propio
    POST   /api/usuarios/{id}/activar/  — reactivar usuario [admin]
    """
    queryset        = Usuario.objects.select_related("rol", "perfil").order_by("usuario")
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields   = ["usuario"]
    ordering_fields = ["usuario", "created_at", "last_login"]
    auditoria_tabla = "usuarios"

    def get_queryset(self):
        qs = super().get_queryset()
        # Admin y Abogado ven todos;
        if not ve_todo(self.request.user):
            qs = qs.filter(pk=self.request.user.pk)
        estado = self.request.query_params.get("estado")
        if estado is not None:
            qs = qs.filter(estado=estado.lower() in ["true", "1"])
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return UsuarioCreateSerializer
        if self.action in ["update", "partial_update"]:
            return UsuarioUpdateSerializer
        return UsuarioReadSerializer

    def get_permissions(self):
        if self.action in ["retrieve"]:
            return [EsUsuarioAutenticado()]
        if self.action == "perfil":
            return [EsUsuarioAutenticado()]
        return [EsAdmin()]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance == request.user:
            return Response(
                {"detail": "No puede desactivar su propia cuenta."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # No permitir que el sistema se quede sin ningún administrador activo.
        if rol_de(instance) == ROL_ADMINISTRADOR:
            otros_admins_activos = administradores_activos_qs().exclude(pk=instance.pk)
            if not otros_admins_activos.exists():
                return Response(
                    {"detail": "No se puede desactivar: es el único administrador activo del sistema."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        instance.estado = False
        instance.save(update_fields=["estado"])
        self._auditar("DELETE", registro_id=instance.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["patch"], url_path="perfil")
    def perfil(self, request, pk=None):
        """PATCH /api/usuarios/{id}/perfil/ — actualiza el perfil del propio usuario."""
        usuario = self.get_object()
        # Solo el propio usuario o admin puede editar
        if usuario != request.user and rol_de(request.user) != ROL_ADMINISTRADOR:
            return Response(
                {"detail": "No tiene permiso para editar el perfil de otro usuario."},
                status=status.HTTP_403_FORBIDDEN,
            )

        perfil     = getattr(usuario, "perfil", None)
        serializer = PerfilUsuarioWriteSerializer(
            perfil, data=request.data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(usuario=usuario)
        self._auditar("UPDATE", registro_id=usuario.pk, metadata={"campo": "perfil"})
        return Response({"detail": "Perfil actualizado correctamente."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="activar")
    def activar(self, request, pk=None):
        """POST /api/usuarios/{id}/activar/ — reactiva un usuario inactivo."""
        if rol_de(request.user) != ROL_ADMINISTRADOR:
            return Response(status=status.HTTP_403_FORBIDDEN)
        instance        = self.get_object()
        instance.estado = True
        instance.save(update_fields=["estado"])
        self._auditar("UPDATE", registro_id=instance.pk, metadata={"campo": "estado", "valor": True})
        return Response({"detail": "Usuario reactivado."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="desbloquear")
    def desbloquear(self, request, pk=None):
        """
        POST /api/usuarios/{id}/desbloquear/ — limpia el bloqueo temporal
        por intentos fallidos de login (ver LoginSerializer.validate en
        auth_serializer.py), sin esperar a que venza solo.
        """
        if rol_de(request.user) != ROL_ADMINISTRADOR:
            return Response(status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        instance.intentos_fallidos = 0
        instance.bloqueado_hasta = None
        instance.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
        self._auditar(
            "UPDATE",
            registro_id=instance.pk,
            metadata={"campo": "bloqueado_hasta", "origen": "desbloqueo_manual"},
        )
        return Response({"detail": "Usuario desbloqueado."}, status=status.HTTP_200_OK)