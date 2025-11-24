import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/variant': 'http://localhost:8000',
      '/gene': 'http://localhost:8000',
      '/region': 'http://localhost:8000',
      '/search': 'http://localhost:8000',
      '/stats': 'http://localhost:8000',
    }
  }
})
