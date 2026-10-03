import numpy as np
from django.test import TestCase

from modulo_usuarios.models.rol import Rol
from modulo_usuarios.models.usuario import Usuario
from modulo_clientes.models.cliente import Cliente
from modulo_catalogo.models.rama import RamaDerecho
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.jerarquia import jerarquia as Jerarquia
from modulo_catalogo.models.articulo import Articulo, ArticuloEntidad
from modulo_catalogo.models.entidad import EntidadJuridica
from modulo_ia.models.embedding import EmbeddingArticulo, EmbeddingChunk, EntidadDetectadaCaso
from modulo_ia.models.chunk import ChunkCaso
from modulo_casos.models.caso import Caso
from modulo_ia.services.ranking_service import RankingService
from modulo_ia.services.model_loader import version_activa


def _vector_bloque(bloque: int, dim: int = 768, n_bloques: int = 3, seed: int = 0) -> list:
    """Vector unitario concentrado en un bloque de dimensiones, ~ortogonal a los otros bloques."""
    rng = np.random.default_rng(seed)
    v = np.zeros(dim)
    ancho = dim // n_bloques
    v[bloque * ancho:(bloque + 1) * ancho] = rng.normal(size=ancho)
    return (v / np.linalg.norm(v)).tolist()


class RankingServiceEntidadesPorChunkTests(TestCase):
    """
    Regresión para el fix de score_entidades: antes se comparaba cada
    artículo contra las entidades de TODO el caso; ahora se compara
    solo contra las entidades del chunk específico que hizo relevante
    a ese artículo (ver RankingService._entidades_por_chunk).

    Sin este fix, un artículo podía recibir score_entidades > 0 por una
    entidad mencionada en una parte del caso totalmente distinta a la
    que realmente lo hizo relevante semánticamente.
    """

    @classmethod
    def setUpTestData(cls):
        rol = Rol.objects.create(nombre="Abogado test ranking")
        cls.usuario = Usuario.objects.create_user(usuario="ranking.test", password="Segura#123", rol=rol)
        cls.cliente = Cliente.objects.create(nombres="Cliente", apellidos="Test")
        cls.rama = RamaDerecho.objects.create(nombre="Rama test ranking")
        jerarquia = Jerarquia.objects.create(nivel=50, nombre="Jerarquía test ranking")
        cls.norma = Norma.objects.create(nombre="Norma test ranking", jerarquia=jerarquia)

        cls.ent_menor = EntidadJuridica.objects.create(nombre="Menor de edad")
        cls.ent_victima = EntidadJuridica.objects.create(nombre="Víctima")
        cls.ent_propietario = EntidadJuridica.objects.create(nombre="Propietario")

        cls.v_a = _vector_bloque(0, seed=1)  # tema "robo"
        cls.v_b = _vector_bloque(1, seed=2)  # tema "violencia familiar"

        cls.articulo_robo = Articulo.objects.create(
            numero_articulo="TEST-A", titulo="Art. TEST-A - ROBO",
            contenido="El que se apoderare de bien mueble ajeno mediante fuerza.",
            norma=cls.norma, rama=cls.rama,
        )
        EmbeddingArticulo.objects.create(articulo=cls.articulo_robo, modelo_version=version_activa(), vector=cls.v_a)
        # A propósito vinculado con "Menor de edad" aunque su contenido real
        # es sobre robo: así se puede detectar si el score de entidades se
        # "presta" indebidamente de otro chunk del mismo caso.
        ArticuloEntidad.objects.create(articulo=cls.articulo_robo, entidad=cls.ent_menor)
        ArticuloEntidad.objects.create(articulo=cls.articulo_robo, entidad=cls.ent_propietario)

        cls.articulo_violencia = Articulo.objects.create(
            numero_articulo="TEST-B", titulo="Art. TEST-B - VIOLENCIA FAMILIAR",
            contenido="El que ejerciere violencia contra una menor de edad en el ámbito familiar.",
            norma=cls.norma, rama=cls.rama,
        )
        EmbeddingArticulo.objects.create(articulo=cls.articulo_violencia, modelo_version=version_activa(), vector=cls.v_b)
        ArticuloEntidad.objects.create(articulo=cls.articulo_violencia, entidad=cls.ent_menor)
        ArticuloEntidad.objects.create(articulo=cls.articulo_violencia, entidad=cls.ent_victima)

    def _crear_caso_con_chunks(self, codigo, chunks_def):
        """chunks_def: lista de (contenido, vector, entidades_detectadas)."""
        caso = Caso.objects.create(
            codigo=codigo, titulo=codigo, descripcion="",
            usuario=self.usuario, cliente=self.cliente, rama_detectada=self.rama,
        )
        for orden, (contenido, vector, entidades) in enumerate(chunks_def, start=1):
            chunk = ChunkCaso.objects.create(caso=caso, contenido=contenido, orden=orden, tipo="texto")
            EmbeddingChunk.objects.create(chunk=chunk, modelo_version=version_activa(), vector=vector)
            for nombre in entidades:
                EntidadDetectadaCaso.objects.create(chunk=chunk, valor_detectado=nombre, score=1.0)
        return caso

    def test_caso_corto_sin_entidades_no_falla_y_score_entidades_es_cero(self):
        """Caso 1: descripción corta tipo 'intento robo', sin entidades."""
        caso = self._crear_caso_con_chunks(
            "CASO-CORTO-SIN-ENTIDADES",
            chunks_def=[("intento robo", self.v_a, [])],
        )
        resultados = RankingService.calcular_ranking(caso)

        self.assertTrue(len(resultados) >= 1)
        resultado_a = next(r for r in resultados if r.articulo_id == self.articulo_robo.id)
        self.assertEqual(float(resultado_a.score_entidades), 0.0)

    def test_busqueda_de_varios_chunks_usa_una_consulta_y_conserva_el_mejor_match(self):
        caso = self._crear_caso_con_chunks(
            "CASO-UNA-CONSULTA",
            [("robo", self.v_a, []), ("violencia", self.v_b, [])] * 5,
        )
        with self.assertNumQueries(1):
            scores, chunks = RankingService._score_semantico_por_articulo(caso)
        self.assertAlmostEqual(scores[self.articulo_robo.pk], 1.0, places=5)
        self.assertAlmostEqual(scores[self.articulo_violencia.pk], 1.0, places=5)
        self.assertIn(chunks[self.articulo_robo.pk], caso.chunks.values_list("id", flat=True))

    def test_entidades_precargadas_no_generan_consultas_adicionales(self):
        articulo = Articulo.objects.prefetch_related("entidades").get(pk=self.articulo_robo.pk)
        with self.assertNumQueries(0):
            score = RankingService._score_entidades(articulo, {"menor de edad"})
        self.assertEqual(score, 1.0)

    def test_chunk_sin_articulos_activos_devuelve_ranking_vacio(self):
        caso = self._crear_caso_con_chunks("CASO-SIN-ARTICULOS", [("texto", self.v_a, [])])
        Articulo.objects.filter(norma=self.norma).update(estado=False)
        scores, chunks = RankingService._score_semantico_por_articulo(caso)
        self.assertEqual(dict(scores), {})
        self.assertEqual(chunks, {})

    def test_sin_embeddings_activos_informa_el_error(self):
        caso = self._crear_caso_con_chunks("CASO-SIN-EMBEDDINGS", [])
        with self.assertRaisesMessage(ValueError, "versión de modelo activa"):
            RankingService._score_semantico_por_articulo(caso)

    def test_busqueda_excluye_otras_ramas_normas_inactivas_y_versiones(self):
        caso = self._crear_caso_con_chunks("CASO-FILTROS-SQL", [("texto", self.v_a, [])])
        otra_rama = RamaDerecho.objects.create(nombre="Rama fuera del filtro")
        fuera = Articulo.objects.create(numero_articulo="FUERA", contenido="Texto", norma=self.norma, rama=otra_rama)
        EmbeddingArticulo.objects.create(articulo=fuera, modelo_version=version_activa(), vector=self.v_a)
        viejo = Articulo.objects.create(numero_articulo="VIEJO", contenido="Texto", norma=self.norma, rama=self.rama)
        EmbeddingArticulo.objects.create(articulo=viejo, modelo_version="version-anterior", vector=self.v_a)
        scores, _ = RankingService._score_semantico_por_articulo(caso)
        self.assertNotIn(fuera.pk, scores)
        self.assertNotIn(viejo.pk, scores)
        self.norma.estado = False
        self.norma.save(update_fields=["estado"])
        scores, _ = RankingService._score_semantico_por_articulo(caso)
        self.assertEqual(dict(scores), {})

    def test_entidad_de_otro_chunk_no_contamina_un_articulo_no_relacionado(self):
        """
        Caso 2: el chunk de "robo" no debe recibir crédito por la entidad
        "Menor de edad" que solo aparece en el chunk de "violencia
        familiar", aunque el artículo de robo esté vinculado a esa
        entidad por otro motivo.
        """
        caso = self._crear_caso_con_chunks(
            "CASO-LARGO-DOS-TEMAS",
            chunks_def=[
                ("El imputado sustrajo bienes de la vivienda mediante fuerza sobre las cosas.",
                 self.v_a, []),
                ("Se denuncia que agredió a su hija, una menor de edad, en el ámbito familiar.",
                 self.v_b, ["Menor de edad"]),
            ],
        )
        resultados = RankingService.calcular_ranking(caso)
        resultados_por_articulo = {r.articulo_id: r for r in resultados}

        resultado_robo = resultados_por_articulo[self.articulo_robo.id]
        resultado_violencia = resultados_por_articulo[self.articulo_violencia.id]

        # El fix: el artículo de robo NO se beneficia de la entidad
        # detectada en el chunk de violencia familiar.
        self.assertEqual(float(resultado_robo.score_entidades), 0.0)
        # El artículo de violencia familiar sí recibe el crédito completo,
        # porque la entidad viene de SU propio chunk.
        self.assertEqual(float(resultado_violencia.score_entidades), 1.0)

    def test_articulo_recibe_credito_completo_cuando_coincide_con_su_propio_chunk(self):
        caso = self._crear_caso_con_chunks(
            "CASO-COINCIDENCIA-DIRECTA",
            chunks_def=[
                ("Se denuncia que agredió a su hija, una menor de edad, en el ámbito familiar. La víctima presenta lesiones.",
                 self.v_b, ["Menor de edad", "Víctima"]),
            ],
        )
        resultados = RankingService.calcular_ranking(caso)
        resultado = next(r for r in resultados if r.articulo_id == self.articulo_violencia.id)
        self.assertEqual(float(resultado.score_entidades), 1.0)


class RankingServiceVersionadoEmbeddingsTests(TestCase):
    """
    Regresión para el versionado de embeddings (ver modulo_ia/models/embedding.py
    y model_loader.py): un caso reanalizado después de cambiar de modelo
    tiene, para el mismo chunk, una fila de EmbeddingChunk por cada
    modelo_version con la que se analizó. Si un método no filtra por la
    versión activa, puede comparar vectores de dos versiones/modelos
    distintos entre sí — mismo tamaño (768), similitud sin sentido, sin
    ningún error visible.
    """

    OTRA_VERSION = "version-vieja-test"

    @classmethod
    def setUpTestData(cls):
        rol = Rol.objects.create(nombre="Abogado test versionado")
        cls.usuario = Usuario.objects.create_user(usuario="versionado.test", password="Segura#123", rol=rol)
        cls.cliente = Cliente.objects.create(nombres="Cliente", apellidos="Test")
        cls.rama = RamaDerecho.objects.create(nombre="Rama test versionado")
        jerarquia = Jerarquia.objects.create(nivel=51, nombre="Jerarquía test versionado")
        cls.norma = Norma.objects.create(nombre="Norma test versionado", jerarquia=jerarquia)

        cls.articulo = Articulo.objects.create(
            numero_articulo="TEST-V", titulo="Art. TEST-V",
            contenido="Contenido de prueba para versionado.",
            norma=cls.norma, rama=cls.rama,
        )

        cls.caso = Caso.objects.create(
            codigo="CASO-VERSIONADO", titulo="CASO-VERSIONADO", descripcion="",
            usuario=cls.usuario, cliente=cls.cliente, rama_detectada=cls.rama,
        )
        cls.chunk = ChunkCaso.objects.create(
            caso=cls.caso, contenido="texto del chunk", orden=1, tipo="texto"
        )

        cls.vector_activo = _vector_bloque(0, seed=10)
        cls.vector_viejo = _vector_bloque(1, seed=20)

        # Mismo chunk, dos versiones de modelo: la activa y una "vieja"
        # que ya no debería usarse para comparar nada.
        EmbeddingChunk.objects.create(
            chunk=cls.chunk, modelo_version=version_activa(), vector=cls.vector_activo,
        )
        EmbeddingChunk.objects.create(
            chunk=cls.chunk, modelo_version=cls.OTRA_VERSION, vector=cls.vector_viejo,
        )

        # Mismo artículo, dos versiones de EmbeddingArticulo.
        EmbeddingArticulo.objects.create(
            articulo=cls.articulo, modelo_version=version_activa(), vector=cls.vector_activo,
        )
        EmbeddingArticulo.objects.create(
            articulo=cls.articulo, modelo_version=cls.OTRA_VERSION, vector=cls.vector_viejo,
        )

    def test_vectores_chunks_caso_solo_trae_la_version_activa(self):
        vectores = RankingService._vectores_chunks_caso(self.caso)
        # Sin el filtro por versión, esto traería 2 filas (una por
        # modelo_version) para el mismo chunk.
        self.assertEqual(len(vectores), 1)
        chunk_id, vector = vectores[0]
        self.assertEqual(chunk_id, self.chunk.id)
        np.testing.assert_allclose(vector, self.vector_activo, rtol=1e-6, atol=1e-8)

    def test_score_semantico_articulo_especifico_usa_solo_la_version_activa(self):
        vectores_chunks_caso = RankingService._vectores_chunks_caso(self.caso)
        similitud, chunk_id = RankingService._score_semantico_articulo_especifico(
            self.articulo.id, vectores_chunks_caso
        )
        # vector_articulo (versión activa) contra vector_chunk (versión
        # activa): mismo vector → similitud coseno = 1.0. Si el método
        # hubiera tomado el EmbeddingArticulo de OTRA_VERSION (vector
        # ortogonal, por construcción de _vector_bloque), la similitud
        # habría salido ~0.0 en vez de 1.0.
        self.assertAlmostEqual(similitud, 1.0, places=5)
        self.assertEqual(chunk_id, self.chunk.id)


class RankingServiceScoresEnLoteTests(TestCase):
    """
    _scores_semanticos_articulos_especificos puntúa varios artículos
    "forzados" (figuras transversales) contra los chunks del caso con UNA
    consulta y similitud coseno normalizada. Antes era una consulta por
    artículo y un np.dot crudo (fuera de [-1, 1] con vectores sin normalizar).
    """

    @classmethod
    def setUpTestData(cls):
        rol = Rol.objects.create(nombre="Abogado test lote")
        cls.usuario = Usuario.objects.create_user(usuario="lote.test", password="Segura#123", rol=rol)
        cls.cliente = Cliente.objects.create(nombres="Cliente", apellidos="Test")
        cls.rama = RamaDerecho.objects.create(nombre="Rama test lote")
        jerarquia = Jerarquia.objects.create(nivel=52, nombre="Jerarquía test lote")
        cls.norma = Norma.objects.create(nombre="Norma test lote", jerarquia=jerarquia)

        cls.caso = Caso.objects.create(
            codigo="CASO-LOTE", titulo="CASO-LOTE", descripcion="",
            usuario=cls.usuario, cliente=cls.cliente, rama_detectada=cls.rama,
        )
        cls.chunk_a = ChunkCaso.objects.create(caso=cls.caso, contenido="tema a", orden=1, tipo="texto")
        cls.chunk_b = ChunkCaso.objects.create(caso=cls.caso, contenido="tema b", orden=2, tipo="texto")
        cls.v_a = _vector_bloque(0, seed=31)
        cls.v_b = _vector_bloque(1, seed=32)
        cls.v_c = _vector_bloque(2, seed=33)
        EmbeddingChunk.objects.create(chunk=cls.chunk_a, modelo_version=version_activa(), vector=cls.v_a)
        EmbeddingChunk.objects.create(chunk=cls.chunk_b, modelo_version=version_activa(), vector=cls.v_b)

        def articulo(numero, vector):
            art = Articulo.objects.create(
                numero_articulo=numero, titulo=f"Art. {numero}", contenido=f"Contenido {numero}",
                norma=cls.norma, rama=cls.rama,
            )
            if vector is not None:
                EmbeddingArticulo.objects.create(articulo=art, modelo_version=version_activa(), vector=vector)
            return art

        cls.art_a = articulo("LOTE-A", cls.v_a)
        cls.art_b = articulo("LOTE-B", cls.v_b)
        # Mismo tema que el chunk A pero con magnitud 5: sin normalizar, un
        # producto punto daría ~5.0 en vez de 1.0.
        cls.art_a_grande = articulo("LOTE-A5", (np.array(cls.v_a) * 5).tolist())
        cls.art_ortogonal = articulo("LOTE-C", cls.v_c)
        cls.art_sin_embedding = articulo("LOTE-SIN", None)

    def _vectores(self):
        return RankingService._vectores_chunks_caso(self.caso)

    def test_cada_articulo_toma_su_mejor_chunk(self):
        res = RankingService._scores_semanticos_articulos_especificos(
            [self.art_a.id, self.art_b.id], self._vectores()
        )
        sim_a, chunk_a = res[self.art_a.id]
        sim_b, chunk_b = res[self.art_b.id]
        self.assertAlmostEqual(sim_a, 1.0, places=5)
        self.assertEqual(chunk_a, self.chunk_a.id)
        self.assertAlmostEqual(sim_b, 1.0, places=5)
        self.assertEqual(chunk_b, self.chunk_b.id)

    def test_similitud_es_coseno_aunque_el_vector_no_este_normalizado(self):
        res = RankingService._scores_semanticos_articulos_especificos(
            [self.art_a_grande.id], self._vectores()
        )
        similitud, chunk_id = res[self.art_a_grande.id]
        self.assertAlmostEqual(similitud, 1.0, places=5)
        self.assertLessEqual(similitud, 1.0 + 1e-9)
        self.assertEqual(chunk_id, self.chunk_a.id)

    def test_sin_embedding_u_ortogonal_queda_en_cero(self):
        res = RankingService._scores_semanticos_articulos_especificos(
            [self.art_sin_embedding.id, self.art_ortogonal.id], self._vectores()
        )
        self.assertEqual(res[self.art_sin_embedding.id], (0.0, None))
        self.assertEqual(res[self.art_ortogonal.id][1], None)
        self.assertEqual(res[self.art_ortogonal.id][0], 0.0)

    def test_sin_ids_o_sin_chunks_devuelve_vacio_sin_consultar(self):
        vectores = self._vectores()
        with self.assertNumQueries(0):
            self.assertEqual(
                RankingService._scores_semanticos_articulos_especificos([], vectores), {}
            )
            self.assertEqual(
                RankingService._scores_semanticos_articulos_especificos([self.art_a.id], []),
                {self.art_a.id: (0.0, None)},
            )

    def test_una_sola_consulta_para_varios_articulos(self):
        vectores = self._vectores()
        ids = [self.art_a.id, self.art_b.id, self.art_a_grande.id, self.art_ortogonal.id]
        with self.assertNumQueries(1):
            RankingService._scores_semanticos_articulos_especificos(ids, vectores)

    def test_wrapper_de_un_solo_articulo_sigue_funcionando(self):
        similitud, chunk_id = RankingService._score_semantico_articulo_especifico(
            self.art_b.id, self._vectores()
        )
        self.assertAlmostEqual(similitud, 1.0, places=5)
        self.assertEqual(chunk_id, self.chunk_b.id)
