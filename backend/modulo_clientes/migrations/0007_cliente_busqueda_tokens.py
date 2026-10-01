import django.db.models.deletion
from django.db import migrations, models

LOTE = 2000


def indexar_clientes_existentes(apps, schema_editor):
    """
    Calcula una sola vez el índice de búsqueda de los clientes ya cargados
    (descifra nombres y apellidos aquí, no en cada búsqueda). Los clientes
    nuevos o editados se indexan solos (modulo_clientes.signals). Si algún
    cliente no se puede descifrar queda sin tokens, sin frenar la migración.
    """
    from core.encryption.aes_encryption import safe_decrypt
    from modulo_clientes.services.busqueda_service import hashes_de_indexado

    Cliente = apps.get_model("modulo_clientes", "Cliente")
    Token = apps.get_model("modulo_clientes", "ClienteBusquedaToken")

    pendientes = []
    for cliente in Cliente.objects.order_by("id").iterator():
        nombres = safe_decrypt(cliente.nombres, fallback="")
        apellidos = safe_decrypt(cliente.apellidos, fallback="")
        for h in hashes_de_indexado(nombres, apellidos):
            pendientes.append(Token(cliente_id=cliente.pk, token_hash=h))
        if len(pendientes) >= LOTE:
            Token.objects.bulk_create(pendientes, ignore_conflicts=True)
            pendientes = []
    if pendientes:
        Token.objects.bulk_create(pendientes, ignore_conflicts=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('modulo_clientes', '0006_papelera_clientes'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClienteBusquedaToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token_hash', models.CharField(max_length=64)),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='busqueda_tokens', to='modulo_clientes.cliente')),
            ],
            options={
                'db_table': 'clientes_busqueda_tokens',
                'constraints': [models.UniqueConstraint(fields=('token_hash', 'cliente'), name='uq_cliente_busqueda_token')],
            },
        ),
        migrations.RunPython(indexar_clientes_existentes, noop_reverse),
    ]
