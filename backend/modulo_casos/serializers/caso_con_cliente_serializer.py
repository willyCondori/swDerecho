from django.db import transaction
from rest_framework import serializers

from modulo_casos.serializers.caso_serializer import CasoCreateSerializer
from modulo_clientes.serializers.cliente_serializer import ClienteWriteSerializer


class CasoConClienteSerializer(serializers.Serializer):
    """
    Crea un Cliente y un Caso en una única transacción atómica.

    Si la creación del Caso falla por cualquier motivo (validación,
    IntegrityError, error de guardado, etc.), Django revierte también
    la creación del Cliente ya insertado — no queda un cliente
    "huérfano" sin caso asociado en la base de datos.

    No duplica reglas de negocio: reutiliza ClienteWriteSerializer
    (regex de nombre, edad máxima...) y CasoCreateSerializer (límites
    de título/descripción, generación de código único, asignación
    del usuario autenticado) que ya existen en cada módulo.

    Requiere en el context:
      - "request": usado por CasoCreateSerializer para asignar el
        usuario autenticado como propietario del caso.
      - "tiene_pdf" (opcional): True si la vista recibió un archivo
        PDF junto con la solicitud, para permitir que 'descripcion'
        venga vacía.
    """
    # Datos del cliente
    nombres          = serializers.CharField(max_length=200)
    apellidos        = serializers.CharField(max_length=200)

    # Datos del caso
    titulo      = serializers.CharField(max_length=500)
    descripcion = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        tiene_pdf = self.context.get("tiene_pdf", False)

        # Reutiliza las validaciones de ClienteWriteSerializer.
        cliente_ser = ClienteWriteSerializer(data={
            "nombres": attrs["nombres"],
            "apellidos": attrs["apellidos"],
        })
        cliente_ser.is_valid(raise_exception=True)
        attrs["_cliente_validado"] = cliente_ser.validated_data

        # Reutiliza las mismas reglas de título/descripción que
        # CasoCreateSerializer, sin necesitar aún un cliente_id
        # (el cliente todavía no existe en este punto).
        caso_validador = CasoCreateSerializer()
        attrs["titulo"] = caso_validador.validate_titulo(attrs["titulo"])
        attrs["descripcion"] = caso_validador.validate_descripcion(
            attrs.get("descripcion", "")
        )

        if not attrs.get("descripcion") and not tiene_pdf:
            raise serializers.ValidationError(
                {"descripcion": "Debe redactar el caso o adjuntar un documento PDF."}
            )

        return attrs

    def create(self, validated_data):
        cliente_data = validated_data.pop("_cliente_validado")

        # transaction.atomic(): si CUALQUIER excepción ocurre dentro de
        # este bloque (incluyendo la validación/guardado del Caso),
        # TODO se revierte — incluyendo el INSERT del Cliente ya
        # ejecutado en la línea siguiente. La base nunca queda en un
        # estado intermedio con cliente sin caso.
        with transaction.atomic():
            cliente = ClienteWriteSerializer().create(cliente_data)

            caso_ser = CasoCreateSerializer(
                data={
                    "titulo": validated_data["titulo"],
                    "descripcion": validated_data.get("descripcion", ""),
                    "cliente_id": cliente.pk,
                },
                context=self.context,
            )
            # Nota: esto vuelve a correr validate_titulo/validate_descripcion.
            # Es intencional y seguro (validación idempotente y barata) —
            # así CasoCreateSerializer sigue siendo la única fuente de
            # verdad de esas reglas, sin necesidad de confiar ciegamente
            # en la validación ya hecha arriba.
            caso_ser.is_valid(raise_exception=True)
            caso = caso_ser.save()

        return {"cliente": cliente, "caso": caso}