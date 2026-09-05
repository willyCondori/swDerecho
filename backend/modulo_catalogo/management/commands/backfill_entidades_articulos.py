# modulo_catalogo/management/commands/backfill_entidades_articulos.py
"""
Llena retroactivamente articulo_entidades para los artículos que ya
estaban cargados antes de que existiera el hook automático en
carga_pdf_service.py (o para volver a correrlo si el catálogo de
entidades cambió).

Uso:
    python manage.py backfill_entidades_articulos
    python manage.py backfill_entidades_articulos --dry-run
    python manage.py backfill_entidades_articulos --rama Penal
    python manage.py backfill_entidades_articulos --solo-sin-entidades
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from modulo_catalogo.models.articulo import Articulo
from modulo_catalogo.services.articulo_entidad_service import ArticuloEntidadService


class Command(BaseCommand):
    help = "Detecta y vincula entidades jurídicas del catálogo en el contenido de los artículos existentes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra qué se detectaría sin escribir nada en la base de datos.",
        )
        parser.add_argument(
            "--rama",
            type=str,
            default=None,
            help="Nombre exacto de la rama a procesar (ej. 'Penal'). Si se omite, procesa todas.",
        )
        parser.add_argument(
            "--solo-sin-entidades",
            action="store_true",
            help="Procesa solo artículos que todavía no tienen ninguna entidad vinculada "
                 "(más rápido para correr de nuevo sin repetir trabajo ya hecho).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        rama_nombre = options["rama"]
        solo_sin_entidades = options["solo_sin_entidades"]

        articulos = Articulo.objects.filter(estado=True)
        if rama_nombre:
            articulos = articulos.filter(rama__nombre=rama_nombre)
        if solo_sin_entidades:
            articulos = articulos.filter(entidades__isnull=True)

        total = articulos.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No hay artículos que procesar con esos filtros."))
            return

        self.stdout.write(f"Procesando {total} artículo(s)"
                           f"{' (dry-run, no se guarda nada)' if dry_run else ''}...")

        catalogo = ArticuloEntidadService.obtener_catalogo()
        self.stdout.write(f"Catálogo activo: {len(catalogo)} entidades.\n")

        procesados = 0
        con_entidades = 0
        total_vinculos = 0

        for articulo in articulos.iterator(chunk_size=200):
            if dry_run:
                from modulo_catalogo.services.entidad_matching import detectar_entidades_en_texto
                detectadas = [e["nombre"] for e in detectar_entidades_en_texto(articulo.contenido, catalogo)]
            else:
                with transaction.atomic():
                    detectadas = ArticuloEntidadService.vincular(articulo, catalogo=catalogo)

            procesados += 1
            if detectadas:
                con_entidades += 1
                total_vinculos += len(detectadas)

            if procesados % 200 == 0:
                self.stdout.write(f"  ... {procesados}/{total}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Listo. Procesados: {procesados}. "
            f"Con al menos una entidad: {con_entidades}. "
            f"Vínculos totales detectados: {total_vinculos}."
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "Esto fue un dry-run: no se escribió nada en articulo_entidades. "
                "Corré sin --dry-run para aplicar los cambios."
            ))
