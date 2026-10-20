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
            name: 'copy-public-assets-without-local-real-worlds',
            closeBundle() {
              const localWorlds = [
                resolve('public/worlds/torquay-poc-001'),
                resolve('public/worlds/torquay-poc-001-2km'),
              ];
              cpSync(resolve('public'), resolve('dist'), {
                recursive: true,
                force: true,
                filter: (source) => {
                  const candidate = resolve(source);
                  return !localWorlds.some(
                    (localWorld) =>
                      candidate === localWorld ||
                      candidate.startsWith(`${localWorld}${sep}`),
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
