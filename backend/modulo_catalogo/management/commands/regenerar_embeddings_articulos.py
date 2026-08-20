"""
Comando: python manage.py regenerar_embeddings_articulos

Regenera EmbeddingArticulo para todo el catálogo, garantizando que
cada vector se genere y se guarde inmediatamente atado a su propio
articulo_id (nunca por posición de lista), para evitar el desfase
que causó el bug original.

Uso:
    python manage.py regenerar_embeddings_articulos
    python manage.py regenerar_embeddings_articulos --dry-run
    python manage.py regenerar_embeddings_articulos --validar-solo
"""
import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from modulo_catalogo.models.articulo import Articulo
from modulo_ia.models.embedding import EmbeddingArticulo

DIMENSION_VECTOR = 768
UMBRAL_INTEGRIDAD = 0.9  # similitud mínima esperada vector_guardado vs re-encode


class Command(BaseCommand):
    help = "Regenera los embeddings del catálogo de artículos de forma segura (1:1 garantizado)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="No escribe nada en la base, solo muestra cuántos artículos se procesarían.",
        )
        parser.add_argument(
            "--validar-solo",
            action="store_true",
            help="No regenera nada: solo valida la integridad de los embeddings ya guardados.",
        )
        parser.add_argument(
            "--muestra",
            type=int,
            default=30,
            help="Cantidad de artículos a validar al azar (default 30).",
        )

    def handle(self, *args, **options):
        from sentence_transformers import SentenceTransformer

        self.stdout.write(f"Cargando modelo {settings.SENTENCE_TRANSFORMER_MODEL} ...")
        modelo = SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL)

        if options["validar_solo"]:
            self._validar(modelo, options["muestra"])
            return

        articulos = list(Articulo.objects.filter(estado=True).only("id", "contenido"))
        total = len(articulos)
        self.stdout.write(f"Artículos activos a procesar: {total}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry-run: no se escribe nada."))
            return

        procesados = 0
        with transaction.atomic():
            # Uno por uno: más lento que batch, pero elimina por completo
            # el riesgo de desalinear texto y vector.
            for articulo in articulos:
                vector = modelo.encode(
                    articulo.contenido, normalize_embeddings=True
                ).tolist()

                if len(vector) != DIMENSION_VECTOR:
                    raise ValueError(
                        f"Articulo {articulo.id}: el embedding tiene "
                        f"{len(vector)} dimensiones, se esperaban {DIMENSION_VECTOR}."
                    )

                EmbeddingArticulo.objects.update_or_create(
                    articulo=articulo,
                    defaults={"vector": vector},
                )
                procesados += 1
                if procesados % 50 == 0:
                    self.stdout.write(f"  ... {procesados}/{total}")

        self.stdout.write(self.style.SUCCESS(f"Listo. {procesados} embeddings regenerados."))

        self.stdout.write("Validando integridad de una muestra...")
        self._validar(modelo, options["muestra"])

    def _validar(self, modelo, muestra):
        problemas = []
        qs = EmbeddingArticulo.objects.select_related("articulo").order_by("?")[:muestra]
        revisados = 0
        for ea in qs:
            revisados += 1
            vec_guardado = np.array(ea.vector)
            vec_recalculado = modelo.encode(
                ea.articulo.contenido, normalize_embeddings=True
            )
            sim = float(np.dot(vec_guardado, vec_recalculado))
            if sim < UMBRAL_INTEGRIDAD:
                problemas.append((ea.articulo_id, round(sim, 3)))

        self.stdout.write(f"Revisados: {revisados}")
        if problemas:
            self.stdout.write(self.style.ERROR(f"Problemas encontrados: {len(problemas)}"))
            for articulo_id, sim in problemas:
                self.stdout.write(f"  articulo_id={articulo_id}  similitud={sim}")
            self.stdout.write(self.style.ERROR(
                "Hay embeddings que no corresponden a su artículo. "
                "Volvé a correr el comando sin --validar-solo."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "OK: todos los embeddings revisados corresponden a su artículo."
            ))