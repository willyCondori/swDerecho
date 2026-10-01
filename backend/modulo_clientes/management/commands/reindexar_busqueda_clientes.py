from django.core.management.base import BaseCommand

from modulo_clientes.models.cliente import Cliente
from modulo_clientes.services.busqueda_service import reindexar_cliente


class Command(BaseCommand):
    help = (
        "Reconstruye el índice de búsqueda por nombre de los clientes "
        "(ClienteBusquedaToken). Útil después de importar clientes con "
        "bulk_create/update() o de rotar ENCRYPTION_KEY."
    )

    def handle(self, *args, **options):
        total = Cliente.objects.count()
        for i, cliente in enumerate(Cliente.objects.order_by("id").iterator(), start=1):
            reindexar_cliente(cliente)
            if i % 500 == 0:
                self.stdout.write(f"Reindexados {i}/{total}")
        self.stdout.write(self.style.SUCCESS(f"Listo. {total} clientes reindexados."))
