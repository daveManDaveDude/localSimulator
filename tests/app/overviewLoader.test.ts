import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  createOverviewResponseBytes,
  fixtureTerrain,
  fixtureTerrainSha256,
} from '../geo/overviewFixtures';
import {
  loadOverviewPackage,
  OverviewLoadError,
  REAL_OVERVIEW_MANIFEST_URL,
  type OverviewFetch,
} from '../../src/app/overviewLoader';

const manifestUrl = new URL(`http://localhost${REAL_OVERVIEW_MANIFEST_URL}`);

afterEach(() => vi.unstubAllGlobals());

function responseFor(bytes: Uint8Array, declaredLength?: string): Response {
  const headers = new Headers({ 'content-type': 'application/json' });
  if (declaredLength !== undefined)
    headers.set('content-length', declaredLength);
  return new Response(bytes.slice().buffer, { status: 200, headers });
}

describe('loadOverviewPackage', () => {
  it('loads only the fixed same-origin manifest and integrity-bound GeoJSON', async () => {
    const fixture = await createOverviewResponseBytes();
    const requests: string[] = [];
    const fetcher: OverviewFetch = async (url) => {
      requests.push(url.pathname);
      return url.pathname.endsWith('manifest.json')
        ? responseFor(fixture.manifestBytes)
        : responseFor(fixture.featureBytes);
    };

    const loaded = await loadOverviewPackage(
      manifestUrl,
      fixtureTerrain,
      fixtureTerrainSha256,
      fetcher,
    );
    expect(loaded.features.features).toHaveLength(1);
    expect(loaded.manifestSha256).toMatch(/^[a-f0-9]{64}$/);
    expect(requests).toEqual([
      REAL_OVERVIEW_MANIFEST_URL,
      '/worlds/torquay-poc-001/overview/features.geojson',
    ]);
  });

  it('rejects external, traversing and non-fixed manifest URLs before fetching', async () => {
    vi.stubGlobal('location', { origin: 'http://localhost' });
    const fetcher: OverviewFetch = async () => {
      throw new Error('fetch must not be called');
    };
    for (const url of [
      'https://example.invalid/worlds/torquay-poc-001/overview/manifest.json',
      'http://localhost/worlds/torquay-poc-001/overview/../manifest.json',
      'http://localhost/worlds/torquay-poc-001/overview/manifest.json?x=1',
    ]) {
      await expect(
        loadOverviewPackage(url, fixtureTerrain, fixtureTerrainSha256, fetcher),
      ).rejects.toMatchObject({ stage: 'manifest URL' });
    }
  });

  it('rejects a feature checksum mismatch with an asset-specific stage', async () => {
    const fixture = await createOverviewResponseBytes();
    const corrupted = fixture.featureBytes.slice();
    corrupted[corrupted.length - 3] = corrupted[corrupted.length - 3]! ^ 1;
    const fetcher: OverviewFetch = async (url) =>
      url.pathname.endsWith('manifest.json')
        ? responseFor(fixture.manifestBytes)
        : responseFor(corrupted);

    await expect(
      loadOverviewPackage(
        manifestUrl,
        fixtureTerrain,
        fixtureTerrainSha256,
        fetcher,
      ),
    ).rejects.toMatchObject({
      name: 'OverviewLoadError',
      stage: 'features checksum',
    } satisfies Partial<OverviewLoadError>);
  });

  it('cancels an oversized feature stream even when length is absent or false', async () => {
    for (const declaredLength of [undefined, '12']) {
      const fixture = await createOverviewResponseBytes();
      let cancelled = false;
      let pulls = 0;
      const tooLarge = new Uint8Array(8 * 1024 * 1024 + 1);
      const stream = new ReadableStream<Uint8Array>({
        pull(controller) {
          pulls += 1;
          if (pulls === 1) controller.enqueue(tooLarge);
          else controller.enqueue(new Uint8Array([1]));
        },
        cancel() {
          cancelled = true;
        },
      });
      const fetcher: OverviewFetch = async (url) =>
        url.pathname.endsWith('manifest.json')
          ? responseFor(fixture.manifestBytes)
          : new Response(stream, {
              status: 200,
              ...(declaredLength === undefined
                ? {}
                : { headers: { 'content-length': declaredLength } }),
            });

      await expect(
        loadOverviewPackage(
          manifestUrl,
          fixtureTerrain,
          fixtureTerrainSha256,
          fetcher,
        ),
      ).rejects.toMatchObject({ stage: 'features response' });
      expect(cancelled).toBe(true);
      expect(pulls).toBeLessThan(3);
    }
  });

  it('rejects terrain-manifest mismatch before requesting feature bytes', async () => {
    const fixture = await createOverviewResponseBytes();
    let featureRequested = false;
    const fetcher: OverviewFetch = async (url) => {
      if (url.pathname.endsWith('manifest.json'))
        return responseFor(fixture.manifestBytes);
      featureRequested = true;
      return responseFor(fixture.featureBytes);
    };
    await expect(
      loadOverviewPackage(manifestUrl, fixtureTerrain, 'e'.repeat(64), fetcher),
    ).rejects.toMatchObject({ stage: 'manifest validation' });
    expect(featureRequested).toBe(false);
  });
});
