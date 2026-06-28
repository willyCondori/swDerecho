from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views.caso_view import CasoViewSet

router = DefaultRouter()
router.register(r"casos", CasoViewSet, basename="casos")

urlpatterns = [
    path("", include(router.urls)),
]