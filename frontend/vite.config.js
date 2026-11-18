import { fileURLToPath, URL } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

// The frontend calls the API at /api, on its own origin: no machine-specific
// URL in the code. In development, this proxy forwards /api to the backend
// (VITE_API_PROXY, http://localhost:8000 by default); in Docker, nginx does.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  return {
    plugins: [react()],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: {
      port: 5173,
      proxy: {
        // The Host header is kept, so that a redirect from the backend stays
        // on this origin (a cross-origin redirect drops the Authorization header).
        '/api': { target: env.VITE_API_PROXY || 'http://localhost:8000' },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
  };
});
