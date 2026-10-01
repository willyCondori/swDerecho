from django.urls import path

from .views.dashboard_view import DashboardResumenView

urlpatterns = [
    path("resumen/", DashboardResumenView.as_view(), name="dashboard-resumen"),
]
