from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views.analisis_view import (
    AnalisisCasoView,
    EstadoTareaView,
    ChunkCasoViewSet,
    ResultadoArticuloViewSet,
    EmbeddingArticuloViewSet,
)

router = DefaultRouter()

router.register(r"chunks", ChunkCasoViewSet, basename="chunks")
router.register(r"ranking", ResultadoArticuloViewSet, basename="ranking")
router.register(
    r"embeddings-articulos",
    EmbeddingArticuloViewSet,
    basename="embeddings-articulos",
)

urlpatterns = [
    # /api/ia/analizar/ ahora corre de forma SÍNCRONA (ver AnalisisCasoView),
    # ya no encola nada en Celery.
    path("analizar/", AnalisisCasoView.as_view(), name="ia-analizar"),

    # Deshabilitada mientras Celery no esté configurado: no hay tareas
    # asíncronas encoladas cuyo task_id se pueda consultar acá (ver
    # notas en EstadoTareaView y en EmbeddingArticuloViewSet.regenerar
    # dentro de views/analisis_view.py). Descomentar cuando Celery
    # esté funcionando y los endpoints vuelvan a usar `.delay()`.
    # path(
    #     "tarea/<str:task_id>/",
    #     EstadoTareaView.as_view(),
    #     name="ia-tarea-estado",
    # ),

    path("", include(router.urls)),
]