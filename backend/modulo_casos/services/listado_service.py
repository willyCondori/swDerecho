from django.db.models import Exists, OuterRef

from modulo_casos.models.resultado_caso import ResultadoCaso
from modulo_documentos.models.documento import DocumentoCaso


def preparar_listado_casos(queryset):
    """Carga relaciones e indicadores sin consultas adicionales por cada fila."""
    return queryset.select_related('usuario', 'cliente', 'rama_detectada').annotate(
        tiene_documento=Exists(DocumentoCaso.objects.filter(
            caso_id=OuterRef('pk'), tipo_archivo='pdf',
        )),
        tiene_resultado=Exists(ResultadoCaso.objects.filter(caso_id=OuterRef('pk'))),
    )
