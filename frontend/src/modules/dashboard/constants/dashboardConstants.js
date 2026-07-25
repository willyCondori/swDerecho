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

// TODO: reemplazar por fetch a /api/ia/ranking/resumen/ cuando el endpoint esté listo
export const TOP_ARTICULOS_MOCK = [
  { numero: 'Art. 251', titulo: 'Homicidio', count: 38, pct: 76 },
  { numero: 'Art. 331', titulo: 'Robo',      count: 29, pct: 58 },
  { numero: 'Art. 263', titulo: 'Lesiones',  count: 21, pct: 42 },
  { numero: 'Art. 335', titulo: 'Estafa',    count: 17, pct: 34 },
  { numero: 'Art. 272', titulo: 'Violencia', count: 14, pct: 28 },
]

export const QUICK_ACCESS_ITEMS = [
  { icon: 'ti-folder-plus', label: 'Nuevo caso',      path: '/casos/nuevo' },
  { icon: 'ti-user-plus',   label: 'Nuevo cliente',   path: '/clientes/nuevo' },
]