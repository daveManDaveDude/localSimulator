import { describe, expect, it } from 'vitest';
import {
  maximumTerrainHeightUnderFeature,
  subdivideTerrainBoundary,
} from '../../src/geo/buildingGeometry';
import { createTerrainGrid } from '../../src/geo/terrainGrid';
import type { XzPosition } from '../../src/geo/buildingSchema';
import { createFeature } from './buildingFixtures';

function createUnevenGrid() {
  const heights = Float32Array.from([
    1, 2, 4, 3, 0, 2, 8, 1, 5, 2, 7, 3, 11, 0, 6, 0, 9, 2, 7, 1, 4, 1, 5, 3, 8,
  ]);
  return createTerrainGrid({
    columns: 5,
    rows: 5,
    spacingM: 1,
    widthM: 4,
    depthM: 4,
    heights,
  });
}

describe('terrain-subdivided building boundaries', () => {
  it('splits each ring across grid rows, columns, and the fixed triangle diagonals', () => {
    const grid = createUnevenGrid();
    const ring = [
      [-1.75, -1.25],
      [1.25, 1.5],
      [1.5, -1.5],
      [-1.5, 1.25],
      [-1.75, -1.25],
    ] as XzPosition[];
    const points = subdivideTerrainBoundary(ring, grid, 'test footprint');
    expect(points.length).toBeGreaterThan(ring.length);
    expect(points[0]).toEqual(points.at(-1));
    for (let index = 0; index < points.length - 1; index += 1) {
      const a = points[index]!;
      const b = points[index + 1]!;
      const midpointHeight = grid.sampleHeight(
        (a.x + b.x) / 2,
        (a.z + b.z) / 2,
      );
      expect(midpointHeight).not.toBeNull();
      expect(midpointHeight).toBeCloseTo((a.groundY + b.groundY) / 2, 5);
    }
  });

  it('samples exact endpoints and reports terrain gaps with feature context', () => {
    const grid = createUnevenGrid();
    const ring = [
      [-2, -2],
      [-1, -2],
      [-1, -1],
      [-2, -1],
      [-2, -2],
    ] as XzPosition[];
    const points = subdivideTerrainBoundary(ring, grid, 'osm:way:9');
    expect(points[0]?.groundY).toBe(grid.sampleHeight(-2, -2));
    expect(points.at(-1)?.groundY).toBe(points[0]?.groundY);
    const outside = [
      [-2.1, 0],
      [-1, 0],
      [-1, 1],
      [-2.1, 0],
    ] as XzPosition[];
    expect(() =>
      subdivideTerrainBoundary(outside, grid, 'osm:way:outside'),
    ).toThrow('osm:way:outside');
  });

  it('includes an interior terrain peak when selecting the feature roof reference', () => {
    const heights = new Float32Array(25);
    heights[12] = 40;
    const grid = createTerrainGrid({
      columns: 5,
      rows: 5,
      spacingM: 1,
      widthM: 4,
      depthM: 4,
      heights,
    });
    const feature = createFeature({
      geometry: {
        type: 'MultiPolygon',
        polygons: [
          {
            exteriorXZ: [
              [-1.5, -1.5],
              [1.5, -1.5],
              [1.5, 1.5],
              [-1.5, 1.5],
              [-1.5, -1.5],
            ],
            interiorRingsXZ: [],
          },
        ],
      },
    });
    expect(maximumTerrainHeightUnderFeature(feature, grid)).toBe(40);
  });

  it('does not count the highest terrain vertex inside a courtyard hole', () => {
    const heights = new Float32Array(25);
    heights[12] = 40;
    const grid = createTerrainGrid({
      columns: 5,
      rows: 5,
      spacingM: 1,
      widthM: 4,
      depthM: 4,
      heights,
    });
    const feature = createFeature({
      geometry: {
        type: 'MultiPolygon',
        polygons: [
          {
            exteriorXZ: [
              [-1.5, -1.5],
              [1.5, -1.5],
              [1.5, 1.5],
              [-1.5, 1.5],
              [-1.5, -1.5],
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
    });
    const maximum = maximumTerrainHeightUnderFeature(feature, grid);
    expect(maximum).toBeLessThan(40);
    expect(maximum).toBeGreaterThan(0);
  });
});
