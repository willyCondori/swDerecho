import json
from pathlib import Path
from django.core.management.base import BaseCommand
from modulo_ia.models.valoracion import ValoracionArticulo


class Command(BaseCommand):
    help = "Exporta valoraciones explícitas actuales por abogado y contexto a JSONL."

    def add_arguments(self, parser):
        parser.add_argument("--salida", required=True)

    def handle(self, *args, **options):
        vistas = set()
        cantidad = 0
        with Path(options["salida"]).open("w", encoding="utf-8") as archivo:
            for v in ValoracionArticulo.objects.order_by("-id").iterator():
                clave = (v.caso_id, v.articulo_id, v.usuario_id, v.contexto_hash)
                if clave in vistas:
                    continue
                vistas.add(clave)
                if v.valor == "sin_valorar":
                    continue
                archivo.write(json.dumps({
                    "valoracion_id": v.id, "caso_id": v.caso_id,
                    "articulo_id": v.articulo_id, "evaluador_id": v.usuario_id,
                    "contexto_hash": v.contexto_hash, "valor": v.valor,
                    "modelo_version": v.modelo_version, "fecha": v.created_at.isoformat(),
                    **v.muestra,
                }, ensure_ascii=False) + "\n")
                cantidad += 1
        self.stdout.write(self.style.SUCCESS(f"Exportadas {cantidad} valoraciones explícitas."))
