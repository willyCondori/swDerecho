from django.urls import include, path
from rest_framework.routers import DefaultRouter

# --- Módulo usuarios ---
from modulo_usuarios.views.auth_view import (
    CambioPasswordView,
    LoginView,
    LogoutView,
    MeView,
    RefreshTokenView,
)
from modulo_usuarios.views.usuario_view import RolViewSet, UsuarioViewSet

# --- Módulo clientes ---
from modulo_clientes.views.cliente_view import ClienteViewSet

# --- Módulo catálogo ---
from modulo_catalogo.views.catalogo_view import (
    ArticuloViewSet,
    EntidadJuridicaViewSet,
    NormaViewSet,
    RamaDerechoViewSet,
)

# --- Módulo casos ---
from modulo_casos.views.caso_view import CasoViewSet

# --- Módulo documentos ---
from modulo_documentos.views.documento_view import (
    DocumentoCasoViewSet,
    DocumentoGeneradoViewSet,
    PlantillaDocumentoViewSet,
    TipoDocViewSet,
)

# --- Módulo IA ---
from modulo_ia.views.analisis_view import (
    AnalisisCasoView,
    ChunkCasoViewSet,
    EmbeddingArticuloViewSet,
    EstadoTareaView,
    ResultadoArticuloViewSet,
)

# --- Módulo auditoría ---
from modulo_auditoria.views.auditoria_view import AuditoriaViewSet


router = DefaultRouter()

# Usuarios & roles
router.register(r"roles",    RolViewSet,    basename="roles")
router.register(r"usuarios", UsuarioViewSet, basename="usuarios")

# Clientes
router.register(r"clientes", ClienteViewSet, basename="clientes")

# Catálogo jurídico
router.register(r"ramas",     RamaDerechoViewSet,    basename="ramas")
router.register(r"normas",    NormaViewSet,           basename="normas")
router.register(r"entidades", EntidadJuridicaViewSet, basename="entidades")
router.register(r"articulos", ArticuloViewSet,        basename="articulos")

# Casos
router.register(r"casos", CasoViewSet, basename="casos")

# Documentos
router.register(r"tipo-doc",             TipoDocViewSet,           basename="tipo-doc")
router.register(r"documentos",           DocumentoCasoViewSet,     basename="documentos")
router.register(r"plantillas",           PlantillaDocumentoViewSet,basename="plantillas")
router.register(r"documentos-generados", DocumentoGeneradoViewSet, basename="documentos-generados")

# IA
router.register(r"chunks",               ChunkCasoViewSet,        basename="chunks")
router.register(r"ranking",              ResultadoArticuloViewSet, basename="ranking")
router.register(r"embeddings-articulos", EmbeddingArticuloViewSet, basename="embeddings-articulos")

# Auditoría
router.register(r"auditoria", AuditoriaViewSet, basename="auditoria")


urlpatterns = [
    # Auth
    path("api/auth/login/",            LoginView.as_view(),          name="auth-login"),
    path("api/auth/logout/",           LogoutView.as_view(),         name="auth-logout"),
    path("api/auth/refresh/",          RefreshTokenView.as_view(),   name="auth-refresh"),
    path("api/auth/cambiar-password/", CambioPasswordView.as_view(), name="auth-cambiar-password"),
    path("api/auth/me/",               MeView.as_view(),             name="auth-me"),

    # IA directa
    path("api/ia/analizar/",               AnalisisCasoView.as_view(), name="ia-analizar"),
    path("api/ia/tarea/<str:task_id>/",    EstadoTareaView.as_view(),  name="ia-tarea-estado"),

    # Router (todos los viewsets)
    path("api/", include(router.urls)),
]
