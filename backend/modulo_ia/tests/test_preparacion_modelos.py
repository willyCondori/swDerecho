import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from modulo_ia.services import model_loader, preparacion_modelos
from modulo_catalogo.services.ollama_normativo import precargar_modelo


@override_settings(SENTENCE_TRANSFORMER_MODEL='modelo-prueba', EMBEDDING_DEVICE='cpu')
class ModeloCompartidoTests(SimpleTestCase):
    def setUp(self):
        self.cache = patch.object(model_loader, '_modelo_cache', {})
        self.cache.start()
        self.addCleanup(self.cache.stop)

    def test_primeras_llamadas_concurrentes_cargan_una_sola_instancia(self):
        barrera = threading.Barrier(4)
        constructor = Mock(return_value=object())
        def obtener():
            barrera.wait(timeout=5)
            return model_loader.obtener_modelo()
        with patch.dict(sys.modules, {'sentence_transformers': SimpleNamespace(SentenceTransformer=constructor)}):
            with ThreadPoolExecutor(max_workers=4) as executor:
                modelos = list(executor.map(lambda _: obtener(), range(4)))
        constructor.assert_called_once_with('modelo-prueba', device='cpu')
        self.assertTrue(all(m is modelos[0] for m in modelos))

    def test_cambio_dispositivo_no_reutiliza_instancia_incorrecta(self):
        constructor = Mock(side_effect=[object(), object()])
        with patch.dict(sys.modules, {'sentence_transformers': SimpleNamespace(SentenceTransformer=constructor)}):
            cpu = model_loader.obtener_modelo()
            with override_settings(EMBEDDING_DEVICE='cuda'):
                gpu = model_loader.obtener_modelo()
            self.assertIs(model_loader.obtener_modelo(), cpu)
        self.assertIsNot(cpu, gpu)
        self.assertEqual(constructor.call_count, 2)


@override_settings(EMBEDDING_PRELOAD_STARTUP=True, OLLAMA_NORMATIVO_PRELOAD_STARTUP=True)
class PreparacionServidorTests(SimpleTestCase):
    def setUp(self):
        self.cache = patch.object(preparacion_modelos, '_preparados', set())
        self.cache.start()
        self.addCleanup(self.cache.stop)

    def test_calienta_encode_y_qwen_una_sola_vez(self):
        with patch.object(preparacion_modelos, 'obtener_modelo') as obtener, patch.object(
            preparacion_modelos, 'vectorizar_textos'
        ) as vectorizar, patch.object(preparacion_modelos, 'precargar_modelo') as qwen:
            preparacion_modelos.preparar_modelos_servidor()
            preparacion_modelos.preparar_modelos_servidor()
        obtener.assert_called_once()
        vectorizar.assert_called_once()
        self.assertIs(vectorizar.call_args.args[1], obtener.return_value)
        qwen.assert_called_once()

    @override_settings(EMBEDDING_PRELOAD_STARTUP=False, OLLAMA_NORMATIVO_PRELOAD_STARTUP=False)
    def test_instalacion_sin_precarga_no_llama_modelos(self):
        with patch.object(preparacion_modelos, 'obtener_modelo') as obtener, patch.object(
            preparacion_modelos, 'precargar_modelo'
        ) as qwen:
            preparacion_modelos.preparar_modelos_servidor()
        obtener.assert_not_called()
        qwen.assert_not_called()

    def test_carga_fallida_no_se_marca_lista_y_permite_reintento(self):
        with patch.object(preparacion_modelos, 'obtener_modelo'), patch.object(
            preparacion_modelos, 'vectorizar_textos'
        ), patch.object(preparacion_modelos, 'precargar_modelo', side_effect=[RuntimeError('Ollama apagado'), None]) as qwen:
            with self.assertRaisesRegex(RuntimeError, 'Ollama apagado'):
                preparacion_modelos.preparar_modelos_servidor()
            self.assertNotIn('qwen', preparacion_modelos._preparados)
            preparacion_modelos.preparar_modelos_servidor()
        self.assertEqual(qwen.call_count, 2)


class PrecargaOllamaTests(SimpleTestCase):
    @override_settings(OLLAMA_NORMATIVO_URL='http://localhost:11434/', OLLAMA_NORMATIVO_MODELO='qwen3.5:2b',
                       OLLAMA_NORMATIVO_KEEP_ALIVE='-1', OLLAMA_NORMATIVO_CONTEXTO=4096,
                       OLLAMA_NORMATIVO_TIMEOUT=180)
    def test_carga_sin_generar_texto_con_contexto_y_residencia(self):
        with patch('modulo_catalogo.services.ollama_normativo.requests.post') as post:
            post.return_value.json.return_value = {'done': True}
            precargar_modelo()
        post.assert_called_once_with('http://localhost:11434/api/generate', json={
            'model': 'qwen3.5:2b', 'stream': False, 'keep_alive': -1, 'options': {'num_ctx': 4096}},
            timeout=(5, 180))

    def test_rechaza_precarga_sin_confirmacion(self):
        with patch('modulo_catalogo.services.ollama_normativo.requests.post') as post:
            post.return_value.json.return_value = {'done': False}
            with self.assertRaisesRegex(RuntimeError, 'Inicia Ollama'):
                precargar_modelo()
