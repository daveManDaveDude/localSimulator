import {
  BufferGeometry,
  MeshStandardMaterial,
  Raycaster,
  Vector3,
} from 'three';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createTerrainGrid } from '../geo/terrainGrid';
import { createTerrain } from './createTerrain';

function makeGrid(heights: number[]) {
  return createTerrainGrid({
    columns: 2,
    rows: 2,
    spacingM: 2,
    widthM: 2,
    depthM: 2,
    heights,
  });
}

describe('createTerrain', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('builds one vertex per sample and six indices per cell', () => {
    const grid = createTerrainGrid({
      columns: 3,
      rows: 2,
      spacingM: 2,
      widthM: 4,
      depthM: 2,
      heights: [0, 1, 2, 3, 4, 5],
    });
    const mesh = createTerrain(grid);
    const position = mesh.geometry.getAttribute('position');
    const index = mesh.geometry.getIndex();

    expect(position.count).toBe(grid.rows * grid.columns);
    expect(index?.count).toBe((grid.rows - 1) * (grid.columns - 1) * 6);
    for (let row = 0; row < grid.rows; row += 1) {
      for (let column = 0; column < grid.columns; column += 1) {
        const vertex = grid.vertexAt(row, column);
        const vertexIndex = row * grid.columns + column;
        expect(position.getX(vertexIndex)).toBeCloseTo(vertex.x, 4);
        expect(position.getY(vertexIndex)).toBeCloseTo(vertex.y, 4);
        expect(position.getZ(vertexIndex)).toBeCloseTo(vertex.z, 4);
        expect(grid.sampleHeight(vertex.x, vertex.z)).toBeCloseTo(vertex.y, 4);
      }
    }
  });

  it('computes finite unit upward normals and bounds for flat terrain', () => {
    const mesh = createTerrain(makeGrid([0, 0, 0, 0]));
    const normals = mesh.geometry.getAttribute('normal');
    const bounds = mesh.geometry.boundingBox;
    expect(bounds).not.toBeNull();
    expect(mesh.geometry.boundingSphere).not.toBeNull();

    for (let index = 0; index < normals.count; index += 1) {
      const normal = new Vector3(
        normals.getX(index),
        normals.getY(index),
        normals.getZ(index),
      );
      expect(Number.isFinite(normal.x)).toBe(true);
      expect(Number.isFinite(normal.y)).toBe(true);
      expect(Number.isFinite(normal.z)).toBe(true);
      expect(normal.length()).toBeCloseTo(1, 5);
      expect(normal.y).toBeGreaterThan(0.999);
    }
    expect(bounds?.min.toArray()).toEqual([-1, 0, -1]);
    expect(bounds?.max.toArray()).toEqual([1, 0, 1]);
  });

  it('computes the expected shared normal for a planar sloped surface', () => {
    const mesh = createTerrain(makeGrid([0, 2, 4, 6]));
    const normals = mesh.geometry.getAttribute('normal');
    const expected = new Vector3(-1, 1, -2).normalize();
    for (let index = 0; index < normals.count; index += 1) {
      const normal = new Vector3(
        normals.getX(index),
        normals.getY(index),
        normals.getZ(index),
      );
      expect(normal.dot(expected)).toBeGreaterThan(0.99999);
    }
  });

  it('matches sampler values against independent downward ray hits on both triangles', () => {
    const grid = makeGrid([0, 2, 4, 10]);
    const mesh = createTerrain(grid);
    mesh.updateMatrixWorld(true);
    const samplePoints = [
      { x: -0.6, z: -0.4 },
      { x: 0.6, z: 0.4 },
      { x: 0, z: 0 },
      { x: 0.8, z: -0.7 },
    ];

    for (const point of samplePoints) {
      const expected = grid.sampleHeight(point.x, point.z);
      const raycaster = new Raycaster(
        new Vector3(point.x, 100, point.z),
        new Vector3(0, -1, 0),
      );
      const [hit] = raycaster.intersectObject(mesh);
      expect(expected).not.toBeNull();
      expect(hit).toBeDefined();
      expect(Math.abs(hit!.point.y - expected!)).toBeLessThan(1e-4);
    }
  });

  it('produces non-degenerate triangle faces', () => {
    const mesh = createTerrain(makeGrid([0, 1, 2, 3]));
    const positions = mesh.geometry.getAttribute('position');
    const indices = mesh.geometry.getIndex();
    expect(indices).not.toBeNull();

    for (let offset = 0; offset < indices!.count; offset += 3) {
      const first = new Vector3().fromBufferAttribute(
        positions,
        indices!.getX(offset),
      );
      const second = new Vector3().fromBufferAttribute(
        positions,
        indices!.getX(offset + 1),
      );
      const third = new Vector3().fromBufferAttribute(
        positions,
        indices!.getX(offset + 2),
      );
      expect(
        new Vector3()
          .subVectors(second, first)
          .cross(new Vector3().subVectors(third, first))
          .length(),
      ).toBeGreaterThan(0);
    }
  });

  it.each([
    {
      spacingM: 1e-50,
      error: 'collapse adjacent columns',
    },
    {
      spacingM: 1e-30,
      error: 'normal at vertex 0 must be nonzero and unit length',
    },
  ])(
    'rejects unsafe Float32 geometry at spacing $spacingM and disposes resources',
    ({ spacingM, error }) => {
      const grid = createTerrainGrid({
        columns: 2,
        rows: 2,
        spacingM,
        widthM: spacingM,
        depthM: spacingM,
        heights: [0, 0, 0, 0],
      });
      const geometryDispose = vi.spyOn(BufferGeometry.prototype, 'dispose');
      const materialDispose = vi.spyOn(
        MeshStandardMaterial.prototype,
        'dispose',
      );

      expect(() => createTerrain(grid)).toThrow(error);
      expect(geometryDispose).toHaveBeenCalledOnce();
      expect(materialDispose).toHaveBeenCalledOnce();
    },
  );
});
