from django.db.models import BooleanField, F, Func


def articulos_disponibles(queryset):
    """Misma validación jurídica en la búsqueda SQL y las sugerencias por reglas."""
    return queryset.filter(estado=True, norma__estado=True, tipo_unidad='articulo').alias(
        _vigente_ranking=Func(F('pk'), F('norma_id'), function='articulo_disponible_ranking',
                             output_field=BooleanField()),
    ).filter(_vigente_ranking=True)
