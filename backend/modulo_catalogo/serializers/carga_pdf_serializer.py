# modulo_catalogo/serializers/carga_pdf_serializer.py
"""
Serializer para el endpoint de carga masiva de artículos desde PDF.

Valida el archivo, la rama, la jerarquía (tipo de norma) y el nombre del
documento antes de encolar la tarea. La Norma destino ya NO se elige de una
lista fija ni de un <select> de "fuentes" predefinidas (Civil/Penal/
Laboral/CPE): se busca o se crea automáticamente a partir del nombre de
documento que escribe el usuario, para poder sumar cualquier norma nueva
(CPP, Código de Comercio, un Decreto Supremo, etc.) sin tocar el backend.
"""

from rest_framework import serializers

from modulo_catalogo.models.jerarquia import jerarquia as Jerarquia
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama import RamaDerecho

TAMANO_MAX_PDF_MB = 50


class CargaArticulosPDFSerializer(serializers.Serializer):
    """
    Campos esperados (multipart/form-data):
        archivo         — archivo PDF
        nombre_documento — nombre en texto del documento (ej. "Código de
                            Procedimiento Penal"). Si ya existe una Norma
                            con ese nombre (o esa sigla), se reutiliza; si
                            no, se crea una nueva.
        sigla            — opcional, sigla del documento (ej. "CPP")
        jerarquia_id     — ID de Jerarquia existente (Constitución, Ley
                            Orgánica, Código, Ley Ordinaria, Decreto
                            Supremo, Resolución Ministerial, Ordenanza
                            Municipal, ...). Solo se aplica si la Norma es
                            nueva o todavía no tenía jerarquía asignada.
        rama_id          — ID de RamaDerecho existente y activa
        sobrescribir     — bool (default False). Si True, elimina
                            artículos previos de esa norma+rama antes de
                            insertar los nuevos.
    """

    archivo          = serializers.FileField(write_only=True)
    nombre_documento = serializers.CharField(max_length=200, allow_blank=False, trim_whitespace=True)
    sigla            = serializers.CharField(max_length=50, required=False, allow_blank=True)
    jerarquia_id     = serializers.PrimaryKeyRelatedField(
                           queryset=Jerarquia.objects.filter(estado=True),
                           source="jerarquia",
                           required=False,
                           allow_null=True,
                       )
    rama_id          = serializers.PrimaryKeyRelatedField(
                           queryset=RamaDerecho.objects.filter(estado=True),
                           source="rama",
                       )
    sobrescribir     = serializers.BooleanField(default=False, required=False)

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

    def validate_nombre_documento(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError(
                "El nombre del documento debe tener al menos 3 caracteres."
            )
        return value

    def validate(self, attrs):
        rama = attrs.get("rama")
        nombre_documento = attrs.get("nombre_documento")
        sigla = attrs.get("sigla") or None

        # Busca una Norma existente por sigla (si se dio) o por nombre
        # exacto (case-insensitive); si no existe, la crea. Así el mismo
        # formulario sirve tanto para "seguir cargando" una norma que ya
        # existe (ej. seguir subiendo artículos del Código Penal) como
        # para dar de alta una norma nueva (ej. CPP) sin pasar antes por
        # la pantalla de administración de normas.
        norma = None
        if sigla:
            norma = Norma.objects.filter(sigla__iexact=sigla, estado=True).first()
        if norma is None:
            norma = Norma.objects.filter(
                nombre__iexact=nombre_documento, estado=True
            ).first()
        if norma is None:
            norma = Norma.objects.create(
                nombre=nombre_documento,
                sigla=sigla,
                estado=True,
            )
            self.context["norma_creada"] = True

        attrs["norma"] = norma

        # Advertencia si ya existen artículos y sobrescribir=False
        if norma and rama and not attrs.get("sobrescribir", False):
            from modulo_catalogo.models.articulo import Articulo
            existentes = Articulo.objects.filter(norma=norma, rama=rama).count()
            if existentes > 0:
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
