# modulo_catalogo/services/articulo_entidad_service.py
"""
Detecta qué entidades jurídicas del catálogo aparecen en el contenido
de un Articulo, y sincroniza la tabla intermedia articulo_entidades
(modelo ArticuloEntidad) para que quede reflejado.

Se usa en dos momentos:
  1. Automáticamente al cargar un PDF nuevo (carga_pdf_service.py),
     para cada artículo nuevo.
  2. Desde el management command `backfill_entidades_articulos`, para
     los artículos que ya estaban cargados antes de que existiera este
     paso (o para volver a correrlo si el catálogo de entidades cambió).

Es idempotente: se puede correr muchas veces sobre el mismo artículo
sin duplicar vínculos ni dejar basura de una corrida anterior si el
contenido del artículo cambió.
"""
from modulo_catalogo.models.articulo import ArticuloEntidad
from modulo_catalogo.models.entidad import EntidadJuridica
from modulo_catalogo.services.entidad_matching import detectar_entidades_en_texto


class ArticuloEntidadService:

    @staticmethod
    def obtener_catalogo() -> list[dict]:
        """
        Catálogo de entidades activas, para pasar una sola vez a
        `vincular()` cuando se procesan muchos artículos seguidos (una
        carga de PDF completa, o el backfill) y no repetir la consulta
        por cada artículo.
        """
        return list(EntidadJuridica.objects.filter(estado=True).values("id", "nombre"))

    @classmethod
    def vincular(cls, articulo, catalogo: list[dict] | None = None) -> list[str]:
        """
        Detecta las entidades del catálogo mencionadas en
        `articulo.contenido` y sincroniza ArticuloEntidad para que
        coincida exactamente con lo detectado ahora (borra vínculos
        que ya no correspondan, agrega los nuevos).

        Args:
            articulo: instancia de Articulo ya guardada (con pk).
            catalogo: resultado de obtener_catalogo(), opcional. Si no
                se pasa, se consulta acá (cómodo para uso puntual, pero
                ineficiente si se llama en un loop grande — en ese caso
                pasar el catálogo ya armado).

        Returns:
            Lista de nombres de entidades vinculadas (para logging /
            reportes de progreso).
        """
        if catalogo is None:
            catalogo = cls.obtener_catalogo()

        detectadas = detectar_entidades_en_texto(articulo.contenido, catalogo)
        ids_detectados = {e["id"] for e in detectadas}

        vinculos_actuales = set(
            ArticuloEntidad.objects.filter(articulo=articulo).values_list("entidad_id", flat=True)
        )

        ids_a_quitar = vinculos_actuales - ids_detectados
        if ids_a_quitar:
            ArticuloEntidad.objects.filter(
                articulo=articulo, entidad_id__in=ids_a_quitar
            ).delete()

        ids_a_agregar = ids_detectados - vinculos_actuales
        if ids_a_agregar:
            ArticuloEntidad.objects.bulk_create(
                [
                    ArticuloEntidad(articulo=articulo, entidad_id=entidad_id)
                    for entidad_id in ids_a_agregar
                ],
                ignore_conflicts=True,
            )

        return [e["nombre"] for e in detectadas]
