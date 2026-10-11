from django.db import migrations


SQL = """
CREATE FUNCTION publicar_notificacion_cambio() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        PERFORM pg_notify('sw_derecho_notificaciones', OLD.usuario_id::text);
    ELSE
        PERFORM pg_notify('sw_derecho_notificaciones', NEW.usuario_id::text);
        IF TG_OP = 'UPDATE' AND OLD.usuario_id IS DISTINCT FROM NEW.usuario_id THEN
            PERFORM pg_notify('sw_derecho_notificaciones', OLD.usuario_id::text);
        END IF;
    END IF;
    RETURN NULL;
END; $$;
CREATE TRIGGER notificaciones_cambio AFTER INSERT OR UPDATE OR DELETE ON notificaciones
FOR EACH ROW EXECUTE FUNCTION publicar_notificacion_cambio();
"""


class Migration(migrations.Migration):
    dependencies = [('modulo_notificaciones', '0002_alter_notificacion_tipo')]
    operations = [migrations.RunSQL(SQL, 'DROP TRIGGER notificaciones_cambio ON notificaciones; DROP FUNCTION publicar_notificacion_cambio();')]
