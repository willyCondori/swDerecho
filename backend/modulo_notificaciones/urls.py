from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views.notificacion_view import NotificacionViewSet

router = DefaultRouter()
router.register(r"", NotificacionViewSet, basename="notificaciones")

urlpatterns = [
    path("", include(router.urls)),
]
