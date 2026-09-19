from rest_framework import serializers

from core.encryption.aes_encryption import safe_decrypt
from modulo_casos.models.etapas import EtapaCaso
from modulo_casos.models.seguimiento import SeguimientoCaso


def nombre_visible_usuario(usuario):
    """Nombre y apellidos del perfil (descifrados); si no hay, el usuario. None si no hay usuario."""
    if usuario is None:
        return None
    perfil = getattr(usuario, "perfil", None)
    if perfil is not None:
        nombres   = safe_decrypt(perfil.nombres, fallback=None)
        apellidos = safe_decrypt(perfil.apellidos, fallback=None)
        if nombres is not None and apellidos is not None:
            completo = f"{nombres} {apellidos}".strip()
            if completo:
                return completo
    return usuario.usuario


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
        if attrs["etapa"] == caso.etapa and not nota:
            raise serializers.ValidationError({
                "etapa": (
                    "El caso ya está en esa etapa. Elige otra etapa o agrega "
                    "una nota para registrar una actualización de seguimiento."
                )
            })
        attrs["nota"] = nota
        return attrs
