from rest_framework.test import APITestCase
from modulo_usuarios.tests.factories import crear_rol, crear_usuario
from modulo_usuarios.models.rol import Rol


class RolesEndpointsTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_rol = crear_rol('Administrador')
        cls.admin = crear_usuario('roles.admin', rol=cls.admin_rol)
        cls.abogado = crear_usuario('roles.abogado', rol=crear_rol('Abogado'))

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_anonimo_no_puede_listar(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/usuarios/roles/').status_code, 401)

    def test_abogado_puede_leer_pero_no_administrar(self):
        self.client.force_authenticate(self.abogado)
        self.assertEqual(self.client.get('/api/usuarios/roles/lista/').status_code, 200)
        self.assertEqual(self.client.post('/api/usuarios/roles/', {'nombre': 'Especialista'}).status_code, 403)

    def test_admin_no_se_desactiva_por_patch_ni_delete(self):
        url = f'/api/usuarios/roles/{self.admin_rol.pk}/'
        self.assertEqual(self.client.patch(url, {'estado': False}).status_code, 400)
        self.assertEqual(self.client.delete(url).status_code, 400)
        self.admin_rol.refresh_from_db()
        self.assertTrue(self.admin_rol.estado)

    def test_no_renombrar_rol_administrador(self):
        self.assertEqual(self.client.patch(f'/api/usuarios/roles/{self.admin_rol.pk}/', {'nombre': 'Visitante'}).status_code, 400)
        self.admin_rol.refresh_from_db()
        self.assertEqual(self.admin_rol.nombre, 'Administrador')

    def test_no_desactivar_rol_con_usuarios_activos_por_patch(self):
        self.assertEqual(self.client.patch(f'/api/usuarios/roles/{self.abogado.rol_id}/', {'estado': False}).status_code, 400)

    def test_eliminacion_logica_reactivacion_y_unicidad(self):
        res = self.client.post('/api/usuarios/roles/', {'nombre': 'Especialista', 'descripcion': 'Rol para pruebas administrativas.'})
        self.assertEqual(res.status_code, 201)
        pk = res.data['id']
        self.assertEqual(self.client.post('/api/usuarios/roles/', {'nombre': 'especialista'}).status_code, 400)
        self.assertEqual(self.client.delete(f'/api/usuarios/roles/{pk}/').status_code, 204)
        self.assertFalse(Rol.objects.get(pk=pk).estado)
        self.assertNotIn(pk, [r['id'] for r in self.client.get('/api/usuarios/roles/lista/').data])
        self.assertEqual(self.client.post(f'/api/usuarios/roles/{pk}/activar/').status_code, 200)
        self.assertTrue(Rol.objects.get(pk=pk).estado)
