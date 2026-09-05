from django.test import TestCase

from modulo_catalogo.models.articulo import Articulo, ArticuloEntidad
from modulo_catalogo.models.entidad import EntidadJuridica
from modulo_catalogo.models.jerarquia import jerarquia as Jerarquia
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama import RamaDerecho
from modulo_catalogo.services.articulo_entidad_service import ArticuloEntidadService
from modulo_catalogo.services.entidad_matching import detectar_entidades_en_texto


class DetectarEntidadesEnTextoTests(TestCase):
    """Función pura de matching, sin base de datos de por medio salvo el catálogo."""

    def setUp(self):
        self.catalogo = [
            {"id": 1, "nombre": "Menor de edad"},
            {"id": 2, "nombre": "Víctima"},
            {"id": 3, "nombre": "Propietario"},
        ]

    def test_detecta_entidad_mencionada(self):
        detectadas = detectar_entidades_en_texto(
            "El agresor causó lesiones a un menor de edad.", self.catalogo
        )
        self.assertEqual([e["nombre"] for e in detectadas], ["Menor de edad"])

    def test_no_detecta_nada_si_no_hay_mencion(self):
        detectadas = detectar_entidades_en_texto(
            "Se establece un plazo procesal de diez días.", self.catalogo
        )
        self.assertEqual(detectadas, [])

    def test_es_case_insensitive(self):
        detectadas = detectar_entidades_en_texto("LA VÍCTIMA declaró.", self.catalogo)
        self.assertEqual([e["nombre"] for e in detectadas], ["Víctima"])

    def test_texto_vacio_no_detecta_nada(self):
        self.assertEqual(detectar_entidades_en_texto("", self.catalogo), [])
        self.assertEqual(detectar_entidades_en_texto(None, self.catalogo), [])

    def test_detecta_varias_entidades_a_la_vez(self):
        detectadas = detectar_entidades_en_texto(
            "El propietario denuncia que la víctima es su hija menor de edad.",
            self.catalogo,
        )
        nombres = {e["nombre"] for e in detectadas}
        self.assertEqual(nombres, {"Menor de edad", "Víctima", "Propietario"})


class ArticuloEntidadServiceTests(TestCase):

    def setUp(self):
        jerarquia = Jerarquia.objects.create(nivel=99, nombre="Jerarquía test")
        norma = Norma.objects.create(nombre="Norma test", jerarquia=jerarquia)
        rama = RamaDerecho.objects.create(nombre="Rama test")
        self.articulo = Articulo.objects.create(
            numero_articulo="1", titulo="Art. 1",
            contenido="El que agrediere a una menor de edad será sancionado.",
            norma=norma, rama=rama,
        )
        EntidadJuridica.objects.get_or_create(nombre="Menor de edad", defaults={"estado": True})
        EntidadJuridica.objects.get_or_create(nombre="Propietario", defaults={"estado": True})

    def test_vincula_las_entidades_detectadas_en_el_contenido(self):
        ArticuloEntidadService.vincular(self.articulo)
        nombres = set(self.articulo.entidades.values_list("nombre", flat=True))
        self.assertEqual(nombres, {"Menor de edad"})

    def test_es_idempotente(self):
        ArticuloEntidadService.vincular(self.articulo)
        ArticuloEntidadService.vincular(self.articulo)
        self.assertEqual(
            ArticuloEntidad.objects.filter(articulo=self.articulo).count(), 1
        )

    def test_si_el_contenido_cambia_actualiza_los_vinculos(self):
        ArticuloEntidadService.vincular(self.articulo)  # -> {"Menor de edad"}

        self.articulo.contenido = "El propietario reclama la restitución del bien."
        self.articulo.save(update_fields=["contenido"])
        ArticuloEntidadService.vincular(self.articulo)

        nombres = set(self.articulo.entidades.values_list("nombre", flat=True))
        self.assertEqual(nombres, {"Propietario"})

    def test_articulo_sin_entidades_no_crea_vinculos(self):
        self.articulo.contenido = "Se establece un plazo procesal de diez días."
        self.articulo.save(update_fields=["contenido"])
        ArticuloEntidadService.vincular(self.articulo)
        self.assertEqual(
            ArticuloEntidad.objects.filter(articulo=self.articulo).count(), 0
        )

    def test_entidad_inactiva_no_se_vincula(self):
        EntidadJuridica.objects.filter(nombre="Menor de edad").update(estado=False)
        ArticuloEntidadService.vincular(self.articulo)
        self.assertEqual(
            ArticuloEntidad.objects.filter(articulo=self.articulo).count(), 0
        )

    def test_acepta_un_catalogo_precargado_sin_volver_a_consultarlo(self):
        catalogo_manual = ArticuloEntidadService.obtener_catalogo()
        with self.assertNumQueries(2):  # SELECT vínculos actuales + INSERT (sin DELETE, no había que quitar nada)
            ArticuloEntidadService.vincular(self.articulo, catalogo=catalogo_manual)
        nombres = set(self.articulo.entidades.values_list("nombre", flat=True))
        self.assertEqual(nombres, {"Menor de edad"})
