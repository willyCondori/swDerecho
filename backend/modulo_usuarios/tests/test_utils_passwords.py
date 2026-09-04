import re

from django.test import SimpleTestCase

from core.utils.passwords import generar_password_aleatoria
from modulo_usuarios.serializers.auth_serializer import validar_fortaleza_password


class GenerarPasswordAleatoriaTests(SimpleTestCase):
    """
    core/utils/passwords.py: generador de contraseñas temporales
    usado al crear un usuario y en la recuperación por correo.
    """

    def test_longitud_por_defecto_es_12(self):
        self.assertEqual(len(generar_password_aleatoria()), 12)

    def test_respeta_longitud_solicitada(self):
        self.assertEqual(len(generar_password_aleatoria(20)), 20)

    def test_longitud_menor_a_8_se_ajusta_a_8(self):
        # El generador nunca debe entregar algo más débil que el
        # mínimo que el propio backend exige en validar_fortaleza_password.
        self.assertEqual(len(generar_password_aleatoria(4)), 8)
        self.assertEqual(len(generar_password_aleatoria(0)), 8)
        self.assertEqual(len(generar_password_aleatoria(-5)), 8)

    def test_contiene_las_cuatro_categorias_obligatorias(self):
        for _ in range(30):
            password = generar_password_aleatoria()
            self.assertRegex(password, r"[A-Z]", "Falta una mayúscula")
            self.assertRegex(password, r"[a-z]", "Falta una minúscula")
            self.assertRegex(password, r"\d", "Falta un número")
            self.assertRegex(password, r"[!@#$%^&*()_+\-=]", "Falta un carácter especial")

    def test_excluye_caracteres_ambiguos(self):
        # 0/O, 1/l/I se excluyen a propósito para que la contraseña se
        # pueda transcribir a mano sin errores.
        ambiguos = set("0O1lI")
        for _ in range(30):
            password = generar_password_aleatoria()
            self.assertFalse(
                ambiguos.intersection(password),
                f"La contraseña '{password}' contiene un carácter ambiguo",
            )

    def test_pasa_siempre_la_validacion_de_fortaleza_del_backend(self):
        # Nunca debe generarse una contraseña que el propio backend
        # rechazaría al intentar usarla (ver CambioPasswordSerializer /
        # ConfirmarRecuperacionSerializer).
        for _ in range(30):
            password = generar_password_aleatoria()
            try:
                validar_fortaleza_password(password)
            except Exception as exc:  # pragma: no cover - solo para el mensaje de falla
                self.fail(f"'{password}' no pasó validar_fortaleza_password: {exc}")

    def test_genera_valores_distintos_en_llamadas_sucesivas(self):
        generadas = {generar_password_aleatoria() for _ in range(20)}
        # Con un generador criptográfico de 12 caracteres la
        # probabilidad de colisión en 20 intentos es despreciable.
        self.assertGreater(len(generadas), 1)

    def test_solo_usa_caracteres_del_alfabeto_permitido(self):
        permitidos = re.compile(r"^[A-Za-z0-9!@#$%^&*()_+\-=]+$")
        password = generar_password_aleatoria()
        self.assertRegex(password, permitidos)
