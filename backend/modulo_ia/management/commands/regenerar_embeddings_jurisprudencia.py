"""Genera el índice del modelo activo sin descargar ni modificar resoluciones."""
from time import monotonic

from django.core.management.base import BaseCommand, CommandError

from modulo_ia.models.jurisprudencia import FragmentoJurisprudencia, EmbeddingJurisprudencia
from modulo_ia.services.model_loader import version_activa
from modulo_ia.services.vectorizacion_service import vectorizar_textos


class Command(BaseCommand):
    help = "Genera los embeddings faltantes de jurisprudencia para el modelo activo; permite reanudar."

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=16)

    def handle(self, *args, **options):
        size = options["batch_size"]
        if size < 1:
            raise CommandError("--batch-size debe ser positivo.")
        version = version_activa()
        pendientes = FragmentoJurisprudencia.objects.filter(resolucion__activa=True).exclude(
            embeddings__modelo_version=version,
        ).order_by("pk")
        total = pendientes.count()
        self.stdout.write(f"Modelo {version}: {total} fragmentos pendientes.")
        inicio = monotonic()
        procesados = 0
        ultimo = 0
        while True:
            lote = list(pendientes.filter(pk__gt=ultimo)[:size])
            if not lote:
                break
            vectores = vectorizar_textos([f.contenido for f in lote])
            EmbeddingJurisprudencia.objects.bulk_create([
                EmbeddingJurisprudencia(fragmento=f, modelo_version=version, vector=v)
                for f, v in zip(lote, vectores)
            ], update_conflicts=True, unique_fields=["fragmento", "modelo_version"], update_fields=["vector"])
            ultimo = lote[-1].pk
            procesados += len(lote)
            if procesados % (size * 10) == 0 or procesados == total:
                self.stdout.write(f"{procesados}/{total}; {monotonic() - inicio:.0f} s")
                self.stdout.flush()
        self.stdout.write(self.style.SUCCESS(f"Completado: {procesados} embeddings de {version}."))
