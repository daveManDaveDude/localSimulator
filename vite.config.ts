import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  server: {
    host: '127.0.0.1',
  },
  build: {
    rollupOptions: {
      input: {
        app: fileURLToPath(new URL('./index.html', import.meta.url)),
        progress: fileURLToPath(new URL('./progress.html', import.meta.url)),
      },
    },
  },
});
