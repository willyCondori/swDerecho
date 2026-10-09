import json
import time
from collections import Counter

import requests
from django.core.management.base import BaseCommand, CommandError

from modulo_ia.services.jurisprudencia_importacion import importar_resolucion
from modulo_ia.services.tsj_api import TSJApi


class Command(BaseCommand):
    help = "Consulta Genesis/TSJ, guarda resoluciones penales y genera sus embeddings."

    def add_arguments(self, parser):
        parser.add_argument("--paginas", type=int, default=1)
        parser.add_argument("--desde-pagina", type=int, default=1)
        parser.add_argument("--limite", type=int)
        parser.add_argument("--palabras", default="penal")
        parser.add_argument("--pausa", type=float, default=1.5)

    def handle(self, *args, **options):
        if options["paginas"] < 1 or options["desde_pagina"] < 1 or options["pausa"] < 0:
            raise CommandError("Páginas positivas y pausa no negativa requeridas.")
        if options["limite"] is not None and options["limite"] < 1:
            raise CommandError("El límite debe ser positivo.")
        if not options["palabras"].strip():
            raise CommandError("Indica palabras para la búsqueda del corpus.")
        try:
            api = TSJApi()
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        resumen = Counter()
        procesadas = 0
        try:
            for pagina in range(options["desde_pagina"], options["desde_pagina"] + options["paginas"]):
                time.sleep(options["pausa"])
                datos = api.buscar(pagina, options["palabras"])
                for fila in datos["data"]:
                    time.sleep(options["pausa"])
                    try:
                        resumen[importar_resolucion(api.detalle(fila["id"]))] += 1
                    except (ValueError, requests.RequestException, KeyError) as exc:
                        resumen["rechazada"] += 1
                        # No mostrar cabeceras ni credenciales de la API.
                        self.stderr.write(f"Resolución {fila.get('id', '?')}: {type(exc).__name__}")
                    procesadas += 1
                    if options["limite"] and procesadas >= options["limite"]:
                        break
                if (options["limite"] and procesadas >= options["limite"]) or pagina >= int(datos["meta"]["totalPages"]):
                    break
        except (requests.RequestException, ValueError, KeyError) as exc:
            raise CommandError(f"No se pudo consultar Genesis: {type(exc).__name__}. Lo ya importado se conserva.") from exc
        finally:
            api.close()
        self.stdout.write(json.dumps(dict(resumen), ensure_ascii=False))
        if resumen["rechazada"]:
            raise CommandError("Sincronización parcial: revisa las resoluciones rechazadas y vuelve a ejecutar.")
