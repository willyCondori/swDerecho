"""
Comando: regenerar_embeddings_articulos

Regenera el embedding (EmbeddingArticulo) de artículos que YA EXISTEN en la
base de datos. No vuelve a parsear ningún PDF, no crea ni modifica Articulo,
Norma ni Jerarquia — solo recalcula el vector semántico y lo guarda 1:1 con
guaranteed pairing (un embedding por articulo_id, en el mismo loop en el que
se genera, nunca por lote separado de texto/IDs).

Casos de uso:
  - Cambiar el modelo de Sentence Transformers (SENTENCE_TRANSFORMER_MODEL)
    y recalcular todos los vectores con el modelo nuevo.
  - Reparar un desalineamiento puntual de embeddings sin re-subir el PDF.

Uso:
    python manage.py regenerar_embeddings_articulos
    python manage.py regenerar_embeddings_articulos --norma-id 3
    python manage.py regenerar_embeddings_articulos --solo-faltantes
    python manage.py regenerar_embeddings_articulos --dry-run
"""

import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modulo_catalogo.models.articulo import Articulo
from modulo_catalogo.services.carga_pdf_service import construir_texto_embedding
from modulo_ia.models.embedding import EmbeddingArticulo

logger = logging.getLogger(__name__)

DIMENSION_VECTOR = 768

_modelo_cache = None


def _obtener_modelo():
    global _modelo_cache
    if _modelo_cache is None:
        from sentence_transformers import SentenceTransformer
        _modelo_cache = SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL)
    return _modelo_cache


class Command(BaseCommand):
    help = (
        "Regenera el embedding de artículos ya existentes en la base de "
        "datos (1:1, sin re-parsear PDFs ni tocar Norma/Jerarquia)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--norma-id",
            type=int,
            default=None,
            help="Solo regenera los artículos de esta Norma (por id).",
        )
        parser.add_argument(
            "--rama-id",
            type=int,
            default=None,
            help="Solo regenera los artículos de esta Rama (por id).",
        )
        parser.add_argument(
            "--solo-faltantes",
            action="store_true",
            help=(
                "Solo genera embeddings para artículos que todavía no "
                "tienen EmbeddingArticulo (embedding__isnull=True). Por "
                "defecto se regeneran TODOS los artículos del filtro."
            ),
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=32,
            help="Cuántos artículos se codifican por lote (default 32).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="No escribe nada en la base, solo informa qué haría.",
        )

    def handle(self, *args, **options):
        norma_id = options["norma_id"]
        rama_id = options["rama_id"]
        solo_faltantes = options["solo_faltantes"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

        if batch_size < 1:
            raise CommandError("--batch-size debe ser >= 1.")

        qs = (
            Articulo.objects
            .filter(estado=True)
            .select_related("norma")
            .order_by("id")
        )
        if norma_id:
            qs = qs.filter(norma_id=norma_id)
        if rama_id:
            qs = qs.filter(rama_id=rama_id)
        if solo_faltantes:
            qs = qs.filter(embedding__isnull=True)

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING(
                "No hay artículos que coincidan con los filtros dados."
            ))
            return

        self.stdout.write(
            f"Regenerando embeddings de {total} artículo(s)"
            f"{' (dry-run, no se escribe nada)' if dry_run else ''}..."
        )

        if not dry_run:
            modelo = _obtener_modelo()

        procesados = 0
        errores = 0
        lote_articulos = []
        lote_textos = []

        def _procesar_lote():
            nonlocal procesados, errores
            if not lote_articulos:
                return

            if dry_run:
                procesados += len(lote_articulos)
                lote_articulos.clear()
                lote_textos.clear()
                return

            vectores = modelo.encode(
                lote_textos,
                normalize_embeddings=True,
            ).tolist()

            # Emparejamiento 1:1 garantizado: mismo índice de lista,
            # mismo loop — nunca se separa el orden del texto del orden
            # de los ids, que fue justamente la causa del desalineamiento
            # histórico de EmbeddingArticulo.
            with transaction.atomic():
                for articulo, vector in zip(lote_articulos, vectores):
                    if len(vector) != DIMENSION_VECTOR:
                        errores += 1
                        logger.error(
                            "Art. id=%s: embedding con %s dimensiones "
                            "(se esperaban %s). Se omite.",
                            articulo.id, len(vector), DIMENSION_VECTOR,
                        )
                        continue

                    EmbeddingArticulo.objects.update_or_create(
                        articulo=articulo,
                        defaults={"vector": vector},
                    )
                    procesados += 1

            lote_articulos.clear()
            lote_textos.clear()

        for articulo in qs.iterator():
            texto_embed = construir_texto_embedding(
                articulo.titulo or "",
                articulo.contenido,
            )
            if not texto_embed.strip():
                errores += 1
                logger.warning(
                    "Art. id=%s (%s): texto vacío para embedding, se omite.",
                    articulo.id, articulo.numero_articulo,
                )
                continue

            lote_articulos.append(articulo)
            lote_textos.append(texto_embed)

            if len(lote_articulos) >= batch_size:
                _procesar_lote()
                self.stdout.write(f"  ...{procesados}/{total} procesados")

        _procesar_lote()

        self.stdout.write(self.style.SUCCESS(
            f"Listo. Procesados: {procesados}/{total}. Errores: {errores}."
        ))
