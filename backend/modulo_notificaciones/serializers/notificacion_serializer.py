from core.public_ids import IdentificadorPublicoSerializer, ReferenciaPublicaField, ClaveInternaDesdeUUIDField
# modulo_notificaciones/serializers/notificacion_serializer.py
from rest_framework import serializers
from core.encryption.aes_encryption import safe_decrypt

from modulo_notificaciones.models import Notificacion


class NotificacionSerializer(IdentificadorPublicoSerializer):
    mensaje = serializers.SerializerMethodField()
    caso = serializers.UUIDField(source="caso.public_id", read_only=True, default=None)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    caso_codigo  = serializers.CharField(source="caso.codigo", read_only=True, default=None)

    def get_mensaje(self, obj):
        # Adaptar también avisos ya guardados. El nombre se descifra al leer,
        # sin duplicar datos personales en el texto persistido del aviso.
        if not obj.caso_id:
            return obj.mensaje
        caso = obj.caso
        referencia = f"({caso.codigo})"
        if referencia not in obj.mensaje:
            return obj.mensaje
        cliente = caso.cliente
        nombres = self.__dict__.setdefault('_clientes_visibles', {})
        if cliente.pk not in nombres:
            partes = [safe_decrypt(cliente.nombres, fallback=''),
                      safe_decrypt(cliente.apellidos, fallback='')]
            nombres[cliente.pk] = ' '.join(p for p in partes if p).strip() or 'Nombre no disponible'
        return obj.mensaje.replace(referencia, f'del cliente {nombres[cliente.pk]}')

    class Meta:
        model  = Notificacion
        fields = [
            "id", "tipo", "tipo_display", "titulo", "mensaje",
            "caso", "caso_codigo", "leida", "created_at",
        ]
        read_only_fields = fields
