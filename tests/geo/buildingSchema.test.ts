import { describe, expect, it } from 'vitest';
import {
  validateBuildingPackageManifest,
  validateBuildingPayload,
} from '../../src/geo/buildingSchema';
import { createRealManifest } from './fixtures';
import {
  createBuildingPayload,
  createBuildingQa,
  createFeature,
  createPackageManifest,
} from './buildingFixtures';

async function createValidInputs() {
  const terrain = createRealManifest();
  const features = [createFeature()];
  const payload = createBuildingPayload(features);
  const qa = createBuildingQa(features);
  const payloadBytes = new TextEncoder().encode(JSON.stringify(payload)).buffer;
  const qaBytes = new TextEncoder().encode(JSON.stringify(qa)).buffer;
  const manifest = await createPackageManifest(terrain, payloadBytes, qaBytes);
  return { terrain, features, payload, qa, payloadBytes, qaBytes, manifest };
}

describe('validateBuildingPackageManifest', () => {
  it('binds the complete package identity to the loaded EA terrain', async () => {
    const { terrain, manifest } = await createValidInputs();
    const result = validateBuildingPackageManifest(manifest, terrain);
    expect(result.ok).toBe(true);
  });

  it.each([
    ['terrainIdentity.origin.eastingM', 'origin'],
    ['terrainIdentity.heightfieldSha256', 'heightfield'],
    ['aoi.boundsM', 'aoi.boundsM'],
    ['coordinateOperation.wgs84ToBng.definition', 'definition'],
    ['buildings.path', 'buildings.json'],
    ['qaReport.path', 'qa.json'],
  ])('rejects mismatched manifest field %s', async (path, message) => {
    const { terrain, manifest } = await createValidInputs();
    const changed = structuredClone(manifest) as unknown as Record<
      string,
      unknown
    >;
    const [parentPath, childPath] = path.split('.');
    if (!parentPath) throw new Error('expected a nested test path');
    if (childPath) {
      const parent = changed[parentPath] as Record<string, unknown>;
      if (parentPath === 'terrainIdentity' && childPath === 'origin') {
        (parent.origin as Record<string, unknown>).eastingM = 123;
      } else if (parentPath === 'coordinateOperation') {
        (parent.wgs84ToBng as Record<string, unknown>).definition =
          'proj=pipeline step proj=tmerc lon_0=20';
      } else if (parentPath === 'terrainIdentity') {
        parent[childPath] = '0'.repeat(64);
      } else if (parentPath === 'aoi') {
        parent.boundsM = [0, 0, 1000, 1000];
      } else if (parentPath === 'buildings') {
        parent.path = '../buildings.json';
      } else if (parentPath === 'qaReport') {
        parent.path = '../qa.json';
      }
    }
    const result = validateBuildingPackageManifest(changed, terrain);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      const evidence = result.issues
        .map((issue) => `${issue.path}: ${issue.message}`)
        .join(' ');
      expect(evidence.toLowerCase()).toContain(message.toLowerCase());
      expect(
        result.issues.some((issue) => issue.path.startsWith(parentPath)),
      ).toBe(true);
    }
  });

  it('rejects an unsafe or oversized asset before fetching it', async () => {
    const { terrain, manifest } = await createValidInputs();
    const changed = structuredClone(manifest) as unknown as Record<
      string,
      unknown
    >;
    (changed.buildings as Record<string, unknown>).byteLength =
      20 * 1024 * 1024;
    const result = validateBuildingPackageManifest(changed, terrain);
    expect(result.ok).toBe(false);
    if (!result.ok)
      expect(
        result.issues.some((issue) => issue.path === 'buildings.byteLength'),
      ).toBe(true);
  });

  it.each([
    'missing',
    'malformed',
    'nonfinite',
    'unclosed',
    'inconsistent',
    'missing closure marker',
  ] as const)('rejects a %s WGS84 AOI boundary', async (mutation) => {
    const { terrain, manifest } = await createValidInputs();
    const changed = structuredClone(manifest) as unknown as Record<
      string,
      unknown
    >;
    const aoi = changed.aoi as Record<string, unknown>;
    if (mutation === 'missing') {
      delete aoi.boundaryWgs84;
    } else {
      const boundary = aoi.boundaryWgs84 as Record<string, unknown>;
      if (mutation === 'missing closure marker') {
        delete boundary.closedRing;
      } else if (mutation === 'malformed') {
        boundary.ring = [[-3.5]];
      } else {
        const ring = boundary.ring as unknown[][];
        if (mutation === 'nonfinite') {
          ring[1]![0] = Number.NaN;
        } else if (mutation === 'unclosed') {
          ring[4] = [-3.54, 50.48];
        } else {
          ring[1]![0] = -3.4;
        }
      }
    }
    const result = validateBuildingPackageManifest(changed, terrain);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(
        result.issues.some((issue) =>
          issue.path.startsWith('aoi.boundaryWgs84'),
        ),
      ).toBe(true);
    }
  });
});

describe('validateBuildingPayload', () => {
  it('accepts an intact feature, terrain binding, and matching QA', async () => {
    const { terrain, payload, qa, payloadBytes, qaBytes } =
      await createValidInputs();
    const manifest = await createPackageManifest(
      terrain,
      payloadBytes,
      qaBytes,
    );
    const manifestResult = validateBuildingPackageManifest(manifest, terrain);
    expect(manifestResult.ok).toBe(true);
    if (!manifestResult.ok) return;
    const result = validateBuildingPayload(payload, qa, manifestResult.value);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.features).toHaveLength(1);
      expect(result.value.componentCount).toBe(1);
      expect(result.value.heightMethodCounts.estimated_default).toBe(1);
    }
  });

  it('rejects feature height and provenance that disagree with retained tags', async () => {
    const { terrain, payload, qa, payloadBytes, qaBytes } =
      await createValidInputs();
    const manifest = await createPackageManifest(
      terrain,
      payloadBytes,
      qaBytes,
    );
    const validManifest = validateBuildingPackageManifest(manifest, terrain);
    expect(validManifest.ok).toBe(true);
    if (!validManifest.ok) return;
    const changed = structuredClone(payload) as Record<string, unknown>;
    const feature = (changed.buildings as Record<string, unknown>[])[0]!;
    (feature.tags as Record<string, string>).height = '100';
    const result = validateBuildingPayload(changed, qa, validManifest.value);
    expect(result.ok).toBe(false);
    if (!result.ok)
      expect(
        result.issues.some((issue) => issue.path.includes('heightProvenance')),
      ).toBe(true);
  });

  it('rejects null geometry, boolean numeric height, and self-intersecting rings', async () => {
    const { terrain, payloadBytes, qaBytes, qa } = await createValidInputs();
    const manifest = await createPackageManifest(
      terrain,
      payloadBytes,
      qaBytes,
    );
    const validManifest = validateBuildingPackageManifest(manifest, terrain);
    if (!validManifest.ok)
      throw new Error('expected fixture manifest to validate');
    const nullGeometry = structuredClone(createBuildingPayload()) as Record<
      string,
      unknown
    >;
    (nullGeometry.buildings as Record<string, unknown>[])[0]!.geometry = null;
    expect(
      validateBuildingPayload(nullGeometry, qa, validManifest.value).ok,
    ).toBe(false);

    const booleanHeight = structuredClone(createBuildingPayload()) as Record<
      string,
      unknown
    >;
    (booleanHeight.buildings as Record<string, unknown>[])[0]!.heightM = true;
    expect(
      validateBuildingPayload(booleanHeight, qa, validManifest.value).ok,
    ).toBe(false);

    const bowTie = createFeature({
      geometry: {
        type: 'MultiPolygon',
        polygons: [
          {
            exteriorXZ: [
              [-1, -1],
              [1, 1],
              [-1, 1],
              [1, -1],
              [-1, -1],
            ],
            interiorRingsXZ: [],
          },
        ],
      },
    });
    const bowTiePayload = createBuildingPayload([bowTie]);
    const invalid = validateBuildingPayload(
      bowTiePayload,
      createBuildingQa([bowTie]),
      validManifest.value,
    );
    expect(invalid.ok).toBe(false);
  });

  it('supports a correctly wound hole and validates the hole count', async () => {
    const feature = createFeature({
      geometry: {
        type: 'MultiPolygon',
        polygons: [
          {
            exteriorXZ: [
              [-1, -1],
              [1, -1],
              [1, 1],
              [-1, 1],
              [-1, -1],
            ],
            interiorRingsXZ: [
              [
                [-0.5, -0.5],
                [-0.5, 0.5],
                [0.5, 0.5],
                [0.5, -0.5],
                [-0.5, -0.5],
              ],
            ],
          },
        ],
      },
      footprintAreaM2: 3,
    });
    const { terrain } = await createValidInputs();
    const payload = createBuildingPayload([feature]);
    const qa = createBuildingQa([feature]);
    const payloadBytes = new TextEncoder().encode(
      JSON.stringify(payload),
    ).buffer;
    const qaBytes = new TextEncoder().encode(JSON.stringify(qa)).buffer;
    const manifest = await createPackageManifest(
      terrain,
      payloadBytes,
      qaBytes,
    );
    const validManifest = validateBuildingPackageManifest(manifest, terrain);
    if (!validManifest.ok)
      throw new Error('expected hole fixture manifest to validate');
    const result = validateBuildingPayload(payload, qa, validManifest.value);
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.value.holeCount).toBe(1);
  });
});
