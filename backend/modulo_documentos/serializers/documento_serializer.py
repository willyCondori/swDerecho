import hashlib
import os

from django.conf import settings
from rest_framework import serializers

from modulo_documentos.models.documento import (
    DocumentoCaso,
    DocumentoGenerado,
    PlantillaDocumento,
    TipoDoc,
)

# Extensiones permitidas por tipo
EXTENSIONES_CASO      = {"pdf", "docx", "doc", "txt"}
EXTENSIONES_PLANTILLA = {"docx", "dotx"}
TAMANO_MAX_MB         = 20


# ---------------------------------------------------------------------------
# TipoDoc
# ---------------------------------------------------------------------------

class TipoDocSerializer(serializers.ModelSerializer):
    class Meta:
        model  = TipoDoc
        fields = ["id", "tipo"]

    def validate_tipo(self, value):
        value = value.strip().lower()
        if len(value) < 2:
            raise serializers.ValidationError("El tipo debe tener al menos 2 caracteres.")
        if TipoDoc.objects.filter(tipo__iexact=value).exclude(
            pk=self.instance.pk if self.instance else None
        ).exists():
            raise serializers.ValidationError("Ya existe un tipo de documento con ese nombre.")
        return value


# ---------------------------------------------------------------------------
# DocumentoCaso
# ---------------------------------------------------------------------------

class DocumentoCasoReadSerializer(serializers.ModelSerializer):
    tipo_documento = TipoDocSerializer(read_only=True)
    url_descarga   = serializers.SerializerMethodField()

    class Meta:
        model  = DocumentoCaso
        fields = [
            "id", "caso", "nombre_original", "ruta_archivo",
            "tipo_archivo", "tamano", "tipo_documento",
            "url_descarga", "created_at",
        ]

    def get_url_descarga(self, obj):
        request = self.context.get("request")
        if request and obj.ruta_archivo:
            return request.build_absolute_uri(
                f"{settings.MEDIA_URL}{obj.ruta_archivo}"
            )
        return None


class DocumentoCasoWriteSerializer(serializers.ModelSerializer):
    archivo        = serializers.FileField(write_only=True)
    tipo_documento = serializers.PrimaryKeyRelatedField(
                         queryset=TipoDoc.objects.all()
                     )

    class Meta:
        model  = DocumentoCaso
        fields = ["caso", "archivo", "tipo_documento"]

    def validate_archivo(self, value):
        extension = value.name.rsplit(".", 1)[-1].lower()
        if extension not in EXTENSIONES_CASO:
            raise serializers.ValidationError(
                f"Extensión no permitida. Permitidas: {', '.join(EXTENSIONES_CASO)}"
            )
        tamano_mb = value.size / (1024 * 1024)
        if tamano_mb > TAMANO_MAX_MB:
            raise serializers.ValidationError(
                f"El archivo supera el tamaño máximo de {TAMANO_MAX_MB} MB."
            )
        # Verificar que el archivo no esté vacío
        if value.size == 0:
            raise serializers.ValidationError("El archivo está vacío.")
        return value

    def create(self, validated_data):
        archivo    = validated_data.pop("archivo")
        extension  = archivo.name.rsplit(".", 1)[-1].lower()

        # Construir ruta de almacenamiento
        caso       = validated_data["caso"]
        nombre_guardado = f"caso_{caso.id}_{archivo.name}"
        ruta_relativa   = f"documentos_caso/{nombre_guardado}"
        ruta_absoluta   = os.path.join(settings.MEDIA_ROOT, ruta_relativa)

        os.makedirs(os.path.dirname(ruta_absoluta), exist_ok=True)
        with open(ruta_absoluta, "wb+") as dest:
            for chunk in archivo.chunks():
                dest.write(chunk)

        return DocumentoCaso.objects.create(
            **validated_data,
            nombre_original=archivo.name,
            ruta_archivo=ruta_relativa,
            tipo_archivo=extension,
            tamano=archivo.size,
        )


# ---------------------------------------------------------------------------
# PlantillaDocumento
# ---------------------------------------------------------------------------

class PlantillaDocumentoReadSerializer(serializers.ModelSerializer):
    tipo_documento = TipoDocSerializer(read_only=True)
    url_descarga   = serializers.SerializerMethodField()

    class Meta:
        model  = PlantillaDocumento
        fields = [
            "id", "nombre", "descripcion",
            "ruta_archivo", "tipo_documento", "url_descarga",
        ]

    def get_url_descarga(self, obj):
        request = self.context.get("request")
        if request and obj.ruta_archivo:
            return request.build_absolute_uri(
                f"{settings.MEDIA_URL}{obj.ruta_archivo}"
            )
        return None


class PlantillaDocumentoWriteSerializer(serializers.ModelSerializer):
    archivo        = serializers.FileField(write_only=True)
    tipo_documento = serializers.PrimaryKeyRelatedField(queryset=TipoDoc.objects.all())

    class Meta:
        model  = PlantillaDocumento
        fields = ["nombre", "descripcion", "archivo", "tipo_documento"]

    def validate_nombre(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("El nombre de la plantilla debe tener al menos 3 caracteres.")
        if PlantillaDocumento.objects.filter(nombre__iexact=value).exclude(
            pk=self.instance.pk if self.instance else None
        ).exists():
            raise serializers.ValidationError("Ya existe una plantilla con ese nombre.")
        return value

    def validate_archivo(self, value):
        extension = value.name.rsplit(".", 1)[-1].lower()
        if extension not in EXTENSIONES_PLANTILLA:
            raise serializers.ValidationError(
                f"La plantilla debe ser .docx o .dotx. Recibido: .{extension}"
            )
        tamano_mb = value.size / (1024 * 1024)
        if tamano_mb > 10:
            raise serializers.ValidationError("La plantilla no puede superar los 10 MB.")
        return value

    def create(self, validated_data):
        archivo = validated_data.pop("archivo")
        nombre_guardado = f"plantilla_{archivo.name}"
        ruta_relativa   = f"plantillas/{nombre_guardado}"
        ruta_absoluta   = os.path.join(settings.MEDIA_ROOT, ruta_relativa)

        os.makedirs(os.path.dirname(ruta_absoluta), exist_ok=True)
        with open(ruta_absoluta, "wb+") as dest:
            for chunk in archivo.chunks():
                dest.write(chunk)

        return PlantillaDocumento.objects.create(
            **validated_data,
            ruta_archivo=ruta_relativa,
        )


# ---------------------------------------------------------------------------
# DocumentoGenerado
# ---------------------------------------------------------------------------

class DocumentoGeneradoSerializer(serializers.ModelSerializer):
    plantilla_nombre = serializers.CharField(source="plantilla.nombre", read_only=True)
    caso_codigo      = serializers.CharField(source="caso.codigo",       read_only=True)
    url_descarga     = serializers.SerializerMethodField()

    class Meta:
        model  = DocumentoGenerado
        fields = [
            "id", "caso", "caso_codigo",
            "plantilla", "plantilla_nombre",
            "ruta_archivo", "hash_archivo",
            "url_descarga", "created_at",
        ]
        read_only_fields = ["id", "hash_archivo", "created_at"]

    def get_url_descarga(self, obj):
        request = self.context.get("request")
        if request and obj.ruta_archivo:
            return request.build_absolute_uri(
                f"{settings.MEDIA_URL}{obj.ruta_archivo}"
            )
        return None


class GenerarDocumentoSerializer(serializers.Serializer):
    """Dispara la generación de un documento a partir de plantilla y caso."""
    caso_id      = serializers.IntegerField()
    plantilla_id = serializers.IntegerField()

    def validate_caso_id(self, value):
        from modulo_casos.models.caso import Caso
        if not Caso.objects.filter(pk=value, estado=True).exists():
            raise serializers.ValidationError("El caso no existe o está inactivo.")
        return value

    def validate_plantilla_id(self, value):
        if not PlantillaDocumento.objects.filter(pk=value).exists():
            raise serializers.ValidationError("La plantilla no existe.")
        return value

    def validate(self, attrs):
        from modulo_casos.models.caso import Caso
        caso = Caso.objects.get(pk=attrs["caso_id"])
        # El caso debe tener al menos un resultado para poder generar el documento
        if not hasattr(caso, "resultado"):
            raise serializers.ValidationError(
                {"caso_id": "El caso no tiene resultados de análisis IA aún. "
                            "Ejecute el análisis primero."}
            )
        return attrs
