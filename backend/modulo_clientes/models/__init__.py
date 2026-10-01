from .cliente import Cliente
from .cliente_busqueda_token import ClienteBusquedaToken

__all__ = ["Cliente", "ClienteBusquedaToken"]

# Conecta el reindexado automático del índice de búsqueda (ver signals.py).
from modulo_clientes import signals  # noqa: E402,F401
