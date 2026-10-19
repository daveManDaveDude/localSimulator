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
