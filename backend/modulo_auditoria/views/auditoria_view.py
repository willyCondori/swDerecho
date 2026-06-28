from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.permissions.roles_permission import EsAdmin
from modulo_auditoria.models.auditoria import Auditoria
from modulo_auditoria.serializers.auditoria_serializer import (
    AuditoriaFiltroSerializer,
    AuditoriaSerializer,
)


class AuditoriaViewSet(ReadOnlyModelViewSet):
    """
    Solo admin puede ver la auditoría.

    GET /api/auditoria/              — lista con filtros
    GET /api/auditoria/{id}/         — detalle de un registro
    GET /api/auditoria/por_usuario/  — actividad de un usuario
    GET /api/auditoria/por_tabla/    — registros de una tabla
    GET /api/auditoria/acciones/     — listado de acciones disponibles
    GET /api/auditoria/resumen/      — conteo agrupado por acción
    """
    serializer_class = AuditoriaSerializer
    filter_backends  = [OrderingFilter]
    ordering_fields  = ["created_at", "accion", "tabla"]

    def get_permissions(self):
        return [EsAdmin()]

    def get_queryset(self):
        qs = (
            Auditoria.objects
            .select_related("usuario")
            .order_by("-created_at")
        )

        # Validar y aplicar filtros
        filtro_ser = AuditoriaFiltroSerializer(data=self.request.query_params)
        if not filtro_ser.is_valid():
            return qs  # sin filtros si los params son inválidos

        filtros = filtro_ser.validated_data

        if uid := filtros.get("usuario_id"):
            qs = qs.filter(usuario_id=uid)
        if tabla := filtros.get("tabla"):
            qs = qs.filter(tabla__iexact=tabla)
        if accion := filtros.get("accion"):
            qs = qs.filter(accion=accion)
        if fecha_desde := filtros.get("fecha_desde"):
            qs = qs.filter(created_at__date__gte=fecha_desde)
        if fecha_hasta := filtros.get("fecha_hasta"):
            qs = qs.filter(created_at__date__lte=fecha_hasta)
        if reg_id := filtros.get("registro_id"):
            qs = qs.filter(registro_id=reg_id)
        if ip := filtros.get("ip"):
            qs = qs.filter(ip__icontains=ip)

        return qs

    @action(detail=False, methods=["get"], url_path="por_usuario")
    def por_usuario(self, request):
        """
        GET /api/auditoria/por_usuario/?usuario_id=X
        Historial completo de acciones de un usuario.
        """
        usuario_id = request.query_params.get("usuario_id")
        if not usuario_id:
            return Response(
                {"detail": "Parámetro usuario_id requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs   = self.get_queryset().filter(usuario_id=usuario_id)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(AuditoriaSerializer(page, many=True).data)
        return Response(AuditoriaSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="por_tabla")
    def por_tabla(self, request):
        """
        GET /api/auditoria/por_tabla/?tabla=casos
        Todos los eventos sobre una tabla específica.
        """
        tabla = request.query_params.get("tabla", "").strip()
        if not tabla:
            return Response(
                {"detail": "Parámetro tabla requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs   = self.get_queryset().filter(tabla__iexact=tabla)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(AuditoriaSerializer(page, many=True).data)
        return Response(AuditoriaSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="acciones")
    def acciones(self, request):
        """GET /api/auditoria/acciones/ — listado de tipos de acción disponibles."""
        return Response(
            [{"value": c[0], "label": c[1]} for c in Auditoria.ACCION_CHOICES]
        )

    @action(detail=False, methods=["get"], url_path="resumen")
    def resumen(self, request):
        """
        GET /api/auditoria/resumen/
        Conteo de registros agrupado por acción.
        Acepta los mismos filtros de fecha que la lista principal.
        """
        from django.db.models import Count

        qs = self.get_queryset()
        resumen = (
            qs.values("accion")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        return Response(
            [
                {
                    "accion": r["accion"],
                    "label" : dict(Auditoria.ACCION_CHOICES).get(r["accion"], r["accion"]),
                    "total" : r["total"],
                }
                for r in resumen
            ]
        )
