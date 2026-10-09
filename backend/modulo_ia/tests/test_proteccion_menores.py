from types import SimpleNamespace
from django.test import SimpleTestCase
from modulo_ia.services.proteccion_menores_service import ProteccionMenoresService as Servicio


class ProteccionMenoresTests(SimpleTestCase):
    def articulo(self, titulo, numero="10426"):
        return SimpleNamespace(titulo=titulo, contenido=f"Artículo 1. ({titulo}). Texto.",
                               norma=SimpleNamespace(numero_norma=numero))

    def test_contexto_corto_y_largo(self):
        for texto in ["asalto a niños", "Antecedentes. " * 500 + "Asaltaron a una adolescente."]:
            self.assertTrue(Servicio.hay_menores(texto))
            self.assertFalse(Servicio.requiere_hechos_no_mencionados(self.articulo("Robo"), texto))
            for titulo in ["Estupro", "Corrupción de niña niño o adolescente", "Abandono", "Inducción a fuga", "Homicidio"]:
                self.assertTrue(Servicio.requiere_hechos_no_mencionados(self.articulo(titulo), texto))
            self.assertTrue(Servicio.requiere_hechos_no_mencionados(self.articulo("Datos estadísticos", "1636"), texto))

    def test_hechos_adicionales_conservan_delitos(self):
        for titulo, texto in [("Estupro", "abuso sexual a niña"), ("Abandono", "abandonaron al niño"),
                              ("Homicidio", "mataron a un adolescente")]:
            self.assertFalse(Servicio.requiere_hechos_no_mencionados(self.articulo(titulo), texto))
        self.assertFalse(Servicio.hay_menores("asalto a una persona adulta"))
