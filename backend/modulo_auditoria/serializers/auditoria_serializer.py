# modulo_auditoria/serializers/auditoria_serializer.py
from rest_framework import serializers

from modulo_auditoria.models.auditoria import Auditoria


class AuditoriaSerializer(serializers.ModelSerializer):
    """
    Solo lectura. Los registros de auditoría nunca se crean ni modifican
    desde la API — se generan automáticamente por el middleware y servicios.
    """
    usuario      = serializers.SerializerMethodField()
    accion_label = serializers.CharField(source="get_accion_display", read_only=True)

    class Meta:
        model  = Auditoria
        fields = [
            "id",
            "usuario", "tabla", "accion", "accion_label",
            "registro_id", "ip", "metadata", "created_at",
        ]
        read_only_fields = fields  # defensa extra: refuerza que nunca se escribe vía API

    def get_usuario(self, obj):
        if obj.usuario:
            return {
                "id": obj.usuario.id,
                "usuario": obj.usuario.usuario,
            }
        return None


class AuditoriaFiltroSerializer(serializers.Serializer):
    """
    Valida los parámetros de búsqueda/filtro para el endpoint de auditoría.
    Usado en la vista como validador de query params. Si los parámetros
    no son válidos, la vista debe responder 400 en vez de ignorar el filtro.
    """
    usuario_id  = serializers.IntegerField(required=False)
    tabla       = serializers.CharField(max_length=100, required=False)
    accion      = serializers.ChoiceField(
                      choices=[c[0] for c in Auditoria.ACCION_CHOICES],
                      required=False,
                  )
    fecha_desde = serializers.DateField(required=False)
    fecha_hasta = serializers.DateField(required=False)
    registro_id = serializers.IntegerField(required=False)
    ip          = serializers.CharField(max_length=100, required=False)

    def validate(self, attrs):
        fecha_desde = attrs.get("fecha_desde")
        fecha_hasta = attrs.get("fecha_hasta")
        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            raise serializers.ValidationError(
                {"fecha_hasta": "La fecha hasta no puede ser anterior a fecha desde."}
            )
        return attrs


class AuditoriaPorUsuarioQuerySerializer(serializers.Serializer):
    """Valida el query param requerido en /auditoria/por_usuario/."""
    usuario_id = serializers.IntegerField(required=True)


class AuditoriaPorTablaQuerySerializer(serializers.Serializer):
    """Valida el query param requerido en /auditoria/por_tabla/."""
    tabla = serializers.CharField(max_length=100, required=True, allow_blank=False)