# modulo_auditoria/views/auditoria_view.py
from django.db.models import Count
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.permissions.roles_permission import EsAdmin
from modulo_auditoria.models.auditoria import Auditoria
from modulo_auditoria.serializers.auditoria_serializer import (
    AuditoriaFiltroSerializer,
    AuditoriaPorTablaQuerySerializer,
    AuditoriaPorUsuarioQuerySerializer,
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
    serializer_class  = AuditoriaSerializer
    permission_classes = [EsAdmin]
    filter_backends    = [OrderingFilter]
    ordering_fields     = ["created_at", "accion", "tabla"]

    def get_queryset(self):
        qs = (
            Auditoria.objects
            .select_related("usuario")
            .order_by("-created_at")
        )
        filtros = self._validar_filtros(self.request.query_params)
        return self._aplicar_filtros(qs, filtros)

    # ── Helpers internos ────────────────────────────────────────────

    def _validar_filtros(self, query_params):
        """Valida los query params de filtro. Lanza 400 si son inválidos
        en vez de ignorarlos silenciosamente."""
        serializer = AuditoriaFiltroSerializer(data=query_params)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def _aplicar_filtros(self, qs, filtros):
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

    def _respuesta_paginada(self, qs):
        page = self.paginate_queryset(qs)
        serializer = AuditoriaSerializer(page if page is not None else qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    # ── Acciones adicionales ───────────────────────────────────────

    @action(detail=False, methods=["get"], url_path="por_usuario")
    def por_usuario(self, request):
        """
        GET /api/auditoria/por_usuario/?usuario_id=X
        Historial completo de acciones de un usuario.
        """
        query_ser = AuditoriaPorUsuarioQuerySerializer(data=request.query_params)
        query_ser.is_valid(raise_exception=True)
        usuario_id = query_ser.validated_data["usuario_id"]

        qs = self.get_queryset().filter(usuario_id=usuario_id)
        return self._respuesta_paginada(qs)

    @action(detail=False, methods=["get"], url_path="por_tabla")
    def por_tabla(self, request):
        """
        GET /api/auditoria/por_tabla/?tabla=casos
        Todos los eventos sobre una tabla específica.
        """
        query_ser = AuditoriaPorTablaQuerySerializer(data=request.query_params)
        query_ser.is_valid(raise_exception=True)
        tabla = query_ser.validated_data["tabla"].strip()

        qs = self.get_queryset().filter(tabla__iexact=tabla)
        return self._respuesta_paginada(qs)

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
        qs = self.get_queryset()
        resumen = (
            qs.values("accion")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        acciones_labels = dict(Auditoria.ACCION_CHOICES)
        return Response(
            [
                {
                    "accion": r["accion"],
                    "label": acciones_labels.get(r["accion"], r["accion"]),
                    "total": r["total"],
                }
                for r in resumen
            ]
        )