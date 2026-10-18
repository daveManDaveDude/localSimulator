import { describe, expect, it } from 'vitest';
import { Mesh } from 'three';
import type { LoadedBuildingPackage } from '../geo/buildingSchema';
import { WALL_BASE_BURIAL_M } from '../geo/buildingSchema';
import { createTerrainGrid } from '../geo/terrainGrid';
import { createBuildings } from './createBuildings';
import { createFeature } from '../../tests/geo/buildingFixtures';

function createGrid(heights: Float32Array = new Float32Array(25)) {
  return createTerrainGrid({
    columns: 5,
    rows: 5,
    spacingM: 1,
    widthM: 4,
    depthM: 4,
    heights,
  });
}

function packageFor(
  features: ReturnType<typeof createFeature>[],
): LoadedBuildingPackage {
  return {
    manifest: {} as LoadedBuildingPackage['manifest'],
    features,
    qa: {} as LoadedBuildingPackage['qa'],
    componentCount: features.reduce(
      (sum, feature) => sum + feature.geometry.polygons.length,
      0,
    ),
    holeCount: features.reduce(
      (sum, feature) =>
        sum +
        feature.geometry.polygons.reduce(
          (count, polygon) => count + polygon.interiorRingsXZ.length,
          0,
        ),
      0,
    ),
    heightMethodCounts: {
      osm_height: 0,
      estimated_levels: 0,
      estimated_default: features.length,
    },
  };
}

function findMesh(
  group: ReturnType<typeof createBuildings>,
  label: string,
): Mesh {
  const mesh = group.children.find((child) => child.name.includes(label));
  if (!(mesh instanceof Mesh)) throw new Error(`missing mesh ${label}`);
  return mesh;
}

function roofArea(mesh: Mesh): number {
  const positions = mesh.geometry.getAttribute('position');
  const indices = mesh.geometry.getIndex();
  if (!indices) throw new Error('expected indexed roof geometry');
  let area = 0;
  for (let offset = 0; offset < indices.count; offset += 3) {
    const a = indices.getX(offset);
    const b = indices.getX(offset + 1);
    const c = indices.getX(offset + 2);
    const ax = positions.getX(a);
    const az = positions.getZ(a);
    const bx = positions.getX(b);
    const bz = positions.getZ(b);
    const cx = positions.getX(c);
    const cz = positions.getZ(c);
    area += Math.abs((bx - ax) * (cz - az) - (bz - az) * (cx - ax)) / 2;
  }
  return area;
}

describe('createBuildings', () => {
  it('creates upward roof normals and sharp finite walls with terrain-contact subdivisions', () => {
    const heights = Float32Array.from([
      0, 1, 0, 2, 0, 1, 3, 2, 1, 0, 0, 1, 8, 3, 0, 2, 1, 4, 0, 1, 0, 1, 0, 2, 0,
    ]);
    const grid = createGrid(heights);
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
      footprintAreaM2: 9,
    });
    const group = createBuildings(packageFor([feature]), grid);
    const roof = findMesh(group, 'flat roofs');
    const walls = findMesh(group, 'terrain-following walls');
    const roofPositions = roof.geometry.getAttribute('position');
    const roofNormals = roof.geometry.getAttribute('normal');
    expect(
      [...Array(roofPositions.count).keys()].every(
        (index) => roofNormals.getY(index) > 0.999,
      ),
    ).toBe(true);
    expect(roofArea(roof)).toBeCloseTo(9, 5);
    expect(roofPositions.getY(0)).toBe(16);

    const positions = walls.geometry.getAttribute('position');
    const normals = walls.geometry.getAttribute('normal');
    const bottomVertices: [number, number, number][] = [];
    for (let index = 0; index < positions.count; index += 1) {
      const x = positions.getX(index);
      const y = positions.getY(index);
      const z = positions.getZ(index);
      if (y < 16) {
        bottomVertices.push([x, y, z]);
        expect(y).toBeCloseTo(
          (grid.sampleHeight(x, z) ?? NaN) - WALL_BASE_BURIAL_M,
          5,
        );
      }
      expect(
        Number.isFinite(
          normals.getX(index) + normals.getY(index) + normals.getZ(index),
        ),
      ).toBe(true);
      expect(
        Math.hypot(
          normals.getX(index),
          normals.getY(index),
          normals.getZ(index),
        ),
      ).toBeCloseTo(1, 5);
    }
    expect(
      bottomVertices.some(([x, , z]) => Math.abs(x) < 1.5 || Math.abs(z) < 1.5),
    ).toBe(true);
    expect(group.userData.roofReferencePolicy).toContain(
      'visual placement convention only',
    );
    expect(group.userData.wallBaseBurialM).toBe(WALL_BASE_BURIAL_M);
  });

  it('triangulates concave and multipart roofs without filling holes', () => {
    const grid = createGrid();
    const feature = createFeature({
      geometry: {
        type: 'MultiPolygon',
        polygons: [
          {
            exteriorXZ: [
              [-1.5, -1.5],
              [0.5, -1.5],
              [0.5, -0.5],
              [-0.5, -0.5],
              [-0.5, 1.5],
              [-1.5, 1.5],
              [-1.5, -1.5],
            ],
            interiorRingsXZ: [
              [
                [-1.25, -0.25],
                [-1.25, 0.25],
                [-0.75, 0.25],
                [-0.75, -0.25],
                [-1.25, -0.25],
              ],
            ],
          },
          {
            exteriorXZ: [
              [0.75, 0.75],
              [1.5, 0.75],
              [1.5, 1.5],
              [0.75, 1.5],
              [0.75, 0.75],
            ],
            interiorRingsXZ: [],
          },
        ],
      },
    });
    const group = createBuildings(packageFor([feature]), grid);
    const roof = findMesh(group, 'flat roofs');
    expect(roofArea(roof)).toBeCloseTo(4.3125, 5);
    const positions = roof.geometry.getAttribute('position');
    const normals = roof.geometry.getAttribute('normal');
    for (let index = 0; index < positions.count; index += 1) {
      expect(normals.getY(index)).toBeGreaterThan(0.999);
    }
    expect(group.userData.componentCount).toBe(2);
    expect(group.userData.holeCount).toBe(1);
  });

  it('faces courtyard wall normals into holes and shares one flat roof per feature', () => {
    const grid = createGrid(
      Float32Array.from([
        0, 1, 0, 0, 0, 1, 2, 1, 0, 0, 0, 1, 7, 1, 0, 0, 0, 1, 2, 0, 0, 0, 0, 0,
        0,
      ]),
    );
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
    const group = createBuildings(packageFor([feature]), grid);
    const roof = findMesh(group, 'flat roofs');
    const positions = roof.geometry.getAttribute('position');
    // The highest sample (7 m) is inside the courtyard hole and must not
    // raise the roof. The highest terrain under the remaining footprint is 4 m.
    expect([
      ...new Set(
        Array.from({ length: positions.count }, (_, i) => positions.getY(i)),
      ),
    ]).toEqual([12]);

    const walls = findMesh(group, 'terrain-following walls');
    const wallPositions = walls.geometry.getAttribute('position');
    const wallNormals = walls.geometry.getAttribute('normal');
    let courtyardFaces = 0;
    for (let index = 0; index < wallPositions.count; index += 3) {
      const x =
        (wallPositions.getX(index) +
          wallPositions.getX(index + 1) +
          wallPositions.getX(index + 2)) /
        3;
      const z =
        (wallPositions.getZ(index) +
          wallPositions.getZ(index + 1) +
          wallPositions.getZ(index + 2)) /
        3;
      if (Math.abs(x) <= 0.50001 && Math.abs(z) <= 0.50001) {
        const nx = wallNormals.getX(index);
        const nz = wallNormals.getZ(index);
        expect(nx * -x + nz * -z).toBeGreaterThan(0);
        courtyardFaces += 1;
      }
    }
    expect(courtyardFaces).toBeGreaterThan(0);
  });

  it('rejects an unavailable terrain boundary with feature context', () => {
    const grid = createGrid();
    const feature = createFeature({
      geometry: {
        type: 'MultiPolygon',
        polygons: [
          {
            exteriorXZ: [
              [-3, -1],
              [-2, -1],
              [-2, 1],
              [-3, 1],
              [-3, -1],
            ],
            interiorRingsXZ: [],
          },
        ],
      },
    });
    expect(() => createBuildings(packageFor([feature]), grid)).toThrow(
      'osm:way:1',
    );
  });
});
