from rest_framework import serializers

from core.utils.usuarios import nombre_visible_usuario  # noqa: F401 (se reexporta)
from modulo_casos.models.etapas import EtapaCaso
from modulo_casos.models.seguimiento import SeguimientoCaso


class SeguimientoCasoSerializer(serializers.ModelSerializer):
    """Entrada de la línea de tiempo de un caso (solo lectura)."""
    etapa_display          = serializers.CharField(source="get_etapa_display", read_only=True)
    etapa_anterior_display = serializers.SerializerMethodField()
    usuario_nombre         = serializers.SerializerMethodField()

    class Meta:
        model  = SeguimientoCaso
        fields = [
            "id", "etapa", "etapa_display",
            "etapa_anterior", "etapa_anterior_display",
            "nota", "usuario_nombre", "created_at",
        ]
        read_only_fields = fields

    def get_etapa_anterior_display(self, obj):
        return obj.get_etapa_anterior_display() if obj.etapa_anterior else None

    def get_usuario_nombre(self, obj):
        return nombre_visible_usuario(obj.usuario)


class CambiarEtapaSerializer(serializers.Serializer):
    """
    Entrada para POST /casos/{id}/cambiar_etapa/.

    Requiere 'caso' en el context para poder rechazar un "cambio" a la
    misma etapa sin nota (no aportaría nada a la trazabilidad).
    """
    NOTA_MAX = 2000

    etapa = serializers.ChoiceField(choices=EtapaCaso.choices)
    nota  = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=NOTA_MAX,
        trim_whitespace=True,
    )

    def validate(self, attrs):
        caso = self.context["caso"]
        nota = attrs.get("nota", "")

        # "Caso registrado" es la etapa inicial automática (la deja
        # registrar_seguimiento_inicial al crear el caso). No se puede
        # volver a elegir a mano: ni para "reconfirmarla" con una nota, ni
        # para retroceder el caso a ese punto — evita una segunda entrada
        # de "Caso registrado" en el historial.
        if attrs["etapa"] == EtapaCaso.REGISTRADO:
            raise serializers.ValidationError({
                "etapa": (
                    "\"Caso registrado\" se asigna automáticamente al crear el "
                    "caso y no se puede volver a elegir. Selecciona la etapa a "
                    "la que avanzó el caso."
                )
            })

        if attrs["etapa"] == caso.etapa and not nota:
            raise serializers.ValidationError({
                "etapa": (
                    "El caso ya está en esa etapa. Elige otra etapa o agrega "
                    "una nota para registrar una actualización de seguimiento."
                )
            })
        attrs["nota"] = nota
        return attrs
