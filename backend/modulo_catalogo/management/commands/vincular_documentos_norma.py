# modulo_catalogo/management/commands/vincular_documentos_norma.py
"""
DocumentoNorma solo se crea desde CargaArticulosView (ver
carga_articulos_view.py) al subir un PDF por el formulario de "Cargar
artículos". Los PDF que ya estaban en MEDIA_ROOT/documentos_normativas/
de antes de que existiera ese modelo (por ejemplo, cargados a mano o por
una versión anterior del sistema) quedan en disco pero sin fila en la
base de datos, así que el panel "Documentos" de la norma los muestra
vacíos aunque el archivo exista.

Este comando recorre MEDIA_ROOT/documentos_normativas/ buscando PDF sin
registrar y, cuando el nombre de la carpeta coincide con la sigla o el
nombre de una Norma existente, crea el DocumentoNorma correspondiente.
Cuando no hay una coincidencia clara (como una carpeta "penal" que no es
ni la sigla ni el nombre de ninguna norma), lo deja pendiente y hay que
vincularlo a mano con --vincular.

Uso:
    python manage.py vincular_documentos_norma
        Modo simulación (por defecto): solo muestra qué haría.

    python manage.py vincular_documentos_norma --aplicar
        Crea los DocumentoNorma para los archivos con coincidencia clara.

    python manage.py vincular_documentos_norma --vincular \\
        documentos_normativas/penal/penal_codigo_penal.pdf --norma-id 1
        Vincula un archivo puntual a una norma, sin depender del nombre
        de la carpeta. La ruta puede ser relativa a MEDIA_ROOT o
        absoluta.
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from modulo_catalogo.models.documento_norma import DocumentoNorma
from modulo_catalogo.models.norma import Norma

CARPETA_BASE = "documentos_normativas"


def _normalizar(texto: str) -> str:
    return texto.strip().lower().replace(" ", "_")


class Command(BaseCommand):
    help = (
        "Registra en DocumentoNorma los PDF que ya estaban en "
        f"MEDIA_ROOT/{CARPETA_BASE}/ antes de que existiera ese modelo."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--aplicar",
            action="store_true",
            help="Escribe los DocumentoNorma detectados automáticamente. Sin este flag, solo simula.",
        )
        parser.add_argument(
            "--vincular",
            metavar="RUTA",
            default=None,
            help="Ruta de un único archivo a vincular a mano (relativa a MEDIA_ROOT o absoluta). "
                 "Requiere --norma-id.",
        )
        parser.add_argument(
            "--norma-id",
            type=int,
            default=None,
            help="ID de la Norma a la que vincular el archivo de --vincular.",
        )

    def handle(self, *args, **options):
        if options["vincular"]:
            self._vincular_uno(options["vincular"], options["norma_id"])
            return
        self._escanear(aplicar=options["aplicar"])

    def _vincular_uno(self, ruta, norma_id):
        if not norma_id:
            raise CommandError("--vincular requiere también --norma-id.")
        try:
            norma = Norma.objects.get(pk=norma_id)
        except Norma.DoesNotExist:
            raise CommandError(f"No existe ninguna Norma con id={norma_id}.")

        ruta_absoluta = ruta if os.path.isabs(ruta) else os.path.join(settings.MEDIA_ROOT, ruta)
        if not os.path.isfile(ruta_absoluta):
            raise CommandError(f"No se encontró el archivo: {ruta_absoluta}")

        ruta_relativa = os.path.relpath(ruta_absoluta, settings.MEDIA_ROOT)
        documento, creado = DocumentoNorma.objects.get_or_create(
            ruta_archivo=ruta_relativa,
            defaults={
                "norma": norma,
                "nombre_original": os.path.basename(ruta_absoluta),
                "tamano": os.path.getsize(ruta_absoluta),
            },
        )
        if creado:
            self.stdout.write(self.style.SUCCESS(
                f'Vinculado: "{documento.nombre_original}" → {norma.nombre} (id={documento.pk})'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'Ya existía un DocumentoNorma para "{ruta_relativa}" (id={documento.pk}); no se tocó.'
            ))

    def _escanear(self, aplicar):
        carpeta_raiz = os.path.join(settings.MEDIA_ROOT, CARPETA_BASE)
        if not os.path.isdir(carpeta_raiz):
            self.stdout.write(self.style.WARNING(f"No existe la carpeta {carpeta_raiz}."))
            return

        ya_registrados = set(DocumentoNorma.objects.values_list("ruta_archivo", flat=True))
        normas = list(Norma.objects.all())
        por_clave = {}
        for norma in normas:
            if norma.sigla:
                por_clave.setdefault(_normalizar(norma.sigla), []).append(norma)
            por_clave.setdefault(_normalizar(norma.nombre), []).append(norma)

        creados, pendientes = 0, []

        for directorio, _subcarpetas, archivos in os.walk(carpeta_raiz):
            for nombre_archivo in archivos:
                if not nombre_archivo.lower().endswith(".pdf"):
                    continue
                ruta_absoluta = os.path.join(directorio, nombre_archivo)
                ruta_relativa = os.path.relpath(ruta_absoluta, settings.MEDIA_ROOT)
                if ruta_relativa in ya_registrados:
                    continue

                carpeta = os.path.basename(directorio)
                candidatas = por_clave.get(_normalizar(carpeta), [])

                if len(candidatas) == 1:
                    norma = candidatas[0]
                    if aplicar:
                        documento = DocumentoNorma.objects.create(
                            norma=norma,
                            nombre_original=nombre_archivo,
                            ruta_archivo=ruta_relativa,
                            tamano=os.path.getsize(ruta_absoluta),
                        )
                        self.stdout.write(self.style.SUCCESS(
                            f'Creado: "{nombre_archivo}" → {norma.nombre} (id={documento.pk})'
                        ))
                    else:
                        self.stdout.write(f'[simulación] "{ruta_relativa}" → {norma.nombre}')
                    creados += 1
                else:
                    motivo = "sin ninguna norma con ese nombre/sigla" if not candidatas \
                        else f"coincide con {len(candidatas)} normas distintas"
                    pendientes.append((ruta_relativa, motivo))

        if pendientes:
            self.stdout.write(self.style.WARNING(
                f"\n{len(pendientes)} archivo(s) sin vincular automáticamente:"
            ))
            for ruta_relativa, motivo in pendientes:
                self.stdout.write(f"  - {ruta_relativa}  ({motivo})")
            self.stdout.write(
                "\nVinculalos a mano con:\n"
                "  python manage.py vincular_documentos_norma --vincular <ruta> --norma-id <id>\n"
                "(python manage.py shell -c \"from modulo_catalogo.models.norma import Norma; "
                "print(list(Norma.objects.values('id','nombre','sigla')))\" para ver los IDs)"
            )

        if not aplicar and creados:
            self.stdout.write(self.style.WARNING(
                f"\n{creados} archivo(s) listos para vincular automáticamente. "
                "Corré de nuevo con --aplicar para escribirlos."
            ))
        elif not creados and not pendientes:
            self.stdout.write(self.style.SUCCESS("No hay archivos pendientes de vincular."))
