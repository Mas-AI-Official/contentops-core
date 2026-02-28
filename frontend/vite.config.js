import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Backend port: launch.bat sets VITE_API_PROXY_TARGET; default 8100 to match backend
const apiTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8100'

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.VITE_PORT) || 3005,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/outputs': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
