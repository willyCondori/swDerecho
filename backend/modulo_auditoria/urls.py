from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views.auditoria_view import AuditoriaViewSet

router = DefaultRouter()
router.register(r"auditoria", AuditoriaViewSet, basename="auditoria")

urlpatterns = [
    path("", include(router.urls)),
]