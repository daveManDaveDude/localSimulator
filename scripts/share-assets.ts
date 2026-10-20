import { cpSync, lstatSync } from 'node:fs';
import { isAbsolute, relative, resolve, sep } from 'node:path';

const SHARE_ROOT_FILES = new Set(['favicon.svg', 'project-progress.json']);
const SHARE_WORLD_FILES = new Set([
  'worlds/synthetic-heightfield/manifest.json',
  'worlds/synthetic-heightfield/heightfield.f32',
  'worlds/synthetic-terrain-demo/manifest.json',
  'worlds/synthetic-terrain-demo/heightfield.f32',
]);
const SHARE_DIRECTORIES = new Set([
  '',
  'worlds',
  'worlds/synthetic-heightfield',
  'worlds/synthetic-terrain-demo',
]);

/** Return true only for reviewed static assets that belong in a share build. */
export function isSharePublicAsset(source: string, publicRoot: string): boolean {
  const root = resolve(publicRoot);
  const candidate = resolve(source);
  const localPath = relative(root, candidate);
  if (
    isAbsolute(localPath) ||
    localPath === '..' ||
    localPath.startsWith(`..${sep}`)
  ) {
    return false;
  }

  const relativePath = localPath.split(sep).join('/');
  if (
    !SHARE_DIRECTORIES.has(relativePath) &&
    !SHARE_ROOT_FILES.has(relativePath) &&
    !SHARE_WORLD_FILES.has(relativePath)
  ) {
    return false;
  }

  let current = root;
  for (const segment of relativePath === '' ? [] : relativePath.split('/')) {
    current = resolve(current, segment);
    try {
      if (lstatSync(current).isSymbolicLink()) return false;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error;
      return false;
    }
  }
  return true;
}

/** Copy only the fixed, reviewed static files needed by offline share mode. */
export function copySharePublicAssets(
  publicRoot: string,
  buildRoot: string,
): void {
  const root = resolve(publicRoot);
  cpSync(root, resolve(buildRoot), {
    recursive: true,
    force: true,
    filter: (source) => isSharePublicAsset(source, root),
  });
}
