# modulo_notificaciones/views/notificacion_view.py
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions.roles_permission import EsUsuarioAutenticado
from modulo_notificaciones.models import Notificacion
from modulo_notificaciones.serializers.notificacion_serializer import NotificacionSerializer


class NotificacionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET  /api/notificaciones/                    — mis notificaciones (paginado, -created_at)
                                                     ?leida=false para solo las no leídas
    GET  /api/notificaciones/{id}/                — detalle
    GET  /api/notificaciones/no_leidas_count/     — contador para la campanita
    POST /api/notificaciones/{id}/marcar_leida/
    POST /api/notificaciones/marcar_todas_leidas/

    Deliberadamente de solo lectura + estas dos acciones: una
    notificación no se "edita" ni se borra, se marca como leída. Y
    siempre es personal — acá NO hay ve_todo(): cada quien ve solo lo
    suyo, sin excepción de rol, por eso el permiso es el más abierto
    (EsUsuarioAutenticado) y la restricción real está en get_queryset.
    """
    serializer_class   = NotificacionSerializer
    permission_classes = [EsUsuarioAutenticado]

    def get_queryset(self):
        qs = Notificacion.objects.filter(usuario=self.request.user).select_related("caso")
        leida = self.request.query_params.get("leida")
        if leida is not None:
            qs = qs.filter(leida=leida.lower() == "true")
        return qs

    @action(detail=False, methods=["get"], url_path="no_leidas_count")
    def no_leidas_count(self, request):
        total = Notificacion.objects.filter(usuario=request.user, leida=False).count()
        return Response({"no_leidas": total})

    @action(detail=True, methods=["post"], url_path="marcar_leida")
    def marcar_leida(self, request, pk=None):
        notificacion = self.get_object()
        if not notificacion.leida:
            notificacion.leida = True
            notificacion.save(update_fields=["leida"])
        return Response(self.get_serializer(notificacion).data)

    @action(detail=False, methods=["post"], url_path="marcar_todas_leidas")
    def marcar_todas_leidas(self, request):
        actualizadas = self.get_queryset().filter(leida=False).update(leida=True)
        return Response({"actualizadas": actualizadas}, status=status.HTTP_200_OK)
