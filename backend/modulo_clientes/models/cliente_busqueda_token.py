from django.db import models

from .cliente import Cliente


class ClienteBusquedaToken(models.Model):
    """
    Índice de búsqueda por nombre de un cliente, sin guardar el nombre en claro.

    Los nombres y apellidos están cifrados con AES-GCM (nonce aleatorio), así
    que la base de datos no puede filtrar por ellos y buscar obligaba a
    descifrar TODOS los clientes en cada request. Aquí se guarda, por cada
    palabra del nombre completo, el HMAC-SHA256 determinístico (ver
    core.encryption.aes_encryption.hash_lookup) de cada uno de sus prefijos
    de 2 o más letras. Buscar "mam" es entonces un filter() indexado por el
    HMAC de "mam", que encuentra a "Mamani" sin descifrar nada.

    Se mantiene sola: ver modulo_clientes.signals (se reindexa en cada
    guardado del cliente) y el comando `reindexar_busqueda_clientes`.
    """
    cliente    = models.ForeignKey(
                     Cliente,
                     on_delete=models.CASCADE,
                     related_name="busqueda_tokens",
                 )
    token_hash = models.CharField(max_length=64)

    class Meta:
        db_table    = "clientes_busqueda_tokens"
        constraints = [
            # Su índice (token_hash, cliente_id) es el que sirve a la
            # búsqueda; el de cliente_id lo crea la FK para el borrado.
            models.UniqueConstraint(
                fields=["token_hash", "cliente"], name="uq_cliente_busqueda_token",
            ),
        ]

    def __str__(self):
        return f"Token de cliente #{self.cliente_id}"
