from urllib import request

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.encryption.aes_encryption import safe_decrypt
from core.permissions.auditoria_mixin import AuditoriaMixin
from core.permissions.roles_permission import EsAbogado, EsAdmin
from modulo_clientes.models.cliente import Cliente
from modulo_clientes.serializers.cliente_serializer import (
    ClienteListSerializer,
    ClienteReadSerializer,
    ClienteWriteSerializer,
)

MIN_CARACTERES_BUSQUEDA = 2


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
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cliente = serializer.save()
        self._auditar("CREATE", registro_id=cliente.pk)
        return Response(
            ClienteReadSerializer(cliente, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

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
        """Soft-delete: no elimina el registro, solo lo marca inactivo."""
        instance = self.get_object()
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
        serializer = ClienteListSerializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="casos")
    def casos(self, request, pk=None):
        """GET /api/clientes/{id}/casos/ — casos asociados al cliente."""
        from modulo_casos.serializers.caso_serializer import CasoListSerializer

        cliente = self.get_object()
        casos = cliente.casos.filter(estado=True).order_by("-created_at")
        return self._respuesta_paginada(casos, CasoListSerializer, request)

    @action(detail=False, methods=["get"], url_path="buscar")
    def buscar(self, request):
        """
        GET /api/clientes/buscar/?q=texto
        Búsqueda por nombre descifrado (itera y compara en memoria).

        No hay riesgo de inyección SQL: `query` nunca se concatena a
        SQL, solo se compara como texto plano en Python contra los
        valores ya descifrados.

        Nota de rendimiento: al estar los nombres cifrados no se
        puede filtrar en la base de datos, así que esto descifra
        TODOS los clientes activos en cada búsqueda. Con volumen
        alto de registros, considerar un índice de hash/búsqueda
        invertida (ej. HMAC determinístico del nombre normalizado)
        para no hacer O(n) descifrados por request.
        """
        query = request.query_params.get("q", "").strip().lower()
        if len(query) < MIN_CARACTERES_BUSQUEDA:
            return Response(
                {"detail": f"Ingrese al menos {MIN_CARACTERES_BUSQUEDA} caracteres para buscar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resultados = [
            cliente
            for cliente in self.get_queryset()
            if self._coincide_busqueda(cliente, query)
        ]

        serializer = ClienteReadSerializer(
            resultados, many=True, context={"request": request}
        )
        return Response(serializer.data)

    # ── Helpers internos ────────────────────────────────────────────

    def _coincide_busqueda(self, cliente, query):
        nombres   = safe_decrypt(cliente.nombres, fallback="").lower()
        apellidos = safe_decrypt(cliente.apellidos, fallback="").lower()
        return query in nombres or query in apellidos

    def _respuesta_paginada(self, qs, serializer_class, request):
        page = self.paginate_queryset(qs)
        serializer = serializer_class(
            page if page is not None else qs, many=True, context={"request": request}
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)