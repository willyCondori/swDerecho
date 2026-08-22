from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views.catalogo_view import (
    RamaDerechoViewSet,
    NormaViewSet,
    EntidadJuridicaViewSet,
    ArticuloViewSet,
)
from .views.carga_articulos_view import (
    CargaArticulosView,
    EstadoCargaPDFView,
    FuentesDisponiblesView,
)

router = DefaultRouter()

router.register(r"ramas", RamaDerechoViewSet, basename="ramas")
router.register(r"normas", NormaViewSet, basename="normas")
router.register(r"entidades", EntidadJuridicaViewSet, basename="entidades")
router.register(r"articulos", ArticuloViewSet, basename="articulos")

urlpatterns = [
    path("", include(router.urls)),
    path("cargar-articulos/", CargaArticulosView.as_view()),
    # Dos rutas para el mismo estado: soporta tanto
    # /cargar-articulos/estado/?task_id=... (query param — la que ya
    # está usando el frontend, según el log) como
    # /cargar-articulos/estado/<task_id>/ (path param, más RESTful)
    path("cargar-articulos/estado/", EstadoCargaPDFView.as_view()),
    path("cargar-articulos/estado/<str:task_id>/", EstadoCargaPDFView.as_view()),
    path("cargar-articulos/fuentes/", FuentesDisponiblesView.as_view()),
]