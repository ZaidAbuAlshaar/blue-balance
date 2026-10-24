import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

const backend = 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': backend, '/chips': backend } },
  preview: { proxy: { '/api': backend, '/chips': backend } },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 2000,
    // FastAPI (Python 3.11 mimetypes) serves .mjs as text/plain, which blocks module workers: emit the MapLibre worker as .js.
    rollupOptions: {
      output: {
        assetFileNames: (info: { names?: string[]; name?: string }) =>
          (info.names?.[0] ?? info.name ?? '').endsWith('.mjs') ? 'assets/[name]-[hash].js' : 'assets/[name]-[hash][extname]',
      },
    },
  },
  test: { include: ['src/**/*.test.ts'], environment: 'node' },
});
