from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views.cliente_view import ClienteViewSet

router = DefaultRouter()
router.register(r"clientes", ClienteViewSet, basename="clientes")

urlpatterns = [
    path("", include(router.urls)),
]