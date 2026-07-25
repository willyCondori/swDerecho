"""
Versión SIN Celery de la carga de artículos.

Antes: ejecutaba en background con Celery
Ahora : se ejecuta de forma síncrona (request-response)

Se mantiene la misma lógica y estructura de retorno.
"""

import logging
import os

logger = logging.getLogger(__name__)


def cargar_articulos_pdf(
    ruta_temporal: str,
    fuente: str,
    norma_id: int,
    rama_id: int,
    sobrescribir: bool = False,
    usuario_id: int = None,
    task=None,  # 👈 opcional (para compatibilidad si luego vuelves a Celery)
):
    """
    Procesa PDF → artículos → embeddings → BD
    """

    from modulo_catalogo.services.carga_pdf_service import cargar_articulos_desde_bytes
    from core.permissions.auditoria_mixin import registrar_auditoria

    # ─────────────────────────────────────────────
    # Estado inicial (solo si existe task tipo Celery)
    # ─────────────────────────────────────────────
    try:
        if task:
            task.update_state(
                state="STARTED",
                meta={"progreso": 1, "paso": "Iniciando carga del PDF..."},
            )
    except Exception:
        pass

    # ─────────────────────────────────────────────
    # Leer archivo
    # ─────────────────────────────────────────────
    try:
        with open(ruta_temporal, "rb") as f:
            contenido = f.read()
    except Exception as e:
        logger.exception("Error leyendo archivo temporal")
        return {"status": "error", "error": str(e)}

    # ─────────────────────────────────────────────
    # Procesar PDF (NÚCLEO DEL SISTEMA)
    # ─────────────────────────────────────────────
    try:
        resultado = cargar_articulos_desde_bytes(
            contenido_pdf=contenido,
            fuente=fuente,
            norma_id=norma_id,
            rama_id=rama_id,
            task=task,  # puede ser None
            sobrescribir=sobrescribir,
        )

    except Exception as e:
        logger.exception("Error en procesamiento del PDF")
        return {"status": "error", "error": str(e)}

    # ─────────────────────────────────────────────
    # Auditoría (no debe romper flujo)
    # ─────────────────────────────────────────────
    try:
        if usuario_id:
            usuario = _get_usuario(usuario_id)
            if usuario:
                registrar_auditoria(
                    usuario=usuario,
                    tabla="articulos",
                    accion="CREATE",
                    registro_id=norma_id,
                    metadata={
                        "fuente": fuente,
                        "norma_id": norma_id,
                        "rama_id": rama_id,
                        "guardados": getattr(resultado, "guardados", 0),
                        "duplicados": getattr(resultado, "duplicados", 0),
                        "errores": getattr(resultado, "errores", 0),
                        "modo": "sync_sin_celery",
                    },
                )
    except Exception:
        logger.warning("Auditoría falló pero no afecta la carga")

    # ─────────────────────────────────────────────
    # Limpieza del archivo temporal
    # ─────────────────────────────────────────────
    try:
        os.remove(ruta_temporal)
    except Exception:
        pass

    # ─────────────────────────────────────────────
    # Resultado final
    # ─────────────────────────────────────────────
    return {
        "status": "ok",
        "resumen": resultado.resumen(),
    }


# ─────────────────────────────────────────────
# Helper seguro
# ─────────────────────────────────────────────
def _get_usuario(usuario_id):
    try:
        from modulo_usuarios.models.usuario import Usuario
        return Usuario.objects.get(pk=usuario_id)
    except Exception:
        return None