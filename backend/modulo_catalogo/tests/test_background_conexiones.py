import threading
from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.db import connection
from django.test import TransactionTestCase

from modulo_catalogo.services.background_tasks import (
    lanzar_carga_en_background,
    obtener_progreso,
)


class CierreConexionBackgroundTests(TransactionTestCase):
    """Una conexión real del worker debe desaparecer antes de borrar la BD."""

    def comprobar_cierre(self, fallo_carga=False, fallo_callback=False):
        self.addCleanup(cache.clear)
        pids = []
        errores = []

        def carga(**kwargs):
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                pids.append(cursor.fetchone()[0])
            if fallo_carga:
                raise RuntimeError("Carga fallida de prueba")
            return SimpleNamespace(resumen=lambda: {"guardados": 0})

        def callback():
            if fallo_callback:
                raise RuntimeError("Callback fallido de prueba")

        with patch("modulo_catalogo.services.background_tasks.threading.Thread") as constructor, \
                patch("modulo_catalogo.services.carga_pdf_service.cargar_articulos_desde_bytes", carga):
            task_id = lanzar_carga_en_background(b"pdf", 1, 1, on_exito=callback)
            target = constructor.call_args.kwargs["target"]

        def ejecutar():
            try:
                target()
            except BaseException as exc:
                errores.append(exc)

        with patch("modulo_catalogo.services.carga_pdf_service.cargar_articulos_desde_bytes", carga), \
                patch("modulo_catalogo.services.background_tasks.logger.exception"):
            hilo = threading.Thread(target=ejecutar)
            hilo.start()
            hilo.join(timeout=10)
        self.assertFalse(hilo.is_alive(), "El worker no terminó")
        self.assertEqual(errores, [])
        self.assertEqual(len(pids), 1)
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE pid = %s", [pids[0]])
            self.assertEqual(cursor.fetchone()[0], 0, "El worker dejó una sesión abierta")
        self.assertEqual(obtener_progreso(task_id)["state"], "FAILURE" if fallo_carga else "SUCCESS")

    def test_cierra_conexion_tras_carga_exitosa(self):
        self.comprobar_cierre()

    def test_cierra_conexion_tras_error_de_carga(self):
        self.comprobar_cierre(fallo_carga=True)

    def test_cierra_conexion_tras_error_del_callback(self):
        self.comprobar_cierre(fallo_callback=True)
