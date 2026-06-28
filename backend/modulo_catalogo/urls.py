from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views.catalogo_view import (
    RamaDerechoViewSet,
    NormaViewSet,
    EntidadJuridicaViewSet,
    ArticuloViewSet,
)

router = DefaultRouter()

router.register(r"ramas", RamaDerechoViewSet, basename="ramas")
router.register(r"normas", NormaViewSet, basename="normas")
router.register(r"entidades", EntidadJuridicaViewSet, basename="entidades")
router.register(r"articulos", ArticuloViewSet, basename="articulos")

urlpatterns = [
    path("", include(router.urls)),
]