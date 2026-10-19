import { describe, expect, it } from 'vitest';
import { loadRoadPackage, type RoadFetch } from '../../src/app/roadLoader';
import { MAX_ROAD_MANIFEST_BYTES } from '../../src/geo/roadSchema';
import { createRoadBundle, type RoadBundle } from './roadFixtures';

const manifestUrl = new URL(
  'https://local.test/worlds/torquay-poc-001/roads/manifest.json',
);

function bytesResponse(bytes: ArrayBuffer, status = 200): Response {
  return new Response(bytes, {
    status,
    headers: { 'content-length': String(bytes.byteLength) },
  });
}

function createFetcher(bundle: RoadBundle, mutateRoads = false) {
  const requests: string[] = [];
  const fetcher: RoadFetch = async (url) => {
    requests.push(url.href);
    if (url.pathname.endsWith('/manifest.json')) {
      return bytesResponse(
        new TextEncoder().encode(JSON.stringify(bundle.manifest)).buffer,
      );
    }
    if (url.pathname.endsWith('/roads.json')) {
      if (!mutateRoads) return bytesResponse(bundle.roadsBytes);
      const mutated = structuredClone(bundle.payload) as Record<
        string,
        unknown
      >;
      const roads = new TextEncoder().encode(JSON.stringify(mutated)).buffer;
      return bytesResponse(roads);
    }
    if (url.pathname.endsWith('/qa.json')) return bytesResponse(bundle.qaBytes);
    return new Response('missing', { status: 404 });
  };
  return { fetcher, requests };
}

async function sha256(bytes: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), (value) =>
    value.toString(16).padStart(2, '0'),
  ).join('');
}

async function refreshRoadAsset(bundle: RoadBundle): Promise<void> {
  const bytes = new TextEncoder().encode(JSON.stringify(bundle.payload))
    .buffer as ArrayBuffer;
  bundle.roadsBytes = bytes;
  bundle.manifest.assets.roads.byteLength = bytes.byteLength;
  bundle.manifest.assets.roads.sha256 = await sha256(bytes);
}

async function refreshQaAsset(bundle: RoadBundle): Promise<void> {
  const bytes = new TextEncoder().encode(JSON.stringify(bundle.qa))
    .buffer as ArrayBuffer;
  bundle.qaBytes = bytes;
  bundle.manifest.assets.qa.byteLength = bytes.byteLength;
  bundle.manifest.assets.qa.sha256 = await sha256(bytes);
}

function refreshSurfaceCountsAndArea(
  bundle: RoadBundle,
  group: 'vehicular' | 'cycleway' | 'path',
  area: number,
): void {
  const batches = bundle.payload.surfaceBatches;
  const vertexCount = Object.values(batches).reduce(
    (total, batch) => total + batch.verticesXZ.length,
    0,
  );
  const triangleCount = Object.values(batches).reduce(
    (total, batch) => total + batch.indices.length,
    0,
  );
  const counts = bundle.manifest.counts;
  counts.renderVertexCount = vertexCount;
  counts.renderTriangleCount = triangleCount;
  bundle.qa.counts.renderVertexCount = vertexCount;
  bundle.qa.counts.renderTriangleCount = triangleCount;
  const batch = bundle.payload.surfaceBatches[group];
  const summary = bundle.qa.displayBatches[group];
  summary.vertexCount = batch.verticesXZ.length;
  summary.triangleCount = batch.indices.length;
  summary.surfaceAreaM2 = area;
  summary.bufferedAreaBeforePriorityM2 = area;
  bundle.qa.areas.byDisplayGroupM2[group] = area;
  bundle.qa.areas.totalDisjointSurfaceM2 = Object.values(
    bundle.qa.areas.byDisplayGroupM2,
  ).reduce((total, value) => total + value, 0);
}

function mutableBatch(
  bundle: RoadBundle,
  group: 'vehicular' | 'cycleway' | 'path',
) {
  return bundle.payload.surfaceBatches[group] as unknown as {
    verticesXZ: unknown[];
    indices: unknown[];
    terrainTriangles: unknown[];
  };
}

describe('loadRoadPackage', () => {
  it('loads the same-origin fixture only after verifying terrain and all asset bytes', async () => {
    const bundle = await createRoadBundle();
    const { fetcher, requests } = createFetcher(bundle);
    const loaded = await loadRoadPackage(
      manifestUrl,
      bundle.terrain,
      bundle.terrainManifestSha256,
      fetcher,
    );
    expect(loaded.features).toHaveLength(1);
    expect(loaded.partCount).toBe(1);
    expect(requests).toEqual([
      manifestUrl.href,
      'https://local.test/worlds/torquay-poc-001/roads/roads.json',
      'https://local.test/worlds/torquay-poc-001/roads/qa.json',
    ]);
  });

  it('rejects an origin-boundary change even when an attacker refreshes the road hash', async () => {
    const bundle = await createRoadBundle();
    const payload = structuredClone(bundle.payload) as {
      surfaceBatches: { vehicular: { verticesXZ: number[][] } };
    };
    payload.surfaceBatches.vehicular.verticesXZ[0] = [900, 0];
    const roadsBytes = new TextEncoder().encode(JSON.stringify(payload)).buffer;
    const digest = await crypto.subtle.digest('SHA-256', roadsBytes);
    bundle.manifest.assets.roads.byteLength = roadsBytes.byteLength;
    bundle.manifest.assets.roads.sha256 = Array.from(
      new Uint8Array(digest),
      (value) => value.toString(16).padStart(2, '0'),
    ).join('');
    const { fetcher } = createFetcher({ ...bundle, roadsBytes }, false);
    await expect(
      loadRoadPackage(
        manifestUrl,
        bundle.terrain,
        bundle.terrainManifestSha256,
        fetcher,
      ),
    ).rejects.toThrow(/outside terrain bounds|outside the exact local AOI/);
  });

  it('rejects a retained bridge tag under the ground-only policy after hashes are refreshed', async () => {
    const bundle = await createRoadBundle();
    (bundle.payload.features[0]!.sourceTags as Record<string, string>).bridge =
      'yes';
    await refreshRoadAsset(bundle);
    const { fetcher } = createFetcher(bundle);
    await expect(
      loadRoadPackage(
        manifestUrl,
        bundle.terrain,
        bundle.terrainManifestSha256,
        fetcher,
      ),
    ).rejects.toThrow(/ground-only policy/);
  });

  it('rejects a changed full BNG-to-WGS84 operation after QA and asset hashes are refreshed', async () => {
    const bundle = await createRoadBundle();
    bundle.manifest.coordinateOperation.bngToWgs84.definition +=
      ' step proj=affine xoff=12345';
    await refreshQaAsset(bundle);
    const { fetcher } = createFetcher(bundle);
    await expect(
      loadRoadPackage(
        manifestUrl,
        bundle.terrain,
        bundle.terrainManifestSha256,
        fetcher,
      ),
    ).rejects.toThrow(/BNG-to-WGS84 inverse operation/);
  });

  it('rejects geometrically duplicate triangles with copied vertices and refreshed package integrity', async () => {
    const bundle = await createRoadBundle();
    const batch = mutableBatch(bundle, 'vehicular');
    const copiedVertices = structuredClone(batch.verticesXZ);
    batch.verticesXZ.push(...copiedVertices);
    batch.indices.push([3, 4, 5]);
    batch.terrainTriangles.push([249, 249, 0]);
    refreshSurfaceCountsAndArea(bundle, 'vehicular', 4);
    await refreshRoadAsset(bundle);
    const { fetcher } = createFetcher(bundle);
    await expect(
      loadRoadPackage(
        manifestUrl,
        bundle.terrain,
        bundle.terrainManifestSha256,
        fetcher,
      ),
    ).rejects.toThrow(/duplicates another triangle by geometric coordinates/);
  });

  it('rejects a nonidentical triangle whose interior overlaps another rendered face', async () => {
    const bundle = await createRoadBundle();
    const batch = mutableBatch(bundle, 'vehicular');
    batch.verticesXZ.push([-1.5, -1.5], [-1.5, -1], [-1, -1.5]);
    batch.indices.push([3, 4, 5]);
    batch.terrainTriangles.push([249, 249, 0]);
    refreshSurfaceCountsAndArea(bundle, 'vehicular', 2.125);
    await refreshRoadAsset(bundle);
    const { fetcher } = createFetcher(bundle);
    await expect(
      loadRoadPackage(
        manifestUrl,
        bundle.terrain,
        bundle.terrainManifestSha256,
        fetcher,
      ),
    ).rejects.toThrow(/triangle interior overlaps/);
  });

  it('reconciles rendered triangle area with the QA report', async () => {
    const bundle = await createRoadBundle();
    bundle.qa.displayBatches.vehicular.surfaceAreaM2 = 2.25;
    bundle.qa.areas.byDisplayGroupM2.vehicular = 2.25;
    bundle.qa.areas.totalDisjointSurfaceM2 = 2.25;
    await refreshQaAsset(bundle);
    const { fetcher } = createFetcher(bundle);
    await expect(
      loadRoadPackage(
        manifestUrl,
        bundle.terrain,
        bundle.terrainManifestSha256,
        fetcher,
      ),
    ).rejects.toThrow(/summed rendered triangle area/);
  });

  it('reports malformed nested payload and missing manifest/QA counts without raw TypeErrors', async () => {
    const vertexBundle = await createRoadBundle();
    mutableBatch(vertexBundle, 'vehicular').verticesXZ[1] = null;
    await refreshRoadAsset(vertexBundle);
    const { fetcher: vertexFetcher } = createFetcher(vertexBundle);
    await expect(
      loadRoadPackage(
        manifestUrl,
        vertexBundle.terrain,
        vertexBundle.terrainManifestSha256,
        vertexFetcher,
      ),
    ).rejects.toThrow(/verticesXZ: must contain finite/);

    const manifestBundle = await createRoadBundle();
    delete (manifestBundle.manifest as unknown as Record<string, unknown>)
      .counts;
    const { fetcher: manifestFetcher } = createFetcher(manifestBundle);
    await expect(
      loadRoadPackage(
        manifestUrl,
        manifestBundle.terrain,
        manifestBundle.terrainManifestSha256,
        manifestFetcher,
      ),
    ).rejects.toThrow(/manifest validation: counts: must include/);

    const qaBundle = await createRoadBundle();
    delete (qaBundle.qa as unknown as Record<string, unknown>).counts;
    await refreshQaAsset(qaBundle);
    const { fetcher: qaFetcher } = createFetcher(qaBundle);
    await expect(
      loadRoadPackage(
        manifestUrl,
        qaBundle.terrain,
        qaBundle.terrainManifestSha256,
        qaFetcher,
      ),
    ).rejects.toThrow(/qa\.counts: must match manifest counts/);
  });

  it('stops reading a headerless oversized manifest response at the configured cap', async () => {
    const bundle = await createRoadBundle();
    let consumedChunks = 0;
    let cancelled = false;
    const fetcher: RoadFetch = async (url) => {
      if (url.pathname.endsWith('/manifest.json')) {
        const body = new ReadableStream<Uint8Array>({
          pull(controller) {
            consumedChunks += 1;
            controller.enqueue(new Uint8Array(32 * 1024));
          },
          cancel() {
            cancelled = true;
          },
        });
        return new Response(body, { status: 200 });
      }
      return bytesResponse(bundle.roadsBytes);
    };
    await expect(
      loadRoadPackage(
        manifestUrl,
        bundle.terrain,
        bundle.terrainManifestSha256,
        fetcher,
      ),
    ).rejects.toThrow(
      `manifest response: response exceeds the ${MAX_ROAD_MANIFEST_BYTES}-byte limit`,
    );
    // The over-limit chunk is delivered to the reader so it can discover the cap;
    // subsequent chunks must not be requested.
    expect(consumedChunks).toBeLessThanOrEqual(4);
    expect(cancelled).toBe(true);
  });
});
