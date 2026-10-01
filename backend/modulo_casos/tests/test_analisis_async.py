"""
POST /api/casos/{id}/analizar/ ya no corre el pipeline dentro del propio
request: lo dispara en un hilo aparte (modulo_ia.services.analisis_background)
y responde al toque con 202. Estos tests cubren:

  - El endpoint: 202 + estado_analisis="procesando" al lanzar, 409 si ya
    había uno en curso (sin depender de que el pipeline real termine —
    se mockea el hilo de fondo para que no corra de verdad).
  - ejecutar_analisis_caso en sí: éxito (COMPLETADO + ResultadoCaso +
    auditoría con el usuario correcto) y falla (ERROR + auditoría con el
    mensaje, y que no tumbe el caller). El único paso mockeado es
    EmbeddingService.generar_para_caso, porque es el único que necesita
    el modelo real de Sentence Transformers (no instalado en este
    entorno de tests — ver el comentario en backend-tests.yml).
  - Caso.analisis_en_curso(): que un "procesando" viejo (más de
    ANALISIS_TIMEOUT_MINUTOS) se considere huérfano y no bloquee.
"""
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from modulo_auditoria.models.auditoria import Auditoria
from modulo_casos.models.caso import Caso, EstadoAnalisis
from modulo_casos.models.resultado_caso import ResultadoCaso
from modulo_clientes.models.cliente import Cliente
from modulo_ia.models.embedding import EmbeddingChunk
from modulo_ia.services.model_loader import version_activa
from modulo_ia.tasks.analisis_task import ejecutar_analisis_caso
from modulo_usuarios.tests.factories import crear_rol, crear_usuario

RUTA_EJECUTAR_EN_HILO = "modulo_ia.services.analisis_background._ejecutar_en_hilo"


class AnalizarEndpointAsyncTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.abogado = crear_usuario("abogado.analisis", rol=crear_rol("Abogado"))
        cls.cliente = Cliente.objects.create(nombres="Cliente", apellidos="Analisis")

    def setUp(self):
        self.caso = Caso.objects.create(
            codigo="CASO-ANALISIS-1", titulo="Caso", descripcion="Robo agravado con violencia.",
            usuario=self.abogado, cliente=self.cliente,
        )
        self.client.force_authenticate(self.abogado)
        self.url = f"/api/casos/{self.caso.pk}/analizar/"

    def test_lanzar_analisis_responde_202_y_marca_procesando(self):
        with patch(RUTA_EJECUTAR_EN_HILO):  # el pipeline real no corre en este test
            resp = self.client.post(self.url)

        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(resp.data["estado_analisis"], EstadoAnalisis.PROCESANDO)
        self.caso.refresh_from_db()
        self.assertEqual(self.caso.estado_analisis, EstadoAnalisis.PROCESANDO)
        self.assertIsNotNone(self.caso.analisis_iniciado_en)
        self.assertEqual(self.caso.analisis_iniciado_por_id, self.abogado.pk)

    def test_doble_clic_da_409_y_no_relanza(self):
        with patch(RUTA_EJECUTAR_EN_HILO):
            primero = self.client.post(self.url)
            segundo = self.client.post(self.url)

        self.assertEqual(primero.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(segundo.status_code, status.HTTP_409_CONFLICT)

    def test_se_puede_relanzar_despues_de_completado(self):
        with patch(RUTA_EJECUTAR_EN_HILO):
            self.client.post(self.url)

        Caso.objects.filter(pk=self.caso.pk).update(estado_analisis=EstadoAnalisis.COMPLETADO)

        with patch(RUTA_EJECUTAR_EN_HILO):
            resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)

    def test_se_puede_relanzar_despues_de_un_procesando_huerfano(self):
        with patch(RUTA_EJECUTAR_EN_HILO):
            self.client.post(self.url)

        # Simula que el hilo murió sin actualizar el estado (ej. reinicio
        # del servidor): sigue en "procesando" pero de hace rato.
        viejo = timezone.now() - timedelta(minutes=Caso.ANALISIS_TIMEOUT_MINUTOS + 1)
        Caso.objects.filter(pk=self.caso.pk).update(analisis_iniciado_en=viejo)

        with patch(RUTA_EJECUTAR_EN_HILO):
            resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)


class AnalisisEnCursoModelTests(APITestCase):

    def setUp(self):
        usuario = crear_usuario("modelo.analisis", rol=crear_rol("Abogado"))
        cliente = Cliente.objects.create(nombres="Cliente", apellidos="Modelo")
        self.caso = Caso.objects.create(
            codigo="CASO-ANALISIS-MODELO", titulo="Caso", descripcion="x",
            usuario=usuario, cliente=cliente,
        )

    def test_pendiente_no_esta_en_curso(self):
        self.assertFalse(self.caso.analisis_en_curso())

    def test_procesando_reciente_esta_en_curso(self):
        self.caso.estado_analisis = EstadoAnalisis.PROCESANDO
        self.caso.analisis_iniciado_en = timezone.now()
        self.assertTrue(self.caso.analisis_en_curso())

    def test_procesando_viejo_no_bloquea(self):
        self.caso.estado_analisis = EstadoAnalisis.PROCESANDO
        self.caso.analisis_iniciado_en = timezone.now() - timedelta(
            minutes=Caso.ANALISIS_TIMEOUT_MINUTOS + 1
        )
        self.assertFalse(self.caso.analisis_en_curso())

    def test_completado_no_esta_en_curso(self):
        self.caso.estado_analisis = EstadoAnalisis.COMPLETADO
        self.assertFalse(self.caso.analisis_en_curso())


def _generar_embeddings_falsos(chunks):
    """Reemplaza a EmbeddingService.generar_para_caso: crea EmbeddingChunk
    reales (con la versión activa) para que RankingService tenga algo
    válido que comparar, sin invocar el modelo real."""
    return [
        EmbeddingChunk.objects.create(
            chunk=chunk, modelo_version=version_activa(), vector=[0.1] * 768,
        )
        for chunk in chunks
    ]


class EjecutarAnalisisCasoTests(APITestCase):
    """
    ejecutar_analisis_caso corrido directo (sin el hilo de fondo), con
    EmbeddingService mockeado — es el único paso que necesita el modelo
    real de Sentence Transformers.
    """

    def setUp(self):
        self.dueño = crear_usuario("dueño.analisis", rol=crear_rol("Abogado"))
        self.otro = crear_usuario("otro.analisis", rol=crear_rol("Abogado"))
        cliente = Cliente.objects.create(nombres="Cliente", apellidos="Ejecutar")
        self.caso = Caso.objects.create(
            codigo="CASO-EJECUTAR-1", titulo="Caso", descripcion="Robo agravado con violencia.",
            usuario=self.dueño, cliente=cliente,
        )

    def test_exito_marca_completado_y_crea_resultado(self):
        with patch("modulo_ia.services.embedding_service.EmbeddingService.generar_para_caso",
                   side_effect=_generar_embeddings_falsos):
            resultado = ejecutar_analisis_caso(self.caso.pk, usuario=self.otro)

        self.caso.refresh_from_db()
        self.assertEqual(self.caso.estado_analisis, EstadoAnalisis.COMPLETADO)
        self.assertEqual(self.caso.analisis_paso, "completado")
        self.assertIsNotNone(self.caso.analisis_completado_en)
        self.assertIsNone(self.caso.analisis_error)
        self.assertTrue(ResultadoCaso.objects.filter(caso=self.caso).exists())
        self.assertEqual(resultado["caso_id"], self.caso.pk)

    def test_exito_audita_con_el_usuario_que_disparo_el_analisis(self):
        with patch("modulo_ia.services.embedding_service.EmbeddingService.generar_para_caso",
                   side_effect=_generar_embeddings_falsos):
            ejecutar_analisis_caso(self.caso.pk, usuario=self.otro)

        auditoria = Auditoria.objects.get(tabla="casos", accion="ANALYZE", registro_id=self.caso.pk)
        self.assertEqual(auditoria.usuario_id, self.otro.pk)  # no el dueño del caso, sino quien lo disparó

    def test_sin_usuario_explicito_audita_al_dueno_del_caso(self):
        with patch("modulo_ia.services.embedding_service.EmbeddingService.generar_para_caso",
                   side_effect=_generar_embeddings_falsos):
            ejecutar_analisis_caso(self.caso.pk, usuario=None)

        auditoria = Auditoria.objects.get(tabla="casos", accion="ANALYZE", registro_id=self.caso.pk)
        self.assertEqual(auditoria.usuario_id, self.dueño.pk)

    def test_falla_marca_error_y_no_relanza_la_excepcion(self):
        with patch(
            "modulo_ia.services.embedding_service.EmbeddingService.generar_para_caso",
            side_effect=RuntimeError("falla simulada del modelo"),
        ):
            resultado = ejecutar_analisis_caso(self.caso.pk, usuario=self.dueño)  # no debe lanzar

        self.caso.refresh_from_db()
        self.assertEqual(self.caso.estado_analisis, EstadoAnalisis.ERROR)
        self.assertIn("falla simulada", self.caso.analisis_error)
        self.assertIn("error", resultado)

    def test_falla_tambien_audita(self):
        with patch(
            "modulo_ia.services.embedding_service.EmbeddingService.generar_para_caso",
            side_effect=RuntimeError("falla simulada"),
        ):
            ejecutar_analisis_caso(self.caso.pk, usuario=self.dueño)

        auditoria = Auditoria.objects.get(tabla="casos", accion="ANALYZE", registro_id=self.caso.pk)
        self.assertIn("falla simulada", auditoria.metadata.get("error", ""))

    def test_falla_no_deja_chunks_del_intento_a_medias(self):
        # La falla ocurre DESPUÉS del chunking (en embeddings), pero como
        # todo el paso de escritura corre en una transacción, el chunk que
        # sí se llegó a crear no debería quedar huérfano en la base.
        with patch(
            "modulo_ia.services.embedding_service.EmbeddingService.generar_para_caso",
            side_effect=RuntimeError("falla simulada"),
        ):
            ejecutar_analisis_caso(self.caso.pk, usuario=self.dueño)

        self.assertEqual(self.caso.chunks.count(), 0)
