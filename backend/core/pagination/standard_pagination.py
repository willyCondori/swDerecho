# core/pagination/standard_pagination.py
from rest_framework.pagination import PageNumberPagination


class StandardResultsPagination(PageNumberPagination):
    """
    Paginación por defecto de toda la API.

    El frontend siempre manda `page` y `page_size` en las listas
    paginadas (ver catalogoApi.articulos, usuariosApi.listarUsuarios,
    clientesApi.listar, casosApi.listar, auditoriaApi...) y sabe
    interpretar tanto una respuesta paginada ({count, next, previous,
    results}) como un array plano (fallback), pero sin esta clase
    configurada como DEFAULT_PAGINATION_CLASS, DRF nunca paginaba:
    `self.paginate_queryset(qs)` devolvía None en todas las vistas y
    siempre se servía el queryset completo, sin importar `page`/
    `page_size` — por eso el catálogo de artículos (y en realidad
    cualquier listado del sistema) mostraba todo en una sola página.
    """
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200
