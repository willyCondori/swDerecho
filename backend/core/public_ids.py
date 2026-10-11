"""Identificadores públicos opacos; las FK internas conservan su integridad."""
import uuid
from rest_framework import serializers

class IdentificadorPublicoSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='public_id', read_only=True)

class ReferenciaPublicaField(serializers.SlugRelatedField):
    def __init__(self, **kwargs):
        super().__init__(slug_field='public_id', **kwargs)

    def to_internal_value(self, data):
        try:
            data = uuid.UUID(str(data))
        except (ValueError, TypeError, AttributeError):
            raise serializers.ValidationError('Se requiere un UUID válido.')
        return super().to_internal_value(data)

class ClaveInternaDesdeUUIDField(ReferenciaPublicaField):
    """Entrada pública, salida interna para servicios que trabajan con PK."""
    def to_internal_value(self, data):
        return super().to_internal_value(data).pk

class VistaIdentificadorPublicoMixin:
    lookup_field = 'public_id'
    lookup_url_kwarg = 'pk'
    lookup_value_regex = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'

def filtrar_uuid(queryset, campo, valor):
    try:
        identificador = uuid.UUID(str(valor))
    except (ValueError, TypeError, AttributeError):
        return queryset.none()
    return queryset.filter(**{campo: identificador})
