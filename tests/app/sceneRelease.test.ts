import { describe, expect, it } from 'vitest';
import {
  CURRENT_2KM_RUNTIME_FILES,
  CURRENT_2KM_HEIGHTFIELD_BYTE_LENGTH,
  loadCurrent2kmRelease,
} from '../../src/app/sceneRelease';

const sha256 = async (bytes: Uint8Array): Promise<string> => {
  const data = bytes.buffer.slice(
    bytes.byteOffset,
    bytes.byteOffset + bytes.byteLength,
  ) as ArrayBuffer;
  const digest = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
};

const canonical = (value: unknown): Uint8Array =>
  new TextEncoder().encode(`${JSON.stringify(sortKeys(value))}\n`);

function sortKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (typeof value !== 'object' || value === null) return value;
  return Object.fromEntries(
    Object.entries(value)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, child]) => [key, sortKeys(child)]),
  );
}

async function makeReleaseResponses(
  byteLengthOverrides: Partial<
    Record<(typeof CURRENT_2KM_RUNTIME_FILES)[number], number>
  > = {},
): Promise<{
  ready: Uint8Array;
  inventory: Uint8Array;
  assets: Map<string, Uint8Array>;
}> {
  const assets = new Map<string, Uint8Array>();
  const entries = await Promise.all(
    CURRENT_2KM_RUNTIME_FILES.map(async (path) => {
      const bytes =
        path === 'heightfield.f32'
          ? new Uint8Array(CURRENT_2KM_HEIGHTFIELD_BYTE_LENGTH)
          : new TextEncoder().encode(`fixture:${path}`);
      assets.set(path, bytes);
      return {
        path,
        byteLength: byteLengthOverrides[path] ?? bytes.byteLength,
        sha256: await sha256(bytes),
      };
    }),
  );
  const body = {
    formatVersion: 1,
    worldId: 'torquay-poc-001',
    sceneProfile: 'current_2km',
    files: entries,
  };
  const releaseId = await sha256(canonical(body));
  const inventory = canonical({ ...body, releaseId });
  const ready = canonical({
    formatVersion: 1,
    worldId: 'torquay-poc-001',
    sceneProfile: 'current_2km',
    releaseId,
    inventoryPath: `releases/${releaseId}/inventory.json`,
    inventoryByteLength: inventory.byteLength,
    inventorySha256: await sha256(inventory),
  });
  return { ready, inventory, assets };
}

function response(bytes: Uint8Array, status = 200): Response {
  const data = bytes.buffer.slice(
    bytes.byteOffset,
    bytes.byteOffset + bytes.byteLength,
  ) as ArrayBuffer;
  return new Response(data, {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

describe('current 2 km readiness and immutable release pin', () => {
  it('loads a bounded ready pointer and inventory and pins every runtime URL', async () => {
    const fixture = await makeReleaseResponses();
    const requests: string[] = [];
    const release = await loadCurrent2kmRelease(
      'http://localhost/worlds/torquay-poc-001-2km/ready.json',
      async (url) => {
        requests.push(url.pathname);
        return url.pathname.endsWith('/ready.json')
          ? response(fixture.ready)
          : response(fixture.inventory);
      },
    );

    expect(requests).toEqual([
      '/worlds/torquay-poc-001-2km/ready.json',
      `/worlds/torquay-poc-001-2km/releases/${release.releaseId}/inventory.json`,
    ]);
    expect(release.releaseRootUrl.pathname).toBe(
      `/worlds/torquay-poc-001-2km/releases/${release.releaseId}/`,
    );
    expect(release.readySha256).toBe(await sha256(fixture.ready));
    expect(release.inventorySha256).toBe(await sha256(fixture.inventory));
    for (const path of CURRENT_2KM_RUNTIME_FILES) {
      const url = new URL(path, release.releaseRootUrl);
      release.assertAssetUrl(url, path);
      expect(release.expectedByteLength(url, path)).toBe(
        fixture.assets.get(path)!.byteLength,
      );
      await release.verifyAsset(
        url,
        fixture.assets.get(path)!.buffer as ArrayBuffer,
        path,
      );
    }
    expect(() =>
      release.assertAssetUrl(
        new URL(
          '/worlds/torquay-poc-001/manifest.json',
          release.releaseRootUrl,
        ),
        'historical manifest',
      ),
    ).toThrow(/outside the pinned immutable release/);
  });

  it('stops before any release or runtime request when readiness is absent', async () => {
    const requests: string[] = [];
    await expect(
      loadCurrent2kmRelease(
        'http://localhost/worlds/torquay-poc-001-2km/ready.json',
        async (url) => {
          requests.push(url.pathname);
          return response(new Uint8Array(), 404);
        },
      ),
    ).rejects.toThrow(/HTTP 404/);
    expect(requests).toEqual(['/worlds/torquay-poc-001-2km/ready.json']);
  });

  it('rejects a bad inventory before constructing any runtime asset URL', async () => {
    const fixture = await makeReleaseResponses();
    const requests: string[] = [];
    await expect(
      loadCurrent2kmRelease(
        'http://localhost/worlds/torquay-poc-001-2km/ready.json',
        async (url) => {
          requests.push(url.pathname);
          if (url.pathname.endsWith('/ready.json'))
            return response(fixture.ready);
          return response(new TextEncoder().encode('{}'));
        },
      ),
    ).rejects.toThrow(/inventory length or SHA-256/);
    expect(requests).toHaveLength(2);
    expect(requests.every((path) => !path.includes('/manifest.json'))).toBe(
      true,
    );
  });

  it.each([
    ['manifest.json', 64 * 1024 + 1],
    ['heightfield.f32', CURRENT_2KM_HEIGHTFIELD_BYTE_LENGTH - 4],
  ] as const)(
    'rejects an impossible %s descriptor before requesting any runtime asset',
    async (path, byteLength) => {
      const fixture = await makeReleaseResponses({ [path]: byteLength });
      const requests: string[] = [];
      await expect(
        loadCurrent2kmRelease(
          'http://localhost/worlds/torquay-poc-001-2km/ready.json',
          async (url) => {
            requests.push(url.pathname);
            return url.pathname.endsWith('/ready.json')
              ? response(fixture.ready)
              : response(fixture.inventory);
          },
        ),
      ).rejects.toThrow(/byteLength.*permitted current_2km size/);
      expect(requests).toHaveLength(2);
      expect(requests[0]).toBe('/worlds/torquay-poc-001-2km/ready.json');
      expect(requests[1]).toContain('/inventory.json');
      expect(
        requests.some(
          (request) =>
            request.endsWith('/manifest.json') ||
            request.endsWith('/heightfield.f32') ||
            request.endsWith('/roads.json') ||
            request.endsWith('/buildings.json'),
        ),
      ).toBe(false);
    },
  );

  it('rejects runtime response bytes that differ from the pinned inventory', async () => {
    const fixture = await makeReleaseResponses();
    const release = await loadCurrent2kmRelease(
      'http://localhost/worlds/torquay-poc-001-2km/ready.json',
      async (url) =>
        url.pathname.endsWith('/ready.json')
          ? response(fixture.ready)
          : response(fixture.inventory),
    );
    const manifestUrl = new URL('manifest.json', release.releaseRootUrl);
    await expect(
      release.verifyAsset(
        manifestUrl,
        new TextEncoder().encode('changed').buffer,
        'manifest',
      ),
    ).rejects.toThrow(/byte length|SHA-256/);
  });
});
