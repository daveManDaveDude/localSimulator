import { defineConfig } from 'vite';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { copySharePublicAssets } from './scripts/share-assets';

export default defineConfig(({ mode }) => {
  const shareableBuild = mode === 'share';

  return {
    server: {
      host: '127.0.0.1',
    },
    publicDir: shareableBuild ? false : 'public',
    plugins: shareableBuild
      ? [
          {
            name: 'copy-public-assets-without-local-real-worlds',
            closeBundle() {
              copySharePublicAssets(resolve('public'), resolve('dist'));
            },
          },
        ]
      : [],
    build: {
      rollupOptions: {
        input: {
          app: fileURLToPath(new URL('./index.html', import.meta.url)),
          progress: fileURLToPath(new URL('./progress.html', import.meta.url)),
        },
      },
    },
  };
});
