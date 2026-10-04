from datetime import date
from django.test import TestCase
from modulo_catalogo.models import Norma, RamaDerecho, Articulo, DocumentoNorma, CambioNormativo, VersionArticulo
from modulo_catalogo.models.jerarquia import jerarquia
from modulo_catalogo.services.vigencia_service import registrar_cambios, confirmar, conservar_version, avisos_visibles, aviso
from modulo_catalogo.serializers.catalogo_serializer import ArticuloListSerializer
from modulo_usuarios.tests.factories import crear_rol, crear_usuario

class VigenciaNormativaTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario('revision.vigencia', rol=crear_rol('Administrador'))
        self.rama = RamaDerecho.objects.create(nombre='Penal')
        self.ley = jerarquia.objects.get_or_create(nombre='Ley', defaults={'nivel': 2})[0]
        self.base = Norma.objects.create(nombre='Decreto Ley 11080', tipo_norma='Decreto Ley', numero_norma='11080', fecha_norma=date(1973,9,19), jerarquia=self.ley)
        self.nueva = Norma.objects.create(nombre='Ley 2298', jerarquia=self.ley)
        self.doc = DocumentoNorma.objects.create(norma=self.nueva, rama=self.rama, nombre_original='2298.pdf', ruta_archivo='2298.pdf', tamano=10)
        self.articulo = Articulo.objects.create(norma=self.base, rama=self.rama, numero_articulo='25', contenido='Texto histórico', titulo='Título histórico')
        self.metadatos = {'tipo_norma': 'Ley', 'numero_norma': '2298', 'fecha_norma': '2001-12-20', 'url_fuente': 'http://www.gacetaoficialdebolivia.gob.bo/normas/verGratis_gob/123'}

    def registrar(self, **extra):
        c = {'operacion': 'abroga', 'norma': 'Decreto Ley No 11080', 'unidad': '', 'alcance': 'total',
             'cita': 'Queda abrogado el Decreto Ley No 11080.', 'origen': 'clausula',
             'causante': '', 'fecha_causante': '', 'unidad_fuente': 'DF TERCERA', **extra}
        registrar_cambios(self.doc, [], [c], self.metadatos)
        return CambioNormativo.objects.get(fuente=self.doc)

    def datos_revision(self, **extra):
        return {'fecha_efecto': '2001-12-21', 'observacion': 'Fecha, alcance y jerarquía contrastados en la fuente.', **extra}

    def test_abrogacion_de_norma_se_muestra_en_todos_sus_articulos_sin_borrarlos(self):
        c = self.registrar()
        self.articulo.refresh_from_db()
        c = confirmar(c, self.datos_revision(), self.usuario)
        self.articulo.refresh_from_db()
        data = ArticuloListSerializer(self.articulo).data
        self.assertTrue(self.articulo.estado)
        self.assertEqual(data['avisos_vigencia'][0]['estado'], 'confirmado')
        self.assertIn('Ley 2298', data['avisos_vigencia'][0]['mensaje'])
        self.assertEqual(data['avisos_vigencia'][0]['documento_id'], self.doc.pk)

    def test_no_confirma_norma_causante_anterior(self):
        self.metadatos['fecha_norma'] = '1970-01-01'
        c = self.registrar()
        with self.assertRaisesMessage(ValueError, 'posterior'):
            confirmar(c, self.datos_revision(fecha_efecto='1970-01-02'), self.usuario)
        c.refresh_from_db()
        self.assertEqual(c.estado_revision, 'pendiente')

    def test_no_confirma_sin_fecha_de_la_norma_afectada(self):
        self.base.fecha_norma = None; self.base.save()
        c = self.registrar()
        with self.assertRaisesMessage(ValueError, 'norma afectada'):
            confirmar(c, self.datos_revision(), self.usuario)

    def test_no_confirma_efecto_antes_de_norma_causante(self):
        c = self.registrar()
        with self.assertRaisesMessage(ValueError, 'fecha de efecto'):
            confirmar(c, self.datos_revision(fecha_efecto='2000-01-01'), self.usuario)

    def test_no_confirma_decreto_inferior_que_pretende_abrogar_ley(self):
        self.nueva.jerarquia = jerarquia.objects.get_or_create(nombre='Decreto Supremo', defaults={'nivel': 5})[0]; self.nueva.save()
        c = self.registrar()
        with self.assertRaisesMessage(ValueError, 'menor jerarquía'):
            confirmar(c, self.datos_revision(), self.usuario)

    def test_clausula_general_no_abroga_el_codigo_penal(self):
        c = self.registrar(operacion='general', norma='Decreto Ley 11080')
        self.assertIsNone(c.norma_afectada)
        self.base.refresh_from_db(); self.assertEqual(self.base.avisos_vigencia, [])
        with self.assertRaisesMessage(ValueError, 'general'):
            confirmar(c, self.datos_revision(), self.usuario)

    def test_articulo_ausente_no_se_convierte_en_abrogacion_de_norma_completa(self):
        c = self.registrar(operacion='deroga', unidad='999')
        self.assertIsNone(c.norma_afectada)
        self.base.refresh_from_db(); self.assertEqual(self.base.avisos_vigencia, [])

    def test_derogacion_parcial_advierte_solo_la_unidad_y_el_alcance(self):
        self.registrar(operacion='deroga', unidad='25', alcance='Parágrafo II')
        self.articulo.refresh_from_db(); self.base.refresh_from_db()
        self.assertFalse(self.base.avisos_vigencia)
        self.assertIn('Afectación parcial', self.articulo.avisos_vigencia[0]['mensaje'])
        self.assertIn('Parágrafo II', self.articulo.avisos_vigencia[0]['mensaje'])
        self.assertEqual(self.articulo.contenido, 'Texto histórico')

    def test_nota_historica_utiliza_fecha_y_ley_causante_no_fecha_editorial_del_pdf(self):
        transitoria = Articulo.objects.create(norma=self.nueva, rama=self.rama, numero_articulo='DT TERCERA', tipo_unidad='transitoria', contenido='TERCERA.- DEROGADO por Ley 2446')
        c = self.registrar(operacion='deroga', norma='', unidad='DT TERCERA', origen='nota_editorial', causante='Ley 2446', fecha_causante='2003-03-19')
        self.assertEqual(c.articulo_afectado, transitoria)
        self.assertEqual(c.fecha_norma_causante, date(2003,3,19))
        self.assertEqual(c.norma_causante, 'Ley 2446')

    def test_repetir_misma_deteccion_no_duplica_avisos(self):
        self.registrar(); self.registrar()
        self.assertEqual(CambioNormativo.objects.count(), 1)
        self.base.refresh_from_db(); self.assertEqual(len(self.base.avisos_vigencia), 1)

    def test_descartar_retira_aviso_sin_borrar_historial(self):
        c = self.registrar()
        confirmar(c, {'descartar': True}, self.usuario)
        self.base.refresh_from_db(); self.assertEqual(self.base.avisos_vigencia, [])
        self.assertTrue(CambioNormativo.objects.filter(pk=c.pk).exists())

    def test_cambio_con_fecha_futura_se_anuncia_como_futuro(self):
        c = self.registrar()
        confirmar(c, self.datos_revision(fecha_efecto='2099-01-01'), self.usuario)
        self.base.refresh_from_db()
        avisos = avisos_visibles(self.base.avisos_vigencia)
        self.assertEqual(avisos[0]['estado'], 'futuro')
        self.assertIn('efecto futuro', avisos[0]['mensaje'])

    def test_preserva_texto_anterior_e_id_del_articulo(self):
        conservar_version(self.articulo)
        self.articulo.contenido = 'Texto nuevo'; self.articulo.save()
        conservar_version(self.articulo); conservar_version(self.articulo)
        self.assertEqual(VersionArticulo.objects.count(), 2)
        self.assertTrue(VersionArticulo.objects.filter(contenido='Texto histórico', articulo=self.articulo).exists())


    def test_no_confirma_derogacion_parcial_sin_identificar_fragmento(self):
        c = self.registrar(operacion='deroga', unidad='25', alcance='Último párrafo', cita='Queda derogado el último párrafo del Artículo 25.')
        with self.assertRaisesMessage(ValueError, 'parte derogada'):
            confirmar(c, self.datos_revision(), self.usuario)

    def test_confirmacion_manual_exige_fragmento_exacto_y_preserva_restante(self):
        self.articulo.contenido = 'ARTÍCULO 25. Texto vigente. Fragmento afectado.'; self.articulo.save()
        c = self.registrar(operacion='deroga', unidad='25', alcance='Último párrafo', cita='Queda derogado el último párrafo del Artículo 25.')
        confirmar(c, self.datos_revision(fragmento_afectado='Fragmento afectado.'), self.usuario)
        self.articulo.refresh_from_db()
        self.assertIn('Texto vigente.', self.articulo.contenido)
        parte = self.articulo.avisos_vigencia[0]['parte_afectada']
        self.assertEqual(parte['tipo'], 'parcial')
        self.assertEqual(parte['partes'][0]['fragmento'], 'Fragmento afectado.')


    def test_destino_presente_avisa_pero_solo_marca_abrogada_despues_de_confirmar(self):
        from modulo_catalogo.views.vigencia_view import CambioSerializer
        from modulo_catalogo.serializers.catalogo_serializer import NormaListSerializer
        c = self.registrar()
        self.base.refresh_from_db()
        self.assertEqual(NormaListSerializer(self.base).data['estado_vigencia'], 'sin_derogacion_confirmada')
        data = CambioSerializer(c).data
        self.assertTrue(data['destino_catalogo']['encontrado'])
        self.assertIn('disposición final tercera', data['aviso']['mensaje'])
        self.assertEqual(data['disposicion_fuente'], 'disposición final tercera')
        confirmar(c, self.datos_revision(), self.usuario)
        self.base.refresh_from_db()
        self.assertEqual(NormaListSerializer(self.base).data['estado_vigencia'], 'abrogada')

    def test_norma_ausente_es_solo_aviso_y_no_permite_forzar_otro_destino(self):
        from modulo_catalogo.views.vigencia_view import CambioSerializer
        c = self.registrar(norma='Ley 99999')
        data = CambioSerializer(c).data
        self.assertFalse(data['destino_catalogo']['encontrado'])
        self.assertIn('Solo aviso', data['destino_catalogo']['mensaje'])
        self.assertIn('Ley 99999', data['aviso']['mensaje'])
        with self.assertRaisesMessage(ValueError, 'Solo aviso'):
            confirmar(c, self.datos_revision(norma_afectada_id=self.base.pk), self.usuario)
        c.refresh_from_db()
        self.assertEqual(c.estado_revision, 'pendiente')

    def test_articulo_ausente_no_puede_confirmarse_como_otro_articulo(self):
        c = self.registrar(operacion='deroga', unidad='999')
        with self.assertRaisesMessage(ValueError, 'Solo aviso'):
            confirmar(c, self.datos_revision(norma_afectada_id=self.base.pk,
                      articulo_afectado_id=self.articulo.pk), self.usuario)
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.avisos_vigencia, [])

    def test_derogacion_parcial_confirmada_no_marca_articulo_completo(self):
        self.articulo.contenido = 'I. Texto conservado.\nII. Texto derogado.'
        self.articulo.save()
        c = self.registrar(operacion='deroga', unidad='25', alcance='Parágrafo II',
                          cita='Queda derogado el Parágrafo II del Artículo 25.')
        confirmar(c, self.datos_revision(), self.usuario)
        self.articulo.refresh_from_db()
        self.assertEqual(ArticuloListSerializer(self.articulo).data['estado_vigencia'], 'derogado_parcialmente')
        self.assertIn('I. Texto conservado.', self.articulo.contenido)

    def test_aviso_sin_destino_se_puede_confirmar_cuando_se_carga_la_norma(self):
        c = self.registrar(norma='Ley 99999')
        destino = Norma.objects.create(nombre='Ley 99999', tipo_norma='Ley', numero_norma='99999',
                                       fecha_norma=date(1990, 1, 1), jerarquia=self.ley)
        Articulo.objects.create(norma=destino, rama=self.rama, numero_articulo='1', contenido='Texto cargado')
        confirmar(c, self.datos_revision(), self.usuario)
        c.refresh_from_db()
        self.assertEqual(c.norma_afectada, destino)
        self.assertEqual(c.estado_revision, 'confirmado')

    def test_fecha_futura_no_marca_abrogada_antes_de_entrar_en_efecto(self):
        from modulo_catalogo.serializers.catalogo_serializer import NormaListSerializer
        c = self.registrar()
        confirmar(c, self.datos_revision(fecha_efecto='2099-01-01'), self.usuario)
        self.base.refresh_from_db()
        self.assertEqual(NormaListSerializer(self.base).data['estado_vigencia'], 'sin_derogacion_confirmada')

    def test_revision_previa_identifica_causa_y_existencia_sin_modificar_catalogo(self):
        from modulo_catalogo.services.vigencia_service import preparar_avisos_revision
        cambios = [{'operacion': 'abroga', 'norma': 'Decreto Ley 11080', 'unidad': '',
                    'origen': 'clausula', 'unidad_fuente': 'DF TERCERA'},
                   {'operacion': 'deroga', 'norma': 'Decreto Ley 11080', 'unidad': '999',
                    'origen': 'clausula', 'unidad_fuente': 'DD ÚNICA'}]
        avisos = preparar_avisos_revision(cambios, self.metadatos)
        self.assertTrue(avisos[0]['destino_catalogo']['encontrado'])
        self.assertFalse(avisos[1]['destino_catalogo']['encontrado'])
        self.assertEqual(avisos[0]['norma_causante'], 'Ley 2298')
        self.assertEqual(avisos[0]['disposicion_fuente'], 'disposición final tercera')
        self.assertEqual(CambioNormativo.objects.count(), 0)

    def test_aviso_temporal_no_presenta_articulo_vacio_ni_derogacion(self):
        c = self.registrar(operacion='temporal', norma='', unidad='', alcance='Plazo de 90 días')
        mensaje = aviso(c)['mensaje']
        self.assertIn('Regla de vigencia o plazo', mensaje)
        self.assertNotIn('Afectación parcial', mensaje)
        self.assertNotIn('pendiente de verificación', mensaje)

    def test_aviso_identifica_destino_ausente_sin_aplicar_efecto(self):
        c = self.registrar(operacion='deroga', unidad='281 QUATER')
        data = aviso(c)
        self.assertFalse(data['destino_catalogo']['encontrado'])
        self.assertEqual(c.estado_revision, 'pendiente')
        self.assertIsNone(c.articulo_afectado_id)

    def test_nota_sin_causante_no_atribuye_codigo_original_ni_permite_confirmar(self):
        self.doc.norma = self.base
        self.doc.save(update_fields=['norma'])
        c = self.registrar(operacion='deroga', origen='nota_editorial', norma='', unidad='25',
                          causante='', fecha_causante='2001-12-20', cita='Artículo 25. Derogado por norma no identificada.')
        self.assertIn('norma causante por verificar', aviso(c)['mensaje'])
        with self.assertRaisesMessage(ValueError, 'Identifica la norma causante'):
            confirmar(c, self.datos_revision(), self.usuario)
