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

from django.db.models import Q
from rest_framework import serializers

from core.utils.archivos import validar_pdf

from modulo_catalogo.models.jerarquia import jerarquia as Jerarquia
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama import RamaDerecho

TAMANO_MAX_PDF_MB = 50


class CargaArticulosPDFSerializer(serializers.Serializer):
    """
    Campos esperados (multipart/form-data):
        archivo         — archivo PDF
        norma_id         — opcional, ID de una Norma existente y activa. Si
                            se manda, ES la norma destino (no se busca ni se
                            crea por nombre): sirve para el modo "norma
                            existente" del formulario, donde el usuario
                            elige de una lista en vez de escribir el nombre
                            a mano. En ese caso nombre_documento/sigla no
                            son obligatorios y se ignoran para buscar/crear.
        nombre_documento — obligatorio si NO se manda norma_id. Nombre en
                            texto del documento (ej. "Código de
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

    motor_lectura = serializers.ChoiceField(choices=['qwen', 'clasico'], required=False)
    metadatos = serializers.JSONField(required=False, default=dict)
    documento_oficial_id = serializers.IntegerField(required=False, min_value=1)
    archivo          = serializers.FileField(write_only=True)
    norma_id         = serializers.PrimaryKeyRelatedField(
                           queryset=Norma.objects.filter(estado=True),
                           source="norma",
                           required=False,
                           allow_null=True,
                       )
    nombre_documento = serializers.CharField(
                           max_length=200, required=False, allow_blank=True, trim_whitespace=True,
                       )
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
    modo_actualizacion = serializers.ChoiceField(choices=['completo', 'articulos'], required=False)
    revision_token = serializers.CharField(required=False, allow_blank=True)
    articulos_seleccionados = serializers.JSONField(required=False)

    def validate_metadatos(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('Los metadatos deben ser un objeto.')
        permitidos = {'tipo_norma', 'numero_norma', 'fecha_norma', 'fecha_publicacion', 'url_fuente'}
        if set(value) - permitidos:
            raise serializers.ValidationError('Metadatos desconocidos.')
        for campo, dato in value.items():
            if not isinstance(dato, str) or len(dato) > (1000 if campo == 'url_fuente' else 80):
                raise serializers.ValidationError('Metadato inválido: ' + campo)
        from modulo_catalogo.services.vigencia_service import fecha
        for campo in ['fecha_norma', 'fecha_publicacion']:
            if value.get(campo) and not fecha(value[campo]):
                raise serializers.ValidationError('Fecha inválida: ' + campo)
        if value.get('url_fuente'):
            from urllib.parse import urlparse
            if urlparse(value['url_fuente']).scheme not in ['http', 'https']:
                raise serializers.ValidationError('La fuente debe ser un enlace HTTP o HTTPS.')
        return value

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

        # La extensión y el tamaño no garantizan que el contenido sea un
        # PDF real (un .exe renombrado a informe.pdf pasaría los chequeos
        # de arriba); esto valida la firma del archivo y que se pueda abrir.
        valido, motivo = validar_pdf(value)
        if not valido:
            raise serializers.ValidationError(motivo)

        return value

    def validate_nombre_documento(self, value):
        value = (value or "").strip()
        # Vacío es válido a este nivel: cuando se manda norma_id (modo
        # "norma existente") este campo no hace falta. Que sea obligatorio
        # cuando NO se manda norma_id se exige en validate().
        if value and len(value) < 3:
            raise serializers.ValidationError(
                "El nombre del documento debe tener al menos 3 caracteres."
            )
        return value

    def validate(self, attrs):
        rama = attrs.get("rama")
        norma_existente = attrs.get("norma")  # viene de norma_id, si se mandó
        nombre_documento = (attrs.get("nombre_documento") or "").strip()
        sigla = attrs.get("sigla") or None

        if norma_existente is not None:
            # Modo "norma existente": el usuario la eligió de una lista, no
            # hay que buscar ni crear nada por nombre/sigla.
            norma = norma_existente
        else:
            if not nombre_documento:
                raise serializers.ValidationError({
                    "nombre_documento": (
                        "Escribe el nombre del documento, o selecciona una "
                        "norma existente de la lista."
                    )
                })

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
                # Si esa norma existe pero está eliminada, no se crea otra
                # igual: hay que restaurarla primero (así no se duplican
                # normas ni se pierden los artículos que ya tenía).
                filtro = Q(nombre__iexact=nombre_documento)
                if sigla:
                    filtro |= Q(sigla__iexact=sigla)
                eliminada = Norma.objects.filter(estado=False).filter(filtro).first()
                if eliminada:
                    raise serializers.ValidationError({
                        "nombre_documento": (
                            f'La norma "{eliminada.nombre}" está eliminada. '
                            "Pídele a un administrador que la restaure desde Catálogo → Normas antes de cargarle artículos."
                        )
                    })
                if not self.context.get('solo_revision'):
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
