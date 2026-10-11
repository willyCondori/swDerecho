from core.throttling import ANALYSIS_THROTTLES
from core.permissions.casos import casos_visibles
from core.public_ids import VistaIdentificadorPublicoMixin, filtrar_uuid
from django.db import transaction
from django.db.models import F
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.permissions.auditoria_mixin import AuditoriaMixin
from core.permissions.roles_permission import EsAbogado, EsOperativo
from modulo_casos.models.caso import Caso
from modulo_casos.models.etapas import EtapaCaso
from modulo_casos.models.hecho import Hecho
from modulo_casos.models.petitorio import Petitorio
from modulo_casos.serializers.caso_con_cliente_serializer import CasoConClienteSerializer
from modulo_casos.serializers.caso_serializer import (
    CasoCreateSerializer,
    CasoListSerializer,
    CasoPapeleraSerializer,
    CasoReadSerializer,
    CasoUpdateSerializer,
    HechoSerializer,
    PetitorioSerializer,
    ResultadoCasoSerializer,
)
from modulo_casos.serializers.seguimiento_serializer import (
    CambiarEtapaSerializer,
    SeguimientoCasoSerializer,
)
from modulo_casos.services.papelera_service import (
    ClienteInactivoError,
    enviar_a_papelera,
    restaurar_desde_papelera,
)
from modulo_casos.services.seguimiento_service import registrar_seguimiento
from modulo_casos.services.listado_service import preparar_listado_casos

class CasoViewSet(VistaIdentificadorPublicoMixin, AuditoriaMixin, ModelViewSet):
    """
    GET    /api/casos/                    — lista con filtros [todos los roles ven todos los casos activos]
    POST   /api/casos/                    — crear caso (texto o PDF), cliente ya existente [admin, abogado]
    POST   /api/casos/crear_con_cliente/  — crea cliente + caso en una transacción atómica [admin, abogado]
    GET    /api/casos/{id}/               — detalle completo
    PATCH  /api/casos/{id}/               — editar título/descripción/estado [admin, abogado]
    DELETE /api/casos/{id}/               — envía el caso a la papelera (soft-delete) [admin, abogado]
    GET    /api/casos/papelera/           — casos eliminados, más recientes primero [admin, abogado]
    POST   /api/casos/{id}/restaurar/     — restaura un caso de la papelera [admin, abogado]
    POST   /api/casos/{id}/subir_pdf/     — adjuntar PDF al caso [admin, abogado]
    GET    /api/casos/{id}/hechos/        — lista hechos del caso
    GET    /api/casos/{id}/petitorios/    — lista petitorios del caso
    GET    /api/casos/{id}/resultado/     — resultado IA del caso
    GET    /api/casos/{id}/articulos/     — artículos del ranking
    POST   /api/casos/{id}/analizar/      — disparar pipeline IA [admin, abogado]
    GET    /api/casos/mis_casos/          — casos del usuario autenticado (filtro de conveniencia)
    GET    /api/casos/etapas/             — catálogo de etapas de seguimiento (value, label)
    GET    /api/casos/{id}/seguimiento/   — línea de tiempo del caso (más reciente primero)
    POST   /api/casos/{id}/cambiar_etapa/ — cambia la etapa y/o agrega una nota al historial [admin, abogado]

    Filtro extra en el listado: ?etapa=<value> (ver GET /api/casos/etapas/).

    Permisos (ver core.permissions.roles_permission.EsOperativo):
    Administrador, Abogado y Asistente ven todos los casos activos.
    Administrador y Abogado tienen acceso total, incluyendo eliminar
    (soft-delete) de forma lógica. Asistente solo puede leer (GET).
    """
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields   = ["codigo", "titulo", "descripcion"]
    ordering_fields = ["created_at", "codigo", "titulo"]
    auditoria_tabla = "casos"

    def get_queryset(self):
        if self.action in ("papelera", "restaurar"):
            # Papelera: solo casos eliminados. El resto de las acciones
            # nunca ve casos con estado=False (404).
            return (
                Caso.objects
                .filter(estado=False)
                .select_related(
                    "usuario", "cliente", "rama_detectada",
                    "eliminado_por", "eliminado_por__perfil",
                )
            )

        qs = (
            Caso.objects
            .filter(estado=True)
            .order_by("-created_at")
        )
        if self.action == 'list':
            qs = preparar_listado_casos(qs)
        else:
            qs = qs.select_related('usuario', 'cliente', 'rama_detectada').prefetch_related(
                'documentos', 'documentos_generados',
            )
        qs = casos_visibles(qs, self.request.user)
        # Todos los roles (Administrador, Abogado, Asistente) ven todos
        # los casos activos. La restricción de "solo lectura" para
        # Asistente ya la resuelve EsOperativo a nivel de método HTTP
        # (ver get_permissions()); acá no hace falta filtrar por dueño.

        # --- filtros opcionales via query params ---
        rama_id     = self.request.query_params.get("rama_id")
        cliente_id  = self.request.query_params.get("cliente_id")
        fecha_desde = self.request.query_params.get("fecha_desde")
        fecha_hasta = self.request.query_params.get("fecha_hasta")
        tiene_pdf   = self.request.query_params.get("tiene_pdf")
        etapa       = self.request.query_params.get("etapa")

        if etapa:
            qs = qs.filter(etapa=etapa)
        if rama_id:
            qs = qs.filter(rama_detectada_id=rama_id)
        if cliente_id:
            qs = filtrar_uuid(qs, "cliente__public_id", cliente_id)
        if fecha_desde:
            qs = qs.filter(created_at__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(created_at__date__lte=fecha_hasta)
        if tiene_pdf is not None:
            con_pdf = tiene_pdf.lower() in ['true', '1']
            if self.action == 'list':
                qs = qs.filter(tiene_documento=con_pdf)
            elif con_pdf:
                qs = qs.filter(documentos__tipo_archivo="pdf")
            else:
                qs = qs.exclude(documentos__tipo_archivo="pdf")

        return qs if self.action == 'list' else qs.distinct()

    def get_serializer_class(self):
        if self.action == "create":
            return CasoCreateSerializer
        if self.action in ["update", "partial_update"]:
            return CasoUpdateSerializer
        if self.action == "list":
            return CasoListSerializer
        return CasoReadSerializer

    def get_permissions(self):
        if self.action in ("papelera", "restaurar"):
            # Administrador y Abogado; el Asistente no ve la papelera.
            return [EsAbogado()]
        return [EsOperativo()]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        POST /api/casos/
        Crea un caso para un cliente que YA existe (cliente_id requerido).
        Acepta opcionalmente un archivo PDF junto al texto.
        """
        tiene_pdf  = "archivo_pdf" in request.FILES
        serializer = self.get_serializer(
            data=request.data,
            context={**self.get_serializer_context(), "tiene_pdf": tiene_pdf},
        )
        serializer.is_valid(raise_exception=True)

        caso = serializer.save()

        if tiene_pdf:
            self._guardar_pdf(request, caso)

        self._auditar("CREATE", registro_id=caso.pk)

        return Response(
            CasoReadSerializer(caso, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="crear_con_cliente")
    @transaction.atomic
    def crear_con_cliente(self, request):
        """
        POST /api/casos/crear_con_cliente/
        Crea el cliente y el caso en una sola operación atómica: si el
        caso falla al crearse, el cliente recién insertado se revierte
        también (ver CasoConClienteSerializer).

        Body: nombres, apellidos, telefono (opcional),
              titulo, descripcion, rama_detectada_id,
              archivo_pdf (opcional, multipart).
        """
        tiene_pdf  = "archivo_pdf" in request.FILES
        serializer = CasoConClienteSerializer(
            data=request.data,
            context={**self.get_serializer_context(), "tiene_pdf": tiene_pdf},
        )
        serializer.is_valid(raise_exception=True)
        resultado = serializer.save()
        caso = resultado["caso"]

        # El PDF forma parte de la creación: si se rechaza o falla su
        # guardado, se revierten también el cliente y el caso. Las
        # notificaciones on_commit se envían solo al confirmar todo.
        if tiene_pdf:
            self._guardar_pdf(request, caso)

        self._auditar("CREATE", registro_id=caso.pk, metadata={"cliente_id": resultado["cliente"].pk})

        return Response(
            CasoReadSerializer(caso, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    def _guardar_pdf(self, request, caso):
        from modulo_documentos.models.documento import TipoDoc
        from modulo_documentos.serializers.documento_serializer import DocumentoCasoWriteSerializer

        tipo, _ = TipoDoc.objects.get_or_create(tipo="caso_pdf")
        doc_ser = DocumentoCasoWriteSerializer(
            data={
                "caso"          : str(caso.public_id),
                "archivo"       : request.FILES["archivo_pdf"],
                "tipo_documento": tipo.pk,
            },
            context={"request": request},
        )
        doc_ser.is_valid(raise_exception=True)
        doc_ser.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        enviar_a_papelera(instance, request.user)
        self._auditar("DELETE", registro_id=instance.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------
    # Acciones extra
    # ------------------------------------------------------------------

    @action(detail=False, methods=["get"], url_path="mis_casos")
    def mis_casos(self, request):
        """GET /api/casos/mis_casos/ — casos del usuario autenticado."""
        qs = preparar_listado_casos(
            Caso.objects.filter(usuario=request.user, estado=True).order_by('-created_at')
        )
        page       = self.paginate_queryset(qs)
        serializer = CasoListSerializer(
            page if page is not None else qs, many=True, context=self.get_serializer_context()
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="papelera")
    def papelera(self, request):
        """
        GET /api/casos/papelera/ — casos eliminados, los enviados más
        recientemente primero (los eliminados antes de la papelera, sin
        fecha, al final). Acepta ?search= (código, título, descripción).
        """
        qs = self.get_queryset().order_by(
            F("eliminado_at").desc(nulls_last=True), "-created_at"
        )
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        serializer = CasoPapeleraSerializer(
            page if page is not None else qs, many=True,
            context=self.get_serializer_context(),
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="restaurar")
    def restaurar(self, request, pk=None):
        """
        POST /api/casos/{id}/restaurar/ — devuelve el caso a la lista de
        casos activos. Responde 409 si su cliente fue eliminado.
        """
        caso = self.get_object()
        try:
            restaurar_desde_papelera(caso, request.user)
        except ClienteInactivoError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)

        self._auditar("UPDATE", registro_id=caso.pk, metadata={"accion": "restaurar"})
        return Response(
            CasoReadSerializer(caso, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="etapas")
    def etapas(self, request):
        """GET /api/casos/etapas/ — etapas disponibles, en orden cronológico."""
        return Response([
            {"value": valor, "label": etiqueta, "orden": orden}
            for orden, (valor, etiqueta) in enumerate(EtapaCaso.choices, start=1)
        ])

    @action(detail=True, methods=["get"], url_path="seguimiento")
    def seguimiento(self, request, pk=None):
        """GET /api/casos/{id}/seguimiento/ — línea de tiempo, más reciente primero."""
        caso = self.get_object()
        entradas = (
            caso.seguimientos
            .select_related("usuario", "usuario__perfil")
            .order_by("-created_at", "-id")
        )
        return Response(
            SeguimientoCasoSerializer(entradas, many=True, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=["post"], url_path="cambiar_etapa")
    def cambiar_etapa(self, request, pk=None):
        """
        POST /api/casos/{id}/cambiar_etapa/
        Body: etapa (obligatoria), nota (opcional, máx. 2000 caracteres).

        Crea una entrada en el historial y actualiza la etapa actual del
        caso. Si 'etapa' es la que ya tiene, solo se acepta con nota
        (actualización de seguimiento sin cambio de etapa).
        """
        caso = self.get_object()
        serializer = CambiarEtapaSerializer(
            data=request.data,
            context={**self.get_serializer_context(), "caso": caso},
        )
        serializer.is_valid(raise_exception=True)

        etapa_anterior = caso.etapa
        seguimiento = registrar_seguimiento(
            caso,
            etapa=serializer.validated_data["etapa"],
            usuario=request.user,
            nota=serializer.validated_data["nota"],
        )
        self._auditar(
            "UPDATE",
            registro_id=caso.pk,
            metadata={
                "accion": "cambiar_etapa",
                "etapa_anterior": etapa_anterior,
                "etapa_nueva": seguimiento.etapa,
                "seguimiento_id": seguimiento.pk,
            },
        )
        return Response(
            {
                "etapa": caso.etapa,
                "etapa_display": caso.get_etapa_display(),
                "etapa_actualizada_at": caso.etapa_actualizada_at,
                "seguimiento": SeguimientoCasoSerializer(
                    seguimiento, context=self.get_serializer_context()
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="subir_pdf")
    def subir_pdf(self, request, pk=None):
        """POST /api/casos/{id}/subir_pdf/ — adjunta o reemplaza el PDF del caso."""
        caso = self.get_object()
        if "archivo_pdf" not in request.FILES:
            return Response(
                {"detail": "Debe adjuntar un archivo PDF en el campo 'archivo_pdf'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self._guardar_pdf(request, caso)
        self._auditar("UPDATE", registro_id=caso.pk, metadata={"accion": "subir_pdf"})
        return Response(
            {"detail": "PDF adjuntado correctamente."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="hechos")
    def hechos(self, request, pk=None):
        """GET /api/casos/{id}/hechos/"""
        caso   = self.get_object()
        hechos = Hecho.objects.filter(casos_hecho__caso=caso).order_by("casos_hecho__orden")
        return Response(HechoSerializer(hechos, many=True).data)

    @action(detail=True, methods=["get"], url_path="petitorios")
    def petitorios(self, request, pk=None):
        """GET /api/casos/{id}/petitorios/"""
        caso       = self.get_object()
        petitorios = Petitorio.objects.filter(casos_petitorio__caso=caso)
        return Response(PetitorioSerializer(petitorios, many=True).data)

    @action(detail=True, methods=["get"], url_path="resultado")
    def resultado(self, request, pk=None):
        """GET /api/casos/{id}/resultado/ — resultado IA (resumen, fortalezas, etc.)."""
        caso = self.get_object()
        if not hasattr(caso, "resultado"):
            return Response(
                {"detail": "Este caso aún no tiene resultados de análisis IA."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            ResultadoCasoSerializer(caso.resultado).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="articulos")
    def articulos(self, request, pk=None):
        """GET /api/casos/{id}/articulos/ — ranking de artículos aplicables."""
        from modulo_ia.models.resultado import ResultadoArticulo

        caso       = self.get_object()
        resultados = (
            ResultadoArticulo.objects
            .filter(caso=caso)
            .select_related("articulo", "articulo__norma", "articulo__rama")
            .order_by("posicion")
        )
        from modulo_ia.services.valoracion_service import articulos_con_seleccion
        resultados = list(resultados)
        return Response(articulos_con_seleccion(caso, resultados))

    @action(detail=True, methods=["post"], url_path="valorar_articulo")
    @transaction.atomic
    def valorar_articulo(self, request, pk=None):
        from rest_framework import serializers
        from modulo_ia.models.resultado import ResultadoArticulo
        from modulo_ia.services.valoracion_service import registrar
        caso = self.get_object()
        # Serializa con el inicio del análisis, que también bloquea el caso.
        caso = Caso.objects.select_for_update().get(pk=caso.pk)
        if caso.estado_analisis == "procesando":
            return Response({"detail": "Espera a que termine el análisis para valorar los artículos."}, status=409)
        class Entrada(serializers.Serializer):
            resultado_id = serializers.IntegerField(min_value=1, required=False)
            valoracion_id = serializers.IntegerField(min_value=1, required=False)
            valor = serializers.ChoiceField(choices=["util", "no_util", "sin_valorar"])

            def validate(self, attrs):
                if ('resultado_id' in attrs) == ('valoracion_id' in attrs):
                    raise serializers.ValidationError('Indica un resultado o una selección histórica.')
                return attrs
        entrada = Entrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        valor = entrada.validated_data['valor']
        from modulo_ia.services.valoracion_service import contexto_caso
        contexto_actual = contexto_caso(caso)
        historica = entrada.validated_data.get('valoracion_id')
        if historica:
            from types import SimpleNamespace
            from modulo_ia.models.valoracion import ValoracionArticulo
            decision = ValoracionArticulo.objects.select_related('articulo__norma').filter(
                caso=caso, pk=historica).first()
            if decision and ValoracionArticulo.objects.filter(caso=caso, articulo=decision.articulo,
                                                             id__gt=decision.pk).exists():
                decision = None
            resultado = None if decision is None else SimpleNamespace(
                id=f'valoracion-{decision.pk}', articulo=decision.articulo, articulo_id=decision.articulo_id,
                contexto_evaluado={k: decision.muestra.get(k, [] if k == 'fragmentos' else '')
                                   for k in ['descripcion', 'fragmentos']},
                modelo_version=decision.modelo_version, posicion=decision.muestra.get('posicion', 1),
                score_total=decision.muestra.get('score_total', '0'),
                es_sugerencia=decision.muestra.get('es_sugerencia', False))
            if resultado and valor == 'util' and caso.estado_analisis == 'completado':
                resultado.contexto_evaluado = contexto_actual
        else:
            resultado = ResultadoArticulo.objects.select_related("articulo__norma").filter(
                caso=caso, pk=entrada.validated_data["resultado_id"]
            ).first()
        if resultado is None:
            return Response({"detail": "El artículo ya no pertenece al resultado actual. Actualiza el caso."}, status=404)
        if valor == 'util' and (not resultado.contexto_evaluado or resultado.contexto_evaluado != contexto_actual):
            return Response({"detail": "Vuelve a analizar el caso antes de valorar: el resultado no corresponde al texto actual."}, status=409)
        registro = registrar(caso, resultado, request.user, valor)
        self._auditar("UPDATE", registro_id=caso.pk, metadata={
            "accion": "valorar_articulo", "articulo_id": resultado.articulo_id,
            "valor": valor, "valoracion_id": registro.id,
        })
        from modulo_ia.services.valoracion_service import valoracion_desactualizada
        return Response({"resultado_id": resultado.id, "valoracion": valor,
                         "valoracion_id": registro.id,
                         "valoracion_desactualizada": valor == 'util' and valoracion_desactualizada(registro, contexto_actual, resultado.articulo)})

    @action(detail=True, methods=["get"], url_path="jurisprudencia")
    def jurisprudencia(self, request, pk=None):
        from modulo_ia.models.jurisprudencia import ResultadoJurisprudencia
        from modulo_ia.services.valoracion_jurisprudencia_service import con_seleccion
        from modulo_ia.services.model_loader import version_activa

        caso = self.get_object()
        resultado = getattr(caso, "resultado", None)
        resultados = ResultadoJurisprudencia.objects.filter(caso=caso).select_related("resolucion")
        return Response({
            "estado": resultado.jurisprudencia_estado if resultado else "pendiente",
            "modelo_version": resultado.jurisprudencia_modelo_version if resultado else "",
            "desactualizada": bool(resultado and (
                caso.estado_analisis != "completado" or
                resultado.jurisprudencia_modelo_version != version_activa()
            )),
            "resultados": con_seleccion(caso, list(resultados)),
        })

    @action(detail=True, methods=["post"], url_path="valorar_jurisprudencia")
    @transaction.atomic
    def valorar_jurisprudencia(self, request, pk=None):
        from types import SimpleNamespace
        from rest_framework import serializers
        from modulo_ia.models.jurisprudencia import ResultadoJurisprudencia
        from modulo_ia.models.valoracion import ValoracionJurisprudencia
        from modulo_ia.services.valoracion_service import contexto_caso
        from modulo_ia.services.valoracion_jurisprudencia_service import registrar
        caso = self.get_object()
        caso = Caso.objects.select_for_update().get(pk=caso.pk)
        if caso.estado_analisis == 'procesando':
            return Response({'detail': 'Espera a que termine el análisis para valorar la jurisprudencia.'}, status=409)

        class Entrada(serializers.Serializer):
            resultado_id = serializers.IntegerField(min_value=1, required=False)
            valoracion_id = serializers.IntegerField(min_value=1, required=False)
            valor = serializers.ChoiceField(choices=['util', 'no_util', 'sin_valorar'])

            def validate(self, attrs):
                if ('resultado_id' in attrs) == ('valoracion_id' in attrs):
                    raise serializers.ValidationError('Indica un resultado o una selección histórica.')
                return attrs

        entrada = Entrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        valor = entrada.validated_data['valor']
        actual = contexto_caso(caso)
        historica = entrada.validated_data.get('valoracion_id')
        resultado = None
        if historica:
            decision = ValoracionJurisprudencia.objects.select_related('resolucion').filter(caso=caso, pk=historica).first()
            if decision and not ValoracionJurisprudencia.objects.filter(caso=caso,
                    resolucion=decision.resolucion, id__gt=decision.pk).exists():
                contexto = {k: decision.muestra[k] for k in ['descripcion', 'fragmentos']}
                resultado = SimpleNamespace(**decision.muestra['resultado'], resolucion=decision.resolucion,
                    resolucion_id=decision.resolucion_id, huella_fuente=decision.muestra['huella_fuente'],
                    contexto_evaluado=actual if valor == 'util' else contexto)
        else:
            resultado = ResultadoJurisprudencia.objects.select_related('resolucion').filter(
                caso=caso, pk=entrada.validated_data['resultado_id']).first()
        if resultado is None:
            return Response({'detail': 'La resolución ya no pertenece al resultado actual. Actualiza el caso.'}, status=404)
        contexto = resultado.contexto_evaluado or actual  # Resultados previos a la migración.
        if valor == 'util' and (caso.estado_analisis != 'completado' or contexto != actual
                or not resultado.resolucion.activa or resultado.huella_fuente != resultado.resolucion.huella):
            return Response({'detail': 'Vuelve a analizar el caso antes de confirmar la utilidad para el contexto actual.'}, status=409)
        registro = registrar(caso, resultado, request.user, valor, contexto)
        self._auditar('UPDATE', registro_id=caso.pk, metadata={'accion': 'valorar_jurisprudencia',
            'resolucion_id': resultado.resolucion_id, 'valor': valor, 'valoracion_id': registro.pk})
        return Response({'valoracion': valor, 'valoracion_id': registro.pk})

    @action(detail=True, methods=["get"], url_path="estado_analisis")
    def estado_analisis(self, request, pk=None):
        from django.shortcuts import get_object_or_404
        # Mantiene el filtro de acceso de la vista; evita descifrar cliente,
        # cargar documentos y serializar el resultado en cada consulta.
        caso = get_object_or_404(self.get_queryset().only(
            'public_id', 'estado_analisis', 'analisis_paso', 'analisis_error',
            'analisis_iniciado_en', 'analisis_completado_en',
            'usuario_id', 'cliente_id', 'rama_detectada_id',
        ).prefetch_related(None).select_related(None), public_id=pk)
        return Response({
            'id': str(caso.public_id), 'estado_analisis': caso.estado_analisis,
            'analisis_paso': caso.analisis_paso, 'analisis_error': caso.analisis_error,
            'analisis_iniciado_en': caso.analisis_iniciado_en,
            'analisis_completado_en': caso.analisis_completado_en,
        })

    @action(detail=True, methods=["post"], url_path="analizar", throttle_classes=ANALYSIS_THROTTLES)
    def analizar(self, request, pk=None):
        """
        POST /api/casos/{id}/analizar/
        Lanza el pipeline IA completo (chunking → embeddings → entidades →
        ranking → resultado) en segundo plano y devuelve al toque. El
        avance se consulta con GET /api/casos/{id}/ (campos
        estado_analisis/analisis_paso) o con GET .../seguimiento/ para el
        historial — no bloquea el request como antes.

        409 si ya hay un análisis en curso para este caso (ver
        Caso.analisis_en_curso): evita que un doble clic dispare dos
        corridas en paralelo sobre los mismos chunks/ranking.
        """
        from modulo_ia.serializers.ia_serializer import AnalisisCasoSerializer
        from modulo_ia.services.analisis_background import iniciar_analisis

        caso       = self.get_object()
        serializer = AnalisisCasoSerializer(data={"caso_id": str(caso.public_id)})
        serializer.is_valid(raise_exception=True)

        ok, detalle = iniciar_analisis(caso, request.user)
        if not ok:
            return Response({"detail": detalle}, status=status.HTTP_409_CONFLICT)

        caso.refresh_from_db(fields=["estado_analisis", "analisis_paso"])
        return Response(
            {
                "detail"        : "Análisis iniciado.",
                "caso_id"       : str(caso.public_id),
                "estado_analisis": caso.estado_analisis,
            },
            status=status.HTTP_202_ACCEPTED,
        )
