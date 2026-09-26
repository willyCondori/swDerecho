"""
Comando: regenerar_embeddings_articulos

Regenera el embedding (EmbeddingArticulo) de artículos que YA EXISTEN en la
base de datos. No vuelve a parsear ningún PDF, no crea ni modifica Articulo,
Norma ni Jerarquia — solo recalcula el vector semántico y lo guarda con
guaranteed pairing (un embedding por articulo_id + modelo_version, en el
mismo loop en el que se genera, nunca por lote separado de texto/IDs).

Casos de uso:
  - Generar los embeddings de un modelo NUEVO (por ejemplo, el afinado con
    el dataset de TSJ) con --version, sin tocar los de la versión activa:
    el catálogo queda sirviendo el ranking con el modelo de siempre hasta
    que decidas cambiar settings.EMBEDDING_MODEL_VERSION.
  - Reparar un desalineamiento puntual de embeddings sin re-subir el PDF.

Uso:
    python manage.py regenerar_embeddings_articulos
    python manage.py regenerar_embeddings_articulos --norma-id 3
    python manage.py regenerar_embeddings_articulos --solo-faltantes
    python manage.py regenerar_embeddings_articulos --dry-run
    python manage.py regenerar_embeddings_articulos --modelo-version sw-derecho-embeddings-v1
"""

import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modulo_catalogo.models.articulo import Articulo
from modulo_catalogo.services.carga_pdf_service import construir_texto_embedding
from modulo_ia.models.embedding import EmbeddingArticulo
from modulo_ia.services.model_loader import DIMENSION_VECTOR, obtener_modelo as _obtener_modelo, version_activa

logger = logging.getLogger(__name__)


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
                "Solo genera embeddings para artículos que todavía no tienen "
                "EmbeddingArticulo de la versión pedida (--version, o la activa "
                "por defecto). Por defecto se regeneran TODOS los artículos del filtro."
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
        parser.add_argument(
            "--modelo-version",
            default=None,
            help="Etiqueta de modelo_version a generar (default: settings.EMBEDDING_MODEL_VERSION, "
                 "la versión activa). Usar una etiqueta distinta a la activa — por ejemplo, la del "
                 "modelo recién afinado — genera esos embeddings SIN tocar los de la versión activa, "
                 "que sigue sirviendo el ranking hasta que se decida cambiar EMBEDDING_MODEL_VERSION.",
        )

    def handle(self, *args, **options):
        norma_id = options["norma_id"]
        rama_id = options["rama_id"]
        solo_faltantes = options["solo_faltantes"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

        if batch_size < 1:
            raise CommandError("--batch-size debe ser >= 1.")

        version = options["modelo_version"] or version_activa()

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
            qs = qs.exclude(embeddings__modelo_version=version)

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING(
                "No hay artículos que coincidan con los filtros dados."
            ))
            return

        self.stdout.write(
            f'Regenerando embeddings de {total} artículo(s), versión "{version}"'
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
                        modelo_version=version,
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
