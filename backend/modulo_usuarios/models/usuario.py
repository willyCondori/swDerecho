from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from .rol import Rol
from core.permissions.roles import ROL_ADMINISTRADOR, rol_de


class UsuarioManager(BaseUserManager):
    def create_user(self, usuario, password=None, **extra_fields):
        if not usuario:
            raise ValueError("El nombre de usuario es obligatorio.")
        user = self.model(usuario=usuario, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, usuario, password=None, **extra_fields):
        extra_fields.setdefault("estado", True)

        if extra_fields.get("rol") is None:
            rol_admin, _ = Rol.objects.get_or_create(
                nombre="Administrador",
                defaults={"descripcion": "Administrador del sistema", "estado": True},
            )
            extra_fields["rol"] = rol_admin

        return self.create_user(usuario, password, **extra_fields)


class Usuario(AbstractBaseUser):
    usuario      = models.CharField(max_length=100, unique=True)
    rol          = models.ForeignKey(
                       Rol,
                       on_delete=models.PROTECT,
                       related_name="usuarios",
                       null=True,
                       blank=True,
                   )
    estado       = models.BooleanField(default=True)
    # Se activa al crear el usuario con contraseña generada
    # automáticamente. Obliga a cambiarla en el primer login antes
    # de dejarlo usar el resto del sistema.
    debe_cambiar_password = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = "usuario"
    REQUIRED_FIELDS = []

    objects = UsuarioManager()

    class Meta:
        db_table = "usuarios"
        ordering = ["usuario"]
        indexes  = [
            models.Index(fields=["rol"],         name="idx_usuarios_rol"),
            models.Index(fields=["estado"],      name="idx_usuarios_estado"),
        ]

    def __str__(self):
        return self.usuario


    @property
    def is_admin(self):
        return bool(self.estado and rol_de(self) == ROL_ADMINISTRADOR)

    # Permisos requeridos por Django admin.
    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin

    @property
    def is_staff(self):
        return self.is_admin