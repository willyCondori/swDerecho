export const THEME_KEY = 'litigiun-theme'

export function initialTheme() {
  try {
    const saved = localStorage.getItem(THEME_KEY)
    if (saved === 'light' || saved === 'dark') return saved
  } catch { /* El tema funciona también sin almacenamiento disponible. */ }
  return 'dark'
}

export function applyTheme(theme, persist = true) {
  const selected = theme === 'light' ? 'light' : 'dark'
  document.documentElement.dataset.theme = selected
  if (persist) {
    try { localStorage.setItem(THEME_KEY, selected) } catch { /* Preferencia solo en esta sesión. */ }
  }
  return selected
}
