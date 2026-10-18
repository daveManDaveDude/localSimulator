import { describe, expect, it } from 'vitest';
import {
  loadBuildingPackage,
  type BuildingFetch,
} from '../../src/app/buildingLoader';
import { createRealManifest } from './fixtures';
import {
  createBuildingPayload,
  createBuildingQa,
  createFeature,
  createPackageManifest,
  sha256Hex,
} from './buildingFixtures';

const manifestUrl = new URL(
  'https://local.test/worlds/torquay-poc-001/buildings/manifest.json',
);

async function prepare() {
  const terrain = createRealManifest();
  const payloadBytes = new TextEncoder().encode(
    JSON.stringify(createBuildingPayload()),
  ).buffer;
  const qaBytes = new TextEncoder().encode(
    JSON.stringify(createBuildingQa()),
  ).buffer;
  const manifest = await createPackageManifest(terrain, payloadBytes, qaBytes);
  const manifestBytes = new TextEncoder().encode(
    JSON.stringify(manifest),
  ).buffer;
  return { terrain, manifest, payloadBytes, qaBytes, manifestBytes };
}

function bytesResponse(buffer: ArrayBuffer, status = 200): Response {
  return new Response(buffer, {
    status,
    headers: { 'content-length': String(buffer.byteLength) },
  });
}

function createFetcher(options: {
  manifestBytes?: ArrayBuffer;
  payloadBytes?: ArrayBuffer;
  qaBytes?: ArrayBuffer;
  statusByPath?: Record<string, number>;
}): { fetcher: BuildingFetch; requests: string[] } {
  const requests: string[] = [];
  const fetcher: BuildingFetch = async (url) => {
    requests.push(url.href);
    const status = options.statusByPath?.[url.pathname] ?? 200;
    if (url.pathname.endsWith('/manifest.json')) {
      return bytesResponse(options.manifestBytes!, status);
    }
    if (url.pathname.endsWith('/buildings.json')) {
      return bytesResponse(options.payloadBytes!, status);
    }
    if (url.pathname.endsWith('/qa.json')) {
      return bytesResponse(options.qaBytes!, status);
    }
    return new Response('missing', { status: 404 });
  };
  return { fetcher, requests };
}

describe('loadBuildingPackage', () => {
  it('loads and verifies the three package files from same-origin relative paths', async () => {
    const prepared = await prepare();
    const { fetcher, requests } = createFetcher(prepared);
    const result = await loadBuildingPackage(
      manifestUrl,
      prepared.terrain,
      fetcher,
    );
    expect(result.features).toHaveLength(1);
    expect(result.componentCount).toBe(1);
    expect(requests).toEqual([
      manifestUrl.href,
      'https://local.test/worlds/torquay-poc-001/buildings/buildings.json',
      'https://local.test/worlds/torquay-poc-001/buildings/qa.json',
    ]);
  });

  it('rejects arbitrary package URLs and does not request assets after a bad manifest', async () => {
    const prepared = await prepare();
    await expect(
      loadBuildingPackage(
        'https://local.test/custom/manifest.json',
        prepared.terrain,
        async () => new Response('{}'),
      ),
    ).rejects.toMatchObject({ stage: 'manifest URL' });

    const changed = structuredClone(prepared.manifest);
    (changed.buildings as { path: string }).path = '../buildings.json';
    const manifestBytes = new TextEncoder().encode(
      JSON.stringify(changed),
    ).buffer;
    const { fetcher, requests } = createFetcher({ ...prepared, manifestBytes });
    await expect(
      loadBuildingPackage(manifestUrl, prepared.terrain, fetcher),
    ).rejects.toMatchObject({ stage: 'manifest validation' });
    expect(requests).toEqual([manifestUrl.href]);
  });

  it('rejects a payload checksum mismatch before parsing features', async () => {
    const prepared = await prepare();
    const corrupt = new TextEncoder().encode('{"buildings":[]}').buffer;
    const { fetcher } = createFetcher({ ...prepared, payloadBytes: corrupt });
    await expect(
      loadBuildingPackage(manifestUrl, prepared.terrain, fetcher),
    ).rejects.toMatchObject({ stage: 'buildings response' });
    const correctLengthCorrupt = new Uint8Array(prepared.payloadBytes.slice(0));
    correctLengthCorrupt[0] = correctLengthCorrupt[0]! ^ 1;
    const corruptFetcher = createFetcher({
      ...prepared,
      payloadBytes: correctLengthCorrupt.buffer,
    });
    await expect(
      loadBuildingPackage(
        manifestUrl,
        prepared.terrain,
        corruptFetcher.fetcher,
      ),
    ).rejects.toMatchObject({ stage: 'buildings checksum' });
  });

  it('rejects QA checksum mismatch and explicit HTTP failures', async () => {
    const prepared = await prepare();
    const changedQa = new TextEncoder().encode('{}').buffer;
    const { fetcher } = createFetcher({ ...prepared, qaBytes: changedQa });
    await expect(
      loadBuildingPackage(manifestUrl, prepared.terrain, fetcher),
    ).rejects.toMatchObject({ stage: 'QA response' });

    const failing = createFetcher({
      ...prepared,
      statusByPath: { '/worlds/torquay-poc-001/buildings/qa.json': 503 },
    });
    await expect(
      loadBuildingPackage(manifestUrl, prepared.terrain, failing.fetcher),
    ).rejects.toMatchObject({ stage: 'QA request' });
  });

  it('rejects corrupt but rehashed nested data through payload validation', async () => {
    const terrain = createRealManifest();
    const badFeature = createFeature({ heightM: 12 });
    const payload = createBuildingPayload([badFeature]);
    const qa = createBuildingQa([badFeature]);
    const payloadBytes = new TextEncoder().encode(
      JSON.stringify(payload),
    ).buffer;
    const qaBytes = new TextEncoder().encode(JSON.stringify(qa)).buffer;
    const manifest = await createPackageManifest(
      terrain,
      payloadBytes,
      qaBytes,
    );
    const manifestBytes = new TextEncoder().encode(
      JSON.stringify(manifest),
    ).buffer;
    const { fetcher } = createFetcher({ manifestBytes, payloadBytes, qaBytes });
    await expect(
      loadBuildingPackage(manifestUrl, terrain, fetcher),
    ).rejects.toMatchObject({ stage: 'payload validation' });
    expect(await sha256Hex(payloadBytes)).toBe(manifest.buildings.sha256);
  });
});
