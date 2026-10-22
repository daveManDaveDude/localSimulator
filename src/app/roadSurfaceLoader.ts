import {
  parseRoadSurfacePreviewManifest,
  parseRoadSurfacePreviewQa,
  ROAD_SURFACE_GRID,
  type RoadSurfaceSourceIdentity,
} from '../geo/roadSurfaceSchema';
import type { SceneReleaseIntegrity } from './sceneRelease';
import type { Current2kmRuntimeFile } from './sceneRelease';

const PREVIEW_ROOT = '/worlds/torquay-road-surface-preview/';
const MAX_MANIFEST_BYTES = 64 * 1024;
const MAX_QA_BYTES = 16 * 1024 * 1024;
const MAX_HEIGHTFIELD_BYTES = ROAD_SURFACE_GRID.heightfieldByteLength;

export type RoadSurfaceFetch = (
  input: URL,
  init?: RequestInit,
) => Promise<Response>;

export interface LoadedRoadSurfacePreview {
  heights: Float32Array;
  manifestSha256: string;
  heightfieldSha256: string;
  qaSha256: string;
  source: RoadSurfaceSourceIdentity;
}

export class RoadSurfaceLoadError extends Error {
  constructor(
    readonly stage: 'request' | 'response' | 'validation' | 'integrity',
    message: string,
  ) {
    super(`road-surface preview ${stage}: ${message}`);
    this.name = 'RoadSurfaceLoadError';
  }
}

const browserFetch: RoadSurfaceFetch = (input, init) =>
  globalThis.fetch(input, init);

async function readBounded(
  fetcher: RoadSurfaceFetch,
  url: URL,
  limit: number,
  signal?: AbortSignal,
): Promise<Uint8Array> {
  let response: Response;
  try {
    response = await fetcher(url, {
      redirect: 'error',
      ...(signal === undefined ? {} : { signal }),
    });
  } catch (error) {
    throw new RoadSurfaceLoadError(
      'request',
      `${url.pathname} failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  if (!response.ok)
    throw new RoadSurfaceLoadError(
      'response',
      `${url.pathname} returned HTTP ${response.status}`,
    );
  if (response.url) {
    const responseUrl = new URL(response.url);
    if (
      responseUrl.origin !== url.origin ||
      responseUrl.pathname !== url.pathname
    )
      throw new RoadSurfaceLoadError(
        'response',
        `${url.pathname} resolved outside the fixed local asset path`,
      );
  }
  const declaredLength = response.headers.get('content-length');
  if (declaredLength !== null) {
    const length = Number(declaredLength);
    if (!Number.isSafeInteger(length) || length < 0 || length > limit) {
      await response.body?.cancel();
      throw new RoadSurfaceLoadError(
        'response',
        `${url.pathname} exceeds its ${limit}-byte limit`,
      );
    }
  }
  if (!response.body) {
    const bytes = new Uint8Array(await response.arrayBuffer());
    if (bytes.byteLength > limit)
      throw new RoadSurfaceLoadError(
        'response',
        `${url.pathname} exceeds its ${limit}-byte limit`,
      );
    return bytes;
  }
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > limit) {
        await reader.cancel('preview response exceeds size limit');
        throw new RoadSurfaceLoadError(
          'response',
          `${url.pathname} exceeds its ${limit}-byte limit`,
        );
      }
      chunks.push(value);
    }
  } catch (error) {
    if (error instanceof RoadSurfaceLoadError) throw error;
    throw new RoadSurfaceLoadError(
      'response',
      `${url.pathname} could not be read: ${error instanceof Error ? error.message : String(error)}`,
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
  return bytes;
}

function parseJson(bytes: Uint8Array, path: string): unknown {
  try {
    return JSON.parse(
      new TextDecoder('utf-8', { fatal: true }).decode(bytes),
    ) as unknown;
  } catch (error) {
    throw new RoadSurfaceLoadError(
      'response',
      `${path} is not valid UTF-8 JSON: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
}

async function sha256(bytes: Uint8Array): Promise<string> {
  const input = bytes.buffer.slice(
    bytes.byteOffset,
    bytes.byteOffset + bytes.byteLength,
  ) as ArrayBuffer;
  const digest = await globalThis.crypto.subtle.digest('SHA-256', input);
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
}

function releaseSource(
  release: SceneReleaseIntegrity,
): RoadSurfaceSourceIdentity {
  const descriptor = (path: Current2kmRuntimeFile) => {
    const url = new URL(path, release.releaseRootUrl);
    release.assertAssetUrl(url, path);
    const file = release.files.get(path);
    if (!file)
      throw new RoadSurfaceLoadError(
        'validation',
        `validated release lacks ${path}`,
      );
    return file.sha256;
  };
  return {
    releaseId: release.releaseId,
    readySha256: release.readySha256,
    inventorySha256: release.inventorySha256,
    terrainManifestSha256: descriptor('manifest.json'),
    terrainHeightfieldSha256: descriptor('heightfield.f32'),
    roadManifestSha256: descriptor('roads/manifest.json'),
    roadPayloadSha256: descriptor('roads/roads.json'),
  };
}

function sameSource(
  a: RoadSurfaceSourceIdentity,
  b: RoadSurfaceSourceIdentity,
): boolean {
  return (
    a.releaseId === b.releaseId &&
    a.readySha256 === b.readySha256 &&
    a.inventorySha256 === b.inventorySha256 &&
    a.terrainManifestSha256 === b.terrainManifestSha256 &&
    a.terrainHeightfieldSha256 === b.terrainHeightfieldSha256 &&
    a.roadManifestSha256 === b.roadManifestSha256 &&
    a.roadPayloadSha256 === b.roadPayloadSha256
  );
}

/** Fetch only the fixed same-origin preview and bind it to a validated release. */
export async function loadRoadSurfacePreview(
  release: SceneReleaseIntegrity,
  fetcher: RoadSurfaceFetch = browserFetch,
  signal?: AbortSignal,
): Promise<LoadedRoadSurfacePreview> {
  const origin = release.releaseRootUrl.origin;
  const manifestUrl = new URL(PREVIEW_ROOT + 'manifest.json', origin);
  const expectedSource = releaseSource(release);
  const manifestBytes = await readBounded(
    fetcher,
    manifestUrl,
    MAX_MANIFEST_BYTES,
    signal,
  );
  let manifest;
  try {
    manifest = parseRoadSurfacePreviewManifest(
      parseJson(manifestBytes, manifestUrl.pathname),
    );
  } catch (error) {
    throw new RoadSurfaceLoadError(
      'validation',
      error instanceof Error ? error.message : String(error),
    );
  }
  if (!sameSource(manifest.source, expectedSource))
    throw new RoadSurfaceLoadError(
      'validation',
      'preview source hashes do not match the active validated release',
    );

  const heightfieldUrl = new URL(manifest.assets.heightfield.path, manifestUrl);
  const qaUrl = new URL(manifest.assets.qa.path, manifestUrl);
  const [heightfieldBytes, qaBytes] = await Promise.all([
    readBounded(fetcher, heightfieldUrl, MAX_HEIGHTFIELD_BYTES, signal),
    readBounded(fetcher, qaUrl, MAX_QA_BYTES, signal),
  ]);
  if (
    heightfieldBytes.byteLength !== manifest.assets.heightfield.byteLength ||
    (await sha256(heightfieldBytes)) !== manifest.assets.heightfield.sha256 ||
    qaBytes.byteLength !== manifest.assets.qa.byteLength ||
    (await sha256(qaBytes)) !== manifest.assets.qa.sha256
  )
    throw new RoadSurfaceLoadError(
      'integrity',
      'preview asset length or SHA-256 does not match its manifest',
    );
  let qa;
  try {
    qa = parseRoadSurfacePreviewQa(parseJson(qaBytes, qaUrl.pathname));
  } catch (error) {
    throw new RoadSurfaceLoadError(
      'validation',
      error instanceof Error ? error.message : String(error),
    );
  }
  if (!sameSource(qa.source, expectedSource))
    throw new RoadSurfaceLoadError(
      'validation',
      'preview QA source hashes do not match the active validated release',
    );
  if (
    qa.derivative.sha256 !== manifest.assets.heightfield.sha256 ||
    qa.derivative.byteLength !== manifest.assets.heightfield.byteLength ||
    qa.derivative.grid.columns !== manifest.grid.columns ||
    qa.derivative.grid.rows !== manifest.grid.rows
  )
    throw new RoadSurfaceLoadError(
      'validation',
      'preview QA and manifest describe different heightfields',
    );
  const view = new DataView(
    heightfieldBytes.buffer,
    heightfieldBytes.byteOffset,
    heightfieldBytes.byteLength,
  );
  const heights = new Float32Array(
    ROAD_SURFACE_GRID.columns * ROAD_SURFACE_GRID.rows,
  );
  for (let index = 0; index < heights.length; index += 1) {
    const value = view.getFloat32(index * Float32Array.BYTES_PER_ELEMENT, true);
    if (!Number.isFinite(value))
      throw new RoadSurfaceLoadError(
        'validation',
        `preview heightfield sample ${index} is not finite`,
      );
    heights[index] = value;
  }
  return {
    heights,
    manifestSha256: await sha256(manifestBytes),
    heightfieldSha256: manifest.assets.heightfield.sha256,
    qaSha256: manifest.assets.qa.sha256,
    source: manifest.source,
  };
}
