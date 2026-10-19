import {
  formatOverviewIssues,
  MAX_OVERVIEW_FEATURES,
  MAX_OVERVIEW_GEOJSON_BYTES,
  MAX_OVERVIEW_MANIFEST_BYTES,
  validateOverviewFeatureCollection,
  validateOverviewManifest,
  type OverviewFeatureCollection,
  type OverviewManifest,
} from '../geo/overviewSchema';
import type { RealTerrainSceneManifest } from '../geo/sceneSchema';

export const REAL_OVERVIEW_MANIFEST_URL =
  '/worlds/torquay-poc-001/overview/manifest.json';

export type OverviewLoadStage =
  | 'manifest URL'
  | 'manifest request'
  | 'manifest response'
  | 'manifest validation'
  | 'features URL'
  | 'features request'
  | 'features response'
  | 'features checksum'
  | 'features validation';

export class OverviewLoadError extends Error {
  constructor(
    readonly stage: OverviewLoadStage,
    message: string,
    readonly statusCode?: number,
  ) {
    super(`${stage}: ${message}`);
    this.name = 'OverviewLoadError';
  }
}

export type OverviewFetch = (
  input: URL,
  init?: RequestInit,
) => Promise<Response>;

export interface LoadedOverviewPackage {
  manifest: OverviewManifest;
  manifestSha256: string;
  features: OverviewFeatureCollection;
}

const browserFetch: OverviewFetch = (input, init) =>
  globalThis.fetch(input, init);

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function resolveManifestUrl(location: string | URL): URL {
  try {
    const href = location instanceof URL ? location.href : location;
    const base = typeof document === 'undefined' ? undefined : document.baseURI;
    const url = base === undefined ? new URL(href) : new URL(href, base);
    if (url.protocol !== 'http:' && url.protocol !== 'https:')
      throw new Error('only local HTTP(S) overview URLs are supported');
    if (
      typeof globalThis.location !== 'undefined' &&
      url.origin !== globalThis.location.origin
    )
      throw new Error(
        'overview package must be served from the current origin',
      );
    if (
      url.pathname !== REAL_OVERVIEW_MANIFEST_URL ||
      url.username ||
      url.password ||
      url.search ||
      url.hash
    )
      throw new Error(
        'only the fixed local Torquay overview package is supported',
      );
    return url;
  } catch (error) {
    throw new OverviewLoadError('manifest URL', errorMessage(error));
  }
}

function resolveFeaturesUrl(manifestUrl: URL, path: string): URL {
  try {
    if (path !== 'features.geojson')
      throw new Error('asset must be the package-local features.geojson file');
    const directory = new URL('.', manifestUrl);
    const url = new URL(path, directory);
    if (
      url.origin !== directory.origin ||
      !url.pathname.startsWith(directory.pathname)
    )
      throw new Error('asset path escapes the local overview package');
    return url;
  } catch (error) {
    throw new OverviewLoadError('features URL', errorMessage(error));
  }
}

async function boundedBytes(
  fetcher: OverviewFetch,
  url: URL,
  stage: 'manifest request' | 'features request',
  responseStage: 'manifest response' | 'features response',
  maximum: number,
  signal?: AbortSignal,
): Promise<Uint8Array> {
  let response: Response;
  try {
    response = await fetcher(url, {
      ...(signal ? { signal } : {}),
      cache: 'no-store',
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new OverviewLoadError(stage, errorMessage(error));
  }
  if (!response.ok) {
    throw new OverviewLoadError(
      responseStage,
      `HTTP ${response.status} ${response.statusText} for ${url.pathname}`,
      response.status,
    );
  }
  const contentLength = response.headers.get('content-length');
  if (contentLength && /^\d+$/.test(contentLength)) {
    const declared = Number(contentLength);
    if (Number.isSafeInteger(declared) && declared > maximum) {
      await response.body
        ?.cancel('overview asset exceeds byte limit')
        .catch(() => undefined);
      throw new OverviewLoadError(
        responseStage,
        `declared size exceeds ${maximum} bytes`,
      );
    }
  }
  if (!response.body) {
    let bytes: ArrayBuffer;
    try {
      bytes = await response.arrayBuffer();
    } catch (error) {
      throw new OverviewLoadError(responseStage, errorMessage(error));
    }
    if (bytes.byteLength > maximum)
      throw new OverviewLoadError(
        responseStage,
        `asset exceeds ${maximum} bytes`,
      );
    return new Uint8Array(bytes);
  }
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > maximum) {
        await reader
          .cancel('overview asset exceeds byte limit')
          .catch(() => undefined);
        throw new OverviewLoadError(
          responseStage,
          `stream exceeds ${maximum} bytes`,
        );
      }
      chunks.push(value);
    }
  } catch (error) {
    await reader.cancel().catch(() => undefined);
    if (error instanceof OverviewLoadError) throw error;
    if (signal?.aborted) throw error;
    throw new OverviewLoadError(responseStage, errorMessage(error));
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return bytes;
}

async function sha256Hex(bytes: Uint8Array): Promise<string> {
  try {
    const copy = bytes.slice();
    const digest = await globalThis.crypto.subtle.digest(
      'SHA-256',
      copy.buffer,
    );
    return Array.from(new Uint8Array(digest), (byte) =>
      byte.toString(16).padStart(2, '0'),
    ).join('');
  } catch (error) {
    throw new OverviewLoadError('features checksum', errorMessage(error));
  }
}

function parseJson(
  bytes: Uint8Array,
  stage: 'manifest response' | 'features response',
): unknown {
  try {
    return JSON.parse(
      new TextDecoder('utf-8', { fatal: true }).decode(bytes),
    ) as unknown;
  } catch (error) {
    throw new OverviewLoadError(
      stage,
      `response is not valid UTF-8 JSON: ${errorMessage(error)}`,
    );
  }
}

/** Load and validate the fixed same-origin overview and its single bounded GeoJSON asset. */
export async function loadOverviewPackage(
  manifestLocation: string | URL,
  terrain: RealTerrainSceneManifest,
  terrainManifestSha256: string,
  fetcher: OverviewFetch = browserFetch,
  signal?: AbortSignal,
): Promise<LoadedOverviewPackage> {
  const manifestUrl = resolveManifestUrl(manifestLocation);
  const manifestBytes = await boundedBytes(
    fetcher,
    manifestUrl,
    'manifest request',
    'manifest response',
    MAX_OVERVIEW_MANIFEST_BYTES,
    signal,
  );
  const manifestSha256 = await sha256Hex(manifestBytes);
  const manifestResult = validateOverviewManifest(
    parseJson(manifestBytes, 'manifest response'),
    terrain,
    terrainManifestSha256,
  );
  if (!manifestResult.ok)
    throw new OverviewLoadError(
      'manifest validation',
      formatOverviewIssues(manifestResult.issues),
    );
  const manifest = manifestResult.value;
  if (
    manifest.features.byteLength > MAX_OVERVIEW_GEOJSON_BYTES ||
    manifest.counts.featuresByRole.total > MAX_OVERVIEW_FEATURES
  )
    throw new OverviewLoadError(
      'manifest validation',
      'overview exceeds browser safety limits',
    );
  const featuresUrl = resolveFeaturesUrl(manifestUrl, manifest.features.path);
  const bytes = await boundedBytes(
    fetcher,
    featuresUrl,
    'features request',
    'features response',
    MAX_OVERVIEW_GEOJSON_BYTES,
    signal,
  );
  if (bytes.byteLength !== manifest.features.byteLength)
    throw new OverviewLoadError(
      'features response',
      `byte length mismatch: expected ${manifest.features.byteLength}, received ${bytes.byteLength}`,
    );
  if ((await sha256Hex(bytes)) !== manifest.features.sha256)
    throw new OverviewLoadError(
      'features checksum',
      'SHA-256 differs from the manifest',
    );
  const featureResult = validateOverviewFeatureCollection(
    parseJson(bytes, 'features response'),
    manifest,
  );
  if (!featureResult.ok)
    throw new OverviewLoadError(
      'features validation',
      formatOverviewIssues(featureResult.issues),
    );
  return { manifest, manifestSha256, features: featureResult.value };
}
