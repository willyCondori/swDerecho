from django.db import models


class Cliente(models.Model):
    """
    Datos personales del cliente atendido.
    Todos los datos personales se almacenan cifrados (AES-256).
    """

    # ----- Campos cifrados -----
    nombres = models.TextField()
    apellidos = models.TextField()
    telefono = models.TextField(blank=True, null=True)
    # ----------------------------

    # AES-GCM usa un nonce aleatorio en cada encrypt(), así que no se
    # puede validar unicidad comparando directamente los campos
    # cifrados de arriba (dos veces el mismo teléfono producen dos
    # ciphertexts distintos). Estos hashes HMAC-SHA256 determinísticos
    # (ver core.encryption.aes_encryption.hash_lookup) permiten un
    # filter() indexado para detectar duplicados sin descifrar toda
    # la tabla. Mismo patrón que PerfilUsuario.email_hash.
    telefono_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    nombre_completo_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    # NOTA: unique=True se agrega recién en la migración
    # 0005_cliente_hash_unique, después de correr el backfill de
    # 0004_cliente_telefono_hash y confirmar que no hay duplicados
    # reales entre los clientes ya cargados (mismo patrón de dos
    # pasos que modulo_usuarios.email_hash — ver 0006/0008 ahí).

    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "clientes"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["estado"], name="idx_clientes_estado"),
            models.Index(fields=["telefono_hash"], name="idx_clientes_telefono_hash"),
            models.Index(fields=["nombre_completo_hash"], name="idx_clientes_nombre_hash"),
        ]

    def __str__(self):
        return f"Cliente #{self.id}"