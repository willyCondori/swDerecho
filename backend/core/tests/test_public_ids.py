import uuid
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase
from core.encryption.aes_encryption import encrypt
from modulo_clientes.models.cliente import Cliente
from modulo_casos.models.caso import Caso
from modulo_catalogo.models.rama import RamaDerecho
from modulo_documentos.models.documento import DocumentoCaso, TipoDoc
from modulo_notificaciones.models import Notificacion
from modulo_usuarios.tests.factories import crear_rol, crear_usuario, crear_perfil

class UUIDPublicosTests(APITestCase):
    def setUp(self):
        self.usuario = crear_usuario('uuidabogado', rol=crear_rol('Abogado'))
        self.otro = crear_usuario('uuidotro', rol=crear_rol('Abogado'))
        crear_perfil(self.usuario)
        self.cliente = Cliente.objects.create(nombres=encrypt('Ana'), apellidos=encrypt('Perez'))
        self.rama = RamaDerecho.objects.create(nombre='Penal')
        self.caso = Caso.objects.create(codigo='UUID-TEST', titulo='Caso de prueba',
            descripcion='Me robaron con cuchillo', cliente=self.cliente, usuario=self.usuario,
            rama_detectada=self.rama)
        self.client.force_authenticate(self.usuario)

    def test_listados_y_relaciones_publican_uuid(self):
        res = self.client.get(f'/api/casos/{self.caso.public_id}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['id'], str(self.caso.public_id))
        self.assertEqual(res.data['cliente']['id'], str(self.cliente.public_id))
        self.assertEqual(res.data['usuario']['id'], str(self.usuario.public_id))
        self.assertEqual(res.data['usuario']['perfil']['usuario'], str(self.usuario.public_id))
        uuid.UUID(res.data['usuario']['perfil']['id'])
        self.assertEqual(self.client.get(f'/api/clientes/{self.cliente.public_id}/').status_code, 200)

    def test_numeros_no_son_identificadores_publicos(self):
        for ruta in [f'/api/casos/{self.caso.pk}/', f'/api/clientes/{self.cliente.pk}/',
                     f'/api/usuarios/{self.usuario.pk}/']:
            self.assertEqual(self.client.get(ruta).status_code, 404)
        res = self.client.post('/api/casos/', {'titulo':'Caso adicional',
            'descripcion':'Descripción del caso adicional', 'cliente_id':self.cliente.pk,
            'rama_detectada_id':self.rama.pk}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_creacion_filtros_y_seguimiento_con_uuid(self):
        res = self.client.post('/api/casos/', {'titulo':'Caso adicional',
            'descripcion':'Descripción del caso adicional', 'cliente_id':str(self.cliente.public_id),
            'rama_detectada_id':self.rama.pk}, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        creado = Caso.objects.get(public_id=res.data['id'])
        self.assertEqual(creado.cliente_id, self.cliente.pk)
        res = self.client.get('/api/casos/', {'cliente_id':str(self.cliente.public_id)})
        self.assertEqual(res.data['count'], 2)
        self.assertEqual(self.client.get('/api/casos/', {'cliente_id':'incorrecto'}).data['count'],0)
        res = self.client.post(f'/api/casos/{creado.public_id}/cambiar_etapa/',
            {'etapa':'en_analisis', 'nota':'Revisión inicial'},format='json')
        self.assertEqual(res.status_code, 201, res.data)

    def test_uuid_no_omite_autenticacion_ni_roles(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f'/api/casos/{self.caso.public_id}/').status_code,401)
        asistente = crear_usuario('uuidasistente',rol=crear_rol('Asistente'))
        self.client.force_authenticate(asistente)
        self.assertEqual(self.client.delete(f'/api/casos/{self.caso.public_id}/').status_code,403)
        self.caso.refresh_from_db()
        self.assertTrue(self.caso.estado)

    def test_notificaciones_aisladas_y_enlazan_uuid_del_caso(self):
        n = Notificacion.objects.create(usuario=self.usuario, tipo='analisis_completado',
            titulo='Análisis completo',mensaje='Prueba',caso=self.caso)
        res=self.client.get('/api/notificaciones/')
        fila=next(f for f in res.data['results'] if f['id']==str(n.public_id))
        self.assertEqual(fila['caso'],str(self.caso.public_id))
        self.client.force_authenticate(self.otro)
        self.assertEqual(self.client.post(f'/api/notificaciones/{n.public_id}/marcar_leida/').status_code,404)
        n.refresh_from_db(); self.assertFalse(n.leida)

    def test_documentos_filtran_caso_y_descargan_por_uuid(self):
        doc=DocumentoCaso.objects.create(caso=self.caso,nombre_original='prueba.pdf',
            ruta_archivo='inexistente.pdf',tamano=5,tipo_archivo='pdf',
            tipo_documento=TipoDoc.objects.create(tipo='uuidprueba'))
        res=self.client.get('/api/documentos/documentos/por_caso/',{'caso_id':str(self.caso.public_id)})
        self.assertEqual(res.status_code,200)
        self.assertEqual(res.data[0]['id'],str(doc.public_id))
        self.assertEqual(res.data[0]['caso'],str(self.caso.public_id))
        self.assertEqual(self.client.get(f'/api/documentos/documentos/{doc.pk}/').status_code,404)

    def test_uuid_unico_y_estable_al_editar(self):
        original=self.cliente.public_id
        self.cliente.nombres=encrypt('Maria'); self.cliente.save()
        self.cliente.refresh_from_db(); self.assertEqual(original,self.cliente.public_id)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cliente.objects.create(public_id=original,nombres=encrypt('Otra'),apellidos=encrypt('Persona'))

    def test_estado_ligero_no_serializa_cliente_y_cuesta_una_consulta(self):
        with self.assertNumQueries(1):
            res=self.client.get(f'/api/casos/{self.caso.public_id}/estado_analisis/')
        self.assertEqual(res.status_code,200)
        self.assertEqual(res.data['id'],str(self.caso.public_id))
        self.assertNotIn('cliente',res.data)
        self.assertNotIn('descripcion',res.data)
