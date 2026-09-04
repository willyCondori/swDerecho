"""
Comando: verificar_emails_duplicados

Descifra el email de todos los perfiles y reporta cuáles comparten el
mismo email real. Existe porque el `unique=True` que tenía la columna
`email` (texto cifrado con AES-GCM, nonce aleatorio en cada encrypt())
nunca impidió duplicados reales: dos encrypt() del mismo email dan
ciphertexts distintos, así que Postgres los veía como "distintos".

Se usa antes de aplicar la migración
0008_perfilusuario_email_hash_unique, que sí exige unicidad real
sobre email_hash (HMAC-SHA256 determinístico) y va a fallar si queda
algún duplicado sin resolver.

Uso:
    python manage.py verificar_emails_duplicados
"""

from collections import defaultdict

from django.core.management.base import BaseCommand

from core.encryption.aes_encryption import decrypt
from modulo_usuarios.models.perfil import PerfilUsuario


class Command(BaseCommand):
    help = "Detecta perfiles que comparten el mismo email real (descifrado)."

    def handle(self, *args, **options):
        por_email = defaultdict(list)
        sin_descifrar = []

        for perfil in PerfilUsuario.objects.select_related("usuario").order_by("id"):
            try:
                email_plano = decrypt(perfil.email) if perfil.email else ""
            except Exception:
                sin_descifrar.append(perfil)
                continue

            if email_plano:
                por_email[email_plano.strip().lower()].append(perfil)

        duplicados = {email: perfiles for email, perfiles in por_email.items() if len(perfiles) > 1}

        if not duplicados and not sin_descifrar:
            self.stdout.write(self.style.SUCCESS(
                "No hay emails duplicados ni perfiles sin descifrar. "
                "Se puede aplicar 0008_perfilusuario_email_hash_unique."
            ))
            return

        if duplicados:
            self.stdout.write(self.style.WARNING(
                f"\nSe encontraron {len(duplicados)} email(s) usados por más de un perfil:\n"
            ))
            for email, perfiles in duplicados.items():
                self.stdout.write(self.style.WARNING(f"  {email}"))
                for p in perfiles:
                    self.stdout.write(
                        f"    - perfil id={p.id}  usuario='{p.usuario.usuario}'  "
                        f"usuario_id={p.usuario_id}  estado_usuario={p.usuario.estado}"
                    )
            self.stdout.write(
                "\nEditá uno de cada par a un email real distinto (panel de "
                "usuarios o shell) y volvé a correr este comando hasta que "
                "no quede ninguno.\n"
            )

        if sin_descifrar:
            self.stdout.write(self.style.WARNING(
                f"\n{len(sin_descifrar)} perfil(es) con email que no se pudo descifrar:\n"
            ))
            for p in sin_descifrar:
                self.stdout.write(f"  - perfil id={p.id}  usuario='{p.usuario.usuario}'")
