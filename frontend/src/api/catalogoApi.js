// api/catalogoApi.js
import api from './axiosInstance'

const catalogoApi = {
  ramas:      ()       => api.get('/api/catalogo/ramas/lista/'),
  jerarquias: ()       => api.get('/api/catalogo/jerarquias/lista/'),
  normas:     ()       => api.get('/api/catalogo/normas/lista/'),
  articulos:  (params) => api.get('/api/catalogo/articulos/', { params }),
  // api/catalogoApi.js
  listaRamas() {
    return api.get('/api/catalogo/ramas/lista/')
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
}

export default catalogoApi
