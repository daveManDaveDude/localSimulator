import { describe, expect, it } from 'vitest';
import {
  parseRoadSurfacePreviewManifest,
  parseRoadSurfacePreviewQa,
  ROAD_SURFACE_GRID,
  ROAD_SURFACE_PREVIEW_ALGORITHM,
} from '../../src/geo/roadSurfaceSchema';

const source = {
  releaseId: 'a'.repeat(64),
  readySha256: 'b'.repeat(64),
  inventorySha256: 'c'.repeat(64),
  terrainManifestSha256: 'd'.repeat(64),
  terrainHeightfieldSha256: 'e'.repeat(64),
  roadManifestSha256: 'f'.repeat(64),
  roadPayloadSha256: '0'.repeat(64),
};

const sourceMetadata = {
  worldId: 'torquay-poc-001',
  sceneProfile: 'current_2km',
  roadFeatureCount: 1044,
  rasterComparisonInputs: [
    {
      path: 'data/raw/ea_dtm/SX96nw/SX96nw_DTM_1m.tif',
      byteLength: 1024,
      sha256: '1'.repeat(64),
    },
    {
      path: 'data/raw/ea_dtm/SX96sw/SX96sw_DTM_1m.tif',
      byteLength: 2048,
      sha256: '2'.repeat(64),
    },
  ],
};

const grid = {
  columns: ROAD_SURFACE_GRID.columns,
  rows: ROAD_SURFACE_GRID.rows,
  spacingM: ROAD_SURFACE_GRID.spacingM,
  widthM: ROAD_SURFACE_GRID.widthM,
  depthM: ROAD_SURFACE_GRID.depthM,
  rowOrder: 'north-to-south',
  byteOrder: 'little-endian',
  encoding: 'float32',
  valueMeaning: 'visual world Y relative to original terrain origin elevation',
};

function manifest() {
  return {
    formatVersion: 1,
    worldId: 'torquay-poc-001',
    sceneProfile: 'current_2km',
    packageType: 'road-surface-display-grid-derivative',
    algorithmVersion: ROAD_SURFACE_PREVIEW_ALGORITHM,
    interpretation: 'Visual approximation only.',
    source,
    grid,
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
        byteLength: ROAD_SURFACE_GRID.heightfieldByteLength,
        sha256: '1'.repeat(64),
      },
      qa: { path: 'qa.json', byteLength: 200, sha256: '2'.repeat(64) },
    },
  };
}

function qa() {
  return {
    formatVersion: 1,
    algorithmVersion: ROAD_SURFACE_PREVIEW_ALGORITHM,
    source,
    sourceMetadata,
    derivative: {
      path: 'heightfield.f32',
      byteLength: ROAD_SURFACE_GRID.heightfieldByteLength,
      sha256: '1'.repeat(64),
      grid,
    },
  };
}

describe('road-surface preview contract', () => {
  it('accepts only the pinned algorithm, fixed grid, and bounded asset descriptors', () => {
    expect(parseRoadSurfacePreviewManifest(manifest()).grid.columns).toBe(1001);
    expect(parseRoadSurfacePreviewQa(qa()).derivative.sha256).toBe(
      '1'.repeat(64),
    );
  });

  it('rejects incompatible parameters, source identity, and grid declarations', () => {
    const invalidParameter = manifest();
    invalidParameter.parameters.targetCrossfallPercent = 1;
    expect(() => parseRoadSurfacePreviewManifest(invalidParameter)).toThrow();

    const invalidGrid = manifest();
    Reflect.set(invalidGrid.grid, 'columns', 1000);
    expect(() => parseRoadSurfacePreviewManifest(invalidGrid)).toThrow();

    const invalidSource = qa();
    invalidSource.source.readySha256 = 'invalid';
    expect(() => parseRoadSurfacePreviewQa(invalidSource)).toThrow();

    const invalidMetadata = qa();
    invalidMetadata.sourceMetadata.rasterComparisonInputs[0]!.path =
      'outside/source.tif';
    expect(() => parseRoadSurfacePreviewQa(invalidMetadata)).toThrow();
  });
});
