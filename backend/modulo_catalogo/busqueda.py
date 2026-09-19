"""
Búsqueda de artículos.

Con el SearchFilter normal de DRF, escribir "artículo 2" o "art 2" separa el
texto en dos palabras ("artículo" y "2") y busca cada una, por separado, dentro
del número, el título y el contenido. El resultado son artículos cualquiera
que solo contienen un "2" en algún lado (Art. 12, Art. 20, Art. 102, ...) en
vez del artículo 2.

Aquí, si lo que se escribe es una referencia a un artículo (con o sin la
palabra "art", "art." o "artículo") se filtra por número exacto. Cualquier otro
texto se busca como siempre.
"""
import re

from rest_framework.filters import SearchFilter

# Acepta: "art 2", "art. 2", "art.2", "arts 2", "artículo 2", "articulo 2",
# "art. n° 2", "artículo 2°". El número va solo: si hay algo más después
# (por ejemplo "artículo 2 del código penal") se busca como texto normal.
_PATRON_REFERENCIA_ARTICULO = re.compile(
    r"^\s*art(?:[ií]culos?)?s?\.?\s*(?:n[°º]\.?\s*)?(\d{1,9})\s*[°º.]?\s*$",
    re.IGNORECASE,
)


def numero_articulo_buscado(texto):
    """
    Devuelve el número de artículo (como texto, "2") si `texto` es una
    referencia a un artículo, o None si es una búsqueda de texto normal.
    """
    coincidencia = _PATRON_REFERENCIA_ARTICULO.match(texto or "")
    if not coincidencia:
        return None
    # int() quita ceros a la izquierda: "art 02" -> "2".
    return str(int(coincidencia.group(1)))


class ArticuloSearchFilter(SearchFilter):
    """
    SearchFilter que trata "art 2" / "artículo 2" como una búsqueda por número
    de artículo exacto; el resto de búsquedas funciona igual que SearchFilter.
    """

    def filter_queryset(self, request, queryset, view):
        texto = request.query_params.get(self.search_param, "")
        numero = numero_articulo_buscado(texto)
        if numero is not None:
            return queryset.filter(numero_articulo=numero)
        return super().filter_queryset(request, queryset, view)
