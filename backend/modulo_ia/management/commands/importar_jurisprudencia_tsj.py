import json
import logging
import time
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from modulo_ia.services.jurisprudencia_importacion import importar_resolucion


class Command(BaseCommand):
    help = "Importa JSON de tsj_scraper/data/raw y genera embeddings con el modelo activo. No descarga ni envía casos."

    def add_arguments(self, parser):
        parser.add_argument("--directorio", required=True)
        parser.add_argument("--limite", type=int)
        parser.add_argument("--progreso-cada", type=int, default=25)

    def handle(self, *args, **options):
        logging.getLogger("sentence_transformers.SentenceTransformer").setLevel(logging.WARNING)
        directorio = Path(options["directorio"])
        if not directorio.is_dir():
            raise CommandError("El directorio de resoluciones no existe.")
        limite = options["limite"]
        if limite is not None and limite < 1:
            raise CommandError("El límite debe ser positivo.")
        archivos = sorted(directorio.glob("*.json"))
        if not archivos:
            raise CommandError("No hay archivos JSON en el directorio indicado.")
        archivos = archivos[:limite] if limite else archivos
        resumen = Counter()
        inicio = time.monotonic()
        self.stdout.write(f"Importando {len(archivos)} resoluciones desde {directorio}")
        self.stdout.flush()
        for indice, archivo in enumerate(archivos, 1):
            try:
                datos = json.loads(archivo.read_text(encoding="utf-8-sig"))
                resumen[importar_resolucion(datos)] += 1
            except (ValueError, OSError) as exc:
                resumen["rechazada"] += 1
                self.stderr.write(f"{archivo.name}: {exc}")
            if indice % max(1, options["progreso_cada"]) == 0 or indice == len(archivos):
                self.stdout.write(json.dumps({
                    "procesadas": indice, "total": len(archivos),
                    "segundos": round(time.monotonic() - inicio), **resumen,
                }, ensure_ascii=False))
                self.stdout.flush()
        self.stdout.write(json.dumps(dict(resumen), ensure_ascii=False))
        if resumen["rechazada"]:
            raise CommandError("Hay resoluciones rechazadas; las válidas quedaron importadas. Corrige las indicadas y vuelve a ejecutar.")
