from django.core.management.base import BaseCommand, CommandError
from modulo_catalogo.services.gaceta_service import recolectar
from modulo_catalogo.services.vigencia_service import fecha


class Command(BaseCommand):
    help = 'Descarga PDFs penales de leyes, decretos y sentencias oficiales; conserva un registro de errores.'

    def add_arguments(self, parser):
        parser.add_argument('--max-paginas', type=int, default=1,
                            help='Páginas por listado. 0 recorre todas las páginas disponibles.')
        parser.add_argument('--desde', help='Fecha de publicación inclusiva YYYY-MM-DD')
        parser.add_argument('--hasta', help='Fecha de publicación inclusiva YYYY-MM-DD')

    def handle(self, *args, **options):
        if options['max_paginas'] < 0:
            raise CommandError('El número de páginas debe ser cero o positivo.')
        for campo in ['desde', 'hasta']:
            if options[campo] and not fecha(options[campo]):
                raise CommandError(f'Fecha {campo} inválida.')
        resultado = recolectar(options['max_paginas'], fecha(options['desde']), fecha(options['hasta']))
        self.stdout.write(str(resultado))
        if resultado['errores']:
            raise CommandError('La sincronización quedó incompleta. Los errores están registrados para reintentar.')
