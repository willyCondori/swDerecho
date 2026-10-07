from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction
from modulo_catalogo.models import DocumentoNorma
from django.utils import timezone
from modulo_catalogo.services.vigencia_service import clave, actualizar_avisos
from modulo_catalogo.services.carga_pdf_service import extraer_texto_pdf_bytes
from modulo_catalogo.services.lectura_normativa_service import detectar_derogaciones_expresas
from modulo_catalogo.services.disposiciones_service import separar_unidades, guardar_disposiciones, recuperar_unidades_seleccionadas
from modulo_catalogo.services.vigencia_service import registrar_cambios


class Command(BaseCommand):
    help = 'Recupera disposiciones y avisos expresos de PDFs vigentes; no confirma efectos jurídicos.'

    def handle(self, *args, **options):
        for documento in DocumentoNorma.objects.filter(vigente=True).select_related('norma'):
            try:
                with default_storage.open(documento.ruta_archivo, 'rb') as pdf:
                    texto = extraer_texto_pdf_bytes(pdf.read())
                _, disposiciones = separar_unidades(recuperar_unidades_seleccionadas(documento, texto))
                cambios = detectar_derogaciones_expresas(disposiciones)
                with transaction.atomic():
                    guardar_disposiciones(documento, disposiciones)
                    anteriores = documento.analisis_normativo.get('cambios_aplicados', [])
                    registrar_cambios(documento, disposiciones, anteriores + [c for c in cambios if c not in anteriores], documento.metadatos)
                    # Corregir detecciones pendientes obsoletas de cláusulas expresas;
                    # jamás modificar confirmaciones ni borrar evidencia histórica.
                    claves = {(c['unidad_fuente'], c['operacion'], clave(c['norma']), clave(c['unidad'])) for c in cambios}
                    fuentes = {c['unidad_fuente'] for c in cambios}
                    vistos, afectadas = set(), set()
                    for evento in documento.cambios_detectados.filter(estado_revision='pendiente', unidad_fuente__in=fuentes).order_by('pk'):
                        ref = evento.referencia
                        identidad = (evento.unidad_fuente, evento.operacion, clave(ref.get('norma', '')), clave(ref.get('unidad', '')))
                        if identidad not in claves or identidad in vistos:
                            evento.estado_revision = 'descartado'
                            evento.observacion = 'Corrección de extracción literal o detección duplicada; se conserva la evidencia original.'
                            evento.revisado_at = timezone.now()
                            evento.save(update_fields=['estado_revision', 'observacion', 'revisado_at'])
                            if evento.norma_afectada_id: afectadas.add(evento.norma_afectada_id)
                        else:
                            vistos.add(identidad)
                    from modulo_catalogo.models import Norma
                    for norma in Norma.objects.filter(pk__in=afectadas): actualizar_avisos(norma)

                self.stdout.write(f'Documento {documento.pk}: {len(disposiciones)} disposiciones, {len(cambios)} avisos expresos.')
            except (OSError, ValueError, RuntimeError) as exc:
                self.stderr.write(f'Documento {documento.pk}: no recuperado ({exc})')
