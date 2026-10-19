import { describe, expect, it } from 'vitest';
import type { OverviewManifest } from '../../src/geo/overviewSchema';
import {
  selectOverviewLayers,
  type OverviewLayerInputs,
} from '../../src/geo/overviewLayerState';
import type { LoadedRoadPackage } from '../../src/geo/roadSchema';
import type { LoadedBuildingPackage } from '../../src/geo/buildingSchema';
import {
  createOverviewFeatures,
  createOverviewManifest,
  fixtureTerrainSha256,
} from './overviewFixtures';

const digest = (letter: string): string => letter.repeat(64);

function overviewWithOptionalLayers(): OverviewManifest {
  const overview = createOverviewManifest(256, digest('a'));
  overview.includedLayers = ['aoi', 'roads', 'buildings'];
  overview.optionalLayerIdentities = {
    roads: {
      manifestSha256: digest('b'),
      payload: { path: 'roads.json', byteLength: 100, sha256: digest('c') },
      qa: { path: 'qa.json', byteLength: 50, sha256: digest('d') },
      source: { sha256: digest('e') },
      terrainManifestSha256: fixtureTerrainSha256,
    },
    buildings: {
      manifestSha256: digest('f'),
      payload: { path: 'buildings.json', byteLength: 200, sha256: digest('a') },
      qa: { path: 'qa.json', byteLength: 60, sha256: digest('b') },
      source: { sha256: digest('c') },
      terrainManifestSha256: fixtureTerrainSha256,
    },
  };
  return overview;
}

function packages(): Pick<OverviewLayerInputs, 'roads' | 'buildings'> {
  const roads = {
    manifestSha256: digest('b'),
    manifest: {
      assets: {
        roads: { path: 'roads.json', byteLength: 100, sha256: digest('c') },
        qa: { path: 'qa.json', byteLength: 50, sha256: digest('d') },
      },
      source: { sha256: digest('e') },
      terrainIdentity: { manifestSha256: fixtureTerrainSha256 },
    },
  } as unknown as LoadedRoadPackage;
  const buildings = {
    manifestSha256: digest('f'),
    manifest: {
      buildings: {
        path: 'buildings.json',
        byteLength: 200,
        sha256: digest('a'),
      },
      qaReport: { path: 'qa.json', byteLength: 60, sha256: digest('b') },
      provenance: { sha256: digest('c') },
      terrainIdentity: { manifestSha256: fixtureTerrainSha256 },
    },
  } as unknown as LoadedBuildingPackage;
  return { roads, buildings };
}

describe('selectOverviewLayers', () => {
  it('shows AOI alone until source packages are loaded and visible', () => {
    const overview = overviewWithOptionalLayers();
    const features = createOverviewFeatures();
    const absent = selectOverviewLayers(overview, features, {
      roadsVisible: true,
      buildingsVisible: true,
    });
    expect(absent.roads).toBe('not-loaded');
    expect(absent.buildings).toBe('not-loaded');
    expect(
      absent.visibleCollection.features.map(
        (feature) => feature.properties.role,
      ),
    ).toEqual(['aoi']);

    const loaded = packages();
    const hidden = selectOverviewLayers(overview, features, {
      ...loaded,
      roadsVisible: false,
      buildingsVisible: false,
    });
    expect(hidden.roads).toBe('hidden');
    expect(hidden.buildings).toBe('hidden');
    expect(hidden.visibleCollection.features).toHaveLength(1);
  });

  it('requires both independently loaded optional packages to match before display', () => {
    const overview = overviewWithOptionalLayers();
    const loaded = packages();
    const valid = selectOverviewLayers(overview, createOverviewFeatures(), {
      ...loaded,
      roadsVisible: true,
      buildingsVisible: true,
    });
    expect(valid.roads).toBe('visible');
    expect(valid.buildings).toBe('visible');
    expect(valid.visibleCollection.features).toHaveLength(1);

    const mismatched = {
      ...loaded,
      roads: {
        ...loaded.roads!,
        manifestSha256: digest('0'),
      },
    };
    const state = selectOverviewLayers(overview, createOverviewFeatures(), {
      ...mismatched,
      roadsVisible: true,
      buildingsVisible: true,
    });
    expect(state.roads).toBe('identity-mismatch');
    expect(state.buildings).toBe('visible');
    expect(state.identityMismatches).toEqual(['roads']);
  });

  it('does not display optional geometry when the overview did not include that layer', () => {
    const overview = createOverviewManifest(256, digest('a'));
    const packagesLoaded = packages();
    const state = selectOverviewLayers(overview, createOverviewFeatures(), {
      ...packagesLoaded,
      roadsVisible: true,
      buildingsVisible: true,
    });
    expect(state.roads).toBe('not-included');
    expect(state.buildings).toBe('not-included');
    expect(state.visibleCollection.features).toHaveLength(1);
  });
});
