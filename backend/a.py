from modulo_catalogo.models.articulo import Articulo, ArticuloEntidad
from modulo_catalogo.models.entidad import EntidadJuridica

entidades = list(EntidadJuridica.objects.filter(estado=True).values("id", "nombre"))
articulos = Articulo.objects.filter(estado=True).only("id", "contenido")

nuevos_links = []
total_articulos = articulos.count()

for i, articulo in enumerate(articulos.iterator(), start=1):
    texto = articulo.contenido.lower()
    for entidad in entidades:
        nombre = entidad["nombre"].strip().lower()
        if nombre and nombre in texto:
            nuevos_links.append(
                ArticuloEntidad(articulo_id=articulo.id, entidad_id=entidad["id"])
            )
    if i % 200 == 0:
        print(f"Procesados {i}/{total_articulos}")

ArticuloEntidad.objects.bulk_create(nuevos_links, ignore_conflicts=True, batch_size=1000)
print(f"Listo. {len(nuevos_links)} relaciones creadas.")