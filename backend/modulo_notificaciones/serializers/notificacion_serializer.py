# modulo_notificaciones/serializers/notificacion_serializer.py
from rest_framework import serializers

from modulo_notificaciones.models import Notificacion


class NotificacionSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    caso_codigo  = serializers.CharField(source="caso.codigo", read_only=True, default=None)

    class Meta:
        model  = Notificacion
        fields = [
            "id", "tipo", "tipo_display", "titulo", "mensaje",
            "caso", "caso_codigo", "leida", "created_at",
        ]
        read_only_fields = fields
