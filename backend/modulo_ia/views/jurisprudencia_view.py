import logging
import threading

import requests
from django.conf import settings
from django.db import connections
from django.db.models import Exists, OuterRef
from django.db.models.functions import Substr
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.permissions.roles_permission import EsOperativo
from modulo_catalogo.views.tareas_normativas_view import iniciar
from modulo_ia.models.jurisprudencia import ResolucionJurisprudencia, EmbeddingJurisprudencia
from modulo_ia.services.jurisprudencia_importacion import importar_resolucion, limpiar_contenido
from modulo_ia.services.model_loader import version_activa
from modulo_ia.services.tsj_api import TSJApi, BASE_URL

logger = logging.getLogger(__name__)
_incorporacion_lock = threading.Lock()


class ResolucionSerializer(serializers.ModelSerializer):
    indexada = serializers.BooleanField(read_only=True)
    extracto = serializers.CharField(read_only=True)

    class Meta:
        model = ResolucionJurisprudencia
        fields = ["id", "fuente_id", "numero", "expediente", "fecha", "materia", "sala",
                  "departamento", "url_fuente", "url_pdf", "indexada", "extracto", "updated_at"]
        read_only_fields = fields


class ResolucionDetalleSerializer(ResolucionSerializer):
    class Meta(ResolucionSerializer.Meta):
        fields = ResolucionSerializer.Meta.fields + ["texto"]
        read_only_fields = fields


class JurisprudenciaViewSet(ReadOnlyModelViewSet):
    permission_classes = [EsOperativo]
    filter_backends = [SearchFilter]
    search_fields = ["numero", "expediente", "texto"]

    def get_serializer_class(self):
        return ResolucionDetalleSerializer if self.action == "retrieve" else ResolucionSerializer

    def get_queryset(self):
        class Filtros(serializers.Serializer):
            desde = serializers.DateField(required=False)
            hasta = serializers.DateField(required=False)
            sala = serializers.CharField(max_length=255, required=False, allow_blank=True)
            departamento = serializers.CharField(max_length=150, required=False, allow_blank=True)
            indexada = serializers.BooleanField(required=False)

        filtros = Filtros(data=dict(self.request.query_params.items()))
        filtros.is_valid(raise_exception=True)
        valores = filtros.validated_data
        if valores.get("desde") and valores.get("hasta") and valores["desde"] > valores["hasta"]:
            raise serializers.ValidationError({"hasta": "La fecha final debe ser posterior a la inicial."})
        embeddings = EmbeddingJurisprudencia.objects.filter(
            fragmento__resolucion_id=OuterRef("pk"), modelo_version=version_activa(),
        )
        qs = ResolucionJurisprudencia.objects.filter(activa=True).annotate(
            indexada=Exists(embeddings), extracto=Substr("texto", 1, 240),
        ).order_by("-fecha", "-id")
        if self.action != "retrieve":
            qs = qs.defer("texto")
        for filtro, lookup in (("desde", "fecha__gte"), ("hasta", "fecha__lte"),
                               ("sala", "sala"), ("departamento", "departamento"), ("indexada", "indexada")):
            if filtro in valores and valores[filtro] != "":
                qs = qs.filter(**{lookup: valores[filtro]})
        return qs

    @action(detail=False, methods=["get"])
    def resumen(self, request):
        resoluciones = ResolucionJurisprudencia.objects.filter(activa=True)
        indexadas = EmbeddingJurisprudencia.objects.filter(
            fragmento__resolucion_id=OuterRef("pk"), modelo_version=version_activa(),
        )
        return Response({
            "resoluciones": resoluciones.count(),
            "indexadas": resoluciones.filter(Exists(indexadas)).count(),
            "embeddings": EmbeddingJurisprudencia.objects.filter(
                modelo_version=version_activa(), fragmento__resolucion__activa=True,
            ).count(),
            "salas": list(resoluciones.exclude(sala="").order_by("sala").values_list("sala", flat=True).distinct()),
            "departamentos": list(resoluciones.exclude(departamento="").order_by("departamento").values_list("departamento", flat=True).distinct()),
        })


class BuscarTSJView(APIView):
    permission_classes = [EsOperativo]

    def get(self, request):
        class Consulta(serializers.Serializer):
            palabras = serializers.CharField(max_length=150, default="penal")
            page = serializers.IntegerField(min_value=1, max_value=10000, default=1)
        consulta = Consulta(data=request.query_params)
        consulta.is_valid(raise_exception=True)
        api = None
        try:
            api = TSJApi()
            datos = api.buscar(consulta.validated_data["page"], consulta.validated_data["palabras"])
            fuentes = [str(fila["id"]) for fila in datos["data"]]
            guardadas = dict(ResolucionJurisprudencia.objects.filter(
                fuente_id__in=fuentes, activa=True,
            ).values_list("fuente_id", "id"))
            resultados = [{
                "fuente_id": str(fila["id"]), "numero": str(fila.get("nro_resolucion") or ""),
                "fecha": str(fila.get("fecha_emision") or ""),
                "sala": str(fila.get("sala") or ""),
                "extracto": limpiar_contenido(fila.get("resumen") or "")[:500],
                "url_fuente": f"{BASE_URL}/resoluciones/{fila['id']}",
                "registro_id": guardadas.get(str(fila["id"])),
            } for fila in datos["data"]]
            return Response({"results": resultados, "count": datos["meta"]["count"],
                             "page": datos["meta"]["page"], "total_pages": datos["meta"]["totalPages"]})
        except ValueError:
            return Response({"detail": "No se pudo consultar el TSJ. Revisa la configuración de acceso y vuelve a intentar."}, status=503)
        except (requests.RequestException, KeyError, TypeError):
            logger.warning("Fallo consultando el listado público del TSJ.", exc_info=False)
            return Response({"detail": "El buscador del TSJ no está disponible en este momento. Puedes consultar la jurisprudencia ya guardada."}, status=502)
        finally:
            if api:
                api.close()


class IncorporarTSJView(APIView):
    permission_classes = [EsOperativo]

    def post(self, request):
        class Seleccion(serializers.Serializer):
            fuente_id = serializers.RegexField(r"^\d{1,40}$")
        seleccion = Seleccion(data=request.data)
        seleccion.is_valid(raise_exception=True)
        fuente_id = seleccion.validated_data["fuente_id"]
        if not settings.TSJ_API_KEY:
            return Response({"detail": "El acceso a la API del TSJ no está configurado."}, status=503)

        def trabajo(progreso):
            api = TSJApi()
            try:
                progreso({"paso": "Consultando resolución en el TSJ"})
                datos = api.detalle(fuente_id)
                progreso({"paso": "Guardando resolución y generando embeddings"})
                estado = importar_resolucion(datos)
                registro = ResolucionJurisprudencia.objects.get(fuente_id=fuente_id)
                return {"registro_id": registro.pk, "fuente_id": fuente_id, "estado_importacion": estado}
            except requests.RequestException:
                raise RuntimeError("No se pudo descargar la resolución del TSJ. Intenta nuevamente.") from None
            finally:
                api.close()
                connections.close_all()
        if not _incorporacion_lock.acquire(blocking=False):
            return Response({"detail": "Ya hay una incorporación del TSJ en curso. Espera a que termine."}, status=409)
        try:
            task_id = iniciar(request.user, trabajo, _incorporacion_lock.release)
        except Exception:
            _incorporacion_lock.release()
            raise
        return Response({"task_id": task_id}, status=202)
