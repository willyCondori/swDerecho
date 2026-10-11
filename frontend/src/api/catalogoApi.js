// api/catalogoApi.js
import api from './axiosInstance'
import cachedGet from './cachedGet'

const catalogoApi = {
  ramas:      ()       => cachedGet('/api/catalogo/ramas/lista/'),
  jerarquias: ()       => cachedGet('/api/catalogo/jerarquias/lista/'),
  normas:     ()       => cachedGet('/api/catalogo/normas/lista/'),
  articulos:  (params, signal) => api.get('/api/catalogo/articulos/', { params, signal }),
  articulo:   (id)     => api.get(`/api/catalogo/articulos/${id}/`),
  // api/catalogoApi.js
  listaRamas() {
    return cachedGet('/api/catalogo/ramas/lista/')
  },

  // ========= ADMINISTRACIÓN DE CATÁLOGO (solo admin) =========
  // Listados completos (incluyen descripción/estado/nivel), a diferencia
  // de ramas()/jerarquias() de arriba que devuelven la versión compacta
  // usada en los <select> del resto de la app.
  listarRamasCompleto:      (params = {}) => api.get('/api/catalogo/ramas/', { params }),
  crearRama:                (data)        => api.post('/api/catalogo/ramas/', data),
  actualizarRama:           (id, data)    => api.patch(`/api/catalogo/ramas/${id}/`, data),
  eliminarRama:              (id)          => api.delete(`/api/catalogo/ramas/${id}/`),
  activarRama:               (id)          => api.post(`/api/catalogo/ramas/${id}/activar/`),

  listarJerarquiasCompleto: (params = {}) => api.get('/api/catalogo/jerarquias/', { params }),
  crearJerarquia:           (data)        => api.post('/api/catalogo/jerarquias/', data),
  actualizarJerarquia:      (id, data)    => api.patch(`/api/catalogo/jerarquias/${id}/`, data),
  eliminarJerarquia:         (id)          => api.delete(`/api/catalogo/jerarquias/${id}/`),
  activarJerarquia:          (id, data = {}) => api.post(`/api/catalogo/jerarquias/${id}/activar/`, data),

  // Normas: solo se listan, se eliminan (borrado lógico) y se restauran.
  // Se crean al cargar un PDF de artículos.
  listarNormasCompleto:    (params = {}) => api.get('/api/catalogo/normas/', { params }),
  actualizarNorma: (id, datos) => api.patch(`/api/catalogo/normas/${id}/`, datos),
  eliminarNorma:            (id)          => api.delete(`/api/catalogo/normas/${id}/`),
  activarNorma:             (id)          => api.post(`/api/catalogo/normas/${id}/activar/`),

  listarEntidadesCompleto: (params = {}) => api.get('/api/catalogo/entidades/', { params }),
  crearEntidad:            (data)        => api.post('/api/catalogo/entidades/', data),
  actualizarEntidad:       (id, data)    => api.patch(`/api/catalogo/entidades/${id}/`, data),
  eliminarEntidad:          (id)          => api.delete(`/api/catalogo/entidades/${id}/`),
  activarEntidad:           (id)          => api.post(`/api/catalogo/entidades/${id}/activar/`),

  // Documentos de norma: los PDF que se subieron para extraer artículos
  // (ver CargaArticulosView, que crea el registro). No hay endpoint de
  // creación acá — solo consultar, descargar o eliminar.
  documentosPorNorma:      (normaId)      => api.get('/api/catalogo/documentos-norma/por_norma/', { params: { norma_id: normaId } }),
  listarDocumentosNorma:   (params, signal) => api.get('/api/catalogo/documentos-norma/', { params, signal }),
  descargarDocumentoNorma: (id, signal)   => api.get(`/api/catalogo/documentos-norma/${id}/descargar/`, { responseType: 'blob', signal }),
  eliminarDocumentoNorma:   (id)           => api.delete(`/api/catalogo/documentos-norma/${id}/`),
}

export default catalogoApi
