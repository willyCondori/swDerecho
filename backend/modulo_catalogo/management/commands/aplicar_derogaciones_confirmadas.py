from django.core.management.base import BaseCommand, CommandError
from modulo_catalogo.models import CambioNormativo
from modulo_catalogo.services.historial_articulos_service import aplicar_texto_confirmado


class Command(BaseCommand):
    help = 'Conserva el historial y aplica al texto las derogaciones confirmadas cuya fecha de efecto llegó.'

    def handle(self, *args, **options):
        errores = 0
        for cambio in CambioNormativo.objects.filter(estado_revision='confirmado', operacion__in=['deroga', 'abroga']).order_by('pk'):
            try:
                aplicar_texto_confirmado(cambio)
            except ValueError as exc:
                errores += 1
                self.stderr.write(f'Cambio {cambio.pk}: {exc}')
        self.stdout.write(f'Historial actualizado. Cambios que requieren revisión: {errores}.')
        if errores:
            raise CommandError('Algunos cambios requieren identificar su fragmento antes de retirar texto.')
