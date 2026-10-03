"""
Búsqueda de clientes por nombre sobre datos cifrados.

Ver ClienteBusquedaToken: en vez de descifrar todos los clientes para
comparar texto, se indexan los prefijos (2+ letras) de cada palabra del
nombre completo como HMAC determinístico, y se busca por igualdad.

Cómo se busca (cambio respecto de la búsqueda anterior por "contiene"):
  - Cada palabra escrita debe ser el COMIENZO de alguna palabra del nombre
    o apellido: "mam" y "ana ro" encuentran a "Ana Rojas Mamani"; "ana" ya
    no encuentra a "Susana" (antes sí, por ser un "contiene").
  - Ignora mayúsculas y tildes: "munoz" encuentra a "Muñoz".
  - Las palabras pueden estar repartidas entre nombres y apellidos
    ("juan perez"); antes solo coincidía dentro de uno de los dos campos.
"""
import re
import unicodedata

from django.db import transaction

from core.encryption.aes_encryption import hash_lookup, safe_decrypt

MIN_PREFIJO = 2    # mismo mínimo que MIN_CARACTERES_BUSQUEDA de la vista
MAX_PREFIJO = 40   # tope de largo de prefijo indexado (acota filas por cliente)
_DOMINIO = "cliente-busqueda:"  # separa estos hashes de los de teléfono/nombre completo
_PALABRA = re.compile(r"[a-z0-9]+")


def palabras(texto):
    """Palabras en minúsculas y sin tildes: "Muñoz-Pérez" -> ["munoz", "perez"]."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto or "")
        if not unicodedata.combining(c)
    )
    return _PALABRA.findall(sin_tildes.lower())


def _hash_prefijo(prefijo):
    return hash_lookup(_DOMINIO + prefijo)


def hashes_de_indexado(nombres, apellidos):
    """Conjunto de HMAC de todos los prefijos de las palabras del nombre completo."""
    hashes = set()
    for palabra in palabras(f"{nombres or ''} {apellidos or ''}"):
        palabra = palabra[:MAX_PREFIJO]
        for largo in range(MIN_PREFIJO, len(palabra) + 1):
            hashes.add(_hash_prefijo(palabra[:largo]))
    return hashes


def reindexar_cliente(cliente):
    """
    Deja el índice del cliente igual al de su nombre actual, tocando solo
    lo que cambió. Un dato que no se pueda descifrar no genera tokens (y
    no lanza), para que guardar un cliente nunca falle por el índice.
    """
    from modulo_clientes.models.cliente_busqueda_token import ClienteBusquedaToken

    nombres = safe_decrypt(cliente.nombres, fallback="")
    apellidos = safe_decrypt(cliente.apellidos, fallback="")
    deseados = hashes_de_indexado(nombres, apellidos)

    with transaction.atomic():
        existentes = set(
            ClienteBusquedaToken.objects
            .filter(cliente_id=cliente.pk)
            .values_list("token_hash", flat=True)
        )
        sobran = existentes - deseados
        faltan = deseados - existentes
        if sobran:
            ClienteBusquedaToken.objects.filter(
                cliente_id=cliente.pk, token_hash__in=sobran
            ).delete()
        if faltan:
            ClienteBusquedaToken.objects.bulk_create(
                [ClienteBusquedaToken(cliente_id=cliente.pk, token_hash=h) for h in faltan],
                ignore_conflicts=True,
            )


def filtrar_por_busqueda(queryset, texto):
    """
    Restringe un queryset de Cliente a los que coinciden con `texto` (todas
    las palabras de 2+ letras deben ser comienzo de alguna palabra del
    nombre). Sin ninguna palabra válida no devuelve nada.

    Un .filter() por palabra: cada uno agrega su propio JOIN a la tabla de
    tokens, así que las palabras se combinan con AND. Cada JOIN aporta como
    mucho una fila por cliente (token único por cliente), sin duplicados.
    """
    buscadas = list(dict.fromkeys(
        p[:MAX_PREFIJO] for p in palabras(texto) if len(p) >= MIN_PREFIJO
    ))
    if not buscadas:
        return queryset.none()
    for palabra in buscadas:
        queryset = queryset.filter(busqueda_tokens__token_hash=_hash_prefijo(palabra))
    return queryset
