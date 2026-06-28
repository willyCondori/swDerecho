from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views.documento_view import (
    TipoDocViewSet,
    DocumentoCasoViewSet,
    PlantillaDocumentoViewSet,
    DocumentoGeneradoViewSet,
)

router = DefaultRouter()

router.register(r"tipo-doc", TipoDocViewSet, basename="tipo-doc")
router.register(r"documentos", DocumentoCasoViewSet, basename="documentos")
router.register(r"plantillas", PlantillaDocumentoViewSet, basename="plantillas")
router.register(
    r"documentos-generados",
    DocumentoGeneradoViewSet,
    basename="documentos-generados",
)

urlpatterns = [
    path("", include(router.urls)),
]