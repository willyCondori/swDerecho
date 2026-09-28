# modulo_catalogo/management/commands/exportar_articulos_codigo_penal.py
"""
Exporta el catálogo de artículos a un JSON que el notebook de fine-tuning
usa para reemplazar el NÚMERO de artículo (lo único que trae el dataset
de TSJ) por su TEXTO real.

Uso:
    python manage.py exportar_articulos_codigo_penal
    python manage.py exportar_articulos_codigo_penal --salida otra_ruta.json
"""
import json

from django.core.management.base import BaseCommand

from modulo_catalogo.models.articulo import Articulo


class Command(BaseCommand):
    help = "Exporta numero_articulo + norma + contenido de todos los artículos activos a JSON."

    def add_arguments(self, parser):
        parser.add_argument(
            "--salida",
            default="articulos_codigo_penal.json",
            help="Ruta del JSON de salida (default: articulos_codigo_penal.json, en la carpeta actual).",
        )

    def handle(self, *args, **options):
        filas = [
            {
                "numero_articulo": art.numero_articulo,
                "norma": art.norma.nombre,
                "norma_sigla": art.norma.sigla or "",
                "contenido": art.contenido,
            }
            for art in Articulo.objects.select_related("norma").filter(estado=True)
        ]

        ruta_salida = options["salida"]
        with open(ruta_salida, "w", encoding="utf-8") as f:
            json.dump(filas, f, ensure_ascii=False, indent=1)

        self.stdout.write(self.style.SUCCESS(
            f"Exportados {len(filas)} artículos a {ruta_salida}"
        ))