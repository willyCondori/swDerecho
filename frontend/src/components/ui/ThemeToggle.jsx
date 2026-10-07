import { useEffect, useState } from 'react'
import { Sun, Moon } from 'lucide-react'
import { applyTheme, initialTheme, THEME_KEY } from '../../styles/theme'
import styles from './ThemeToggle.module.css'

export default function ThemeToggle() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || initialTheme())
  useEffect(() => {
    const sync = (event) => {
      if (event.key === THEME_KEY) setTheme(applyTheme(initialTheme(), false))
    }
    window.addEventListener('storage', sync)
    return () => window.removeEventListener('storage', sync)
  }, [])
  const label = theme === 'dark' ? 'Activar tema de día' : 'Activar tema de noche'
  return <button type="button" className={styles.toggle} title={label} aria-label={label}
    onClick={() => setTheme(applyTheme(theme === 'dark' ? 'light' : 'dark'))}>
    {theme === 'dark' ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
    <span>{theme === 'dark' ? 'Día' : 'Noche'}</span>
  </button>
}
