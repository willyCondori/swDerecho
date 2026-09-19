from urllib import request

from django.db.models import Count, F, Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.encryption.aes_encryption import safe_decrypt
from core.permissions.auditoria_mixin import AuditoriaMixin, registrar_auditoria
from core.permissions.roles_permission import EsAbogado, EsOperativo
from modulo_clientes.models.cliente import Cliente
from modulo_clientes.serializers.cliente_serializer import (
    ClienteListSerializer,
    ClientePapeleraSerializer,
    ClienteReadSerializer,
    ClienteWriteSerializer,
)
from modulo_clientes.services.papelera_service import (
    ClienteConCasosActivosError,
    enviar_cliente_a_papelera,
    restaurar_cliente,
)

MIN_CARACTERES_BUSQUEDA = 2


class ClienteViewSet(AuditoriaMixin, ModelViewSet):
    """
    GET    /api/clientes/           — lista [admin/abogado: todo | asistente: lectura]
    POST   /api/clientes/           — crear [admin, abogado]
    GET    /api/clientes/{id}/      — detalle
    PATCH  /api/clientes/{id}/      — actualizar [admin, abogado]
    DELETE /api/clientes/{id}/      — envía el cliente a la papelera (soft-delete) [admin, abogado].
                                      Con casos activos responde 400 (code=cliente_con_casos_activos);
                                      con ?eliminar_casos=true los envía a la papelera junto con él.
    GET    /api/clientes/papelera/  — clientes eliminados, más recientes primero [admin, abogado]
    POST   /api/clientes/{id}/restaurar/ — restaura un cliente y los casos que se eliminaron con él [admin, abogado]
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

    def get_queryset(self):
        if self.action in ("papelera", "restaurar"):
            # Papelera: solo clientes eliminados. El resto de las acciones
            # nunca ve clientes con estado=False (404).
            return Cliente.objects.filter(estado=False).select_related(
                "eliminado_por", "eliminado_por__perfil"
            )
        return super().get_queryset()

    def get_permissions(self):
        if self.action in ("papelera", "restaurar"):
            # Administrador y Abogado; el Asistente no ve la papelera.
            return [EsAbogado()]
        return [EsOperativo()]

    def destroy(self, request, *args, **kwargs):
        """
        Soft-delete: envía el cliente a la papelera (se puede restaurar).

        Si tiene casos activos responde 400 con code=cliente_con_casos_activos
        y casos_activos=N, sin cambiar nada. Con ?eliminar_casos=true esos
        casos también se envían a la papelera, y volverán al restaurar al cliente.
        """
        instance = self.get_object()
        eliminar_casos = request.query_params.get("eliminar_casos", "").lower() in ("1", "true", "si", "sí")
        try:
            casos = enviar_cliente_a_papelera(instance, request.user, eliminar_casos=eliminar_casos)
        except ClienteConCasosActivosError as e:
            return Response(
                {
                    "detail": f"No se puede eliminar un cliente con casos activos. {e}",
                    "code": "cliente_con_casos_activos",
                    "casos_activos": e.casos_activos,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        self._auditar_casos(casos, "DELETE", instance.pk)
        self._auditar(
            "DELETE",
            registro_id=instance.pk,
            metadata={"casos_eliminados": [c.pk for c in casos]} if casos else None,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="papelera")
    def papelera(self, request):
        """
        GET /api/clientes/papelera/ — clientes eliminados, los enviados más
        recientemente primero (los eliminados antes de la papelera, sin fecha,
        al final). Acepta ?search= (nombre o apellido, mínimo 2 caracteres).
        Cada fila trae `casos_para_restaurar`: los casos que se eliminaron
        junto con el cliente y que volverán al restaurarlo.
        """
        qs = (
            self.get_queryset()
            .annotate(
                casos_para_restaurar=Count(
                    "casos",
                    filter=Q(casos__estado=False, casos__eliminado_con_cliente=True),
                )
            )
            .order_by(F("eliminado_at").desc(nulls_last=True), "-created_at")
        )
        query = request.query_params.get("search", "").strip().lower()
        filas = qs
        if len(query) >= MIN_CARACTERES_BUSQUEDA:
            # Nombres cifrados: se filtra en Python (la papelera es chica).
            filas = [c for c in qs if self._coincide_busqueda(c, query)]

        page = self.paginate_queryset(filas)
        serializer = ClientePapeleraSerializer(
            page if page is not None else filas, many=True,
            context=self.get_serializer_context(),
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="restaurar")
    def restaurar(self, request, pk=None):
        """
        POST /api/clientes/{id}/restaurar/ — devuelve el cliente a la lista de
        clientes activos y restaura los casos que se eliminaron junto con él.
        Responde el cliente con `casos_restaurados` (cantidad).
        """
        cliente = self.get_object()
        casos = restaurar_cliente(cliente, request.user)

        self._auditar_casos(casos, "UPDATE", cliente.pk)
        self._auditar(
            "UPDATE",
            registro_id=cliente.pk,
            metadata={"accion": "restaurar", "casos_restaurados": [c.pk for c in casos]},
        )
        data = ClienteReadSerializer(cliente, context=self.get_serializer_context()).data
        data["casos_restaurados"] = len(casos)
        return Response(data, status=status.HTTP_200_OK)

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

    def _auditar_casos(self, casos, accion, cliente_id):
        """Un registro de auditoría por cada caso afectado en cascada por el cliente."""
        eliminando = accion == "DELETE"
        metadata = {"motivo": "cliente_eliminado" if eliminando else "cliente_restaurado", "cliente_id": cliente_id}
        if not eliminando:
            metadata["accion"] = "restaurar"
        for caso in casos:
            registrar_auditoria(
                usuario=self.request.user,
                tabla="casos",
                accion=accion,
                registro_id=caso.pk,
                request=self.request,
                metadata=metadata,
            )

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