import { decodeFloat32Heightfield } from '../geo/heightfield';
import { MAX_HEIGHTFIELD_SAMPLES } from '../geo/sceneSchema';
import {
  isSafeLocalAssetPath,
  validateSceneManifest,
  type RealTerrainSceneManifest,
  type SyntheticSceneManifest,
} from '../geo/sceneSchema';
import type { SceneReleaseIntegrity } from './sceneRelease';

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
  manifestSha256: string;
}

export type LoadedWorld = LoadedSyntheticWorld | LoadedRealWorld;

export type WorldFetch = (input: URL, init?: RequestInit) => Promise<Response>;

const browserFetch: WorldFetch = (input, init) => globalThis.fetch(input, init);
// Fixed finite caps also apply to the unpinned historical and synthetic routes.
const MAX_MANIFEST_RESPONSE_BYTES = 256 * 1024;
const MAX_HEIGHTFIELD_RESPONSE_BYTES =
  MAX_HEIGHTFIELD_SAMPLES * Float32Array.BYTES_PER_ELEMENT;

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

async function cancelBody(response: Response): Promise<void> {
  try {
    await response.body?.cancel();
  } catch {
    // Preserve the useful size/integrity error even if transport cancellation fails.
  }
}

async function readBoundedResponse(
  response: Response,
  url: URL,
  stage: 'manifest response' | 'heightfield response',
  limit: number,
  expectedByteLength?: number,
): Promise<ArrayBuffer> {
  if (
    expectedByteLength !== undefined &&
    (!Number.isSafeInteger(expectedByteLength) ||
      expectedByteLength < 0 ||
      expectedByteLength > limit)
  ) {
    await cancelBody(response);
    throw new WorldLoadError(
      stage,
      `${url.href} has an invalid or oversized expected byte length (${expectedByteLength}; limit ${limit})`,
    );
  }

  const contentLength = response.headers.get('content-length');
  let declaredLength: number | undefined;
  if (contentLength !== null) {
    if (!/^\d+$/.test(contentLength)) {
      await cancelBody(response);
      throw new WorldLoadError(
        stage,
        `${url.href} declares an invalid Content-Length '${contentLength}'`,
      );
    }
    declaredLength = Number(contentLength);
    if (
      !Number.isSafeInteger(declaredLength) ||
      declaredLength > limit ||
      (expectedByteLength !== undefined &&
        declaredLength !== expectedByteLength)
    ) {
      await cancelBody(response);
      throw new WorldLoadError(
        stage,
        `${url.href} byte length mismatch: Content-Length declares ${contentLength} bytes; expected ${expectedByteLength ?? `at most ${limit}`}`,
      );
    }
  }

  if (response.body === null) {
    const empty = new ArrayBuffer(0);
    if (expectedByteLength !== undefined && expectedByteLength !== 0) {
      throw new WorldLoadError(
        stage,
        `${url.href} ended at 0 bytes; expected ${expectedByteLength}`,
      );
    }
    if (declaredLength !== undefined && declaredLength !== 0) {
      throw new WorldLoadError(
        stage,
        `${url.href} ended at 0 bytes; Content-Length declared ${declaredLength}`,
      );
    }
    return empty;
  }

  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (
        !Number.isSafeInteger(total) ||
        total > limit ||
        (expectedByteLength !== undefined && total > expectedByteLength)
      ) {
        try {
          await reader.cancel('world asset exceeded its bounded response size');
        } catch {
          // Keep the size violation as the primary error.
        }
        throw new WorldLoadError(
          stage,
          `${url.href} exceeded the ${expectedByteLength ?? limit}-byte response bound`,
        );
      }
      chunks.push(value);
    }
  } catch (error) {
    if (error instanceof WorldLoadError) throw error;
    throw new WorldLoadError(
      stage,
      `could not read response bytes from ${url.href}: ${messageFrom(error)}`,
    );
  } finally {
    reader.releaseLock();
  }

  if (
    (expectedByteLength !== undefined && total !== expectedByteLength) ||
    (declaredLength !== undefined && total !== declaredLength)
  ) {
    throw new WorldLoadError(
      stage,
      `${url.href} byte length mismatch: received ${total} bytes; expected ${expectedByteLength ?? declaredLength}`,
    );
  }
  const output = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    output.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return output.buffer as ArrayBuffer;
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
  releaseIntegrity?: SceneReleaseIntegrity,
): Promise<LoadedWorld> {
  const manifestUrl = resolveManifestUrl(manifestLocation);
  releaseIntegrity?.assertAssetUrl(manifestUrl, 'terrain manifest');
  const manifestResponse = await fetchResponse(
    fetcher,
    manifestUrl,
    'manifest request',
    signal,
  );

  const manifestInventoryLength = releaseIntegrity?.expectedByteLength(
    manifestUrl,
    'terrain manifest',
  );
  const manifestBytes = await readBoundedResponse(
    manifestResponse,
    manifestUrl,
    'manifest response',
    MAX_MANIFEST_RESPONSE_BYTES,
    manifestInventoryLength,
  );
  if (releaseIntegrity) {
    await releaseIntegrity.verifyAsset(
      manifestUrl,
      manifestBytes,
      'terrain manifest',
    );
  }
  let unknownManifest: unknown;
  try {
    unknownManifest = JSON.parse(
      new TextDecoder('utf-8', { fatal: true }).decode(manifestBytes),
    ) as unknown;
  } catch (error) {
    throw new WorldLoadError(
      'manifest response',
      `response was not valid UTF-8 JSON: ${messageFrom(error)}`,
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
  releaseIntegrity?.assertAssetUrl(heightfieldUrl, 'terrain heightfield');
  const sampleCount =
    validation.manifest.heightfield.columns *
    validation.manifest.heightfield.rows;
  const expectedHeightfieldByteLength =
    sampleCount * Float32Array.BYTES_PER_ELEMENT;
  if (
    !Number.isSafeInteger(sampleCount) ||
    sampleCount < 1 ||
    sampleCount > MAX_HEIGHTFIELD_SAMPLES ||
    !Number.isSafeInteger(expectedHeightfieldByteLength) ||
    expectedHeightfieldByteLength > MAX_HEIGHTFIELD_RESPONSE_BYTES
  ) {
    throw new WorldLoadError(
      'heightfield response',
      `manifest dimensions exceed the ${MAX_HEIGHTFIELD_SAMPLES.toLocaleString('en-US')}-sample response limit`,
    );
  }
  const inventoryHeightfieldLength = releaseIntegrity?.expectedByteLength(
    heightfieldUrl,
    'terrain heightfield',
  );
  if (
    inventoryHeightfieldLength !== undefined &&
    inventoryHeightfieldLength !== expectedHeightfieldByteLength
  ) {
    throw new WorldLoadError(
      'heightfield response',
      `pinned inventory expects ${inventoryHeightfieldLength} bytes but the validated manifest dimensions require ${expectedHeightfieldByteLength}`,
    );
  }
  const heightfieldResponse = await fetchResponse(
    fetcher,
    heightfieldUrl,
    'heightfield request',
    signal,
  );

  const bytes = await readBoundedResponse(
    heightfieldResponse,
    heightfieldUrl,
    'heightfield response',
    MAX_HEIGHTFIELD_RESPONSE_BYTES,
    expectedHeightfieldByteLength,
  );
  if (releaseIntegrity) {
    await releaseIntegrity.verifyAsset(
      heightfieldUrl,
      bytes,
      'terrain heightfield',
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

  if (validation.manifest.worldType === 'synthetic') {
    return { manifest: validation.manifest, heights };
  }
  const manifestSha256 = await sha256Hex(manifestBytes);
  return { manifest: validation.manifest, heights, manifestSha256 };
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
