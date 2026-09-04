from django.db import migrations, models


def backfill_email_hash(apps, schema_editor):
    """
    Calcula email_hash para los perfiles ya existentes, descifrando su
    email una sola vez (migración, no en cada request). Los registros
    nuevos ya llegan con email_hash calculado desde
    PerfilUsuarioWriteSerializer._encrypt_fields.

    A propósito NO se agrega unique=True en esta misma migración: el
    email de PerfilUsuario está cifrado con AES-GCM (nonce aleatorio
    en cada encrypt()), así que el `unique=True` que tenía la columna
    `email` en texto cifrado NUNCA impidió que dos perfiles tuvieran
    el mismo email real en texto plano — dos encrypt() del mismo
    email dan ciphertexts distintos. Si esta migración corre sobre un
    proyecto con datos reales, es muy probable que haya duplicados
    "silenciosos" que recién salen a la luz acá.

    Por eso: se guarda el hash igual (sin bloquear la migración) y se
    imprime un reporte con los perfiles en conflicto para resolverlos
    a mano. Recién en 0008_perfilusuario_email_hash_unique se agrega
    el unique=True de verdad — aplicar esa migración antes de limpiar
    los duplicados fallará de nuevo, a propósito.
    """
    from core.encryption.aes_encryption import decrypt, hash_lookup

    PerfilUsuario = apps.get_model("modulo_usuarios", "PerfilUsuario")

    vistos = {}          # email_hash -> primer perfil.id que lo tuvo
    duplicados = []      # [(perfil.id duplicado, perfil.id original, email)]
    sin_descifrar = []   # perfil.id cuyo email no se pudo descifrar

    for perfil in PerfilUsuario.objects.filter(email_hash__isnull=True).order_by("id"):
        try:
            email_plano = decrypt(perfil.email) if perfil.email else ""
        except Exception:
            sin_descifrar.append(perfil.id)
            continue

        hash_calculado = hash_lookup(email_plano)  # None si email_plano es ""

        if hash_calculado is not None:
            if hash_calculado in vistos:
                duplicados.append((perfil.id, vistos[hash_calculado], email_plano))
            else:
                vistos[hash_calculado] = perfil.id

        perfil.email_hash = hash_calculado
        perfil.save(update_fields=["email_hash"])

    if duplicados or sin_descifrar:
        print("\n" + "=" * 78)
        print("modulo_usuarios.0006: revisar antes de aplicar la migración 0008")
        print("=" * 78)
        if duplicados:
            print(
                "Perfiles con el MISMO email real (el email 'cifrado único' nunca\n"
                "lo impidió, porque AES-GCM usa nonce aleatorio). Hay que editar\n"
                "uno de los dos a un email real distinto antes de 0008:"
            )
            for id_dup, id_original, email in duplicados:
                print(f"  - perfil id={id_dup} repite el email de perfil id={id_original}  ({email})")
        if sin_descifrar:
            print(
                "Perfiles cuyo email NO se pudo descifrar (clave rotada o dato\n"
                "corrupto). Quedan con email_hash=NULL: la recuperación de\n"
                "contraseña por correo no va a funcionar para ellos hasta que se\n"
                "les vuelva a cargar el email:"
            )
            for id_perfil in sin_descifrar:
                print(f"  - perfil id={id_perfil}")
        print("=" * 78 + "\n")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("modulo_usuarios", "0005_usuario_debe_cambiar_password"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfilusuario",
            name="email_hash",
            field=models.CharField(max_length=64, null=True, blank=True),
        ),
        migrations.RunPython(backfill_email_hash, noop_reverse),
        migrations.AddIndex(
            model_name="perfilusuario",
            index=models.Index(fields=["email_hash"], name="idx_perfil_email_hash"),
        ),
    ]