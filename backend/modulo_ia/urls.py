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
    path("analizar/", AnalisisCasoView.as_view(), name="ia-analizar"),
    path(
        "tarea/<str:task_id>/",
        EstadoTareaView.as_view(),
        name="ia-tarea-estado",
    ),
    path("", include(router.urls)),
]