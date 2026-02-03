import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:9080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/status': 'http://localhost:9080',
      '/devices': 'http://localhost:9080',
      '/protocols': 'http://localhost:9080',
      '/simulation': 'http://localhost:9080',
      '/export': 'http://localhost:9080',
      '/mqtt': 'http://localhost:9080',
      '/metrics': 'http://localhost:9080',
      '/health': 'http://localhost:9080',
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
