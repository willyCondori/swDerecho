from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """
    Paginación global de la API.

    El frontend ya venía preparado en varios módulos (Casos, Clientes,
    Usuarios, catálogo de Artículos) para trabajar con respuestas
    paginadas (envían ?page y ?page_size, y sus hooks ya manejan tanto
    un array plano como {count, results}) — pero como no había ningún
    DEFAULT_PAGINATION_CLASS configurado, DRF nunca paginaba nada y
    esos endpoints devolvían la tabla completa en cada request.

    page_size_query_param permite que cada módulo pida el tamaño de
    página que ya tiene definido en su propio hook (12 en Casos, 10 en
    Clientes/Usuarios, 25 en el catálogo de Artículos), con un tope
    (max_page_size) para que nadie pueda pedir, por ejemplo,
    ?page_size=999999 y anular el propósito de paginar.

    Las acciones @action de solo lectura para selects (.../lista/) NO
    pasan por esta clase: llaman Response(serializer.data) directo, sin
    self.paginate_queryset(), así que siguen devolviendo la lista
    completa — es lo correcto para poblar un <select>.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
