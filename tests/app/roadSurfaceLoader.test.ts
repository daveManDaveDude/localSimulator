import { describe, expect, it } from 'vitest';
import {
  CURRENT_2KM_RUNTIME_FILES,
  type Current2kmRuntimeFile,
  type SceneReleaseFile,
  type SceneReleaseIntegrity,
} from '../../src/app/sceneRelease';
import {
  ROAD_SURFACE_GRID,
  ROAD_SURFACE_PREVIEW_ALGORITHM,
} from '../../src/geo/roadSurfaceSchema';
import {
  loadRoadSurfacePreview,
  type RoadSurfaceFetch,
} from '../../src/app/roadSurfaceLoader';

const digest = async (bytes: Uint8Array): Promise<string> => {
  const input = bytes.buffer.slice(
    bytes.byteOffset,
    bytes.byteOffset + bytes.byteLength,
  ) as ArrayBuffer;
  const hash = await crypto.subtle.digest('SHA-256', input);
  return Array.from(new Uint8Array(hash), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
};

function canonical(value: unknown): Uint8Array {
  return new TextEncoder().encode(`${JSON.stringify(value)}\n`);
}

async function fixture(): Promise<{
  release: SceneReleaseIntegrity;
  fetcher: RoadSurfaceFetch;
  requests: URL[];
  expectedHeights: Float32Array;
}> {
  const releaseId = 'a'.repeat(64);
  const releaseRootUrl = new URL(
    `/worlds/torquay-poc-001-2km/releases/${releaseId}/`,
    'https://local.test',
  );
  const fileContents = new Map<Current2kmRuntimeFile, Uint8Array>();
  const files = new Map<Current2kmRuntimeFile, SceneReleaseFile>();
  for (const path of CURRENT_2KM_RUNTIME_FILES) {
    const bytes = new TextEncoder().encode(`fixture:${path}`);
    fileContents.set(path, bytes);
    files.set(path, {
      path,
      byteLength: bytes.byteLength,
      sha256: await digest(bytes),
    });
  }
  const source = {
    releaseId,
    readySha256: 'b'.repeat(64),
    inventorySha256: 'c'.repeat(64),
    terrainManifestSha256: files.get('manifest.json')!.sha256,
    terrainHeightfieldSha256: files.get('heightfield.f32')!.sha256,
    roadManifestSha256: files.get('roads/manifest.json')!.sha256,
    roadPayloadSha256: files.get('roads/roads.json')!.sha256,
  };
  const heights = new Float32Array(
    ROAD_SURFACE_GRID.columns * ROAD_SURFACE_GRID.rows,
  );
  heights[0] = 1.25;
  heights[heights.length - 1] = -2.5;
  const heightfield = new Uint8Array(heights.byteLength);
  const view = new DataView(heightfield.buffer);
  for (let index = 0; index < heights.length; index += 1)
    view.setFloat32(index * 4, heights[index]!, true);
  const manifestValue = {
    formatVersion: 1,
    worldId: 'torquay-poc-001',
    sceneProfile: 'current_2km',
    packageType: 'road-surface-display-grid-derivative',
    algorithmVersion: ROAD_SURFACE_PREVIEW_ALGORITHM,
    interpretation: 'Approximate visual grading.',
    source,
    grid: {
      columns: ROAD_SURFACE_GRID.columns,
      rows: ROAD_SURFACE_GRID.rows,
      spacingM: ROAD_SURFACE_GRID.spacingM,
      widthM: ROAD_SURFACE_GRID.widthM,
      depthM: ROAD_SURFACE_GRID.depthM,
      rowOrder: 'north-to-south',
      byteOrder: 'little-endian',
      encoding: 'float32',
      valueMeaning:
        'visual world Y relative to original terrain origin elevation',
    },
    parameters: {
      transitionDistanceFactor: 1,
      ambiguityDistanceM: 2,
      ambiguityHeightDifferenceM: 1,
      ambiguityRetentionCore:
        'larger involved half-width plus one grid spacing',
      ambiguityFadeDistance:
        'larger involved configured width or two grid spacings',
      maximumChangedHeightM: 10,
      fallbackAbsoluteChangeM: 5,
      fallbackAddedGradientMPerM: 1,
      fallbackMinimumRegionAreaM2: 64,
      fallbackFadeDistanceM: 32,
      targetCrossfallPercent: 0,
      roadSurfaceOffsetM: 0.05,
    },
    assets: {
      heightfield: {
        path: 'heightfield.f32',
        byteLength: heightfield.byteLength,
        sha256: await digest(heightfield),
      },
      qa: { path: 'qa.json', byteLength: 0, sha256: '' },
    },
  };
  const qaValue = {
    formatVersion: 1,
    algorithmVersion: ROAD_SURFACE_PREVIEW_ALGORITHM,
    issue: 'Road-surface treatment preview',
    source,
    sourceMetadata: {
      worldId: 'torquay-poc-001',
      sceneProfile: 'current_2km',
      roadFeatureCount: 1044,
      rasterComparisonInputs: [
        {
          path: 'data/raw/ea_dtm/SX96nw/SX96nw_DTM_1m.tif',
          byteLength: 1,
          sha256: 'd'.repeat(64),
        },
        {
          path: 'data/raw/ea_dtm/SX96sw/SX96sw_DTM_1m.tif',
          byteLength: 2,
          sha256: 'e'.repeat(64),
        },
      ],
    },
    derivative: {
      path: 'heightfield.f32',
      byteLength: heightfield.byteLength,
      sha256: manifestValue.assets.heightfield.sha256,
      grid: manifestValue.grid,
    },
  };
  const qa = canonical(qaValue);
  manifestValue.assets.qa = {
    path: 'qa.json',
    byteLength: qa.byteLength,
    sha256: await digest(qa),
  };
  const manifest = canonical(manifestValue);
  const responseFromBytes = (bytes: Uint8Array): Response => {
    const body = bytes.buffer.slice(
      bytes.byteOffset,
      bytes.byteOffset + bytes.byteLength,
    ) as ArrayBuffer;
    return new Response(body);
  };
  const requests: URL[] = [];
  const release: SceneReleaseIntegrity = {
    releaseId,
    readySha256: source.readySha256,
    inventorySha256: source.inventorySha256,
    releaseRootUrl,
    files,
    assertAssetUrl(url, label) {
      if (
        url.origin !== releaseRootUrl.origin ||
        !url.pathname.startsWith(releaseRootUrl.pathname)
      )
        throw new Error(`invalid release URL for ${label}`);
    },
    expectedByteLength() {
      return 1;
    },
    async verifyAsset() {
      return;
    },
  };
  const fetcher: RoadSurfaceFetch = async (url, init) => {
    requests.push(url);
    expect(init?.redirect).toBe('error');
    if (url.pathname.endsWith('/manifest.json'))
      return responseFromBytes(manifest);
    if (url.pathname.endsWith('/heightfield.f32'))
      return responseFromBytes(heightfield);
    if (url.pathname.endsWith('/qa.json')) return responseFromBytes(qa);
    return new Response(null, { status: 404 });
  };
  return { release, fetcher, requests, expectedHeights: heights };
}

describe('road-surface derivative loader', () => {
  it('checks same-origin assets and returns finite little-endian Float32 samples', async () => {
    const test = await fixture();
    const loaded = await loadRoadSurfacePreview(test.release, test.fetcher);

    expect(test.requests.map((request) => request.pathname)).toEqual([
      '/worlds/torquay-road-surface-preview/manifest.json',
      '/worlds/torquay-road-surface-preview/heightfield.f32',
      '/worlds/torquay-road-surface-preview/qa.json',
    ]);
    expect(loaded.heights).toEqual(test.expectedHeights);
    expect(loaded.heights[0]).toBe(1.25);
    expect(loaded.heights.at(-1)).toBe(-2.5);
  });

  it('rejects a stale derivative source before requesting its binary', async () => {
    const test = await fixture();
    const requests: string[] = [];
    const stale: RoadSurfaceFetch = async (url, init) => {
      requests.push(url.pathname);
      if (url.pathname.endsWith('/manifest.json')) {
        const manifest = JSON.parse(
          new TextDecoder().decode(
            await (await test.fetcher(url, init)).arrayBuffer(),
          ),
        ) as Record<string, unknown>;
        const source = manifest['source'] as Record<string, unknown>;
        source['readySha256'] = 'd'.repeat(64);
        return new Response(JSON.stringify(manifest));
      }
      return test.fetcher(url, init);
    };

    await expect(loadRoadSurfacePreview(test.release, stale)).rejects.toThrow(
      'do not match the active validated release',
    );
    expect(requests).toHaveLength(1);
  });
});
