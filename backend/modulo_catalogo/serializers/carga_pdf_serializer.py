# modulo_catalogo/serializers/carga_pdf_serializer.py
"""
Serializer para el endpoint de carga masiva de artículos desde PDF.
Valida el archivo, la fuente, la norma y la rama antes de encolar la tarea.
"""

from rest_framework import serializers

from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama  import RamaDerecho
from modulo_catalogo.services.carga_pdf_service import PATRONES_POR_FUENTE

FUENTES_VALIDAS   = list(PATRONES_POR_FUENTE.keys())
TAMANO_MAX_PDF_MB = 50


class CargaArticulosPDFSerializer(serializers.Serializer):
    """
    Campos esperados (multipart/form-data):
        archivo      — archivo PDF
        fuente       — "Civil" | "Penal" | "Laboral" | "CPE"
        norma_id     — ID de Norma existente y activa
        rama_id      — ID de RamaDerecho existente y activa
        sobrescribir — bool (default False)
                       Si True, elimina artículos previos de esa norma+rama
                       antes de insertar los nuevos.
    """

    archivo      = serializers.FileField(write_only=True)
    fuente       = serializers.ChoiceField(choices=FUENTES_VALIDAS)
    norma_id     = serializers.PrimaryKeyRelatedField(
                       queryset=Norma.objects.filter(estado=True),
                       source="norma",
                   )
    rama_id      = serializers.PrimaryKeyRelatedField(
                       queryset=RamaDerecho.objects.filter(estado=True),
                       source="rama",
                   )
    sobrescribir = serializers.BooleanField(default=False, required=False)

    def validate_archivo(self, value):
        # Solo PDF
        nombre = value.name.lower()
        if not nombre.endswith(".pdf"):
            raise serializers.ValidationError(
                "Solo se aceptan archivos PDF (.pdf)."
            )
        # Tamaño
        tamano_mb = value.size / (1024 * 1024)
        if tamano_mb > TAMANO_MAX_PDF_MB:
            raise serializers.ValidationError(
                f"El archivo supera el tamaño máximo de {TAMANO_MAX_PDF_MB} MB "
                f"(tamaño actual: {tamano_mb:.1f} MB)."
            )
        if value.size == 0:
            raise serializers.ValidationError("El archivo PDF está vacío.")
        return value

    def validate_fuente(self, value):
        if value not in FUENTES_VALIDAS:
            raise serializers.ValidationError(
                f"Fuente no válida. Opciones: {', '.join(FUENTES_VALIDAS)}"
            )
        return value

    def validate(self, attrs):
        norma = attrs.get("norma")
        rama  = attrs.get("rama")
        # Advertencia si ya existen artículos y sobrescribir=False
        if norma and rama and not attrs.get("sobrescribir", False):
            from modulo_catalogo.models.articulo import Articulo
            existentes = Articulo.objects.filter(norma=norma, rama=rama).count()
            if existentes > 0:
                # Guardar el conteo en el contexto para devolverlo en la respuesta
                self.context["existentes"] = existentes
        return attrs


class EstadoCargaSerializer(serializers.Serializer):
    """
    Solo lectura — resultado que devuelve el endpoint de estado de carga
    (reutiliza GET /api/ia/tarea/{task_id}/).
    """
    task_id  = serializers.CharField(read_only=True)
    estado   = serializers.CharField(read_only=True)
    progreso = serializers.IntegerField(read_only=True, required=False)
    paso     = serializers.CharField(read_only=True,    required=False)
    resumen  = serializers.DictField(read_only=True,    required=False)
    error    = serializers.CharField(read_only=True,    required=False)