# modulo_catalogo/views/carga_articulos_view.py

import logging
import os

from django.conf import settings
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions.auditoria_mixin import registrar_auditoria
from core.permissions.roles_permission import EsOperativo
from modulo_catalogo.serializers.carga_pdf_serializer import CargaArticulosPDFSerializer
from modulo_catalogo.services.background_tasks import (
    lanzar_carga_en_background,
    obtener_progreso,
)

logger = logging.getLogger(__name__)


class CargaArticulosView(APIView):
    """
    POST /api/catalogo/cargar-articulos/

    El formulario de carga pide solo 3 campos + el PDF:
        - rama_id          (rama de derecho)
        - jerarquia_id      (tipo de norma / jerarquía normativa)
        - nombre_documento  (nombre en texto del documento, ej. "Código de
                              Procedimiento Penal")

    Ya NO existe una lista fija de "fuentes" (Civil/Penal/Laboral/CPE): la
    Norma destino se busca o se crea automáticamente a partir del nombre
    de documento (ver CargaArticulosPDFSerializer), así que se puede
    cargar el CPP o cualquier otra norma nueva sin tocar el backend.

    Este endpoint NO espera a que termine todo el procesamiento del PDF.
    Guarda el archivo, arranca la carga en un hilo de background, y
    devuelve el task_id de inmediato (202 Accepted). El frontend debe
    hacer polling a GET /api/catalogo/cargar-articulos/estado/{task_id}/
    hasta que "estado" sea "SUCCESS" o "FAILURE".
    """
    permission_classes = [EsOperativo]
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
        norma = data["norma"]
        rama = data["rama"]
        jerarquia = data.get("jerarquia")
        sobrescribir = data.get("sobrescribir", False)

        existentes = serializer.context.get("existentes", 0)
        norma_creada = serializer.context.get("norma_creada", False)
        usuario = request.user

        # ─────────────────────────────
        # GUARDAR PDF
        # ─────────────────────────────
        try:
            carpeta_norma = (norma.sigla or norma.nombre).lower().replace(" ", "_")

            ruta_carpeta = os.path.join(
                settings.MEDIA_ROOT,
                "documentos_normativas",
                carpeta_norma,
            )

            os.makedirs(ruta_carpeta, exist_ok=True)

            nombre_archivo = f"{carpeta_norma}_{archivo.name}"
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
        # ─────────────────────────────
        try:
            with open(ruta_archivo, "rb") as f:
                contenido = f.read()

            task_id = lanzar_carga_en_background(
                contenido_pdf=contenido,
                norma_id=norma.id,
                rama_id=rama.id,
                jerarquia_id=jerarquia.id if jerarquia else None,
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
        # AUDITORÍA
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
                    "norma_id": norma.id,
                    "norma_nombre": norma.nombre,
                    "norma_creada": norma_creada,
                    "rama_id": rama.id,
                    "rama_nombre": rama.nombre,
                    "jerarquia_id": jerarquia.id if jerarquia else None,
                    "sobrescribir": sobrescribir,
                    "archivo": archivo.name,
                    "tamano_bytes": archivo.size,
                    "task_id": task_id,
                },
            )
        except Exception:
            logger.warning("Error en auditoría (no crítico)")

        # ─────────────────────────────
        # RESPUESTA INMEDIATA
        # ─────────────────────────────
        respuesta = {
            "detail": "Carga de PDF iniciada. Consultá el progreso con el task_id.",
            "task_id": task_id,
            "norma": norma.nombre,
            "norma_creada": norma_creada,
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
    GET /api/catalogo/cargar-articulos/estado/{task_id}/

    El frontend hace polling acá (cada 1-2 segundos) hasta que "estado"
    sea "SUCCESS" o "FAILURE".

    Respuesta mientras está en curso:
        {"task_id": "...", "estado": "STARTED", "progreso": 45, "paso": "Procesando artículo 180/364..."}

    Respuesta al terminar OK:
        {"task_id": "...", "estado": "SUCCESS", "resumen": {...}}  # resumen = ResultadoCarga.resumen()

    Respuesta si falló:
        {"task_id": "...", "estado": "FAILURE", "error": "..."}

    Si el task_id no existe o ya expiró del cache (2 horas):
        404 {"detail": "Tarea no encontrada o expirada."}
    """
    permission_classes = [EsOperativo]

    def get(self, request, task_id=None):
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
