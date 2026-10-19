import {
  formatRoadIssues,
  MAX_ROAD_MANIFEST_BYTES,
  MAX_ROAD_QA_BYTES,
  MAX_ROADS_BYTES,
  validateRoadManifest,
  validateRoadPayload,
  type LoadedRoadPackage,
} from '../geo/roadSchema';
import type { RealTerrainSceneManifest } from '../geo/sceneSchema';

export type RoadLoadStage =
  | 'manifest URL'
  | 'manifest request'
  | 'manifest response'
  | 'manifest validation'
  | 'roads URL'
  | 'roads request'
  | 'roads response'
  | 'roads checksum'
  | 'QA URL'
  | 'QA request'
  | 'QA response'
  | 'QA checksum'
  | 'payload validation';

export class RoadLoadError extends Error {
  constructor(
    readonly stage: RoadLoadStage,
    message: string,
  ) {
    super(`${stage}: ${message}`);
    this.name = 'RoadLoadError';
  }
}

export type RoadFetch = (input: URL, init?: RequestInit) => Promise<Response>;

const browserFetch: RoadFetch = (input, init) => globalThis.fetch(input, init);

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function resolveManifestUrl(input: string | URL): URL {
  try {
    const value = input instanceof URL ? input.href : input;
    const base = typeof document === 'undefined' ? undefined : document.baseURI;
    const url = base === undefined ? new URL(value) : new URL(value, base);
    if (url.protocol !== 'http:' && url.protocol !== 'https:') {
      throw new Error('only local HTTP(S) package URLs are supported');
    }
    if (
      typeof globalThis.location !== 'undefined' &&
      url.origin !== globalThis.location.origin
    ) {
      throw new Error(
        'roads package must be served from the current local origin',
      );
    }
    if (
      url.pathname !== '/worlds/torquay-poc-001/roads/manifest.json' ||
      url.username ||
      url.password ||
      url.search ||
      url.hash
    ) {
      throw new Error(
        'only the fixed local Torquay roads package is supported',
      );
    }
    return url;
  } catch (error) {
    throw new RoadLoadError('manifest URL', errorMessage(error));
  }
}

function resolveAssetUrl(
  manifestUrl: URL,
  path: string,
  stage: RoadLoadStage,
): URL {
  try {
    if (path.includes('/') || path.includes('\\') || path.includes('%')) {
      throw new Error('asset must be a direct package-local JSON filename');
    }
    const directory = new URL('.', manifestUrl);
    const url = new URL(path, directory);
    if (
      url.origin !== directory.origin ||
      !url.pathname.startsWith(directory.pathname)
    ) {
      throw new Error('asset path escapes the local roads package');
    }
    return url;
  } catch (error) {
    throw new RoadLoadError(stage, errorMessage(error));
  }
}

async function readBoundedResponse(
  fetcher: RoadFetch,
  url: URL,
  requestStage: 'manifest request' | 'roads request' | 'QA request',
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
    throw new RoadLoadError(
      requestStage,
      `request failed for ${url.href}: ${errorMessage(error)}`,
    );
  }
  if (!response.ok) {
    throw new RoadLoadError(
      requestStage,
      `request for ${url.href} returned HTTP ${response.status}`,
    );
  }
  const length = response.headers.get('content-length');
  if (length !== null) {
    const declared = Number(length);
    if (
      !Number.isSafeInteger(declared) ||
      declared < 0 ||
      declared > maximumBytes
    ) {
      try {
        await response.body?.cancel('roads response exceeds byte limit');
      } catch {
        // Preserve the useful size failure.
      }
      throw new RoadLoadError(
        requestStage.replace('request', 'response') as RoadLoadStage,
        `response exceeds the ${maximumBytes}-byte limit`,
      );
    }
  }
  if (!response.body) return new ArrayBuffer(0);
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (value.byteLength > maximumBytes - total) {
        try {
          await reader.cancel('roads response exceeded byte limit');
        } catch {
          // Preserve the useful size failure.
        }
        throw new RoadLoadError(
          requestStage.replace('request', 'response') as RoadLoadStage,
          `response exceeds the ${maximumBytes}-byte limit`,
        );
      }
      total += value.byteLength;
      chunks.push(value);
    }
  } catch (error) {
    if (error instanceof RoadLoadError) throw error;
    throw new RoadLoadError(
      requestStage.replace('request', 'response') as RoadLoadStage,
      `could not read ${url.href}: ${errorMessage(error)}`,
    );
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return bytes.buffer;
}

async function parseJson(
  bytes: ArrayBuffer,
  stage: RoadLoadStage,
): Promise<unknown> {
  try {
    return JSON.parse(
      new TextDecoder('utf-8', { fatal: true }).decode(bytes),
    ) as unknown;
  } catch (error) {
    throw new RoadLoadError(
      stage,
      `response is not valid UTF-8 JSON: ${errorMessage(error)}`,
    );
  }
}

async function sha256Hex(
  bytes: ArrayBuffer,
  stage: RoadLoadStage,
): Promise<string> {
  try {
    const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
    return Array.from(new Uint8Array(digest), (byte) =>
      byte.toString(16).padStart(2, '0'),
    ).join('');
  } catch (error) {
    throw new RoadLoadError(
      stage,
      `Web Crypto could not calculate SHA-256: ${errorMessage(error)}`,
    );
  }
}

async function readAsset(
  fetcher: RoadFetch,
  manifestUrl: URL,
  path: string,
  byteLength: number,
  expectedSha256: string,
  kind: 'roads' | 'QA',
  signal?: AbortSignal,
): Promise<unknown> {
  const urlStage = kind === 'roads' ? 'roads URL' : 'QA URL';
  const requestStage = kind === 'roads' ? 'roads request' : 'QA request';
  const responseStage = kind === 'roads' ? 'roads response' : 'QA response';
  const checksumStage = kind === 'roads' ? 'roads checksum' : 'QA checksum';
  const maximum = kind === 'roads' ? MAX_ROADS_BYTES : MAX_ROAD_QA_BYTES;
  const url = resolveAssetUrl(manifestUrl, path, urlStage);
  const bytes = await readBoundedResponse(
    fetcher,
    url,
    requestStage,
    maximum,
    signal,
  );
  if (bytes.byteLength !== byteLength) {
    throw new RoadLoadError(
      responseStage,
      `byte length mismatch: expected ${byteLength}, received ${bytes.byteLength}`,
    );
  }
  if ((await sha256Hex(bytes, checksumStage)) !== expectedSha256) {
    throw new RoadLoadError(checksumStage, `SHA-256 mismatch for ${url.href}`);
  }
  return parseJson(bytes, responseStage);
}

/** Load the fixed same-origin roads package after terrain identity is available. */
export async function loadRoadPackage(
  manifestLocation: string | URL,
  terrainManifest: RealTerrainSceneManifest,
  terrainManifestSha256: string,
  fetcher: RoadFetch = browserFetch,
  signal?: AbortSignal,
): Promise<LoadedRoadPackage> {
  const manifestUrl = resolveManifestUrl(manifestLocation);
  const manifestBytes = await readBoundedResponse(
    fetcher,
    manifestUrl,
    'manifest request',
    MAX_ROAD_MANIFEST_BYTES,
    signal,
  );
  const manifestSha256 = await sha256Hex(manifestBytes, 'manifest validation');
  const unknownManifest = await parseJson(manifestBytes, 'manifest response');
  const manifestResult = validateRoadManifest(unknownManifest, terrainManifest);
  if (!manifestResult.ok) {
    throw new RoadLoadError(
      'manifest validation',
      formatRoadIssues(manifestResult.issues),
    );
  }
  if (
    manifestResult.value.terrainIdentity.manifestSha256 !==
    terrainManifestSha256
  ) {
    throw new RoadLoadError(
      'manifest validation',
      'roads package is bound to a different terrain manifest',
    );
  }
  const manifest = manifestResult.value;
  const [roads, qa] = await Promise.all([
    readAsset(
      fetcher,
      manifestUrl,
      manifest.assets.roads.path,
      manifest.assets.roads.byteLength,
      manifest.assets.roads.sha256,
      'roads',
      signal,
    ),
    readAsset(
      fetcher,
      manifestUrl,
      manifest.assets.qa.path,
      manifest.assets.qa.byteLength,
      manifest.assets.qa.sha256,
      'QA',
      signal,
    ),
  ]);
  const result = validateRoadPayload(roads, qa, manifest);
  if (!result.ok) {
    throw new RoadLoadError(
      'payload validation',
      formatRoadIssues(result.issues),
    );
  }
  return { ...result.value, manifestSha256 };
}
