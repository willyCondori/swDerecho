from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.encryption.aes_encryption import decrypt
from core.permissions.auditoria_mixin import AuditoriaMixin
from core.permissions.roles_permission import EsAbogado, EsAdmin
from modulo_clientes.models.cliente import Cliente
from modulo_clientes.serializers.cliente_serializer import (
    ClienteListSerializer,
    ClienteReadSerializer,
    ClienteWriteSerializer,
)


class ClienteViewSet(AuditoriaMixin, ModelViewSet):
    """
    GET    /api/clientes/           — lista [abogado, admin]
    POST   /api/clientes/           — crear [abogado, admin]
    GET    /api/clientes/{id}/      — detalle [abogado, admin]
    PATCH  /api/clientes/{id}/      — actualizar [abogado, admin]
    DELETE /api/clientes/{id}/      — soft-delete [admin]
    GET    /api/clientes/lista/     — compacto para selects
    GET    /api/clientes/{id}/casos/— casos del cliente
    GET    /api/clientes/buscar/    — búsqueda por nombre (descifrado)
    """
    queryset        = Cliente.objects.filter(estado=True).order_by("-created_at")
    filter_backends = [OrderingFilter]
    ordering_fields = ["id", "created_at"]
    auditoria_tabla = "clientes"

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return ClienteWriteSerializer
        if self.action == "lista":
            return ClienteListSerializer
        return ClienteReadSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [EsAdmin()]
        return [EsAbogado()]

    def destroy(self, request, *args, **kwargs):
        """Soft-delete."""
        instance        = self.get_object()
        if instance.casos.filter(estado=True).exists():
            return Response(
                {"detail": "No se puede desactivar un cliente con casos activos."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.estado = False
        instance.save(update_fields=["estado"])
        self._auditar("DELETE", registro_id=instance.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="lista")
    def lista(self, request):
        """GET /api/clientes/lista/ — compacto para selects."""
        qs         = self.get_queryset()
        serializer = ClienteListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="casos")
    def casos(self, request, pk=None):
        """GET /api/clientes/{id}/casos/ — casos asociados al cliente."""
        from modulo_casos.serializers.caso_serializer import CasoListSerializer
        cliente = self.get_object()
        casos   = cliente.casos.filter(estado=True).order_by("-created_at")
        page    = self.paginate_queryset(casos)
        if page is not None:
            return self.get_paginated_response(
                CasoListSerializer(page, many=True, context={"request": request}).data
            )
        return Response(
            CasoListSerializer(casos, many=True, context={"request": request}).data
        )

    @action(detail=False, methods=["get"], url_path="buscar")
    def buscar(self, request):
        """
        GET /api/clientes/buscar/?q=texto
        Búsqueda por nombre descifrado (itera y compara).
        Nota: para producción con muchos registros considerar
        un índice de hash o búsqueda invertida.
        """
        query = request.query_params.get("q", "").strip().lower()
        if len(query) < 2:
            return Response(
                {"detail": "Ingrese al menos 2 caracteres para buscar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resultados = []
        for cliente in self.get_queryset():
            try:
                nombres   = decrypt(cliente.nombres).lower()
                apellidos = decrypt(cliente.apellidos).lower()
                if query in nombres or query in apellidos:
                    resultados.append(cliente)
            except Exception:
                continue

        serializer = ClienteReadSerializer(
            resultados, many=True, context={"request": request}
        )
        return Response(serializer.data)
