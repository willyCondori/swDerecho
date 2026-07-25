// api/catalogoApi.js
import api from './axiosInstance'

const catalogoApi = {
  ramas:     ()       => api.get('/api/catalogo/ramas/lista/'),
  normas:    ()       => api.get('/api/catalogo/normas/lista/'),
  articulos: (params) => api.get('/api/catalogo/articulos/', { params }),
  // api/catalogoApi.js
  listaRamas() {
    return api.get('/api/catalogo/ramas/lista/')
  },
}

export default catalogoApi
