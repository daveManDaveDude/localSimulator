import { describe, expect, it } from 'vitest';
import {
  createOverviewFeatures,
  createOverviewManifest,
  fixtureTerrain,
  fixtureTerrainSha256,
} from './overviewFixtures';
import {
  validateOverviewFeatureCollection,
  validateOverviewManifest,
} from '../../src/geo/overviewSchema';

describe('overview package schema', () => {
  it('accepts a fixed offline AOI overview bound to the loaded terrain', () => {
    const result = validateOverviewManifest(
      createOverviewManifest(256, 'a'.repeat(64)),
      fixtureTerrain,
      fixtureTerrainSha256,
    );
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    const features = validateOverviewFeatureCollection(
      createOverviewFeatures(),
      result.value,
    );
    expect(features.ok).toBe(true);
    if (features.ok) {
      expect(features.value.features).toHaveLength(1);
      expect(features.value.features[0]?.properties.selectionStatus).toBe(
        'selected_pending_coverage',
      );
    }
  });

  it.each([
    [
      'terrain identity',
      (manifest: Record<string, unknown>) => {
        (manifest.terrainIdentity as Record<string, unknown>).manifestSha256 =
          '0'.repeat(64);
      },
      'terrainIdentity.manifestSha256',
    ],
    [
      'AOI status',
      (manifest: Record<string, unknown>) => {
        (manifest.aoi as Record<string, unknown>).selectionStatus = 'approved';
      },
      'aoi.selectionStatus',
    ],
    [
      'geographic boundary',
      (manifest: Record<string, unknown>) => {
        const aoi = manifest.aoi as Record<string, unknown>;
        const boundary = aoi.boundaryWgs84 as Record<string, unknown>;
        boundary.ring = [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
          [0, 0],
        ];
      },
      'boundaryWgs84.ring',
    ],
    [
      'coordinate operation',
      (manifest: Record<string, unknown>) => {
        (manifest.coordinateOperation as Record<string, unknown>).bngToWgs84 =
          null;
      },
      'coordinateOperation.bngToWgs84',
    ],
  ])('rejects inconsistent %s metadata', (_name, mutate, path) => {
    const manifest = structuredClone(
      createOverviewManifest(256, 'a'.repeat(64)),
    ) as unknown as Record<string, unknown>;
    mutate(manifest);
    const result = validateOverviewManifest(
      manifest,
      fixtureTerrain,
      fixtureTerrainSha256,
    );
    expect(result.ok).toBe(false);
    if (!result.ok)
      expect(result.issues.some((issue) => issue.path.includes(path))).toBe(
        true,
      );
  });

  it.each([
    [
      'duplicate IDs',
      (features: ReturnType<typeof createOverviewFeatures>) => {
        features.features.push(structuredClone(features.features[0]!));
      },
    ],
    [
      'outside coordinates',
      (features: ReturnType<typeof createOverviewFeatures>) => {
        const geometry = features.features[0]!.geometry;
        if (geometry.type === 'Polygon') geometry.coordinates[0]![0] = [0, 0];
      },
    ],
    [
      'a changed AOI ring',
      (features: ReturnType<typeof createOverviewFeatures>) => {
        const geometry = features.features[0]!.geometry;
        if (geometry.type === 'Polygon')
          geometry.coordinates[0]![0] = [-3.5, 50.47];
      },
    ],
  ])('rejects feature collection with %s', (_name, mutate) => {
    const manifest = createOverviewManifest(256, 'a'.repeat(64));
    const features = createOverviewFeatures();
    mutate(features);
    const result = validateOverviewFeatureCollection(features, manifest);
    expect(result.ok).toBe(false);
  });
});
