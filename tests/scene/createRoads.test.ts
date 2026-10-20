import { describe, expect, it } from 'vitest';
import { Mesh } from 'three';
import { createTerrainGrid } from '../../src/geo/terrainGrid';
import type { LoadedRoadPackage } from '../../src/geo/roadSchema';
import { createRoads } from '../../src/scene/createRoads';

function roadFixture() {
  const grid = createTerrainGrid({
    columns: 3,
    rows: 3,
    spacingM: 2,
    widthM: 4,
    depthM: 4,
    heights: [0, 1, 2, 2, 3, 4, 4, 5, 6],
  });
  const roads = {
    manifest: {},
    features: [],
    qa: {},
    partCount: 0,
    countsByGroup: { vehicular: 0, cycleway: 0, path: 0 },
    batches: {
      vehicular: {
        verticesXZ: [
          [-2, -2],
          [-2, 0],
          [0, -2],
        ],
        indices: [[0, 1, 2]],
        terrainTriangles: [[0, 0, 0]],
      },
      cycleway: { verticesXZ: [], indices: [], terrainTriangles: [] },
      path: { verticesXZ: [], indices: [], terrainTriangles: [] },
    },
  } as unknown as LoadedRoadPackage;
  return { grid, roads };
}

describe('createRoads', () => {
  it('drapes every road vertex on the exact sampled terrain triangle', () => {
    const { grid, roads } = roadFixture();
    const group = createRoads(roads, grid);
    const mesh = group.children[0];
    expect(mesh).toBeDefined();
    const geometry = mesh instanceof Mesh ? mesh.geometry : undefined;
    expect(geometry).toBeDefined();
    const positions = geometry!.getAttribute('position');
    for (let index = 0; index < positions.count; index += 1) {
      const x = positions.getX(index);
      const y = positions.getY(index);
      const z = positions.getZ(index);
      expect(y).toBeCloseTo(grid.sampleHeight(x, z)! + 0.05, 5);
    }
    const normals = geometry!.getAttribute('normal');
    for (let index = 0; index < normals.count; index += 1) {
      expect(normals.getY(index)).toBeGreaterThan(0);
    }
  });

  it('rejects a vertex that crosses its claimed TerrainGrid triangle', () => {
    const { grid, roads } = roadFixture();
    roads.batches.vehicular.verticesXZ[2] = [0, 0];
    expect(() => createRoads(roads, grid)).toThrow(
      /crosses its claimed terrain triangle/,
    );
  });

  it('repairs Float32 winding flips and omits a Float32-collapsed sliver', () => {
    const grid = createTerrainGrid({
      columns: 1001,
      rows: 1001,
      spacingM: 2,
      widthM: 2000,
      depthM: 2000,
      heights: new Float32Array(1001 * 1001),
    });
    const roads = {
      manifest: {},
      features: [],
      qa: {},
      partCount: 0,
      countsByGroup: { vehicular: 0, cycleway: 0, path: 0 },
      batches: {
        vehicular: {
          verticesXZ: [
            [528.0857104781996, -294.0],
            [528.037549784934, -294.03754978493396],
            [528.0856213450894, -294.00006048510386],
            [-251.99997548305203, 889.999975483052],
            [-252.0, 890.0],
            [-251.99995252749667, 890.0],
          ],
          indices: [
            [0, 1, 2],
            [3, 4, 5],
          ],
          terrainTriangles: [
            [352, 764, 1],
            [944, 374, 1],
          ],
        },
        cycleway: { verticesXZ: [], indices: [], terrainTriangles: [] },
        path: { verticesXZ: [], indices: [], terrainTriangles: [] },
      },
    } as unknown as LoadedRoadPackage;

    const group = createRoads(roads, grid);
    const mesh = group.children[0];
    expect(mesh).toBeDefined();
    expect(group.userData['float32ReorientedTriangles']).toBe(1);
    expect(group.userData['float32CollapsedTriangles']).toBe(1);
    expect((mesh as Mesh).geometry.getIndex()?.array).toEqual(
      new Uint32Array([0, 2, 1]),
    );
    const normals = (mesh as Mesh).geometry.getAttribute('normal');
    for (const index of [0, 1, 2]) {
      expect(normals.getY(index)).toBeGreaterThan(0);
    }
  });
});
