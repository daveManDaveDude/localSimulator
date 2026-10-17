import { decodeFloat32Heightfield } from '../geo/heightfield';
import {
  isSafeLocalAssetPath,
  validateSceneManifest,
  type RealTerrainSceneManifest,
  type SyntheticSceneManifest,
} from '../geo/sceneSchema';

export type WorldLoadStage =
  | 'manifest URL'
  | 'manifest request'
  | 'manifest response'
  | 'manifest validation'
  | 'heightfield URL'
  | 'heightfield request'
  | 'heightfield response'
  | 'heightfield checksum'
  | 'heightfield decode';

export class WorldLoadError extends Error {
  constructor(
    readonly stage: WorldLoadStage,
    message: string,
  ) {
    super(`${stage}: ${message}`);
    this.name = 'WorldLoadError';
  }
}

export interface LoadedSyntheticWorld {
  manifest: SyntheticSceneManifest;
  heights: Float32Array;
}

export interface LoadedRealWorld {
  manifest: RealTerrainSceneManifest;
  heights: Float32Array;
}

export type LoadedWorld = LoadedSyntheticWorld | LoadedRealWorld;

export type WorldFetch = (input: URL, init?: RequestInit) => Promise<Response>;

const browserFetch: WorldFetch = (input, init) => globalThis.fetch(input, init);

function messageFrom(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function resolveManifestUrl(input: string | URL): URL {
  try {
    const value = input instanceof URL ? input.href : input;
    const base = typeof document === 'undefined' ? undefined : document.baseURI;
    const url = base === undefined ? new URL(value) : new URL(value, base);
    if (url.protocol !== 'http:' && url.protocol !== 'https:') {
      throw new Error('only local HTTP(S) manifest URLs are supported');
    }
    if (url.username !== '' || url.password !== '') {
      throw new Error('credentials are not allowed in manifest URLs');
    }
    if (typeof location !== 'undefined' && url.origin !== location.origin) {
      throw new Error('manifest must be served from the current local origin');
    }
    return url;
  } catch (error) {
    throw new WorldLoadError('manifest URL', messageFrom(error));
  }
}

function resolveAssetUrl(manifestUrl: URL, path: string): URL {
  if (!isSafeLocalAssetPath(path)) {
    throw new WorldLoadError(
      'heightfield URL',
      'asset path is not a safe local relative path',
    );
  }

  try {
    const directory = new URL('.', manifestUrl);
    const assetUrl = new URL(path, directory);
    if (
      assetUrl.origin !== directory.origin ||
      !assetUrl.pathname.startsWith(directory.pathname)
    ) {
      throw new Error('asset path escapes the manifest directory');
    }
    return assetUrl;
  } catch (error) {
    throw new WorldLoadError('heightfield URL', messageFrom(error));
  }
}

async function fetchResponse(
  fetcher: WorldFetch,
  url: URL,
  stage: 'manifest request' | 'heightfield request',
  signal?: AbortSignal,
): Promise<Response> {
  let response: Response;
  try {
    response = await fetcher(
      url,
      signal === undefined ? undefined : { signal },
    );
  } catch (error) {
    throw new WorldLoadError(
      stage,
      `request failed for ${url.href}: ${messageFrom(error)}`,
    );
  }

  if (!response.ok) {
    throw new WorldLoadError(
      stage,
      `request for ${url.href} returned HTTP ${response.status}`,
    );
  }
  return response;
}

async function sha256Hex(bytes: ArrayBuffer): Promise<string> {
  let digest: ArrayBuffer;
  try {
    digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  } catch (error) {
    throw new WorldLoadError(
      'heightfield checksum',
      `Web Crypto could not calculate SHA-256: ${messageFrom(error)}`,
    );
  }

  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
}

/** Load and validate one local v1 world without creating Three.js objects. */
export async function loadWorld(
  manifestLocation: string | URL,
  fetcher: WorldFetch = browserFetch,
  signal?: AbortSignal,
): Promise<LoadedWorld> {
  const manifestUrl = resolveManifestUrl(manifestLocation);
  const manifestResponse = await fetchResponse(
    fetcher,
    manifestUrl,
    'manifest request',
    signal,
  );

  let unknownManifest: unknown;
  try {
    unknownManifest = await manifestResponse.json();
  } catch (error) {
    throw new WorldLoadError(
      'manifest response',
      `response was not valid JSON: ${messageFrom(error)}`,
    );
  }

  const validation = validateSceneManifest(unknownManifest);
  if (!validation.ok) {
    const detail = validation.issues
      .map(({ path, message }) => `${path}: ${message}`)
      .join('; ');
    throw new WorldLoadError('manifest validation', detail);
  }

  const heightfieldUrl = resolveAssetUrl(
    manifestUrl,
    validation.manifest.heightfield.path,
  );
  const heightfieldResponse = await fetchResponse(
    fetcher,
    heightfieldUrl,
    'heightfield request',
    signal,
  );

  let bytes: ArrayBuffer;
  try {
    bytes = await heightfieldResponse.arrayBuffer();
  } catch (error) {
    throw new WorldLoadError(
      'heightfield response',
      `could not read response bytes: ${messageFrom(error)}`,
    );
  }

  if (
    validation.manifest.worldType === 'real' &&
    bytes.byteLength !== validation.manifest.heightfield.byteLength
  ) {
    throw new WorldLoadError(
      'heightfield response',
      `byte length mismatch for ${heightfieldUrl.href}: expected ${validation.manifest.heightfield.byteLength}, received ${bytes.byteLength}`,
    );
  }

  const actualHash = await sha256Hex(bytes);
  if (actualHash !== validation.manifest.heightfield.sha256) {
    throw new WorldLoadError(
      'heightfield checksum',
      `SHA-256 mismatch for ${heightfieldUrl.href}: expected ${validation.manifest.heightfield.sha256}, received ${actualHash}`,
    );
  }

  let heights: Float32Array;
  try {
    heights = decodeFloat32Heightfield(bytes, {
      columns: validation.manifest.heightfield.columns,
      rows: validation.manifest.heightfield.rows,
    });
  } catch (error) {
    throw new WorldLoadError('heightfield decode', messageFrom(error));
  }

  return validation.manifest.worldType === 'synthetic'
    ? { manifest: validation.manifest, heights }
    : { manifest: validation.manifest, heights };
}

/** Preserve the typed synthetic-only loader used by the M0/M1 fixtures and tests. */
export async function loadSyntheticWorld(
  manifestLocation: string | URL,
  fetcher: WorldFetch = browserFetch,
  signal?: AbortSignal,
): Promise<LoadedSyntheticWorld> {
  const loaded = await loadWorld(manifestLocation, fetcher, signal);
  if (loaded.manifest.worldType !== 'synthetic') {
    throw new WorldLoadError(
      'manifest validation',
      'loadSyntheticWorld accepts only synthetic package manifests',
    );
  }
  return { manifest: loaded.manifest, heights: loaded.heights };
}
