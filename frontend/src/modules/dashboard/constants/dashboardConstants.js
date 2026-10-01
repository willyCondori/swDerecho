// modules/dashboard/constants/dashboardConstants.js

export const PIPELINE_STEPS = [
  { key: 'chunking',   label: 'Chunking',         icon: 'ti-scissors' },
  { key: 'embeddings', label: 'Embeddings',        icon: 'ti-vector' },
  { key: 'ranking',    label: 'Ranking jurídico',  icon: 'ti-sort-descending' },
]

export const PIPELINE_WIDTH = {
  done:    '100%',
  active:  '55%',
  waiting: '0%',
}

// El mock de "artículos más aplicados" que vivía acá ya no hace falta:
// ArticulosCard ahora recibe normas_mas_consultadas real desde
// GET /api/dashboard/resumen/ (ver useDashboardResumen).

export const QUICK_ACCESS_ITEMS = [
  { icon: 'ti-folder-plus', label: 'Nuevo caso',      path: '/casos/nuevo' },
  { icon: 'ti-user-plus',   label: 'Nuevo cliente',   path: '/clientes/nuevo' },
  { icon: 'ti-books',       label: 'Administrar normas', path: '/catalogo/normas', adminOnly: true },
]