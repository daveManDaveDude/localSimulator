import { defineConfig } from 'vite';
import { cpSync } from 'node:fs';
import { resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

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
            name: 'copy-public-assets-without-local-ea-terrain',
            closeBundle() {
              const localTerrain = resolve('public/worlds/torquay-poc-001');
              cpSync(resolve('public'), resolve('dist'), {
                recursive: true,
                force: true,
                filter: (source) => {
                  const candidate = resolve(source);
                  return (
                    candidate !== localTerrain &&
                    !candidate.startsWith(`${localTerrain}${sep}`)
                  );
                },
              });
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
