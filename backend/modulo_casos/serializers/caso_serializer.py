import uuid

from rest_framework import serializers

from modulo_casos.models.caso import Caso
from modulo_casos.models.hecho import Hecho, HechoCaso
from modulo_casos.models.petitorio import Petitorio, PetitorioCaso
from modulo_casos.models.resultado_caso import ResultadoCaso
from modulo_catalogo.models.rama import RamaDerecho
from modulo_clientes.models.cliente import Cliente
from modulo_clientes.serializers.cliente_serializer import ClienteListSerializer
from modulo_usuarios.serializers.usuario_serializer import UsuarioReadSerializer


# ---------------------------------------------------------------------------
# Hecho
# ---------------------------------------------------------------------------

class HechoSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Hecho
        fields = ["id", "descripcion", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_descripcion(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError(
                "La descripción del hecho debe tener al menos 10 caracteres."
            )
        if len(value) > 5000:
            raise serializers.ValidationError(
                "La descripción del hecho no puede exceder 5000 caracteres."
            )
        return value


# ---------------------------------------------------------------------------
# Petitorio
# ---------------------------------------------------------------------------

class PetitorioSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Petitorio
        fields = ["id", "descripcion", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_descripcion(self, value):
        value = value.strip()
        if len(value) < 20:
            raise serializers.ValidationError(
                "El petitorio debe tener al menos 20 caracteres."
            )
        if len(value) > 10000:
            raise serializers.ValidationError(
                "El petitorio no puede exceder 10000 caracteres."
            )
        return value


# ---------------------------------------------------------------------------
# ResultadoCaso
# ---------------------------------------------------------------------------

class ResultadoCasoSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ResultadoCaso
        fields = [
            "id", "caso",
            "resumen", "fortalezas", "debilidades",
            "estrategias", "observaciones",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "caso", "created_at", "updated_at"]

    def validate_resumen(self, value):
        if value and len(value.strip()) < 30:
            raise serializers.ValidationError("El resumen debe tener al menos 30 caracteres.")
        return value.strip() if value else value

    def validate_fortalezas(self, value):
        if value and len(value.strip()) < 10:
            raise serializers.ValidationError("Las fortalezas deben tener al menos 10 caracteres.")
        return value.strip() if value else value

    def validate_debilidades(self, value):
        if value and len(value.strip()) < 10:
            raise serializers.ValidationError("Las debilidades deben tener al menos 10 caracteres.")
        return value.strip() if value else value

    def validate_estrategias(self, value):
        if value and len(value.strip()) < 10:
            raise serializers.ValidationError("Las estrategias deben tener al menos 10 caracteres.")
        return value.strip() if value else value


# ---------------------------------------------------------------------------
# Validaciones compartidas de título/descripción del Caso
# ---------------------------------------------------------------------------

class CasoTituloDescripcionMixin:
    """
    Reglas de validación de título/descripción compartidas entre
    CasoCreateSerializer y CasoUpdateSerializer, para que no se
    puedan violar los mismos límites en un endpoint y no en el otro.
    """
    TITULO_MIN = 5
    TITULO_MAX = 500
    DESCRIPCION_MIN = 5

    def validate_titulo(self, value):
        value = value.strip()
        if len(value) < self.TITULO_MIN:
            raise serializers.ValidationError(
                f"El título debe tener al menos {self.TITULO_MIN} caracteres."
            )
        if len(value) > self.TITULO_MAX:
            raise serializers.ValidationError(
                f"El título no puede exceder {self.TITULO_MAX} caracteres."
            )
        return value

    def validate_descripcion(self, value):
        if value:
            value = value.strip()
            if len(value) < self.DESCRIPCION_MIN:
                raise serializers.ValidationError(
                    f"La descripción debe tener al menos {self.DESCRIPCION_MIN} caracteres."
                )
        return value


# ---------------------------------------------------------------------------
# Caso
# ---------------------------------------------------------------------------

class CasoReadSerializer(serializers.ModelSerializer):
    usuario         = UsuarioReadSerializer(read_only=True)
    cliente         = ClienteListSerializer(read_only=True)
    rama_detectada  = serializers.StringRelatedField()
    hechos          = serializers.SerializerMethodField()
    petitorios      = serializers.SerializerMethodField()
    resultado       = ResultadoCasoSerializer(read_only=True)
    tiene_documento = serializers.SerializerMethodField()
    tiene_generado  = serializers.SerializerMethodField()

    class Meta:
        model  = Caso
        fields = [
            "id", "codigo", "titulo", "descripcion",
            "usuario", "cliente", "rama_detectada",
            "hechos", "petitorios", "resultado",
            "tiene_documento", "tiene_generado",
            "estado", "created_at",
        ]

    def get_hechos(self, obj):
        hechos = Hecho.objects.filter(casos_hecho__caso=obj).order_by("casos_hecho__orden")
        return HechoSerializer(hechos, many=True).data

    def get_petitorios(self, obj):
        pets = Petitorio.objects.filter(casos_petitorio__caso=obj)
        return PetitorioSerializer(pets, many=True).data

    def get_tiene_documento(self, obj):
        return obj.documentos.filter(tipo_archivo="pdf").exists()

    def get_tiene_generado(self, obj):
        return obj.documentos_generados.exists()


class CasoCreateSerializer(CasoTituloDescripcionMixin, serializers.ModelSerializer):
    """
    Creación de caso. El abogado puede:
      a) Redactar el caso en 'descripcion' (campo de texto).
      b) Subir un PDF (se procesa en modulo_documentos; aquí 'descripcion' queda vacío).
    Al menos uno de los dos es obligatorio → se valida en validate().

    Requiere 'request' en el context (usado para asignar el usuario
    autenticado como propietario del caso).
    """
    cliente_id = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.filter(estado=True),
        source="cliente",
    )
    rama_detectada_id = serializers.PrimaryKeyRelatedField(
        queryset=RamaDerecho.objects.filter(estado=True),
        source="rama_detectada",
        required=False,
        allow_null=True,
    )

    class Meta:
        model  = Caso
        fields = [
            "titulo", "descripcion",
            "cliente_id", "rama_detectada_id", "estado",
        ]

    def validate(self, attrs):
        # descripcion puede venir vacía solo si en la vista se recibió también
        # un archivo PDF. La vista pasa el flag 'tiene_pdf' en el contexto.
        tiene_pdf = self.context.get("tiene_pdf", False)
        if not attrs.get("descripcion") and not tiene_pdf:
            raise serializers.ValidationError(
                {"descripcion": "Debe redactar el caso o adjuntar un documento PDF."}
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            raise serializers.ValidationError(
                "No se pudo determinar el usuario autenticado para crear el caso."
            )
        validated_data["codigo"] = self._generar_codigo()
        validated_data["usuario"] = request.user
        return super().create(validated_data)

    @staticmethod
    def _generar_codigo() -> str:
        prefijo = "CASO"
        sufijo  = uuid.uuid4().hex[:8].upper()
        codigo  = f"{prefijo}-{sufijo}"
        # Garantizar unicidad (colisión extremadamente improbable, pero se
        # verifica de todas formas antes de persistir).
        while Caso.objects.filter(codigo=codigo).exists():
            sufijo = uuid.uuid4().hex[:8].upper()
            codigo = f"{prefijo}-{sufijo}"
        return codigo


class CasoUpdateSerializer(CasoTituloDescripcionMixin, serializers.ModelSerializer):
    """Actualización parcial: solo título, descripción y estado."""
    class Meta:
        model  = Caso
        fields = ["titulo", "descripcion", "estado"]


class CasoListSerializer(serializers.ModelSerializer):
    """Versión compacta para listados y búsquedas con filtros."""
    cliente_nombre  = serializers.SerializerMethodField()
    usuario_nombre  = serializers.CharField(source="usuario.usuario", read_only=True)
    rama_detectada  = serializers.StringRelatedField()
    tiene_documento = serializers.SerializerMethodField()
    tiene_resultado = serializers.SerializerMethodField()

    class Meta:
        model  = Caso
        fields = [
            "id", "codigo", "titulo",
            "usuario_nombre", "cliente_nombre", "rama_detectada",
            "tiene_documento", "tiene_resultado",
            "estado", "created_at",
        ]

    def get_cliente_nombre(self, obj):
        from core.encryption.aes_encryption import safe_decrypt
        nombres   = safe_decrypt(obj.cliente.nombres, fallback=None)
        apellidos = safe_decrypt(obj.cliente.apellidos, fallback=None)
        if nombres is None or apellidos is None:
            return f"Cliente #{obj.cliente_id}"
        return f"{nombres} {apellidos}".strip()

    def get_tiene_documento(self, obj):
        return obj.documentos.filter(tipo_archivo="pdf").exists()

    def get_tiene_resultado(self, obj):
        return hasattr(obj, "resultado")