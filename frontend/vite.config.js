import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  root: '.',
  server: {
    host: 'localhost',
    port: 5173,
    strictPort: false,
    open: false,
    fs: {
      strict: false
    }
  },
  optimizeDeps: {
    include: []
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})