from django.conf import settings
from rest_framework import serializers

from modulo_catalogo.models.documento_norma import DocumentoNorma


class DocumentoNormaSerializer(serializers.ModelSerializer):
    """
    Solo lectura: estos registros los crea CargaArticulosView al guardar
    el PDF antes de lanzar la extracción de artículos en background (ver
    modulo_catalogo/views/carga_articulos_view.py). No hay un endpoint de
    creación aparte — subir un documento nuevo siempre pasa por el
    formulario de "Cargar artículos".
    """
    norma_nombre = serializers.CharField(source="norma.nombre", read_only=True)
    rama_nombre  = serializers.CharField(source="rama.nombre",  read_only=True, default=None)
    subido_por_nombre = serializers.SerializerMethodField()
    url_descarga = serializers.SerializerMethodField()

    class Meta:
        model  = DocumentoNorma
        fields = [
            "id", "norma", "norma_nombre", "rama", "rama_nombre",
            "nombre_original", "tamano",
            "subido_por", "subido_por_nombre",
            "url_descarga", "created_at",
        ]

    def get_subido_por_nombre(self, obj):
        if not obj.subido_por:
            return None
        return getattr(obj.subido_por, "usuario", None) or str(obj.subido_por)

    def get_url_descarga(self, obj):
        request = self.context.get("request")
        if request and obj.ruta_archivo:
            return request.build_absolute_uri(f"{settings.MEDIA_URL}{obj.ruta_archivo}")
        return None
