# modulo_catalogo/views/carga_articulos_view.py

import logging
import os

from django.conf import settings
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions.auditoria_mixin import registrar_auditoria
from core.permissions.roles_permission import EsAdmin
from modulo_catalogo.serializers.carga_pdf_serializer import CargaArticulosPDFSerializer
from modulo_catalogo.services.carga_pdf_service import JERARQUIA_POR_FUENTE
from modulo_catalogo.services.background_tasks import (
    lanzar_carga_en_background,
    obtener_progreso,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# FUENTES
# ─────────────────────────────────────────────
FUENTES_INFO = {
    "Civil": {
        "label": "Código Civil",
        "descripcion": "Código Civil Boliviano. Patrón: ARTÍCULO N.",
        "jerarquia_nivel": JERARQUIA_POR_FUENTE.get("Civil", 2),
        "esperados": 1570,
    },
    "Penal": {
        "label": "Código Penal",
        "descripcion": "Código Penal Boliviano. Patrón: Art. N°.-",
        "jerarquia_nivel": JERARQUIA_POR_FUENTE.get("Penal", 2),
        "esperados": 363,
    },
    "Laboral": {
        "label": "Código Laboral",
        "descripcion": "Ley General del Trabajo",
        "jerarquia_nivel": JERARQUIA_POR_FUENTE.get("Laboral", 2),
        "esperados": 122,
    },
    "CPE": {
        "label": "Constitución Política del Estado",
        "descripcion": "CPE Bolivia 2009",
        "jerarquia_nivel": JERARQUIA_POR_FUENTE.get("CPE", 1),
        "esperados": 411,
    },
}


class CargaArticulosView(APIView):
    """
    POST /api/catalogo/cargar-pdf/

    IMPORTANTE — cambio de comportamiento respecto a la versión síncrona:
    Este endpoint YA NO espera a que termine todo el procesamiento del
    PDF. Guarda el archivo, arranca la carga en un hilo de background,
    y devuelve el task_id de inmediato (202 Accepted). El frontend debe
    hacer polling a GET /api/catalogo/cargar-pdf/estado/{task_id}/
    hasta que "estado" sea "SUCCESS" o "FAILURE".

    Esto es lo que arregla el bug de "el backend termina bien pero el
    frontend muestra error": antes, con PDFs grandes (Civil ~1570
    artículos), el procesamiento completo corría dentro del mismo
    request HTTP y tardaba minutos — tiempo suficiente para que algo
    del lado del cliente (timeout de fetch/axios) cortara la conexión
    antes de que la respuesta llegara, aunque los artículos ya se
    hubieran guardado en la BD durante el loop.
    """
    permission_classes = [EsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):

        serializer = CargaArticulosPDFSerializer(
            data=request.data,
            context={"request": request},
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data

        archivo = data["archivo"]
        fuente = data["fuente"]
        norma = data["norma"]
        rama = data["rama"]
        sobrescribir = data.get("sobrescribir", False)

        existentes = serializer.context.get("existentes", 0)
        usuario = request.user

        # ─────────────────────────────
        # GUARDAR PDF
        # ─────────────────────────────
        try:
            carpeta_fuente = fuente.lower()

            ruta_carpeta = os.path.join(
                settings.MEDIA_ROOT,
                "documentos_normativas",
                carpeta_fuente,
            )

            os.makedirs(ruta_carpeta, exist_ok=True)

            nombre_archivo = f"{carpeta_fuente}_{archivo.name}"
            ruta_archivo = os.path.join(ruta_carpeta, nombre_archivo)

            with open(ruta_archivo, "wb+") as destino:
                for chunk in archivo.chunks():
                    destino.write(chunk)

        except Exception as e:
            logger.exception("Error guardando PDF")
            return Response(
                {"detail": f"Error guardando archivo: {e}"},
                status=500,
            )

        # ─────────────────────────────
        # LEER CONTENIDO Y LANZAR EN BACKGROUND
        # (ya no se procesa acá — se dispara el hilo y se responde ya)
        # ─────────────────────────────
        try:
            with open(ruta_archivo, "rb") as f:
                contenido = f.read()

            task_id = lanzar_carga_en_background(
                contenido_pdf=contenido,
                fuente=fuente,
                norma_id=norma.id,
                rama_id=rama.id,
                sobrescribir=sobrescribir,
            )

        except Exception as e:
            logger.exception("Error lanzando la carga del PDF en background")
            try:
                os.remove(ruta_archivo)
            except Exception:
                pass

            return Response(
                {"detail": f"Error al iniciar el procesamiento del PDF: {e}"},
                status=500,
            )

        # ─────────────────────────────
        # AUDITORÍA (registra que se INICIÓ la carga, no el resultado final —
        # eso lo audita el hilo en background si querés, o el frontend puede
        # loguearlo aparte cuando el polling confirme SUCCESS)
        # ─────────────────────────────
        try:
            registrar_auditoria(
                usuario=usuario,
                tabla="articulos",
                accion="CREATE",
                registro_id=norma.id,
                request=request,
                metadata={
                    "accion": "carga_masiva_pdf_iniciada",
                    "fuente": fuente,
                    "norma_id": norma.id,
                    "norma_nombre": norma.nombre,
                    "rama_id": rama.id,
                    "rama_nombre": rama.nombre,
                    "sobrescribir": sobrescribir,
                    "archivo": archivo.name,
                    "tamano_bytes": archivo.size,
                    "task_id": task_id,
                },
            )
        except Exception:
            logger.warning("Error en auditoría (no crítico)")

        # ─────────────────────────────
        # RESPUESTA INMEDIATA — sin esperar el procesamiento
        # ─────────────────────────────
        respuesta = {
            "detail": "Carga de PDF iniciada. Consultá el progreso con el task_id.",
            "task_id": task_id,
            "fuente": fuente,
            "norma": norma.nombre,
            "rama": rama.nombre,
            "sobrescribir": sobrescribir,
        }

        if existentes:
            respuesta["advertencia"] = (
                f"Ya existían {existentes} artículos en esta norma+rama"
            )

        return Response(respuesta, status=status.HTTP_202_ACCEPTED)


class EstadoCargaPDFView(APIView):
    """
    GET /api/catalogo/cargar-pdf/estado/{task_id}/

    El frontend hace polling acá (cada 1-2 segundos, por ejemplo) hasta
    que "estado" sea "SUCCESS" o "FAILURE".

    Respuesta mientras está en curso:
        {"task_id": "...", "estado": "STARTED", "progreso": 45, "paso": "Procesando artículo 180/364..."}

    Respuesta al terminar OK:
        {"task_id": "...", "estado": "SUCCESS", "resumen": {...}}  # resumen = ResultadoCarga.resumen()

    Respuesta si falló:
        {"task_id": "...", "estado": "FAILURE", "error": "..."}

    Si el task_id no existe o ya expiró del cache (2 horas):
        404 {"detail": "Tarea no encontrada o expirada."}
    """
    permission_classes = [EsAdmin]

    def get(self, request, task_id=None):
        # Acepta el task_id tanto por la URL (/estado/<task_id>/) como
        # por query param (/estado/?task_id=...) — el log mostró que el
        # frontend actual usa query param, así que cubrimos los dos casos.
        task_id = task_id or request.query_params.get("task_id")

        if not task_id:
            return Response(
                {"detail": "Parámetro task_id requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        info = obtener_progreso(task_id)

        if info is None:
            return Response(
                {"detail": "Tarea no encontrada o expirada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        estado = info.get("state", "PENDING")
        meta = info.get("meta", {})

        respuesta = {"task_id": task_id, "estado": estado}

        if estado == "SUCCESS":
            respuesta["resumen"] = meta.get("resumen")
        elif estado == "FAILURE":
            respuesta["error"] = meta.get("error")
        else:
            respuesta["progreso"] = meta.get("progreso", 0)
            respuesta["paso"] = meta.get("paso", "procesando")

        return Response(respuesta, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# FUENTES
# ─────────────────────────────────────────────
class FuentesDisponiblesView(APIView):
    permission_classes = [EsAdmin]

    def get(self, request):
        from modulo_catalogo.models.jerarquia import jerarquia as Jerarquia

        niveles_usados = {info["jerarquia_nivel"] for info in FUENTES_INFO.values()}
        nombres_por_nivel = dict(
            Jerarquia.objects.filter(nivel__in=niveles_usados).values_list("nivel", "nombre")
        )

        fuentes = []

        for clave, info in FUENTES_INFO.items():
            nivel = info["jerarquia_nivel"]
            fuentes.append(
                {
                    "value": clave,
                    "label": info["label"],
                    "descripcion": info["descripcion"],
                    "jerarquia": {
                        "nivel": nivel,
                        "nombre": nombres_por_nivel.get(nivel),
                    },
                    "esperados": info["esperados"],
                }
            )

        return Response({"fuentes": fuentes})