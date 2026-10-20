import {
  formatBuildingIssues,
  buildingPackageLimits,
  validateBuildingPackageManifest,
  validateBuildingPayload,
  type LoadedBuildingPackage,
} from '../geo/buildingSchema';
import type { RealTerrainSceneManifest } from '../geo/sceneSchema';
import type { SceneReleaseIntegrity } from './sceneRelease';

export type BuildingLoadStage =
  | 'manifest URL'
  | 'manifest request'
  | 'manifest response'
  | 'manifest validation'
  | 'buildings URL'
  | 'buildings request'
  | 'buildings response'
  | 'buildings checksum'
  | 'QA URL'
  | 'QA request'
  | 'QA response'
  | 'QA checksum'
  | 'payload validation';

export class BuildingLoadError extends Error {
  constructor(
    readonly stage: BuildingLoadStage,
    message: string,
  ) {
    super(`${stage}: ${message}`);
    this.name = 'BuildingLoadError';
  }
}

export type BuildingFetch = (
  input: URL,
  init?: RequestInit,
) => Promise<Response>;

const browserFetch: BuildingFetch = (input, init) =>
  globalThis.fetch(input, init);

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function resolveManifestUrl(location: string | URL): URL {
  try {
    const href = location instanceof URL ? location.href : location;
    const base = typeof document === 'undefined' ? undefined : document.baseURI;
    const url = base === undefined ? new URL(href) : new URL(href, base);
    if (url.protocol !== 'http:' && url.protocol !== 'https:') {
      throw new Error('only local HTTP(S) package URLs are supported');
    }
    if (
      typeof globalThis.location !== 'undefined' &&
      url.origin !== globalThis.location.origin
    ) {
      throw new Error('package must be served from the current local origin');
    }
    if (url.username || url.password || url.search || url.hash) {
      throw new Error(
        'credentials, query strings, and fragments are not allowed',
      );
    }
    return url;
  } catch (error) {
    throw new BuildingLoadError('manifest URL', errorMessage(error));
  }
}

function resolveAssetUrl(
  manifestUrl: URL,
  path: string,
  stage: BuildingLoadStage,
): URL {
  try {
    if (path.includes('/') || path.includes('\\') || path.includes('%')) {
      throw new Error('asset must be a direct package-local filename');
    }
    const directory = new URL('.', manifestUrl);
    const assetUrl = new URL(path, directory);
    if (
      assetUrl.origin !== directory.origin ||
      !assetUrl.pathname.startsWith(directory.pathname)
    ) {
      throw new Error('asset path escapes the local package');
    }
    return assetUrl;
  } catch (error) {
    throw new BuildingLoadError(stage, errorMessage(error));
  }
}

async function fetchJsonBytes(
  fetcher: BuildingFetch,
  url: URL,
  stage: Extract<
    BuildingLoadStage,
    'manifest request' | 'buildings request' | 'QA request'
  >,
  maximumBytes: number,
  signal?: AbortSignal,
): Promise<ArrayBuffer> {
  let response: Response;
  try {
    response = await fetcher(
      url,
      signal === undefined ? undefined : { signal },
    );
  } catch (error) {
    throw new BuildingLoadError(
      stage,
      `request failed for ${url.href}: ${errorMessage(error)}`,
    );
  }
  if (!response.ok) {
    throw new BuildingLoadError(
      stage,
      `request for ${url.href} returned HTTP ${response.status}`,
    );
  }
  const lengthHeader = response.headers.get('content-length');
  if (lengthHeader !== null) {
    const declaredLength = Number(lengthHeader);
    if (
      !Number.isSafeInteger(declaredLength) ||
      declaredLength < 0 ||
      declaredLength > maximumBytes
    ) {
      try {
        await response.body?.cancel(
          'declared package response exceeds its byte limit',
        );
      } catch {
        // Keep the size error as the primary diagnostic.
      }
      throw new BuildingLoadError(
        stage.replace('request', 'response') as BuildingLoadStage,
        `response exceeds the ${maximumBytes}-byte package limit`,
      );
    }
  }
  const responseStage = stage.replace(
    'request',
    'response',
  ) as BuildingLoadStage;
  if (!response.body) return new ArrayBuffer(0);
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let totalBytes = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (value.byteLength > maximumBytes - totalBytes) {
        try {
          await reader.cancel('package response exceeded its byte limit');
        } catch {
          // The size error remains the actionable failure if cancel also fails.
        }
        throw new BuildingLoadError(
          responseStage,
          `response exceeds the ${maximumBytes}-byte package limit`,
        );
      }
      totalBytes += value.byteLength;
      chunks.push(value);
    }
    const bytes = new Uint8Array(totalBytes);
    let offset = 0;
    for (const chunk of chunks) {
      bytes.set(chunk, offset);
      offset += chunk.byteLength;
    }
    return bytes.buffer;
  } catch (error) {
    if (error instanceof BuildingLoadError) throw error;
    throw new BuildingLoadError(
      responseStage,
      `could not read ${url.href}: ${errorMessage(error)}`,
    );
  } finally {
    reader.releaseLock();
  }
}

async function parseJson(
  bytes: ArrayBuffer,
  stage: BuildingLoadStage,
): Promise<unknown> {
  try {
    const text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    return JSON.parse(text) as unknown;
  } catch (error) {
    throw new BuildingLoadError(
      stage,
      `response is not valid UTF-8 JSON: ${errorMessage(error)}`,
    );
  }
}

async function sha256Hex(bytes: ArrayBuffer): Promise<string> {
  try {
    const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
    return Array.from(new Uint8Array(digest), (byte) =>
      byte.toString(16).padStart(2, '0'),
    ).join('');
  } catch (error) {
    throw new BuildingLoadError(
      'buildings checksum',
      `Web Crypto could not calculate SHA-256: ${errorMessage(error)}`,
    );
  }
}

async function readVerifiedJson(
  fetcher: BuildingFetch,
  manifestUrl: URL,
  path: string,
  byteLength: number,
  sha256: string,
  asset: 'buildings' | 'QA',
  maximumBytes: number,
  signal?: AbortSignal,
  releaseIntegrity?: SceneReleaseIntegrity,
): Promise<unknown> {
  const urlStage = asset === 'buildings' ? 'buildings URL' : 'QA URL';
  const requestStage =
    asset === 'buildings' ? 'buildings request' : 'QA request';
  const responseStage =
    asset === 'buildings' ? 'buildings response' : 'QA response';
  const checksumStage =
    asset === 'buildings' ? 'buildings checksum' : 'QA checksum';
  const url = resolveAssetUrl(manifestUrl, path, urlStage);
  releaseIntegrity?.assertAssetUrl(url, `building ${asset.toLowerCase()}`);
  const bytes = await fetchJsonBytes(
    fetcher,
    url,
    requestStage,
    maximumBytes,
    signal,
  );
  if (releaseIntegrity) {
    await releaseIntegrity.verifyAsset(
      url,
      bytes,
      `building ${asset.toLowerCase()}`,
    );
  }
  if (bytes.byteLength !== byteLength) {
    throw new BuildingLoadError(
      responseStage,
      `byte length mismatch for ${url.href}: expected ${byteLength}, received ${bytes.byteLength}`,
    );
  }
  const actualHash = await sha256Hex(bytes);
  if (actualHash !== sha256) {
    throw new BuildingLoadError(
      checksumStage,
      `SHA-256 mismatch for ${url.href}: expected ${sha256}, received ${actualHash}`,
    );
  }
  return parseJson(bytes, responseStage);
}

/** Load a single local TVW-009 package bound to the already validated terrain. */
export async function loadBuildingPackage(
  manifestLocation: string | URL,
  terrainManifest: RealTerrainSceneManifest,
  fetcher: BuildingFetch = browserFetch,
  signal?: AbortSignal,
  releaseIntegrity?: SceneReleaseIntegrity,
): Promise<LoadedBuildingPackage> {
  const current2km = terrainManifest.sceneProfile === 'current_2km';
  const manifestUrl = resolveManifestUrl(manifestLocation);
  const expectedPath = current2km
    ? releaseIntegrity === undefined
      ? '/worlds/torquay-poc-001-2km/buildings/manifest.json'
      : `/worlds/torquay-poc-001-2km/releases/${releaseIntegrity.releaseId}/buildings/manifest.json`
    : '/worlds/torquay-poc-001/buildings/manifest.json';
  if (manifestUrl.pathname !== expectedPath) {
    throw new BuildingLoadError(
      'manifest URL',
      `only the fixed ${current2km ? 'current_2km' : 'historical_1km'} buildings package is supported`,
    );
  }
  releaseIntegrity?.assertAssetUrl(manifestUrl, 'building manifest');
  const limits = buildingPackageLimits(terrainManifest.sceneProfile);
  const manifestBytes = await fetchJsonBytes(
    fetcher,
    manifestUrl,
    'manifest request',
    limits.manifestBytes,
    signal,
  );
  const manifestSha256 = await sha256Hex(manifestBytes);
  if (releaseIntegrity) {
    await releaseIntegrity.verifyAsset(
      manifestUrl,
      manifestBytes,
      'building manifest',
    );
  }
  const unknownManifest = await parseJson(manifestBytes, 'manifest response');
  const manifestResult = validateBuildingPackageManifest(
    unknownManifest,
    terrainManifest,
  );
  if (!manifestResult.ok) {
    throw new BuildingLoadError(
      'manifest validation',
      formatBuildingIssues(manifestResult.issues),
    );
  }
  const manifest = manifestResult.value;
  const [payload, qa] = await Promise.all([
    readVerifiedJson(
      fetcher,
      manifestUrl,
      manifest.buildings.path,
      manifest.buildings.byteLength,
      manifest.buildings.sha256,
      'buildings',
      limits.payloadBytes,
      signal,
      releaseIntegrity,
    ),
    readVerifiedJson(
      fetcher,
      manifestUrl,
      manifest.qaReport.path,
      manifest.qaReport.byteLength,
      manifest.qaReport.sha256,
      'QA',
      limits.qaBytes,
      signal,
      releaseIntegrity,
    ),
  ]);
  const payloadResult = validateBuildingPayload(payload, qa, manifest);
  if (!payloadResult.ok) {
    throw new BuildingLoadError(
      'payload validation',
      formatBuildingIssues(payloadResult.issues),
    );
  }
  return { ...payloadResult.value, manifestSha256 };
}
