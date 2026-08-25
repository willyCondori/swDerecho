// App.jsx
import { BrowserRouter } from 'react-router-dom'
import AppRouter from './routes/AppRouter'
import './styles/global.css'
import './styles/App.css'

// Tabler Icons CDN
const tablerLink = document.createElement('link')
tablerLink.rel  = 'stylesheet'
tablerLink.href = 'https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/dist/tabler-icons.min.css'
document.head.appendChild(tablerLink)

export default function App() {
  return (
    <BrowserRouter>
      <AppRouter />
    </BrowserRouter>
  )
}