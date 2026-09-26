from django.db.models import F
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.permissions.auditoria_mixin import AuditoriaMixin
from core.permissions.roles_permission import EsAbogado, EsOperativo
from modulo_casos.models.caso import Caso
from modulo_casos.models.etapas import EtapaCaso
from modulo_casos.models.hecho import Hecho
from modulo_casos.models.petitorio import Petitorio
from modulo_casos.serializers.caso_con_cliente_serializer import CasoConClienteSerializer
from modulo_casos.serializers.caso_serializer import (
    CasoCreateSerializer,
    CasoListSerializer,
    CasoPapeleraSerializer,
    CasoReadSerializer,
    CasoUpdateSerializer,
    HechoSerializer,
    PetitorioSerializer,
    ResultadoCasoSerializer,
)
from modulo_casos.serializers.seguimiento_serializer import (
    CambiarEtapaSerializer,
    SeguimientoCasoSerializer,
)
from modulo_casos.services.papelera_service import (
    ClienteInactivoError,
    enviar_a_papelera,
    restaurar_desde_papelera,
)
from modulo_casos.services.seguimiento_service import registrar_seguimiento

class CasoViewSet(AuditoriaMixin, ModelViewSet):
    """
    GET    /api/casos/                    — lista con filtros [todos los roles ven todos los casos activos]
    POST   /api/casos/                    — crear caso (texto o PDF), cliente ya existente [admin, abogado]
    POST   /api/casos/crear_con_cliente/  — crea cliente + caso en una transacción atómica [admin, abogado]
    GET    /api/casos/{id}/               — detalle completo
    PATCH  /api/casos/{id}/               — editar título/descripción/estado [admin, abogado]
    DELETE /api/casos/{id}/               — envía el caso a la papelera (soft-delete) [admin, abogado]
    GET    /api/casos/papelera/           — casos eliminados, más recientes primero [admin, abogado]
    POST   /api/casos/{id}/restaurar/     — restaura un caso de la papelera [admin, abogado]
    POST   /api/casos/{id}/subir_pdf/     — adjuntar PDF al caso [admin, abogado]
    GET    /api/casos/{id}/hechos/        — lista hechos del caso
    GET    /api/casos/{id}/petitorios/    — lista petitorios del caso
    GET    /api/casos/{id}/resultado/     — resultado IA del caso
    GET    /api/casos/{id}/articulos/     — artículos del ranking
    POST   /api/casos/{id}/analizar/      — disparar pipeline IA [admin, abogado]
    GET    /api/casos/mis_casos/          — casos del usuario autenticado (filtro de conveniencia)
    GET    /api/casos/etapas/             — catálogo de etapas de seguimiento (value, label)
    GET    /api/casos/{id}/seguimiento/   — línea de tiempo del caso (más reciente primero)
    POST   /api/casos/{id}/cambiar_etapa/ — cambia la etapa y/o agrega una nota al historial [admin, abogado]

    Filtro extra en el listado: ?etapa=<value> (ver GET /api/casos/etapas/).

    Permisos (ver core.permissions.roles_permission.EsOperativo):
    Administrador, Abogado y Asistente ven todos los casos activos.
    Administrador y Abogado tienen acceso total, incluyendo eliminar
    (soft-delete) de forma lógica. Asistente solo puede leer (GET).
    """
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields   = ["codigo", "titulo", "descripcion"]
    ordering_fields = ["created_at", "codigo", "titulo"]
    auditoria_tabla = "casos"

    def get_queryset(self):
        if self.action in ("papelera", "restaurar"):
            # Papelera: solo casos eliminados. El resto de las acciones
            # nunca ve casos con estado=False (404).
            return (
                Caso.objects
                .filter(estado=False)
                .select_related(
                    "usuario", "cliente", "rama_detectada",
                    "eliminado_por", "eliminado_por__perfil",
                )
            )

        qs = (
            Caso.objects
            .filter(estado=True)
            .select_related("usuario", "cliente", "rama_detectada")
            .prefetch_related("documentos", "documentos_generados")
            .order_by("-created_at")
        )
        # Todos los roles (Administrador, Abogado, Asistente) ven todos
        # los casos activos. La restricción de "solo lectura" para
        # Asistente ya la resuelve EsOperativo a nivel de método HTTP
        # (ver get_permissions()); acá no hace falta filtrar por dueño.

        # --- filtros opcionales via query params ---
        rama_id     = self.request.query_params.get("rama_id")
        cliente_id  = self.request.query_params.get("cliente_id")
        fecha_desde = self.request.query_params.get("fecha_desde")
        fecha_hasta = self.request.query_params.get("fecha_hasta")
        tiene_pdf   = self.request.query_params.get("tiene_pdf")
        etapa       = self.request.query_params.get("etapa")

        if etapa:
            qs = qs.filter(etapa=etapa)
        if rama_id:
            qs = qs.filter(rama_detectada_id=rama_id)
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)
        if fecha_desde:
            qs = qs.filter(created_at__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(created_at__date__lte=fecha_hasta)
        if tiene_pdf is not None:
            if tiene_pdf.lower() in ["true", "1"]:
                qs = qs.filter(documentos__tipo_archivo="pdf")
            else:
                qs = qs.exclude(documentos__tipo_archivo="pdf")

        return qs.distinct()

    def get_serializer_class(self):
        if self.action == "create":
            return CasoCreateSerializer
        if self.action in ["update", "partial_update"]:
            return CasoUpdateSerializer
        if self.action == "list":
            return CasoListSerializer
        return CasoReadSerializer

    def get_permissions(self):
        if self.action in ("papelera", "restaurar"):
            # Administrador y Abogado; el Asistente no ve la papelera.
            return [EsAbogado()]
        return [EsOperativo()]

    def create(self, request, *args, **kwargs):
        """
        POST /api/casos/
        Crea un caso para un cliente que YA existe (cliente_id requerido).
        Acepta opcionalmente un archivo PDF junto al texto.
        """
        tiene_pdf  = "archivo_pdf" in request.FILES
        serializer = self.get_serializer(
            data=request.data,
            context={**self.get_serializer_context(), "tiene_pdf": tiene_pdf},
        )
        serializer.is_valid(raise_exception=True)

        caso = serializer.save()
        self._auditar("CREATE", registro_id=caso.pk)

        if tiene_pdf:
            self._guardar_pdf(request, caso)

        return Response(
            CasoReadSerializer(caso, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="crear_con_cliente")
    def crear_con_cliente(self, request):
        """
        POST /api/casos/crear_con_cliente/
        Crea el cliente y el caso en una sola operación atómica: si el
        caso falla al crearse, el cliente recién insertado se revierte
        también (ver CasoConClienteSerializer).

        Body: nombres, apellidos,
              titulo, descripcion, archivo_pdf (opcional, multipart).
        """
        tiene_pdf  = "archivo_pdf" in request.FILES
        serializer = CasoConClienteSerializer(
            data=request.data,
            context={**self.get_serializer_context(), "tiene_pdf": tiene_pdf},
        )
        serializer.is_valid(raise_exception=True)
        resultado = serializer.save()
        caso = resultado["caso"]

        self._auditar("CREATE", registro_id=caso.pk, metadata={"cliente_id": resultado["cliente"].pk})

        # El PDF se guarda DESPUÉS de confirmar la transacción de
        # cliente+caso. Si esto falla, el cliente y el caso ya quedaron
        # creados correctamente (correcto: la falta de PDF no debe
        # revertir un caso válido); el usuario puede reintentar subirlo
        # con POST /api/casos/{id}/subir_pdf/.
        if tiene_pdf:
            self._guardar_pdf(request, caso)

        return Response(
            CasoReadSerializer(caso, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    def _guardar_pdf(self, request, caso):
        from modulo_documentos.models.documento import TipoDoc
        from modulo_documentos.serializers.documento_serializer import DocumentoCasoWriteSerializer

        tipo, _ = TipoDoc.objects.get_or_create(tipo="caso_pdf")
        doc_ser = DocumentoCasoWriteSerializer(
            data={
                "caso"          : caso.pk,
                "archivo"       : request.FILES["archivo_pdf"],
                "tipo_documento": tipo.pk,
            },
            context={"request": request},
        )
        doc_ser.is_valid(raise_exception=True)
        doc_ser.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        enviar_a_papelera(instance, request.user)
        self._auditar("DELETE", registro_id=instance.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------
    # Acciones extra
    # ------------------------------------------------------------------

    @action(detail=False, methods=["get"], url_path="mis_casos")
    def mis_casos(self, request):
        """GET /api/casos/mis_casos/ — casos del usuario autenticado."""
        qs         = Caso.objects.filter(usuario=request.user, estado=True).order_by("-created_at")
        page       = self.paginate_queryset(qs)
        serializer = CasoListSerializer(
            page if page is not None else qs, many=True, context=self.get_serializer_context()
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="papelera")
    def papelera(self, request):
        """
        GET /api/casos/papelera/ — casos eliminados, los enviados más
        recientemente primero (los eliminados antes de la papelera, sin
        fecha, al final). Acepta ?search= (código, título, descripción).
        """
        qs = self.get_queryset().order_by(
            F("eliminado_at").desc(nulls_last=True), "-created_at"
        )
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        serializer = CasoPapeleraSerializer(
            page if page is not None else qs, many=True,
            context=self.get_serializer_context(),
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="restaurar")
    def restaurar(self, request, pk=None):
        """
        POST /api/casos/{id}/restaurar/ — devuelve el caso a la lista de
        casos activos. Responde 409 si su cliente fue eliminado.
        """
        caso = self.get_object()
        try:
            restaurar_desde_papelera(caso, request.user)
        except ClienteInactivoError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)

        self._auditar("UPDATE", registro_id=caso.pk, metadata={"accion": "restaurar"})
        return Response(
            CasoReadSerializer(caso, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="etapas")
    def etapas(self, request):
        """GET /api/casos/etapas/ — etapas disponibles, en orden cronológico."""
        return Response([
            {"value": valor, "label": etiqueta, "orden": orden}
            for orden, (valor, etiqueta) in enumerate(EtapaCaso.choices, start=1)
        ])

    @action(detail=True, methods=["get"], url_path="seguimiento")
    def seguimiento(self, request, pk=None):
        """GET /api/casos/{id}/seguimiento/ — línea de tiempo, más reciente primero."""
        caso = self.get_object()
        entradas = (
            caso.seguimientos
            .select_related("usuario", "usuario__perfil")
            .order_by("-created_at", "-id")
        )
        return Response(
            SeguimientoCasoSerializer(entradas, many=True, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=["post"], url_path="cambiar_etapa")
    def cambiar_etapa(self, request, pk=None):
        """
        POST /api/casos/{id}/cambiar_etapa/
        Body: etapa (obligatoria), nota (opcional, máx. 2000 caracteres).

        Crea una entrada en el historial y actualiza la etapa actual del
        caso. Si 'etapa' es la que ya tiene, solo se acepta con nota
        (actualización de seguimiento sin cambio de etapa).
        """
        caso = self.get_object()
        serializer = CambiarEtapaSerializer(
            data=request.data,
            context={**self.get_serializer_context(), "caso": caso},
        )
        serializer.is_valid(raise_exception=True)

        etapa_anterior = caso.etapa
        seguimiento = registrar_seguimiento(
            caso,
            etapa=serializer.validated_data["etapa"],
            usuario=request.user,
            nota=serializer.validated_data["nota"],
        )
        self._auditar(
            "UPDATE",
            registro_id=caso.pk,
            metadata={
                "accion": "cambiar_etapa",
                "etapa_anterior": etapa_anterior,
                "etapa_nueva": seguimiento.etapa,
                "seguimiento_id": seguimiento.pk,
            },
        )
        return Response(
            {
                "etapa": caso.etapa,
                "etapa_display": caso.get_etapa_display(),
                "etapa_actualizada_at": caso.etapa_actualizada_at,
                "seguimiento": SeguimientoCasoSerializer(
                    seguimiento, context=self.get_serializer_context()
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="subir_pdf")
    def subir_pdf(self, request, pk=None):
        """POST /api/casos/{id}/subir_pdf/ — adjunta o reemplaza el PDF del caso."""
        caso = self.get_object()
        if "archivo_pdf" not in request.FILES:
            return Response(
                {"detail": "Debe adjuntar un archivo PDF en el campo 'archivo_pdf'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self._guardar_pdf(request, caso)
        self._auditar("UPDATE", registro_id=caso.pk, metadata={"accion": "subir_pdf"})
        return Response(
            {"detail": "PDF adjuntado correctamente."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="hechos")
    def hechos(self, request, pk=None):
        """GET /api/casos/{id}/hechos/"""
        caso   = self.get_object()
        hechos = Hecho.objects.filter(casos_hecho__caso=caso).order_by("casos_hecho__orden")
        return Response(HechoSerializer(hechos, many=True).data)

    @action(detail=True, methods=["get"], url_path="petitorios")
    def petitorios(self, request, pk=None):
        """GET /api/casos/{id}/petitorios/"""
        caso       = self.get_object()
        petitorios = Petitorio.objects.filter(casos_petitorio__caso=caso)
        return Response(PetitorioSerializer(petitorios, many=True).data)

    @action(detail=True, methods=["get"], url_path="resultado")
    def resultado(self, request, pk=None):
        """GET /api/casos/{id}/resultado/ — resultado IA (resumen, fortalezas, etc.)."""
        caso = self.get_object()
        if not hasattr(caso, "resultado"):
            return Response(
                {"detail": "Este caso aún no tiene resultados de análisis IA."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            ResultadoCasoSerializer(caso.resultado).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="articulos")
    def articulos(self, request, pk=None):
        """GET /api/casos/{id}/articulos/ — ranking de artículos aplicables."""
        from modulo_ia.models.resultado import ResultadoArticulo
        from modulo_ia.serializers.ia_serializer import ResultadoArticuloSerializer

        caso       = self.get_object()
        resultados = (
            ResultadoArticulo.objects
            .filter(caso=caso)
            .select_related("articulo", "articulo__norma", "articulo__rama")
            .order_by("posicion")
        )
        return Response(
            ResultadoArticuloSerializer(resultados, many=True).data
        )

    @action(detail=True, methods=["post"], url_path="analizar")
    def analizar(self, request, pk=None):
        """
        POST /api/casos/{id}/analizar/
        Lanza el pipeline IA completo (chunking → embeddings → entidades →
        ranking → resultado) en segundo plano y devuelve al toque. El
        avance se consulta con GET /api/casos/{id}/ (campos
        estado_analisis/analisis_paso) o con GET .../seguimiento/ para el
        historial — no bloquea el request como antes.

        409 si ya hay un análisis en curso para este caso (ver
        Caso.analisis_en_curso): evita que un doble clic dispare dos
        corridas en paralelo sobre los mismos chunks/ranking.
        """
        from modulo_ia.serializers.ia_serializer import AnalisisCasoSerializer
        from modulo_ia.services.analisis_background import iniciar_analisis

        caso       = self.get_object()
        serializer = AnalisisCasoSerializer(data={"caso_id": caso.pk})
        serializer.is_valid(raise_exception=True)

        ok, detalle = iniciar_analisis(caso, request.user)
        if not ok:
            return Response({"detail": detalle}, status=status.HTTP_409_CONFLICT)

        caso.refresh_from_db(fields=["estado_analisis", "analisis_paso"])
        return Response(
            {
                "detail"        : "Análisis iniciado.",
                "caso_id"       : caso.pk,
                "estado_analisis": caso.estado_analisis,
            },
            status=status.HTTP_202_ACCEPTED,
        )