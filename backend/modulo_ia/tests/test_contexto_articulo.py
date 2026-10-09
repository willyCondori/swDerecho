from types import SimpleNamespace
from django.test import SimpleTestCase
from modulo_ia.services.contexto_articulo_service import ContextoArticuloService as Servicio


class ContextoArticuloTests(SimpleTestCase):
    def articulo(self, titulo):
        return SimpleNamespace(titulo=titulo, contenido=f"Artículo 332. ({titulo}). Texto.")

    def test_robo_general_no_infiere_minerales_en_textos_cortos_o_largos(self):
        for texto in ["Robo a mano armada", "Antecedentes. " * 500 + "Robaron un celular con un arma."]:
            for titulo in ["Robo", "Robo agravado"]:
                self.assertTrue(Servicio.compatible(self.articulo(titulo), texto))
            for titulo in ["Robo Agravado de Minerales", "Asociación delictuosa para la sustracción de minerales"]:
                self.assertFalse(Servicio.compatible(self.articulo(titulo), texto))

    def test_objeto_minero_explicito_conserva_candidato(self):
        articulo = self.articulo("Robo Agravado de Minerales")
        for texto in ["Robo de minerales con armas", "Sustrajeron concentrado de estaño", "Antecedentes. " * 500 + "Robaron mineral."]:
            self.assertTrue(Servicio.compatible(articulo, texto))

    def test_remision_en_cuerpo_no_cambia_objeto_del_articulo(self):
        articulo = self.articulo("Robo")
        articulo.contenido += " Véase robo de minerales."
        self.assertTrue(Servicio.compatible(articulo, "Robo a mano armada"))
