import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import {
  createTerrainGrid,
  createTerrainIndices,
  type TerrainGridInput,
} from '../../src/geo/terrainGrid';
import { decodeFloat32Heightfield } from '../../src/geo/heightfield';
import { validateSceneManifest } from '../../src/geo/sceneSchema';
import {
  readSyntheticTerrainDemoBytes,
  readSyntheticTerrainDemoManifest,
} from './fixtures';

function gridInput(
  overrides: Partial<TerrainGridInput> = {},
): TerrainGridInput {
  return {
    columns: 2,
    rows: 2,
    spacingM: 2,
    widthM: 2,
    depthM: 2,
    heights: [0, 2, 4, 10],
    ...overrides,
  };
}

describe('createTerrainGrid', () => {
  it('maps rectangular row-major samples north-to-south and spans extent endpoints', () => {
    const grid = createTerrainGrid(
      gridInput({
        columns: 3,
        rows: 2,
        widthM: 4,
        depthM: 2,
        heights: [0, 10, 20, 30, 40, 50],
      }),
    );

    expect(grid.vertexAt(0, 0)).toEqual({ x: -2, y: 0, z: -1 });
    expect(grid.vertexAt(0, 2)).toEqual({ x: 2, y: 20, z: -1 });
    expect(grid.vertexAt(1, 0)).toEqual({ x: -2, y: 30, z: 1 });
    expect(grid.vertexAt(1, 2)).toEqual({ x: 2, y: 50, z: 1 });
  });

  it('uses six upward-wound indices per rectangular cell in the fixed diagonal order', () => {
    const indices = createTerrainIndices(3, 2);
    expect(indices).toEqual(
      new Uint16Array([0, 3, 1, 1, 3, 4, 1, 4, 2, 2, 4, 5]),
    );
    expect(indices).toHaveLength((3 - 1) * (2 - 1) * 6);

    const grid = createTerrainGrid(
      gridInput({
        columns: 3,
        rows: 2,
        widthM: 4,
        depthM: 2,
        heights: [0, 10, 20, 30, 40, 50],
      }),
    );
    for (let offset = 0; offset < indices.length; offset += 3) {
      const a = grid.vertexAt(
        Math.floor(indices[offset]! / grid.columns),
        indices[offset]! % grid.columns,
      );
      const b = grid.vertexAt(
        Math.floor(indices[offset + 1]! / grid.columns),
        indices[offset + 1]! % grid.columns,
      );
      const c = grid.vertexAt(
        Math.floor(indices[offset + 2]! / grid.columns),
        indices[offset + 2]! % grid.columns,
      );
      const ab = { x: b.x - a.x, z: b.z - a.z };
      const ac = { x: c.x - a.x, z: c.z - a.z };
      expect(ab.z * ac.x - ab.x * ac.z).toBeGreaterThan(0);
    }
  });

  it('samples known vertices and points on both cell triangles', () => {
    const grid = createTerrainGrid(gridInput());
    expect(grid.sampleHeight(-1, -1)).toBe(0);
    expect(grid.sampleHeight(1, -1)).toBe(2);
    expect(grid.sampleHeight(-1, 1)).toBe(4);
    expect(grid.sampleHeight(1, 1)).toBe(10);
    expect(grid.sampleHeight(-0.6, -0.4)).toBeCloseTo(1.6, 6);
    expect(grid.sampleHeight(0.6, 0.4)).toBeCloseTo(6.4, 6);
  });

  it('uses the same fixed triangle planes rather than bilinear interpolation', () => {
    const grid = createTerrainGrid(gridInput());
    const triangleHeight = grid.sampleHeight(0.6, 0.4);
    const u = 0.8;
    const v = 0.7;
    const [a, b, c, d] = [0, 2, 4, 10];
    const bilinearHeight =
      a * (1 - u) * (1 - v) + b * u * (1 - v) + c * (1 - u) * v + d * u * v;

    expect(triangleHeight).toBeCloseTo(6.4, 6);
    expect(triangleHeight).not.toBeCloseTo(bilinearHeight, 1);
  });

  it('covers the diagonal, shared cell edges, all outer edges and corners', () => {
    const grid = createTerrainGrid(
      gridInput({
        columns: 3,
        rows: 3,
        widthM: 4,
        depthM: 4,
        heights: [0, 1, 2, 10, 11, 12, 20, 21, 22],
      }),
    );

    expect(grid.sampleHeight(-1, -1)).toBe(5.5);
    expect(grid.sampleHeight(0, 0)).toBe(11);
    expect(grid.sampleHeight(-2, 0)).toBe(10);
    expect(grid.sampleHeight(2, 0)).toBe(12);
    expect(grid.sampleHeight(0, -2)).toBe(1);
    expect(grid.sampleHeight(0, 2)).toBe(21);
    expect(grid.sampleHeight(-2, -2)).toBe(0);
    expect(grid.sampleHeight(2, -2)).toBe(2);
    expect(grid.sampleHeight(-2, 2)).toBe(20);
    expect(grid.sampleHeight(2, 2)).toBe(22);
    expect(grid.sampleHeight(0, -1)).toBeCloseTo(6, 6);
    expect(grid.sampleHeight(-1, 0)).toBeCloseTo(10.5, 6);
  });

  it('returns null outside the finite extent and for non-finite queries', () => {
    const grid = createTerrainGrid(gridInput());
    expect(grid.sampleHeight(-1.001, 0)).toBeNull();
    expect(grid.sampleHeight(0, 1.001)).toBeNull();
    expect(grid.sampleHeight(Number.NaN, 0)).toBeNull();
    expect(grid.sampleHeight(0, Number.POSITIVE_INFINITY)).toBeNull();
  });

  it.each([
    [gridInput({ columns: 1 }), 'columns'],
    [gridInput({ rows: 1 }), 'rows'],
    [gridInput({ spacingM: 0 }), 'spacingM'],
    [gridInput({ heights: [0, 1, 2] }), 'exactly 4'],
    [gridInput({ heights: [0, Number.NaN, 2, 3] }), 'row 0, column 1'],
    [gridInput({ heights: [0, Number.POSITIVE_INFINITY, 2, 3] }), 'finite'],
    [gridInput({ widthM: 3 }), 'does not match grid extent'],
    [
      gridInput({
        columns: 3,
        rows: 2,
        spacingM: 1e308,
        widthM: 1,
        depthM: 1e308,
        heights: new Array(6).fill(0),
      }),
      'computed terrain widthM must be finite',
    ],
    [
      gridInput({
        columns: 3,
        rows: 3,
        spacingM: Number.MAX_VALUE / 2,
        widthM: Number.MAX_VALUE,
        depthM: Number.MAX_VALUE,
        heights: new Array(9).fill(0),
      }),
      'not representable as float32',
    ],
    [
      gridInput({ heights: [0, Number.MAX_VALUE, 2, 3] }),
      'float32-representable',
    ],
  ])('rejects malformed direct input (%s)', (input, message) => {
    expect(() => createTerrainGrid(input)).toThrow(message);
  });

  it('rejects a vertex query outside the integer row/column range', () => {
    const grid = createTerrainGrid(gridInput());
    expect(() => grid.vertexAt(-1, 0)).toThrow('outside the grid');
    expect(() => grid.vertexAt(0, 0.5)).toThrow('outside the grid');
  });

  it('validates and samples the deterministic synthetic hill and ridge fixture', () => {
    const bytes = readSyntheticTerrainDemoBytes();
    const hash = createHash('sha256')
      .update(new Uint8Array(bytes))
      .digest('hex');
    const validation = validateSceneManifest(
      readSyntheticTerrainDemoManifest(),
    );
    expect(validation.ok).toBe(true);
    expect(hash).toBe(
      'cf57dd9d5551eaad413c5e1ea43c8d2f9acb709c410bb016e8fbf7afd95dcd3b',
    );
    if (!validation.ok) return;

    const manifest = validation.manifest;
    expect(manifest.id).toBe('synthetic-terrain-demo');
    expect(manifest.worldType).toBe('synthetic');
    expect(manifest.heightfield.columns).toBe(25);
    expect(manifest.heightfield.rows).toBe(19);
    expect(manifest.extentM).toEqual({ width: 48, depth: 36 });
    expect(manifest.heightfield.sha256).toBe(hash);

    const heights = decodeFloat32Heightfield(bytes, {
      columns: manifest.heightfield.columns,
      rows: manifest.heightfield.rows,
    });
    const grid = createTerrainGrid({
      columns: manifest.heightfield.columns,
      rows: manifest.heightfield.rows,
      spacingM: manifest.heightfield.spacingM,
      widthM: manifest.extentM.width,
      depthM: manifest.extentM.depth,
      heights,
    });

    expect(grid.vertexAt(0, 0).z).toBe(-18);
    expect(grid.vertexAt(0, 0).x).toBe(-24);
    expect(grid.vertexAt(0, 0).y).toBeLessThan(grid.vertexAt(18, 24).y);
    expect(grid.sampleHeight(-8, -2)).toBeGreaterThan(
      grid.sampleHeight(-14, -2)!,
    );
    expect(grid.sampleHeight(10, 0)).toBeGreaterThan(grid.sampleHeight(6, 0)!);
  });
});
