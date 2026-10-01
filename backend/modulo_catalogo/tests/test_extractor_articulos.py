"""
Tests del extractor de artículos de PDFs (carga_pdf_service): limpieza de
encabezados y pies de página repetidos, y división por artículos con
encabezados de capítulo colgantes y referencias dentro de oraciones.

Son pruebas de lógica pura (sin base de datos).
"""
import sys
import types
from unittest.mock import patch

from django.test import SimpleTestCase

from modulo_catalogo.services.carga_pdf_service import (
    dividir_por_articulos,
    extraer_texto_pdf_bytes,
    quitar_encabezados_y_pies,
)

PIE = "Caja de herramientas para la atención de la violencia en servicios de salud"

# Fragmento real de la Ley 348 tal como llega de un PDF sin saltos de línea.
LEY_348_PLANO = (
    "DISPOSICIONES GENERALES CAPÍTULO ÚNICO MARCO CONSTITUCIONAL, OBJETO, FINALIDAD, "
    "ALCANCE Y APLICACIÓN ARTÍCULO 1. (MARCO CONSTITUCIONAL). La presente Ley se funda en el "
    "mandato constitucional y en los Instrumentos, Tratados y Convenios Internacionales de "
    "Derechos Humanos ratificados por Bolivia. ARTÍCULO 2. (OBJETO Y FINALIDAD). La presente "
    "Ley tiene por objeto establecer mecanismos, medidas y políticas integrales de prevención. "
    "ARTÍCULO 3. (PRIORIDAD NACIONAL). I. El Estado Plurinacional de Bolivia asume como "
    "prioridad la erradicación de la violencia hacia las mujeres. II. Los Órganos del Estado "
    "adoptarán las medidas y políticas necesarias, con carácter obligatorio. III. Las Entidades "
    "Territoriales Autónomas asignarán los recursos humanos y económicos. ARTÍCULO 4. "
    "(PRINCIPIOS Y VALORES). La presente Ley se rige por los siguientes principios y valores: "
    "1. Vivir Bien. Es la condición y desarrollo de una vida íntegra. 2. Igualdad. El Estado "
    "garantiza la igualdad real y efectiva entre mujeres y hombres."
)


def numeros(texto):
    return [a["numero"] for a in dividir_por_articulos(texto)]


def articulo(texto, numero):
    return next(a for a in dividir_por_articulos(texto) if a["numero"] == numero)


CUERPOS = [
    "El Estado garantiza la igualdad real y efectiva entre mujeres y hombres",
    "Las instituciones públicas adoptarán las medidas necesarias de prevención",
    "Se brindará atención integral, oportuna y gratuita a las víctimas",
    "La persecución y sanción de los agresores será prioridad del Ministerio Público",
    "Los servicios de salud deberán registrar y reportar los casos atendidos",
    "Las entidades territoriales autónomas asignarán recursos suficientes",
    "La reparación del daño comprenderá medidas de rehabilitación y satisfacción",
    "Se garantiza la confidencialidad de la información de las mujeres atendidas",
]


class QuitarEncabezadosYPiesTests(SimpleTestCase):
    def paginas_con_pie(self, cuerpos, primer_numero=1):
        return [f"{c}\n{PIE} {i}" for i, c in enumerate(cuerpos, start=primer_numero)]

    def test_quita_el_pie_repetido_ignorando_el_numero_de_pagina(self):
        paginas = self.paginas_con_pie(CUERPOS[:4], 8)
        limpias = quitar_encabezados_y_pies(paginas)
        self.assertEqual(limpias, CUERPOS[:4])

    def test_quita_encabezados_en_la_parte_superior(self):
        paginas = [f"LEY N° 348 — página {i}\n{CUERPOS[i]}\n{CUERPOS[i + 1]}" for i in range(5)]
        limpias = quitar_encabezados_y_pies(paginas)
        self.assertTrue(all("LEY N°" not in p for p in limpias))
        self.assertEqual(limpias[0], f"{CUERPOS[0]}\n{CUERPOS[1]}")

    def test_encabezados_alternados_en_paginas_pares_e_impares(self):
        paginas = [
            (f"LEY INTEGRAL {i}" if i % 2 else f"{PIE} {i}") + f"\n{CUERPOS[i - 1]}" for i in range(1, 9)
        ]
        limpias = quitar_encabezados_y_pies(paginas)
        self.assertEqual(limpias, CUERPOS)

    def test_una_linea_que_aparece_una_sola_vez_no_se_toca(self):
        paginas = self.paginas_con_pie(CUERPOS[:4])
        paginas[1] += "\nDISPOSICIÓN FINAL ÚNICA"
        limpias = quitar_encabezados_y_pies(paginas)
        self.assertIn("DISPOSICIÓN FINAL ÚNICA", limpias[1])

    def test_con_menos_de_tres_paginas_no_se_toca_nada(self):
        paginas = self.paginas_con_pie(CUERPOS[:2])
        self.assertEqual(quitar_encabezados_y_pies(paginas), paginas)

    def test_no_quita_el_inicio_de_un_articulo_aunque_se_repita(self):
        paginas = [f"ARTÍCULO 1. (X). Texto de la página\n{c}" for c in CUERPOS[:5]]
        self.assertEqual(quitar_encabezados_y_pies(paginas), paginas)

    def test_solo_mira_los_bordes_de_la_pagina(self):
        medio = "Texto que se repite en el medio del cuerpo de cada página"
        paginas = [f"uno {i}\ndos {i}\ntres {i}\ncuatro {i}\n{medio}\ncinco {i}\nseis {i}\nsiete {i}\nocho {i}" for i in range(6)]
        limpias = quitar_encabezados_y_pies(paginas)
        self.assertTrue(all(medio in p for p in limpias))

    def test_numeros_de_pagina_sueltos_no_cuentan_como_pie(self):
        paginas = [f"{CUERPOS[i - 1]}\n{i}" for i in range(1, 6)]
        self.assertEqual(quitar_encabezados_y_pies(paginas), paginas)

    def test_extraer_texto_pdf_bytes_limpia_los_pies(self):
        class PaginaFalsa:
            def __init__(self, texto):
                self.texto = texto

            def extract_text(self):
                return self.texto

        class LectorFalso:
            def __init__(self, _flujo):
                self.pages = [PaginaFalsa(t) for t in self.textos]

            textos = [f"{CUERPOS[i - 1]}\n{PIE} {i}" for i in range(1, 6)] + [""]

        pypdf_falso = types.ModuleType("pypdf")
        pypdf_falso.PdfReader = LectorFalso
        with patch.dict(sys.modules, {"pypdf": pypdf_falso}):
            texto = extraer_texto_pdf_bytes(b"%PDF-falso")
        self.assertEqual(texto, "\n".join(CUERPOS[:5]))

    def test_el_pie_no_queda_dentro_del_articulo_que_cruza_la_pagina(self):
        # El Art. 3 empieza en una página y sigue en la siguiente: el pie de
        # la primera queda entre el inciso II y el III.
        paginas = [
            "ARTÍCULO 1. (MARCO CONSTITUCIONAL). La presente Ley se funda en el mandato constitucional.\n"
            "ARTÍCULO 2. (OBJETO Y FINALIDAD). La presente Ley tiene por objeto establecer mecanismos.",
            "ARTÍCULO 3. (PRIORIDAD NACIONAL). I. El Estado asume como prioridad la erradicación de la violencia.\n"
            "II. Los Órganos del Estado adoptarán las medidas necesarias, con carácter obligatorio.",
            "III. Las Entidades Territoriales Autónomas asignarán los recursos humanos y económicos.\n"
            "ARTÍCULO 4. (PRINCIPIOS Y VALORES). La presente Ley se rige por los siguientes principios.",
            "1. Vivir Bien. Es la condición y desarrollo de una vida íntegra.",
        ]
        texto = "\n".join(quitar_encabezados_y_pies(self.paginas_con_pie(paginas, 7)))
        art3 = articulo(texto, 3)
        self.assertNotIn("Caja de herramientas", art3["texto"])
        self.assertIn("obligatorio.\nIII. Las Entidades", art3["texto"])
        self.assertEqual(numeros(texto), [1, 2, 3, 4])


class DivisionPorArticulosTests(SimpleTestCase):
    def test_texto_plano_de_la_ley_348_detecta_los_articulos_y_sus_titulos(self):
        arts = dividir_por_articulos(LEY_348_PLANO)
        self.assertEqual([a["numero"] for a in arts], [1, 2, 3, 4])
        self.assertEqual(
            [a["titulo"] for a in arts],
            [
                "Art. 1 - MARCO CONSTITUCIONAL",
                "Art. 2 - OBJETO Y FINALIDAD",
                "Art. 3 - PRIORIDAD NACIONAL",
                "Art. 4 - PRINCIPIOS Y VALORES",
            ],
        )

    def test_el_preambulo_no_forma_parte_de_ningun_articulo(self):
        self.assertNotIn("DISPOSICIONES GENERALES", articulo(LEY_348_PLANO, 1)["texto"])

    def test_incisos_y_listas_numeradas_no_se_confunden_con_articulos(self):
        art3 = articulo(LEY_348_PLANO, 3)["texto"]
        art4 = articulo(LEY_348_PLANO, 4)["texto"]
        self.assertIn("III. Las Entidades", art3)
        self.assertIn("2. Igualdad.", art4)

    BASE5 = "ARTÍCULO 5. (PREVENCIÓN). El Estado adoptará medidas de prevención. "
    BASE6 = "ARTÍCULO 6. (ATENCIÓN). Se brindará atención integral a las mujeres."

    def test_encabezado_corto_en_mayusculas_se_quita(self):
        texto = self.BASE5 + "TÍTULO II MEDIDAS DE PREVENCIÓN CAPÍTULO I PREVENCIÓN " + self.BASE6
        self.assertTrue(articulo(texto, 5)["texto"].endswith("medidas de prevención."))

    def test_encabezados_largos_apilados_en_mayusculas_se_quitan(self):
        texto = (
            self.BASE5
            + "TÍTULO II MECANISMOS, MEDIDAS Y POLÍTICAS DE PREVENCIÓN, ATENCIÓN Y PROTECCIÓN INTEGRAL "
            + "CAPÍTULO I POLÍTICAS PÚBLICAS DE PREVENCIÓN "
            + self.BASE6
        )
        self.assertTrue(articulo(texto, 5)["texto"].endswith("medidas de prevención."))
        self.assertEqual(numeros(texto), [5, 6])

    def test_encabezado_con_minusculas_en_texto_plano_se_quita_y_no_se_pierde_el_siguiente(self):
        texto = self.BASE5 + "Capítulo II Derechos de las mujeres " + self.BASE6
        self.assertEqual(numeros(texto), [5, 6])
        self.assertTrue(articulo(texto, 5)["texto"].endswith("medidas de prevención."))

    def test_encabezado_con_minusculas_con_salto_de_linea(self):
        texto = self.BASE5.strip() + "\nCapítulo II Derechos de las mujeres\n" + self.BASE6
        self.assertEqual(numeros(texto), [5, 6])
        self.assertTrue(articulo(texto, 5)["texto"].endswith("medidas de prevención."))

    def test_encabezado_con_ordinal_o_arabigo(self):
        for encabezado in ("Sección Primera De la prevención", "TÍTULO 3 Medidas", "Capítulo Único Disposiciones"):
            with self.subTest(encabezado=encabezado):
                texto = self.BASE5 + encabezado + " " + self.BASE6
                self.assertTrue(articulo(texto, 5)["texto"].endswith("medidas de prevención."))

    def test_una_oracion_final_que_menciona_un_capitulo_no_se_corta(self):
        texto = self.BASE5 + "Sección II de esta Ley se aplica de forma supletoria. " + self.BASE6
        self.assertTrue(articulo(texto, 5)["texto"].endswith("de forma supletoria."))

    def test_articulo_precedido_por_minuscula_sin_punto_no_se_pierde_en_texto_plano(self):
        texto = "ARTÍCULO 5. (X). Texto del artículo cinco con más palabras para validar sin punto final ARTÍCULO 6. (Y). Texto del seis con más palabras."
        self.assertEqual(numeros(texto), [5, 6])

    def test_referencia_en_mayusculas_tras_un_conector_no_divide_el_articulo(self):
        texto = self.BASE5 + "Se aplicará lo dispuesto según el ARTÍCULO 9. Además, se adoptarán otras medidas. " + self.BASE6
        self.assertEqual(numeros(texto), [5, 6])
        self.assertIn("Además, se adoptarán otras medidas.", articulo(texto, 5)["texto"])

    def test_referencia_al_inicio_de_una_oracion_no_trunca_el_articulo(self):
        texto = self.BASE5 + "Se aplicará. Artículo 5 de la presente Ley se aplica de forma supletoria. Además, se adoptarán otras medidas. " + self.BASE6
        self.assertEqual(numeros(texto), [5, 6])
        self.assertTrue(articulo(texto, 5)["texto"].endswith("otras medidas."))

    def test_referencia_titulada_a_mitad_de_oracion_no_divide(self):
        texto = self.BASE5 + "Lo señalado en el Artículo 5 de la presente Ley se mantiene. " + self.BASE6
        self.assertEqual(numeros(texto), [5, 6])

    def test_encabezado_real_con_espacio_y_mayuscula_sigue_detectandose(self):
        texto = "Artículo 7 Los derechos de las mujeres son irrenunciables y exigibles.\nArtículo 8 El Estado garantiza la aplicación de esta norma."
        self.assertEqual(numeros(texto), [7, 8])

    def test_numeracion_repetida_no_pisa_el_primer_articulo(self):
        texto = self.BASE5 + self.BASE6 + " ARTÍCULO 5. (OTRO). Texto de una disposición transitoria distinta."
        arts = dividir_por_articulos(texto)
        self.assertEqual([a["numero"] for a in arts], [5, 6])
        self.assertEqual(arts[0]["titulo"], "Art. 5 - PREVENCIÓN")
