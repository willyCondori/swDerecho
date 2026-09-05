# modulo_catalogo/services/entidad_matching.py
"""
Matching de entidades jurídicas del catálogo contra un texto libre.

Función pura, sin acceso a base de datos: recibe el texto y la lista de
entidades ya cargada (para no repetir la consulta por cada texto), y
devuelve qué entidades del catálogo aparecen mencionadas.

La usan:
  - modulo_ia.services.entidad_service.EntidadDetectionService
    (detecta entidades en los chunks de un CASO)
  - modulo_catalogo.services.articulo_entidad_service.ArticuloEntidadService
    (detecta entidades en el CONTENIDO de un ARTÍCULO)

Antes esta misma lógica de matching (substring, case-insensitive)
estaba duplicada en EntidadDetectionService y en ningún lado más,
porque nadie la aplicaba todavía a artículos. Se extrae acá para que
ambos flujos usen exactamente el mismo criterio de detección y no se
puedan desincronizar con el tiempo.
"""


def detectar_entidades_en_texto(texto: str, catalogo: list[dict]) -> list[dict]:
    """
    Args:
        texto: texto libre a analizar (chunk de caso, o contenido de
            un artículo).
        catalogo: lista de dicts con al menos {"id": ..., "nombre": ...},
            típicamente EntidadJuridica.objects.filter(estado=True)
            .values("id", "nombre"). Se recibe ya armada para no volver
            a consultarla por cada texto cuando se procesan muchos
            textos seguidos (muchos chunks de un caso, o muchos
            artículos de un PDF).

    Returns:
        Subconjunto de `catalogo` cuyo nombre aparece como substring
        (case-insensitive) en el texto. Devuelve los dicts completos
        (no solo el nombre) para que el llamador tenga el id a mano
        sin tener que volver a buscarlo.
    """
    if not texto:
        return []

    texto_normalizado = texto.lower()

    return [
        entidad
        for entidad in catalogo
        if entidad["nombre"].strip().lower() in texto_normalizado
    ]
