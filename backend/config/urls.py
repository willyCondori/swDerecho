from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/usuarios/", include("modulo_usuarios.urls")),
    path("api/clientes/", include("modulo_clientes.urls")),
    path("api/catalogo/", include("modulo_catalogo.urls")),
    path("api/casos/", include("modulo_casos.urls")),
    path("api/documentos/", include("modulo_documentos.urls")),
    path("api/ia/", include("modulo_ia.urls")),
    path("api/auditoria/", include("modulo_auditoria.urls")),

    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]