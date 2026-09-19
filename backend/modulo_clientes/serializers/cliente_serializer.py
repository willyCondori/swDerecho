import re
from datetime import date

from django.db import transaction
from rest_framework import serializers

from core.encryption.aes_encryption import encrypt, safe_decrypt, hash_lookup
from core.utils.usuarios import nombre_visible_usuario
from modulo_clientes.models.cliente import Cliente
from modulo_clientes.services.papelera_service import (
    ClienteConCasosActivosError,
    enviar_cliente_a_papelera,
)

AVISO_EN_PAPELERA = " Ese cliente está en la papelera: restáuralo desde Clientes → Papelera."


def _aviso_si_esta_en_papelera(queryset_duplicados):
    """Si el duplicado es un cliente eliminado, avisa dónde recuperarlo."""
    return AVISO_EN_PAPELERA if queryset_duplicados.filter(estado=False).exists() else ""


class ClienteNombreMixin:
    """
    Lógica compartida para descifrar nombres/apellidos y construir
    el nombre completo. La usan tanto el serializer de detalle como
    el compacto, evitando repetir el mismo try/except en cada uno.
    """

    def get_nombres(self, obj):
        return safe_decrypt(obj.nombres)

    def get_apellidos(self, obj):
        return safe_decrypt(obj.apellidos)

    def get_nombre_completo(self, obj):
        nombres = safe_decrypt(obj.nombres)
        apellidos = safe_decrypt(obj.apellidos)
        if nombres == "[cifrado]" or apellidos == "[cifrado]":
            return f"Cliente #{obj.id}"
        return f"{nombres} {apellidos}".strip()

class ClienteReadSerializer(ClienteNombreMixin, serializers.ModelSerializer):
    nombres = serializers.SerializerMethodField()
    apellidos = serializers.SerializerMethodField()
    telefono = serializers.SerializerMethodField()
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = Cliente
        fields = [
            "id",
            "nombres",
            "apellidos",
            "telefono",
            "nombre_completo",
            "estado",
            "created_at",
        ]

    def get_telefono(self, obj):
        return safe_decrypt(obj.telefono)


class ClienteListSerializer(ClienteNombreMixin, serializers.ModelSerializer):
    """Versión compacta para selects y búsquedas."""
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model  = Cliente
        fields = ["id", "nombre_completo"]


class ClientePapeleraSerializer(ClienteNombreMixin, serializers.ModelSerializer):
    """
    Cliente eliminado, para el listado de la papelera. `casos_para_restaurar`
    son los casos que se eliminaron junto con él y que volverán al restaurarlo.
    """
    nombre_completo       = serializers.SerializerMethodField()
    telefono              = serializers.SerializerMethodField()
    eliminado_por_nombre  = serializers.SerializerMethodField()
    casos_para_restaurar  = serializers.SerializerMethodField()

    class Meta:
        model  = Cliente
        fields = [
            "id", "nombre_completo", "telefono",
            "eliminado_at", "eliminado_por_nombre",
            "casos_para_restaurar", "created_at",
        ]

    def get_telefono(self, obj):
        return safe_decrypt(obj.telefono)

    def get_eliminado_por_nombre(self, obj):
        return nombre_visible_usuario(obj.eliminado_por)

    def get_casos_para_restaurar(self, obj):
        # La vista lo anota con un COUNT; si no viene anotado, se cuenta aquí.
        anotado = getattr(obj, "casos_para_restaurar", None)
        if anotado is not None:
            return anotado
        return obj.casos.filter(estado=False, eliminado_con_cliente=True).count()


class ClienteWriteSerializer(serializers.ModelSerializer):
    """Valida y cifra campos sensibles antes de persistir."""
    nombres          = serializers.CharField(max_length=200)
    apellidos        = serializers.CharField(max_length=200)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)

    NOMBRE_REGEX = re.compile(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$")

    class Meta:
        model  = Cliente
        fields = ["nombres", "apellidos", "telefono", "estado"]

    def _validar_nombre(self, value, campo_label):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError(
                f"{campo_label} debe tener al menos 2 caracteres."
            )
        if not self.NOMBRE_REGEX.match(value):
            raise serializers.ValidationError(
                f"{campo_label} solo puede contener letras y espacios."
            )
        return value

    def validate_nombres(self, value):
        return self._validar_nombre(value, "El nombre")

    def validate_apellidos(self, value):
        return self._validar_nombre(value, "Los apellidos")

    def validate_telefono(self, value):
        if not value:
            return value

        value = value.strip()

        if not value.isdigit():
            raise serializers.ValidationError(
                "El teléfono solo puede contener números."
            )

        if len(value) != 8:
            raise serializers.ValidationError(
                "El teléfono debe tener 8 dígitos."
            )

        if value[0] not in ("6", "7"):
            raise serializers.ValidationError(
                "El teléfono debe empezar con 6 o 7."
            )

        # Unicidad vía telefono_hash (HMAC-SHA256 determinístico): el
        # campo cifrado en sí no sirve para esto, porque AES-GCM usa
        # un nonce aleatorio y el mismo teléfono da un ciphertext
        # distinto cada vez. Con telefono_hash es un filter() directo.
        qs = Cliente.objects.filter(telefono_hash=hash_lookup(value))
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Ya existe un cliente registrado con este teléfono."
                + _aviso_si_esta_en_papelera(qs)
            )

        return value

    def validate(self, attrs):
        # El nombre completo se arma con nombres + apellidos juntos,
        # así que el chequeo de duplicado va a nivel de objeto (no de
        # un solo campo) para tener ambos valores disponibles incluso
        # en un PATCH parcial que solo mande uno de los dos.
        nombres = attrs.get("nombres")
        apellidos = attrs.get("apellidos")
        if self.instance:
            nombres = nombres if nombres is not None else safe_decrypt(self.instance.nombres)
            apellidos = apellidos if apellidos is not None else safe_decrypt(self.instance.apellidos)

        if nombres and apellidos:
            nombre_completo = f"{nombres.strip()} {apellidos.strip()}".strip()
            qs = Cliente.objects.filter(nombre_completo_hash=hash_lookup(nombre_completo))
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"nombres": "Ya existe un cliente registrado con este nombre y apellido."
                                + _aviso_si_esta_en_papelera(qs)}
                )

        return attrs

    def _encrypt_fields(self, validated_data: dict) -> dict:
        nombres = validated_data.get("nombres")
        apellidos = validated_data.get("apellidos")

        if nombres is not None:
            validated_data["nombres"] = encrypt(nombres)

        if apellidos is not None:
            validated_data["apellidos"] = encrypt(apellidos)

        # nombre_completo_hash se recalcula si cambió cualquiera de los
        # dos, usando el valor plano definitivo del otro (el ya
        # guardado en la instancia, si no vino en este request).
        if nombres is not None or apellidos is not None:
            nombres_final = nombres if nombres is not None else (
                safe_decrypt(self.instance.nombres) if self.instance else ""
            )
            apellidos_final = apellidos if apellidos is not None else (
                safe_decrypt(self.instance.apellidos) if self.instance else ""
            )
            nombre_completo = f"{nombres_final.strip()} {apellidos_final.strip()}".strip()
            validated_data["nombre_completo_hash"] = hash_lookup(nombre_completo)

        if "telefono" in validated_data:
            telefono = validated_data.get("telefono")
            validated_data["telefono_hash"] = hash_lookup(telefono) if telefono else None
            if telefono:
                validated_data["telefono"] = encrypt(telefono)

        return validated_data

    def create(self, validated_data):
        return super().create(self._encrypt_fields(validated_data))

    def update(self, instance, validated_data):
        # estado=False equivale a eliminar: pasa por la papelera (queda quién
        # y cuándo) y respeta la regla de los casos activos. Reactivar un
        # cliente eliminado no se hace por aquí sino con POST /restaurar/.
        desactivar = validated_data.pop("estado", True) is False and instance.estado
        with transaction.atomic():
            instance = super().update(instance, self._encrypt_fields(validated_data))
            if desactivar:
                try:
                    enviar_cliente_a_papelera(instance, self.context["request"].user, eliminar_casos=False)
                except ClienteConCasosActivosError as e:
                    raise serializers.ValidationError({
                        "estado": f"No se puede eliminar un cliente con casos activos. {e}",
                    })
        return instance