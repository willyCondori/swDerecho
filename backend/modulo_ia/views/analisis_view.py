from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet

from core.permissions.auditoria_mixin import AuditoriaMixin, registrar_auditoria
from core.permissions.roles_permission import EsAdmin, EsOperativo, EsUsuarioAutenticado
from modulo_ia.models.chunk import ChunkCaso
from modulo_ia.models.embedding import (
    EmbeddingArticulo,
    EmbeddingChunk,
    EntidadDetectadaCaso,
)
from modulo_ia.models.resultado import ResultadoArticulo
from modulo_ia.serializers.ia_serializer import (
    AnalisisCasoSerializer,
    ChunkCasoSerializer,
    EmbeddingArticuloSerializer,
    EmbeddingChunkSerializer,
    EntidadDetectadaSerializer,
    ResultadoArticuloSerializer,
)
from core.permissions.roles import ve_todo


# ---------------------------------------------------------------------------
# ChunkCaso — solo lectura (los chunks los genera el servicio internamente)
# ---------------------------------------------------------------------------

class ChunkCasoViewSet(ReadOnlyModelViewSet):
    """
    GET /api/chunks/             — lista de chunks [abogado, admin]
    GET /api/chunks/{id}/        — detalle
    GET /api/chunks/por_caso/    — filtrar por caso_id
    GET /api/chunks/{id}/entidades/ — entidades detectadas en el chunk
    """
    serializer_class = ChunkCasoSerializer
    filter_backends  = [OrderingFilter]
    ordering_fields  = ["orden", "created_at"]

    def get_permissions(self):
        return [EsOperativo()]

    def get_queryset(self):
        qs      = ChunkCaso.objects.select_related("caso").order_by("caso", "orden")
        user    = self.request.user
        rol     = getattr(user.rol, "nombre", "") if user.rol else ""
        caso_id = self.request.query_params.get("caso_id")

        if not ve_todo(user):
            qs = qs.filter(caso__usuario=user)
        if caso_id:
            qs = qs.filter(caso_id=caso_id)
        return qs

    @action(detail=False, methods=["get"], url_path="por_caso")
    def por_caso(self, request):
        """GET /api/chunks/por_caso/?caso_id=X"""
        caso_id = request.query_params.get("caso_id")
        if not caso_id:
            return Response(
                {"detail": "Parámetro caso_id requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = self.get_queryset().filter(caso_id=caso_id)
        return Response(ChunkCasoSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"], url_path="entidades")
    def entidades(self, request, pk=None):
        """GET /api/chunks/{id}/entidades/ — entidades detectadas en el chunk."""
        chunk     = self.get_object()
        entidades = EntidadDetectadaCaso.objects.filter(chunk=chunk).order_by("-score")
        return Response(EntidadDetectadaSerializer(entidades, many=True).data)


# ---------------------------------------------------------------------------
# ResultadoArticulo — ranking jurídico (solo lectura pública, admin puede ver todo)
# ---------------------------------------------------------------------------

class ResultadoArticuloViewSet(ReadOnlyModelViewSet):
    """
    GET /api/ranking/            — lista de rankings
    GET /api/ranking/{id}/       — detalle
    GET /api/ranking/por_caso/   — top artículos de un caso
    GET /api/ranking/top/        — top N artículos de un caso
    """
    serializer_class = ResultadoArticuloSerializer
    filter_backends  = [OrderingFilter]
    ordering_fields  = ["posicion", "score_total"]

    def get_permissions(self):
        return [EsOperativo()]

    def get_queryset(self):
        qs      = (
            ResultadoArticulo.objects
            .select_related(
                "caso", "articulo",
                "articulo__norma", "articulo__rama",
            )
            .order_by("caso", "posicion")
        )
        user    = self.request.user
        rol     = getattr(user.rol, "nombre", "") if user.rol else ""
        caso_id = self.request.query_params.get("caso_id")

        if not ve_todo(user):
            qs = qs.filter(caso__usuario=user)
        if caso_id:
            qs = qs.filter(caso_id=caso_id)
        return qs

    @action(detail=False, methods=["get"], url_path="por_caso")
    def por_caso(self, request):
        """GET /api/ranking/por_caso/?caso_id=X — todos los artículos del ranking."""
        caso_id = request.query_params.get("caso_id")
        if not caso_id:
            return Response(
                {"detail": "Parámetro caso_id requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = self.get_queryset().filter(caso_id=caso_id)
        return Response(ResultadoArticuloSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="top")
    def top(self, request):
        """
        GET /api/ranking/top/?caso_id=X&n=10
        Devuelve los N artículos más relevantes (por defecto 10).
        """
        caso_id = request.query_params.get("caso_id")
        n       = int(request.query_params.get("n", 10))

        if not caso_id:
            return Response(
                {"detail": "Parámetro caso_id requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if n < 1 or n > 50:
            return Response(
                {"detail": "El parámetro n debe estar entre 1 y 50."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = self.get_queryset().filter(caso_id=caso_id)[:n]
        return Response(ResultadoArticuloSerializer(qs, many=True).data)


# ---------------------------------------------------------------------------
# EmbeddingArticulo — solo admin (información técnica interna)
# ---------------------------------------------------------------------------

class EmbeddingArticuloViewSet(ReadOnlyModelViewSet):
    """
    GET /api/embeddings-articulos/       — lista [admin]
    GET /api/embeddings-articulos/{id}/  — detalle
    POST /api/embeddings-articulos/regenerar/ — regenera todos los embeddings [admin]
    """
    queryset         = EmbeddingArticulo.objects.select_related("articulo").order_by("id")
    serializer_class = EmbeddingArticuloSerializer

    def get_permissions(self):
        return [EsAdmin()]

    @action(detail=False, methods=["post"], url_path="regenerar")
    def regenerar(self, request):
        """
        POST /api/embeddings-articulos/regenerar/
        Regenera los embeddings de TODOS los artículos activos.

        DESHABILITADO TEMPORALMENTE: esta es una operación masiva
        (cientos de artículos) pensada para correr en segundo plano
        vía Celery (`regenerar_embeddings_articulos.delay()`). Como
        Celery no está configurado (config/celery.py vacío), antes
        este endpoint encolaba la tarea y nunca se ejecutaba —
        parecía funcionar (202 Accepted) pero no hacía nada.

        A diferencia del análisis de un caso individual (ver
        AnalisisCasoView / CasoViewSet.analizar), correr esto de
        forma síncrona dentro de un request HTTP arriesga timeout de
        proxy/gateway y del propio cliente (el frontend usa un
        timeout de 30s en axiosInstance.js) para un solo request de
        cientos de artículos. Por eso, en vez de "arreglarlo" con una
        llamada síncrona que probablemente truene, queda desactivado
        hasta que Celery esté funcionando.

        Mientras tanto, para regenerar embeddings usar el management
        command directamente en el servidor:
            python manage.py finetune_embeddings_penal  # o el comando
                                                          # de regeneración
                                                          # correspondiente
        """
        return Response(
            {
                "detail": (
                    "Esta operación requiere Celery, que todavía no está "
                    "configurado en este entorno. Ejecutá el management "
                    "command de regeneración de embeddings directamente "
                    "en el servidor en lugar de este endpoint."
                ),
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


# ---------------------------------------------------------------------------
# Estado de tarea Celery
# ---------------------------------------------------------------------------

class EstadoTareaView(APIView):
    """
    GET /api/ia/tarea/{task_id}/
    Consulta el estado de una tarea Celery (análisis IA, regeneración, etc.)

    SIN USO POR AHORA: como AnalisisCasoView y CasoViewSet.analizar ya
    no encolan nada (corren de forma síncrona mientras Celery no esté
    configurado, ver notas ahí) y la regeneración de embeddings está
    deshabilitada, no queda ninguna tarea con task_id que consultar
    acá. La ruta correspondiente está comentada en modulo_ia/urls.py.
    Cuando Celery esté funcionando y los endpoints anteriores vuelvan
    a usar `.delay()`, se puede reactivar esta vista tal cual está.
    """
    permission_classes = [EsOperativo]

    def get(self, request, task_id):
        try:
            from celery.result import AsyncResult
            result = AsyncResult(task_id)

            respuesta = {
                "task_id": task_id,
                "estado" : result.status,   # PENDING, STARTED, SUCCESS, FAILURE, RETRY
            }

            if result.status == "SUCCESS":
                respuesta["resultado"] = result.result
            elif result.status == "FAILURE":
                respuesta["error"] = str(result.result)
            elif result.status == "STARTED":
                # Si la tarea reporta progreso vía meta
                info = result.info or {}
                respuesta["progreso"] = info.get("progreso", 0)
                respuesta["paso"]     = info.get("paso", "procesando")

            return Response(respuesta, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"detail": f"No se pudo consultar la tarea: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ---------------------------------------------------------------------------
# Disparar análisis desde el módulo IA directamente
# ---------------------------------------------------------------------------

class AnalisisCasoView(APIView):
    """
    POST /api/ia/analizar/
    Body: { "caso_id": X }
    Alternativa al endpoint /api/casos/{id}/analizar/ del módulo casos.

    NOTA: se ejecuta de forma SÍNCRONA (idéntico a
    CasoViewSet.analizar en modulo_casos/views/caso_view.py) mientras
    Celery no esté configurado (config/celery.py está vacío). Antes
    llamaba a `ejecutar_analisis_caso.delay(caso_id)`, lo que sin un
    worker corriendo se queda colgado o falla en silencio. Cuando
    Celery esté funcionando, revertir esto a `.delay()` y volver a
    habilitar la ruta `tarea/<task_id>/` (ver EstadoTareaView más abajo).
    """
    permission_classes = [EsOperativo]

    def post(self, request):
        serializer = AnalisisCasoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        caso_id = serializer.validated_data["caso_id"]

        try:
            from modulo_ia.tasks.analisis_task import ejecutar_analisis_caso
            ejecutar_analisis_caso(caso_id)

            registrar_auditoria(
                usuario=request.user,
                tabla="casos",
                accion="ANALYZE",
                registro_id=caso_id,
                request=request,
            )
            return Response(
                {
                    "detail" : "Análisis completado correctamente.",
                    "caso_id": caso_id,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"detail": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )