from django.db import migrations, models


def backfill_hashes(apps, schema_editor):
    """
    Calcula telefono_hash y nombre_completo_hash para los clientes ya
    existentes, descifrando sus datos una sola vez (migración, no en
    cada request). Los clientes nuevos ya llegan con ambos hashes
    calculados desde ClienteWriteSerializer._encrypt_fields.

    A propósito NO se agrega unique=True en esta misma migración: los
    campos cifrados con AES-GCM (nonce aleatorio en cada encrypt())
    nunca impidieron que dos clientes tuvieran el mismo teléfono o
    nombre completo reales — dos encrypt() del mismo valor dan
    ciphertexts distintos. Si esta migración corre sobre datos reales,
    es posible que aparezcan duplicados "silenciosos" recién ahora.

    Por eso: se guarda el hash igual (sin bloquear la migración) y se
    imprime un reporte con los clientes en conflicto para resolverlos
    a mano. Recién en 0005_cliente_hash_unique se agrega el
    unique=True de verdad — aplicar esa migración antes de limpiar los
    duplicados fallará de nuevo, a propósito (mismo patrón que
    modulo_usuarios.email_hash, ver sus migraciones 0006/0008).
    """
    from core.encryption.aes_encryption import decrypt, hash_lookup

    Cliente = apps.get_model("modulo_clientes", "Cliente")

    vistos_telefono = {}   # hash -> primer cliente.id que lo tuvo
    vistos_nombre = {}
    duplicados_telefono = []
    duplicados_nombre = []
    sin_descifrar = []

    for cliente in Cliente.objects.filter(
        telefono_hash__isnull=True, nombre_completo_hash__isnull=True
    ).order_by("id"):
        try:
            nombres_plano = decrypt(cliente.nombres) if cliente.nombres else ""
            apellidos_plano = decrypt(cliente.apellidos) if cliente.apellidos else ""
            telefono_plano = decrypt(cliente.telefono) if cliente.telefono else ""
        except Exception:
            sin_descifrar.append(cliente.id)
            continue

        telefono_hash = hash_lookup(telefono_plano)  # None si telefono_plano es ""
        nombre_completo = f"{nombres_plano.strip()} {apellidos_plano.strip()}".strip()
        nombre_hash = hash_lookup(nombre_completo)

        if telefono_hash is not None:
            if telefono_hash in vistos_telefono:
                duplicados_telefono.append(
                    (cliente.id, vistos_telefono[telefono_hash], telefono_plano)
                )
            else:
                vistos_telefono[telefono_hash] = cliente.id

        if nombre_hash is not None:
            if nombre_hash in vistos_nombre:
                duplicados_nombre.append(
                    (cliente.id, vistos_nombre[nombre_hash], nombre_completo)
                )
            else:
                vistos_nombre[nombre_hash] = cliente.id

        cliente.telefono_hash = telefono_hash
        cliente.nombre_completo_hash = nombre_hash
        cliente.save(update_fields=["telefono_hash", "nombre_completo_hash"])

    if duplicados_telefono or duplicados_nombre or sin_descifrar:
        print("\n" + "=" * 78)
        print("modulo_clientes.0004: revisar antes de aplicar la migración 0005")
        print("=" * 78)
        if duplicados_telefono:
            print(
                "Clientes con el MISMO teléfono real (el cifrado nunca lo\n"
                "impidió, porque AES-GCM usa nonce aleatorio). Hay que corregir\n"
                "uno de los dos antes de 0005:"
            )
            for id_dup, id_original, telefono in duplicados_telefono:
                print(f"  - cliente id={id_dup} repite el teléfono de cliente id={id_original}  ({telefono})")
        if duplicados_nombre:
            print(
                "Clientes con el MISMO nombre completo real:"
            )
            for id_dup, id_original, nombre in duplicados_nombre:
                print(f"  - cliente id={id_dup} repite el nombre de cliente id={id_original}  ({nombre})")
        if sin_descifrar:
            print(
                "Clientes cuyos datos NO se pudieron descifrar (clave rotada o\n"
                "dato corrupto). Quedan con los hashes en NULL:"
            )
            for id_cliente in sin_descifrar:
                print(f"  - cliente id={id_cliente}")
        print("=" * 78 + "\n")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_clientes", "0003_remove_cliente_fecha_nacimiento"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="telefono_hash",
            field=models.CharField(max_length=64, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="cliente",
            name="nombre_completo_hash",
            field=models.CharField(max_length=64, null=True, blank=True),
        ),
        migrations.RunPython(backfill_hashes, noop_reverse),
        migrations.AddIndex(
            model_name="cliente",
            index=models.Index(fields=["telefono_hash"], name="idx_clientes_telefono_hash"),
        ),
        migrations.AddIndex(
            model_name="cliente",
            index=models.Index(fields=["nombre_completo_hash"], name="idx_clientes_nombre_hash"),
        ),
    ]
