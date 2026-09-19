"""
Orden natural de los artículos por número.

`Articulo.numero_articulo` es un CharField, así que ordenarlo tal cual da
orden alfabético ("1", "10", "100", "2", ...). Aquí se saca la parte numérica
del comienzo del número para ordenar 1, 2, ..., 9, 10, 100; lo que venga
después del número ("10 bis", "10-A") desempata en orden alfabético, y los
números que no empiezan con un dígito quedan al final.
"""
from django.db.models import BigIntegerField, CharField, F, Func, Value
from django.db.models.functions import Cast
from rest_framework.filters import OrderingFilter

# Hasta 9 dígitos: de sobra para un número de artículo y cabe en un entero.
_PATRON_NUMERO_INICIAL = r"^\d{1,9}"


def anotar_numero_orden(queryset):
    """Agrega `numero_orden`: el número al inicio de numero_articulo (NULL si no hay)."""
    parte_numerica = Func(
        F("numero_articulo"),
        Value(_PATRON_NUMERO_INICIAL),
        function="SUBSTRING",
        output_field=CharField(),
    )
    return queryset.annotate(numero_orden=Cast(parte_numerica, BigIntegerField()))


def orden_natural_articulo(descendente=False):
    """Expresiones de order_by para el número de artículo en orden natural."""
    expresiones = [F("numero_orden"), F("numero_articulo")]
    if descendente:
        return [e.desc(nulls_last=True) for e in expresiones]
    return [e.asc(nulls_last=True) for e in expresiones]


class ArticuloOrderingFilter(OrderingFilter):
    """
    OrderingFilter que ordena `numero_articulo` en orden natural (1, 2, 10) y
    desempata siempre por número de artículo para que la paginación sea estable.
    Requiere que el queryset tenga la anotación `numero_orden`.
    """

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if not ordering:
            return queryset

        terminos = []
        for campo in ordering:
            if campo.lstrip("-") == "numero_articulo":
                terminos += orden_natural_articulo(descendente=campo.startswith("-"))
            else:
                terminos.append(campo)

        terminos += orden_natural_articulo() + ["id"]
        return queryset.order_by(*terminos)
