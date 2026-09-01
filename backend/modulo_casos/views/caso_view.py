from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.permissions.auditoria_mixin import AuditoriaMixin
from core.permissions.roles_permission import EsOperativo
from core.permissions.roles import ve_todo
from modulo_casos.models.caso import Caso
from modulo_casos.models.hecho import Hecho
from modulo_casos.models.petitorio import Petitorio
from modulo_casos.serializers.caso_con_cliente_serializer import CasoConClienteSerializer
from modulo_casos.serializers.caso_serializer import (
    CasoCreateSerializer,
    CasoListSerializer,
    CasoReadSerializer,
    CasoUpdateSerializer,
    HechoSerializer,
    PetitorioSerializer,
    ResultadoCasoSerializer,
)

class CasoViewSet(AuditoriaMixin, ModelViewSet):
    """
    GET    /api/casos/                    — lista con filtros [admin/abogado: todos | asistente: solo propios, lectura]
    POST   /api/casos/                    — crear caso (texto o PDF), cliente ya existente [admin, abogado]
    POST   /api/casos/crear_con_cliente/  — crea cliente + caso en una transacción atómica [admin, abogado]
    GET    /api/casos/{id}/               — detalle completo
    PATCH  /api/casos/{id}/               — editar título/descripción/estado [admin, abogado]
    DELETE /api/casos/{id}/               — soft-delete [admin, abogado]
    POST   /api/casos/{id}/subir_pdf/     — adjuntar PDF al caso [admin, abogado]
    GET    /api/casos/{id}/hechos/        — lista hechos del caso
    GET    /api/casos/{id}/petitorios/    — lista petitorios del caso
    GET    /api/casos/{id}/resultado/     — resultado IA del caso
    GET    /api/casos/{id}/articulos/     — artículos del ranking
    POST   /api/casos/{id}/analizar/      — disparar pipeline IA [admin, abogado]
    GET    /api/casos/mis_casos/          — casos del usuario autenticado

    Permisos (ver core.permissions.roles_permission.EsOperativo):
    Administrador y Abogado tienen acceso total, incluyendo eliminar
    (soft-delete) de forma lógica. Asistente solo puede leer (GET) y
    únicamente ve sus propios casos.
    """
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields   = ["codigo", "titulo", "descripcion"]
    ordering_fields = ["created_at", "codigo", "titulo"]
    auditoria_tabla = "casos"

    def get_queryset(self):
        qs = (
            Caso.objects
            .filter(estado=True)
            .select_related("usuario", "cliente", "rama_detectada")
            .prefetch_related("documentos", "documentos_generados")
            .order_by("-created_at")
        )
        user = self.request.user

        # Administrador y Abogado ven todos los casos; Asistente solo
        # ve los propios (y en modo lectura, ver get_permissions()).
        if not ve_todo(user):
            qs = qs.filter(usuario=user)

        # --- filtros opcionales via query params ---
        rama_id     = self.request.query_params.get("rama_id")
        cliente_id  = self.request.query_params.get("cliente_id")
        fecha_desde = self.request.query_params.get("fecha_desde")
        fecha_hasta = self.request.query_params.get("fecha_hasta")
        tiene_pdf   = self.request.query_params.get("tiene_pdf")

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
        instance.estado = False
        instance.save(update_fields=["estado"])
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
        Ejecuta el pipeline IA completo de forma síncrona:
        chunking → embeddings → ranking → LLM → resultados → docx
        """
        from modulo_ia.serializers.ia_serializer import AnalisisCasoSerializer

        caso       = self.get_object()
        serializer = AnalisisCasoSerializer(data={"caso_id": caso.pk})
        serializer.is_valid(raise_exception=True)

        from modulo_ia.tasks.analisis_task import ejecutar_analisis_caso
        ejecutar_analisis_caso(caso.pk)

        self._auditar("ANALYZE", registro_id=caso.pk)

        return Response(
            {
                "detail" : "Análisis completado correctamente.",
                "caso_id": caso.pk,
            },
            status=status.HTTP_200_OK,
        )