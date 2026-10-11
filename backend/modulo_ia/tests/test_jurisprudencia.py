import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, SimpleTestCase, override_settings
from rest_framework.test import APITestCase

from modulo_casos.models.caso import Caso
from modulo_clientes.models.cliente import Cliente
from modulo_catalogo.models.rama import RamaDerecho
from modulo_ia.models.chunk import ChunkCaso
from modulo_ia.models.embedding import EmbeddingChunk
from modulo_ia.models.jurisprudencia import (
    ResolucionJurisprudencia, FragmentoJurisprudencia, EmbeddingJurisprudencia, ResultadoJurisprudencia,
)
from modulo_ia.services.jurisprudencia_importacion import importar_resolucion, limpiar_contenido, url_oficial
from modulo_ia.services.jurisprudencia_service import JurisprudenciaService
from modulo_ia.services.model_loader import version_activa
from modulo_ia.tasks.analisis_task import ejecutar_analisis_caso
from modulo_usuarios.tests.factories import crear_rol, crear_usuario

VECTOR = [1.0] + [0.0] * 767
OTRO_VECTOR = [0.0, 1.0] + [0.0] * 766
TEXTO = "La víctima relató que el acusado se apoderó de su teléfono mediante violencia. El Tribunal examinó la prueba y el recurso planteado."


def datos(fuente_id=100):
    return dict(id=fuente_id, nro_resolucion="AS/100/2024", fecha_emision="29/02/2024", materia="Penal", contenido=f"<p>{TEXTO}</p>")


class ImportacionTests(TestCase):
    def test_idempotencia_y_cambio_de_modelo_sin_mezclar_vectores(self):
        with patch("modulo_ia.services.jurisprudencia_importacion.vectorizar_textos", side_effect=lambda ts: [VECTOR for _ in ts]) as encode:
            self.assertEqual(importar_resolucion(datos()), "creada")
            self.assertEqual(importar_resolucion(datos()), "omitida")
            self.assertEqual(encode.call_count, 1)
            with override_settings(EMBEDDING_MODEL_VERSION="otra-version"):
                self.assertEqual(importar_resolucion(datos()), "actualizada")
        self.assertEqual(ResolucionJurisprudencia.objects.count(), 1)
        self.assertEqual(EmbeddingJurisprudencia.objects.count(), 2)
        self.assertEqual(ResolucionJurisprudencia.objects.get().fecha.isoformat(), "2024-02-29")

    def test_cambio_de_texto_invalida_vectores_y_marca_resultado_anterior(self):
        with patch("modulo_ia.services.jurisprudencia_importacion.vectorizar_textos", return_value=[VECTOR]):
            importar_resolucion(datos())
        anterior = ResolucionJurisprudencia.objects.get().huella
        nuevo = datos(); nuevo["contenido"] = TEXTO + " El recurso fue declarado infundado."
        with patch("modulo_ia.services.jurisprudencia_importacion.vectorizar_textos", return_value=[OTRO_VECTOR]):
            importar_resolucion(nuevo)
        self.assertNotEqual(anterior, ResolucionJurisprudencia.objects.get().huella)
        self.assertEqual(EmbeddingJurisprudencia.objects.count(), 1)
        self.assertEqual(list(EmbeddingJurisprudencia.objects.get().vector), OTRO_VECTOR)

    def test_modelo_fallido_conserva_texto_y_vectores_previos(self):
        with patch("modulo_ia.services.jurisprudencia_importacion.vectorizar_textos", return_value=[VECTOR]):
            importar_resolucion(datos())
        anterior = ResolucionJurisprudencia.objects.get().huella
        nuevo = datos(); nuevo["contenido"] = TEXTO + " Modificación del documento."
        with patch("modulo_ia.services.jurisprudencia_importacion.vectorizar_textos", side_effect=RuntimeError("modelo")):
            with self.assertRaises(RuntimeError):
                importar_resolucion(nuevo)
        self.assertEqual(anterior, ResolucionJurisprudencia.objects.get().huella)

    def test_rechaza_pdf_sin_texto_y_otras_materias(self):
        for cambio in ({"contenido": ""}, {"materia": "Civil"}, {"id": "../1"}):
            with self.assertRaises(ValueError):
                importar_resolucion({**datos(), **cambio})
        self.assertEqual(ResolucionJurisprudencia.objects.count(), 0)


class RecuperacionTests(APITestCase):
    def test_recuperacion_hibrida_rescata_cuerpo_de_menor_confianza_y_descarta_caratula(self):
        vector = [.55, (1 - .55 ** 2) ** .5] + [0.] * 766
        r = self.resolucion(55, vector=vector)
        f = r.fragmentos.get()
        f.contenido = 'El Tribunal examinó los elementos del delito de robo agravado y estableció la aplicación del artículo 332 del Código Penal.'
        f.save(update_fields=['contenido'])
        encabezado = FragmentoJurisprudencia.objects.create(resolucion=r, orden=1,
            contenido='TRIBUNAL SUPREMO DE JUSTICIA SALA PENAL AUTO SUPREMO Número 55 Partes: Ministerio Público contra A y B Delito: Robo agravado')
        EmbeddingJurisprudencia.objects.create(fragmento=encabezado, vector=VECTOR, modelo_version=version_activa())
        with override_settings(JURISPRUDENCIA_UMBRAL=.65, JURISPRUDENCIA_UMBRAL_RECOMENDACION=.50):
            salida = JurisprudenciaService.calcular(self.caso)
        self.assertEqual(len(salida['resultados']), 1)
        resultado = salida['resultados'][0]
        self.assertTrue(resultado.es_sugerencia)
        self.assertEqual(resultado.fragmento, f.contenido)
        self.assertEqual(resultado.coincidencias, ['Robo'])
        self.assertAlmostEqual(resultado.score_semantico, .55, places=5)

    def test_secuestro_de_objetos_no_se_publica_para_secuestro_de_personas(self):
        self.caso.chunks.update(contenido='Intentaron secuestrarme')
        r = self.resolucion(56)
        f = r.fragmentos.get()
        f.contenido = 'El Tribunal examinó el acta de secuestro de hoja de coca y estableció los requisitos de la prueba documental presentada.'
        f.save(update_fields=['contenido'])
        self.assertEqual(JurisprudenciaService.calcular(self.caso)['estado'], 'sin_coincidencias')

    def setUp(self):
        self.usuario = crear_usuario("juris.abogado", rol=crear_rol("Abogado"))
        self.caso = Caso.objects.create(codigo="JURIS-1", titulo="Robo de teléfono", descripcion=TEXTO,
            usuario=self.usuario, cliente=Cliente.objects.create(nombres="Ana", apellidos="Prueba"),
            rama_detectada=RamaDerecho.objects.create(nombre="Derecho Penal"))
        chunk = ChunkCaso.objects.create(caso=self.caso, contenido=TEXTO, orden=0)
        EmbeddingChunk.objects.create(chunk=chunk, vector=VECTOR, modelo_version=version_activa())

    def resolucion(self, fuente_id, vector=VECTOR, version=None, activa=True):
        r = ResolucionJurisprudencia.objects.create(fuente_id=str(fuente_id), texto=TEXTO, huella="a" * 64,
            url_fuente=f"https://apigenesis.tsj.bo/api/v1/resoluciones/{fuente_id}", activa=activa)
        f = FragmentoJurisprudencia.objects.create(resolucion=r, orden=0, contenido=TEXTO)
        EmbeddingJurisprudencia.objects.create(fragmento=f, vector=vector, modelo_version=version or version_activa())
        return r

    def test_sql_coseno_deduplica_y_excluye_inactivas_versiones_y_no_similares(self):
        r = self.resolucion(1)
        f = FragmentoJurisprudencia.objects.create(resolucion=r, orden=1, contenido="Otro fragmento similar")
        EmbeddingJurisprudencia.objects.create(fragmento=f, vector=VECTOR, modelo_version=version_activa())
        otra = self.resolucion(2, version="version-ajena")
        EmbeddingJurisprudencia.objects.create(fragmento=otra.fragmentos.get(), vector=OTRO_VECTOR, modelo_version=version_activa())
        self.resolucion(3, activa=False)
        self.resolucion(4, vector=OTRO_VECTOR)
        salida = JurisprudenciaService.calcular(self.caso)
        self.assertEqual(salida["estado"], "completado")
        self.assertEqual([x.resolucion_id for x in salida["resultados"]], [r.pk])
        self.assertAlmostEqual(salida["resultados"][0].score_semantico, 1)
        JurisprudenciaService.calcular(self.caso)
        self.assertEqual(ResultadoJurisprudencia.objects.count(), 1)

    def test_no_simula_resultados_sin_corpus_y_no_devuelve_penal_a_civil(self):
        self.assertEqual(JurisprudenciaService.calcular(self.caso)["estado"], "sin_corpus")
        self.resolucion(1, version="antigua")
        self.assertEqual(JurisprudenciaService.calcular(self.caso)["estado"], "sin_embeddings")
        self.caso.rama_detectada.nombre = "Civil"
        self.assertEqual(JurisprudenciaService.calcular(self.caso)["estado"], "fuera_cobertura")

    def test_indice_incompleto_no_publica_resultados_parciales_y_se_puede_reanudar(self):
        self.resolucion(1)
        self.resolucion(2, version="anterior")
        self.assertEqual(JurisprudenciaService.calcular(self.caso)["estado"], "sin_embeddings")
        with patch("modulo_ia.management.commands.regenerar_embeddings_jurisprudencia.vectorizar_textos", return_value=[VECTOR]) as encode:
            call_command("regenerar_embeddings_jurisprudencia", stdout=io.StringIO())
            call_command("regenerar_embeddings_jurisprudencia", stdout=io.StringIO())
            self.assertEqual(encode.call_count, 1)
        self.assertEqual(EmbeddingJurisprudencia.objects.filter(modelo_version="anterior").count(), 1)
        self.assertEqual(JurisprudenciaService.calcular(self.caso)["estado"], "completado")

    def test_pipeline_incluye_jurisprudencia_y_endpoint_respeta_permisos(self):
        r = self.resolucion(1)
        with patch("modulo_ia.services.embedding_service.EmbeddingService.preparar_vectores", side_effect=lambda chunks: [VECTOR] * len(chunks)):
            salida = ejecutar_analisis_caso(self.caso.pk)
        self.assertNotIn("error", salida)
        self.assertEqual(salida["resoluciones_relacionadas"], 1)
        url = f"/api/casos/{self.caso.public_id}/jurisprudencia/"
        self.assertEqual(self.client.get(url).status_code, 401)
        asistente = crear_usuario("juris.asistente", rol=crear_rol("Asistente"))
        self.client.force_authenticate(asistente)
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["estado"], "completado")
        self.assertFalse(respuesta.data["desactualizada"])
        self.assertEqual(respuesta.data["resultados"][0]["fragmento"], TEXTO)
        r.huella = "b" * 64; r.save()
        self.assertTrue(self.client.get(url).data["resultados"][0]["desactualizada"])
        self.caso.estado = False; self.caso.save()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_falla_al_guardar_resultado_revierte_ambos_rankings(self):
        self.resolucion(1)
        JurisprudenciaService.calcular(self.caso)
        anterior = ResultadoJurisprudencia.objects.get().pk
        with patch("modulo_ia.services.embedding_service.EmbeddingService.preparar_vectores", side_effect=lambda chunks: [VECTOR] * len(chunks)), \
             patch("modulo_casos.models.resultado_caso.ResultadoCaso.objects.update_or_create", side_effect=RuntimeError("guardado")):
            salida = ejecutar_analisis_caso(self.caso.pk)
        self.assertIn("error", salida)
        self.assertEqual(ResultadoJurisprudencia.objects.get().pk, anterior)


class ClienteTSJTests(SimpleTestCase):
    def test_importacion_reporta_progreso_y_continua_con_archivos_rechazados(self):
        with tempfile.TemporaryDirectory() as directorio:
            Path(directorio, "1.json").write_text("JSON roto", encoding="utf-8")
            Path(directorio, "2.json").write_text(json.dumps(datos(2)), encoding="utf-8")
            output = io.StringIO()
            with patch("modulo_ia.management.commands.importar_jurisprudencia_tsj.importar_resolucion", return_value="creada") as importar:
                with self.assertRaises(CommandError):
                    call_command("importar_jurisprudencia_tsj", directorio=directorio,
                                 progreso_cada=1, stdout=output, stderr=io.StringIO())
            importar.assert_called_once()
            self.assertIn('"procesadas": 2', output.getvalue())
            self.assertIn('"rechazada": 1', output.getvalue())
            self.assertIn('"creada": 1', output.getvalue())

    def test_html_y_enlaces_no_ejecutan_codigo(self):
        self.assertEqual(limpiar_contenido('<p>Hechos</p><script>malicioso()</script><p>Decisión</p>'), "Hechos\n\nDecisión")
        self.assertEqual(url_oficial("javascript:alert(1)"), "")
        self.assertEqual(url_oficial("https://tsj.bo.ejemplo.com/a.pdf"), "")
        self.assertEqual(url_oficial("https://genesis.tsj.bo/a.pdf"), "https://genesis.tsj.bo/a.pdf")

    @override_settings(TSJ_API_KEY="clave-de-prueba", TSJ_API_USERNAME="buscadorgenesis")
    def test_busqueda_contrato_penal_y_validacion_del_detalle(self):
        from modulo_ia.services.tsj_api import TSJApi
        with patch("modulo_ia.services.tsj_api.requests.Session") as session:
            session.return_value.post.return_value.json.return_value = {"data": {"data": [{"id": 1}], "meta": {"totalPages": 1}}}
            session.return_value.get.return_value.json.return_value = {"data": {"id": 2}}
            api = TSJApi()
            self.assertEqual(api.buscar(1)["data"], [{"id": 1}])
            body = session.return_value.post.call_args.kwargs["json"]
            self.assertEqual(body["filter"]["idMateria"], "1")
            self.assertEqual(body["searchData"]["todasEstasPalabras"], "penal")
            with self.assertRaises(ValueError): api.detalle(1)
            api.close()

    def test_sincronizacion_acotada_y_repetible(self):
        api = Mock()
        api.buscar.return_value = {"data": [{"id": 1}, {"id": 2}], "meta": {"totalPages": 10}}
        api.detalle.return_value = datos(1)
        with patch("modulo_ia.management.commands.sincronizar_jurisprudencia_tsj.TSJApi", return_value=api), \
             patch("modulo_ia.management.commands.sincronizar_jurisprudencia_tsj.importar_resolucion", return_value="omitida"):
            output = io.StringIO()
            call_command("sincronizar_jurisprudencia_tsj", limite=1, pausa=0, stdout=output)
        api.detalle.assert_called_once_with(1)
        api.close.assert_called_once()
        self.assertIn('"omitida": 1', output.getvalue())
