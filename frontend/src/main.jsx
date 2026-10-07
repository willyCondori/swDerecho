// main.jsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import DialogHost from './components/ui/DialogHost'
import { applyTheme, initialTheme } from './styles/theme'

applyTheme(initialTheme(), false)

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
    <DialogHost />
  </StrictMode>,
)
