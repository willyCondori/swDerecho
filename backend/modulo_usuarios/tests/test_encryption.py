from django.test import SimpleTestCase

from core.encryption.aes_encryption import decrypt, encrypt, hash_lookup, safe_decrypt


class EncryptDecryptTests(SimpleTestCase):
    def test_roundtrip_conserva_el_texto_original(self):
        original = "Juan Pérez"
        cifrado = encrypt(original)
        self.assertNotEqual(cifrado, original)
        self.assertEqual(decrypt(cifrado), original)

    def test_encrypt_valor_vacio_devuelve_el_mismo_valor(self):
        self.assertEqual(encrypt(""), "")
        self.assertEqual(encrypt(None), None)

    def test_decrypt_valor_vacio_devuelve_el_mismo_valor(self):
        self.assertEqual(decrypt(""), "")

    def test_dos_cifrados_del_mismo_texto_son_distintos(self):
        # AES-GCM usa un nonce aleatorio en cada encrypt(): el mismo
        # texto plano nunca debe producir el mismo ciphertext dos
        # veces (por eso existe hash_lookup para poder buscar).
        original = "correo@example.com"
        self.assertNotEqual(encrypt(original), encrypt(original))

    def test_safe_decrypt_devuelve_fallback_si_falla(self):
        self.assertEqual(safe_decrypt("dato-corrupto-no-base64"), "[cifrado]")

    def test_safe_decrypt_devuelve_fallback_personalizado(self):
        self.assertEqual(
            safe_decrypt("dato-corrupto-no-base64", fallback="???"), "???"
        )

    def test_safe_decrypt_valor_falsy_no_lo_intenta_descifrar(self):
        self.assertEqual(safe_decrypt(""), "")
        self.assertIsNone(safe_decrypt(None))

    def test_safe_decrypt_valor_valido_lo_descifra(self):
        cifrado = encrypt("dato válido")
        self.assertEqual(safe_decrypt(cifrado), "dato válido")


class HashLookupTests(SimpleTestCase):
    def test_es_determinista(self):
        self.assertEqual(
            hash_lookup("juan@mail.com"), hash_lookup("juan@mail.com")
        )

    def test_normaliza_mayusculas_y_espacios(self):
        # "Juan@Mail.com" y " juan@mail.com " deben generar el mismo
        # hash que "juan@mail.com" para que la búsqueda por email no
        # dependa de cómo lo haya tipeado el usuario.
        base = hash_lookup("juan@mail.com")
        self.assertEqual(hash_lookup("Juan@Mail.com"), base)
        self.assertEqual(hash_lookup("  juan@mail.com  "), base)

    def test_valores_distintos_generan_hashes_distintos(self):
        self.assertNotEqual(hash_lookup("juan@mail.com"), hash_lookup("pedro@mail.com"))

    def test_valor_falsy_devuelve_none(self):
        self.assertIsNone(hash_lookup(""))
        self.assertIsNone(hash_lookup(None))

    def test_devuelve_hex_digest_de_64_caracteres(self):
        resultado = hash_lookup("juan@mail.com")
        self.assertEqual(len(resultado), 64)
        int(resultado, 16)  # no debe lanzar ValueError: es hex válido
