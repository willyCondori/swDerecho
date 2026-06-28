from modulo_auditoria.models.auditoria import Auditoria


def registrar_auditoria(
    usuario,
    tabla: str,
    accion: str,
    registro_id=None,
    request=None,
    metadata: dict = None,
):
    """
    Crea un registro de auditoría de forma silenciosa.
    Si falla no interrumpe el flujo principal.
    """
    try:
        ip = None
        if request:
            x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
            ip = x_forwarded.split(",")[0] if x_forwarded else request.META.get("REMOTE_ADDR")

        Auditoria.objects.create(
            usuario=usuario,
            tabla=tabla,
            accion=accion,
            registro_id=registro_id,
            ip=ip,
            metadata=metadata or {},
        )
    except Exception:
        pass


class AuditoriaMixin:
    """
    Mixin para ViewSets.
    Llama a registrar_auditoria en create, update y destroy.
    La subclase puede sobreescribir `auditoria_tabla`.
    """
    auditoria_tabla = "desconocido"

    def _auditar(self, accion, registro_id=None, metadata=None):
        registrar_auditoria(
            usuario=self.request.user,
            tabla=self.auditoria_tabla,
            accion=accion,
            registro_id=registro_id,
            request=self.request,
            metadata=metadata,
        )

    def perform_create(self, serializer):
        instance = serializer.save()
        self._auditar("CREATE", registro_id=instance.pk)
        return instance

    def perform_update(self, serializer):
        instance = serializer.save()
        self._auditar("UPDATE", registro_id=instance.pk)
        return instance

    def perform_destroy(self, instance):
        pk = instance.pk
        instance.delete()
        self._auditar("DELETE", registro_id=pk)
