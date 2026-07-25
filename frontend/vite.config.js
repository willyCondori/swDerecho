import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173, // El puerto que definiste en el archivo de entorno del backend
  }
})
