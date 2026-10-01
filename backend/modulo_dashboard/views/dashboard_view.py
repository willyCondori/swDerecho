# modulo_dashboard/views/dashboard_view.py
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions.roles import ve_todo
from core.permissions.roles_permission import EsOperativo
from modulo_casos.models.caso import Caso, EstadoAnalisis
from modulo_casos.models.etapas import EtapaCaso
from modulo_catalogo.models.articulo import Articulo
from modulo_catalogo.models.norma import Norma
from modulo_clientes.models.cliente import Cliente
from modulo_usuarios.models.usuario import Usuario

MESES_TENDENCIA = 6
TOP_NORMAS = 10


class DashboardResumenView(APIView):
    """
    GET /api/dashboard/resumen/

    Panorama general para la pantalla de inicio: cuántos casos hay y en
    qué etapa, cómo se reparte el trabajo, y qué tan atascado está el
    pipeline de IA. No crea ninguna tabla nueva — todo sale de agregar
    lo que ya existe en Caso, Cliente, Norma y Articulo.

    Visibilidad (mismo criterio que el resto de endpoints operativos,
    ver core.permissions.roles.ve_todo):
      - Administrador / Abogado: panorama completo del bufete, incluida
        la carga de trabajo por abogado y las normas más citadas en los
        análisis de TODOS los casos.
      - Asistente: solo los agregados de sus propios casos. No ve carga
        de trabajo de otros abogados ni las normas más consultadas,
        porque esas dos vistas cruzan datos de casos que no son suyos.
    """
    permission_classes = [EsOperativo]

    def get(self, request):
        usuario = request.user
        visibilidad_total = ve_todo(usuario)

        casos_qs = Caso.objects.filter(estado=True)
        papelera_qs = Caso.objects.filter(estado=False)
        if not visibilidad_total:
            casos_qs = casos_qs.filter(usuario=usuario)
            papelera_qs = papelera_qs.filter(usuario=usuario)

        totales = {
            "casos_activos": casos_qs.count(),
            "casos_en_papelera": papelera_qs.count(),
        }

        casos_por_etapa_raw = dict(
            casos_qs.values_list("etapa").annotate(cantidad=Count("id"))
        )
        casos_por_etapa = [
            {
                "etapa": etapa,
                "etapa_nombre": nombre,
                "cantidad": casos_por_etapa_raw.get(etapa, 0),
            }
            for etapa, nombre in EtapaCaso.choices
        ]

        casos_por_rama = [
            {"rama": fila["rama_detectada__nombre"], "cantidad": fila["cantidad"]}
            for fila in (
                casos_qs.exclude(rama_detectada__isnull=True)
                .values("rama_detectada__nombre")
                .annotate(cantidad=Count("id"))
                .order_by("-cantidad")
            )
        ]

        estado_analisis_raw = dict(
            casos_qs.values_list("estado_analisis").annotate(cantidad=Count("id"))
        )
        estado_analisis = [
            {
                "estado": estado,
                "estado_nombre": nombre,
                "cantidad": estado_analisis_raw.get(estado, 0),
            }
            for estado, nombre in EstadoAnalisis.choices
        ]

        data = {
            "totales": totales,
            "casos_por_etapa": casos_por_etapa,
            "casos_por_rama": casos_por_rama,
            "estado_analisis": estado_analisis,
            "casos_por_usuario": [],
            "casos_por_mes": [],
            "normas_mas_consultadas": [],
        }

        if visibilidad_total:
            data["casos_por_usuario"] = [
                {"usuario": fila["usuario__usuario"], "cantidad": fila["cantidad"]}
                for fila in (
                    Caso.objects.filter(estado=True)
                    .values("usuario__usuario")
                    .annotate(cantidad=Count("id"))
                    .order_by("-cantidad")
                )
            ]

            totales["clientes_activos"] = Cliente.objects.filter(estado=True).count()
            totales["normas_activas"] = Norma.objects.filter(estado=True).count()
            totales["usuarios_activos"] = Usuario.objects.filter(estado=True).count()

            desde = (timezone.now() - timedelta(days=30 * MESES_TENDENCIA)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            data["casos_por_mes"] = [
                {"mes": fila["mes"].strftime("%Y-%m"), "cantidad": fila["cantidad"]}
                for fila in (
                    Caso.objects.filter(estado=True, created_at__gte=desde)
                    .annotate(mes=TruncMonth("created_at"))
                    .values("mes")
                    .annotate(cantidad=Count("id"))
                    .order_by("mes")
                )
            ]

            # frecuencia_historica se incrementa en el pipeline de ranking
            # cada vez que un artículo queda seleccionado en el resultado
            # de un caso (ver modulo_ia/models/resultado.py) — ya es,
            # literalmente, el contador de "artículo más consultado" sin
            # necesidad de otra tabla.
            data["normas_mas_consultadas"] = [
                {
                    "articulo_id": art.id,
                    "numero_articulo": art.numero_articulo,
                    "norma": art.norma.nombre,
                    "frecuencia": art.frecuencia_historica,
                }
                for art in (
                    Articulo.objects.filter(estado=True, frecuencia_historica__gt=0)
                    .select_related("norma")
                    .order_by("-frecuencia_historica")[:TOP_NORMAS]
                )
            ]

        return Response(data)
