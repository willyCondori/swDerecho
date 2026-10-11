"""Comparación sin alterar análisis ni declarar validación jurídica."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.test import override_settings
from modulo_casos.models.caso import Caso
from modulo_ia.models.jurisprudencia import ResolucionJurisprudencia
from modulo_ia.services.jurisprudencia_service import JurisprudenciaService
from modulo_ia.services.model_loader import version_activa


class Command(BaseCommand):
    help = 'Exporta candidatos por umbral para revisión profesional, sin guardar rankings.'

    def add_arguments(self, parser):
        parser.add_argument('--caso', required=True, type=int)
        parser.add_argument('--salida', required=True)

    def handle(self, *args, **opciones):
        caso = Caso.objects.get(pk=opciones['caso'])
        evaluaciones = []
        for umbral in [.50, .55, .60, .65]:
            with override_settings(JURISPRUDENCIA_UMBRAL_RECOMENDACION=umbral):
                candidatos = JurisprudenciaService.recuperar(caso)
            for candidato in candidatos:
                resolucion = ResolucionJurisprudencia.objects.get(pk=candidato['resolucion_id'])
                candidato.update(numero=resolucion.numero, url_fuente=resolucion.url_fuente,
                                 revision_profesional='pendiente', pertinencia=None, observaciones='')
            evaluaciones.append(dict(umbral_recomendacion=umbral, candidatos=candidatos))
        datos = dict(caso_id=caso.pk, modelo_version=version_activa(),
                     validacion_juridica='pendiente', evaluaciones=evaluaciones)
        ruta = Path(opciones['salida'])
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding='utf-8')
        self.stdout.write(f'Comparación guardada: {ruta}. Revisión profesional pendiente.')
