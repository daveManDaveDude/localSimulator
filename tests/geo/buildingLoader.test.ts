import { describe, expect, it } from 'vitest';
import {
  loadBuildingPackage,
  type BuildingFetch,
} from '../../src/app/buildingLoader';
import { MAX_BUILDING_MANIFEST_BYTES } from '../../src/geo/buildingSchema';
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

  it.each([['missing'], ['understated']])(
    'stops reading a headerless or understated oversized manifest stream (%s)',
    async (headerVariant) => {
      const prepared = await prepare();
      let pulls = 0;
      let cancelled = false;
      const responseStream = new ReadableStream<Uint8Array>(
        {
          pull(controller) {
            if (pulls === 8) {
              controller.close();
              return;
            }
            pulls += 1;
            controller.enqueue(new Uint8Array(64 * 1024));
          },
          cancel() {
            cancelled = true;
          },
        },
        { highWaterMark: 0 },
      );
      const headers = new Headers();
      if (headerVariant === 'understated') headers.set('content-length', '1');
      const fetcher: BuildingFetch = async (url) =>
        url.pathname.endsWith('/manifest.json')
          ? new Response(responseStream, { headers })
          : new Response('{}');

      await expect(
        loadBuildingPackage(manifestUrl, prepared.terrain, fetcher),
      ).rejects.toMatchObject({
        stage: 'manifest response',
        message: expect.stringContaining(
          `${MAX_BUILDING_MANIFEST_BYTES}-byte package limit`,
        ),
      });
      expect(pulls).toBeLessThan(8);
      expect(cancelled).toBe(true);
    },
  );

  it('rejects an oversized declared manifest before consuming the body', async () => {
    const prepared = await prepare();
    let pulls = 0;
    let cancelled = false;
    const responseStream = new ReadableStream<Uint8Array>(
      {
        pull(controller) {
          pulls += 1;
          controller.enqueue(new Uint8Array(1));
        },
        cancel() {
          cancelled = true;
        },
      },
      { highWaterMark: 0 },
    );
    const fetcher: BuildingFetch = async () =>
      new Response(responseStream, {
        headers: {
          'content-length': String(MAX_BUILDING_MANIFEST_BYTES + 1),
        },
      });
    await expect(
      loadBuildingPackage(manifestUrl, prepared.terrain, fetcher),
    ).rejects.toMatchObject({ stage: 'manifest response' });
    expect(pulls).toBe(0);
    expect(cancelled).toBe(true);
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

  it('loads fully rehashed components that share only a boundary edge', async () => {
    const terrain = createRealManifest();
    const feature = createFeature({
      geometry: {
        type: 'MultiPolygon',
        polygons: [
          {
            exteriorXZ: [
              [-2, -2],
              [0, -2],
              [0, 0],
              [-2, 0],
              [-2, -2],
            ],
            interiorRingsXZ: [],
          },
          {
            exteriorXZ: [
              [0, -2],
              [2, -2],
              [2, 0],
              [0, 0],
              [0, -2],
            ],
            interiorRingsXZ: [],
          },
        ],
      },
      footprintAreaM2: 8,
    });
    const payloadBytes = new TextEncoder().encode(
      JSON.stringify(createBuildingPayload([feature])),
    ).buffer;
    const qaBytes = new TextEncoder().encode(
      JSON.stringify(createBuildingQa([feature])),
    ).buffer;
    const manifest = await createPackageManifest(
      terrain,
      payloadBytes,
      qaBytes,
    );
    const manifestBytes = new TextEncoder().encode(
      JSON.stringify(manifest),
    ).buffer;
    const { fetcher } = createFetcher({
      manifestBytes,
      payloadBytes,
      qaBytes,
    });

    const result = await loadBuildingPackage(manifestUrl, terrain, fetcher);
    expect(result.componentCount).toBe(2);
  });

  it.each([
    'crossing-hole',
    'overlapping-components',
    'boundary-contained-overlap',
    'identical-components',
    'collinear-equivalent-components',
    'outside-aoi',
    'canonical-duplicate',
  ] as const)(
    'rejects fully rehashed %s package geometry in the loader',
    async (kind) => {
      const terrain = createRealManifest();
      const outer: [number, number][] = [
        [-10, -10],
        [10, -10],
        [10, 10],
        [-10, 10],
        [-10, -10],
      ];
      let features;
      if (kind === 'crossing-hole') {
        features = [
          createFeature({
            geometry: {
              type: 'MultiPolygon',
              polygons: [
                {
                  exteriorXZ: outer,
                  interiorRingsXZ: [
                    [
                      [-2, -2],
                      [-2, 12],
                      [2, 12],
                      [2, -2],
                      [-2, -2],
                    ],
                  ],
                },
              ],
            },
            footprintAreaM2: 344,
          }),
        ];
      } else if (kind === 'overlapping-components') {
        features = [
          createFeature({
            geometry: {
              type: 'MultiPolygon',
              polygons: [
                {
                  exteriorXZ: [
                    [-5, -5],
                    [0, -5],
                    [0, 0],
                    [-5, 0],
                    [-5, -5],
                  ],
                  interiorRingsXZ: [],
                },
                {
                  exteriorXZ: [
                    [-1, -1],
                    [4, -1],
                    [4, 4],
                    [-1, 4],
                    [-1, -1],
                  ],
                  interiorRingsXZ: [],
                },
              ],
            },
            footprintAreaM2: 50,
          }),
        ];
      } else if (kind === 'boundary-contained-overlap') {
        features = [
          createFeature({
            geometry: {
              type: 'MultiPolygon',
              polygons: [
                {
                  exteriorXZ: [
                    [-2, -2],
                    [2, -2],
                    [2, 2],
                    [-2, 2],
                    [-2, -2],
                  ],
                  interiorRingsXZ: [],
                },
                {
                  exteriorXZ: [
                    [0, -2],
                    [2, 0],
                    [0, 2],
                    [-2, 0],
                    [0, -2],
                  ],
                  interiorRingsXZ: [],
                },
              ],
            },
            footprintAreaM2: 24,
          }),
        ];
      } else if (
        kind === 'identical-components' ||
        kind === 'collinear-equivalent-components'
      ) {
        const square: [number, number][] = [
          [-1, -1],
          [1, -1],
          [1, 1],
          [-1, 1],
          [-1, -1],
        ];
        const second: [number, number][] =
          kind === 'identical-components'
            ? square
            : [
                [-1, -1],
                [0, -1],
                [1, -1],
                [1, 1],
                [-1, 1],
                [-1, -1],
              ];
        features = [
          createFeature({
            geometry: {
              type: 'MultiPolygon',
              polygons: [
                { exteriorXZ: square, interiorRingsXZ: [] },
                { exteriorXZ: second, interiorRingsXZ: [] },
              ],
            },
            footprintAreaM2: 8,
          }),
        ];
      } else if (kind === 'outside-aoi') {
        features = [
          createFeature({
            geometry: {
              type: 'MultiPolygon',
              polygons: [
                {
                  exteriorXZ: [
                    [499, -1],
                    [501, -1],
                    [501, 1],
                    [499, 1],
                    [499, -1],
                  ],
                  interiorRingsXZ: [],
                },
              ],
            },
            footprintAreaM2: 4,
          }),
        ];
      } else {
        const first = createFeature({ id: 'osm:way:1' });
        const baseRing = first.geometry.polygons[0]!.exteriorXZ;
        const reverseOpen = baseRing.slice(0, -1).reverse();
        const rotatedOpen = [...reverseOpen.slice(1), reverseOpen[0]!];
        const rotatedReversed = [...rotatedOpen, rotatedOpen[0]!];
        features = [
          first,
          createFeature({
            id: 'osm:way:2',
            source: {
              dataset: 'Geofabrik Devon OpenStreetMap extract',
              objectType: 'way',
              osmId: 2,
              version: 1,
              timestamp: '2026-10-17 12:00:00+00:00',
            },
            geometry: {
              type: 'MultiPolygon',
              polygons: [
                {
                  exteriorXZ: rotatedReversed,
                  interiorRingsXZ: [],
                },
              ],
            },
          }),
        ];
      }
      const payload = createBuildingPayload(features);
      const qa = createBuildingQa(features);
      const payloadBytes = new TextEncoder().encode(
        JSON.stringify(payload),
      ).buffer;
      const qaBytes = new TextEncoder().encode(JSON.stringify(qa)).buffer;
      const manifest = await createPackageManifest(
        terrain,
        payloadBytes,
        qaBytes,
        features.length,
      );
      const manifestBytes = new TextEncoder().encode(
        JSON.stringify(manifest),
      ).buffer;
      const { fetcher } = createFetcher({
        manifestBytes,
        payloadBytes,
        qaBytes,
      });
      await expect(
        loadBuildingPackage(manifestUrl, terrain, fetcher),
      ).rejects.toMatchObject({ stage: 'payload validation' });
    },
  );

  it.each([
    ['worldId', 'OTHER-WORLD'],
    ['buildingsSha256', '0'.repeat(64)],
    ['buildingsByteLength', 1],
  ] as const)(
    'rejects a fully rehashed QA package identity mismatch for %s',
    async (field, value) => {
      const prepared = await prepare();
      const changedQa = JSON.parse(
        new TextDecoder().decode(prepared.qaBytes),
      ) as Record<string, unknown>;
      (changedQa.package as Record<string, unknown>)[field] = value;
      const qaBytes = new TextEncoder().encode(
        JSON.stringify(changedQa),
      ).buffer;
      const manifest = structuredClone(prepared.manifest);
      manifest.qaReport.byteLength = qaBytes.byteLength;
      manifest.qaReport.sha256 = await sha256Hex(qaBytes);
      const manifestBytes = new TextEncoder().encode(
        JSON.stringify(manifest),
      ).buffer;
      const { fetcher } = createFetcher({
        manifestBytes,
        payloadBytes: prepared.payloadBytes,
        qaBytes,
      });
      await expect(
        loadBuildingPackage(manifestUrl, prepared.terrain, fetcher),
      ).rejects.toMatchObject({ stage: 'payload validation' });
    },
  );

  it('accepts Python-rounded QA mean heights for a rehashed three-feature fixture', async () => {
    const terrain = createRealManifest();
    const makeDefault = (id: number, offset: number) =>
      createFeature({
        id: `osm:way:${id}`,
        source: {
          dataset: 'Geofabrik Devon OpenStreetMap extract',
          objectType: 'way',
          osmId: id,
          version: 1,
          timestamp: '2026-10-17 12:00:00+00:00',
        },
        geometry: {
          type: 'MultiPolygon',
          polygons: [
            {
              exteriorXZ: [
                [offset, -1],
                [offset + 2, -1],
                [offset + 2, 1],
                [offset, 1],
                [offset, -1],
              ],
              interiorRingsXZ: [],
            },
          ],
        },
      });
    const base = makeDefault(11, 10);
    const tagged = {
      ...base,
      heightM: 3.048,
      heightMethod: 'osm_height' as const,
      heightConfidence: 'tagged_but_unverified' as const,
      heightProvenance: {
        heightM: 3.048,
        method: 'osm_height' as const,
        confidence: 'tagged_but_unverified' as const,
        rawHeight: '10 ft',
        parsedHeightM: 3.048,
        parsedUnit: 'feet',
        rawLevels: null,
        clamp: null,
        fallbackReason: null,
      },
      tags: { building: 'yes', height: '10 ft' },
    };
    const features = [tagged, makeDefault(12, 20), makeDefault(13, 30)];
    const payload = createBuildingPayload(features);
    const qa = createBuildingQa(features);
    (qa.summary as Record<string, unknown>).meanHeightM = 6.349;
    const payloadBytes = new TextEncoder().encode(
      JSON.stringify(payload),
    ).buffer;
    const qaBytes = new TextEncoder().encode(JSON.stringify(qa)).buffer;
    const manifest = await createPackageManifest(
      terrain,
      payloadBytes,
      qaBytes,
      features.length,
    );
    const manifestBytes = new TextEncoder().encode(
      JSON.stringify(manifest),
    ).buffer;
    const { fetcher } = createFetcher({
      manifestBytes,
      payloadBytes,
      qaBytes,
    });
    const result = await loadBuildingPackage(manifestUrl, terrain, fetcher);
    expect(result.features.map((feature) => feature.heightM)).toEqual([
      3.048, 8, 8,
    ]);
  });
});
