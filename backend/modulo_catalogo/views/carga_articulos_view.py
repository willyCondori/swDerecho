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

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# FUENTES
# ─────────────────────────────────────────────
FUENTES_INFO = {
    "Civil": {
        "label": "Código Civil",
        "descripcion": "Código Civil Boliviano. Patrón: ARTÍCULO N.",
        "jerarquia": JERARQUIA_POR_FUENTE.get("Civil", 0.8),
        "esperados": 1570,
    },
    "Penal": {
        "label": "Código Penal",
        "descripcion": "Código Penal Boliviano. Patrón: Art. N°.-",
        "jerarquia": JERARQUIA_POR_FUENTE.get("Penal", 0.8),
        "esperados": 363,
    },
    "Laboral": {
        "label": "Código Laboral",
        "descripcion": "Ley General del Trabajo",
        "jerarquia": JERARQUIA_POR_FUENTE.get("Laboral", 0.8),
        "esperados": 122,
    },
    "CPE": {
        "label": "Constitución Política del Estado",
        "descripcion": "CPE Bolivia 2009",
        "jerarquia": JERARQUIA_POR_FUENTE.get("CPE", 1.0),
        "esperados": 411,
    },
}


class CargaArticulosView(APIView):
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

        # usuario seguro
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
        # PROCESAMIENTO DIRECTO (SIN CELERY)
        # ─────────────────────────────
        try:
            from modulo_catalogo.services.carga_pdf_service import (
                cargar_articulos_desde_bytes,
            )

            with open(ruta_archivo, "rb") as f:
                contenido = f.read()

            resultado = cargar_articulos_desde_bytes(
                contenido_pdf=contenido,
                fuente=fuente,
                norma_id=norma.id,
                rama_id=rama.id,
                task=None,  # antes Celery
                sobrescribir=sobrescribir,
            )

        except Exception as e:
            logger.exception("Error procesando PDF")
            try:
                os.remove(ruta_archivo)
            except Exception:
                pass

            return Response(
                {"detail": f"Error procesando PDF: {e}"},
                status=500,
            )

        # ─────────────────────────────
        # AUDITORÍA (CORREGIDA)
        # ─────────────────────────────
        try:
            registrar_auditoria(
                usuario=usuario,
                tabla="articulos",
                accion="CREATE",
                registro_id=norma.id,
                request=request,
                metadata={
                    "accion": "carga_masiva_pdf",
                    "fuente": fuente,
                    "norma_id": norma.id,
                    "norma_nombre": norma.nombre,
                    "rama_id": rama.id,
                    "rama_nombre": rama.nombre,
                    "sobrescribir": sobrescribir,
                    "archivo": archivo.name,
                    "tamano_bytes": archivo.size,
                    "articulos_creados": getattr(resultado, "guardados", None),
                },
            )
        except Exception:
            logger.warning("Error en auditoría (no crítico)")

        # ─────────────────────────────
        # RESPUESTA FINAL
        # ─────────────────────────────
        respuesta = {
            "detail": "PDF procesado correctamente",
            "fuente": fuente,
            "norma": norma.nombre,
            "rama": rama.nombre,
            "sobrescribir": sobrescribir,
            "resultado": (
                resultado.resumen()
                if hasattr(resultado, "resumen")
                else None
            ),
        }

        if existentes:
            respuesta["advertencia"] = (
                f"Ya existían {existentes} artículos en esta norma+rama"
            )

        return Response(respuesta, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# ESTADO (YA NO ES NECESARIO CELERY)
# ─────────────────────────────────────────────
class EstadoCargaView(APIView):
    permission_classes = [EsAdmin]

    def get(self, request):
        return Response(
            {
                "detail": "Celery eliminado. El procesamiento ahora es síncrono.",
                "estado": "NO_ASYNC",
            }
        )


# ─────────────────────────────────────────────
# FUENTES
# ─────────────────────────────────────────────
class FuentesDisponiblesView(APIView):
    permission_classes = [EsAdmin]

    def get(self, request):
        fuentes = []

        for clave, info in FUENTES_INFO.items():
            fuentes.append(
                {
                    "value": clave,
                    "label": info["label"],
                    "descripcion": info["descripcion"],
                    "jerarquia": info["jerarquia"],
                    "esperados": info["esperados"],
                }
            )

        return Response({"fuentes": fuentes})