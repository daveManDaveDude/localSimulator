import { MAX_HEIGHTFIELD_SAMPLES } from './sceneSchema';

const EXTENT_TOLERANCE = 1e-9;

export interface TerrainGridInput {
  columns: number;
  rows: number;
  spacingM: number;
  widthM: number;
  depthM: number;
  heights: ArrayLike<number>;
}

export interface TerrainVertex {
  x: number;
  y: number;
  z: number;
}

export interface TerrainGrid {
  readonly columns: number;
  readonly rows: number;
  readonly spacingM: number;
  readonly widthM: number;
  readonly depthM: number;
  readonly heights: Float32Array;
  vertexAt(row: number, column: number): TerrainVertex;
  sampleHeight(x: number, z: number): number | null;
}

function isFloat32Representable(value: number): boolean {
  return Number.isFinite(value) && Number.isFinite(Math.fround(value));
}

function validateDimensions(columns: number, rows: number): number {
  if (!Number.isSafeInteger(columns) || columns < 2) {
    throw new Error('terrain columns must be a safe integer of at least 2');
  }
  if (!Number.isSafeInteger(rows) || rows < 2) {
    throw new Error('terrain rows must be a safe integer of at least 2');
  }

  const count = columns * rows;
  if (!Number.isSafeInteger(count)) {
    throw new Error('terrain sample count exceeds safe integer arithmetic');
  }
  if (count > MAX_HEIGHTFIELD_SAMPLES) {
    throw new Error(
      `terrain sample count exceeds the ${MAX_HEIGHTFIELD_SAMPLES.toLocaleString('en-US')} sample limit`,
    );
  }
  return count;
}

function assertExtentMatches(
  declared: number,
  computed: number,
  label: string,
): void {
  if (!Number.isFinite(computed)) {
    throw new Error(`computed terrain ${label} must be finite`);
  }
  if (!Number.isFinite(declared) || declared <= 0) {
    throw new Error(`terrain ${label} must be positive and finite`);
  }
  const tolerance =
    EXTENT_TOLERANCE * Math.max(1, Math.abs(declared), Math.abs(computed));
  if (Math.abs(declared - computed) > tolerance) {
    throw new Error(
      `terrain ${label} ${declared} does not match grid extent ${computed}`,
    );
  }
}

/**
 * Create an engine-independent row-major grid. Row zero is north (negative Z),
 * X increases east, and grid values are already world Y in metres.
 */
export function createTerrainGrid(input: TerrainGridInput): TerrainGrid {
  if (typeof input !== 'object' || input === null) {
    throw new Error('terrain grid input must be an object');
  }
  const { columns, rows, spacingM, widthM, depthM, heights } = input;
  const sampleCount = validateDimensions(columns, rows);
  if (!Number.isFinite(spacingM) || spacingM <= 0) {
    throw new Error('terrain spacingM must be positive and finite');
  }

  const computedWidth = (columns - 1) * spacingM;
  const computedDepth = (rows - 1) * spacingM;
  assertExtentMatches(widthM, computedWidth, 'widthM');
  assertExtentMatches(depthM, computedDepth, 'depthM');

  const halfWidth = computedWidth / 2;
  const halfDepth = computedDepth / 2;
  if (
    !isFloat32Representable(halfWidth) ||
    !isFloat32Representable(halfDepth)
  ) {
    throw new Error('terrain half-extents are not representable as float32');
  }

  if (
    heights === null ||
    heights === undefined ||
    !Number.isSafeInteger(heights.length) ||
    heights.length !== sampleCount
  ) {
    throw new Error(
      `terrain heights must contain exactly ${sampleCount} finite samples`,
    );
  }

  const ownedHeights = new Float32Array(sampleCount);
  for (let index = 0; index < sampleCount; index += 1) {
    const value = heights[index];
    if (typeof value !== 'number' || !isFloat32Representable(value)) {
      const row = Math.floor(index / columns);
      const column = index % columns;
      throw new Error(
        `terrain height at row ${row}, column ${column} must be finite and float32-representable`,
      );
    }
    ownedHeights[index] = value;
  }

  const vertexAt = (row: number, column: number): TerrainVertex => {
    if (
      !Number.isSafeInteger(row) ||
      !Number.isSafeInteger(column) ||
      row < 0 ||
      row >= rows ||
      column < 0 ||
      column >= columns
    ) {
      throw new RangeError('terrain vertex row or column is outside the grid');
    }

    return {
      x: column * spacingM - halfWidth,
      y: ownedHeights[row * columns + column]!,
      z: row * spacingM - halfDepth,
    };
  };

  const sampleHeight = (x: number, z: number): number | null => {
    if (
      !Number.isFinite(x) ||
      !Number.isFinite(z) ||
      x < -halfWidth ||
      x > halfWidth ||
      z < -halfDepth ||
      z > halfDepth
    ) {
      return null;
    }

    const gridX = (x + halfWidth) / spacingM;
    const gridZ = (z + halfDepth) / spacingM;
    const column = Math.min(Math.floor(gridX), columns - 2);
    const row = Math.min(Math.floor(gridZ), rows - 2);
    const u = gridX - column;
    const v = gridZ - row;

    const a = ownedHeights[row * columns + column]!;
    const b = ownedHeights[row * columns + column + 1]!;
    const c = ownedHeights[(row + 1) * columns + column]!;
    const d = ownedHeights[(row + 1) * columns + column + 1]!;

    if (u + v <= 1) {
      return a + (b - a) * u + (c - a) * v;
    }
    return d + (c - d) * (1 - u) + (b - d) * (1 - v);
  };

  return {
    columns,
    rows,
    spacingM,
    widthM: computedWidth,
    depthM: computedDepth,
    heights: ownedHeights,
    vertexAt,
    sampleHeight,
  };
}

/** Return the fixed upward-wound `(a,c,b)` and `(b,c,d)` triangles per cell. */
export function createTerrainIndices(
  columns: number,
  rows: number,
): Uint16Array | Uint32Array {
  const vertexCount = validateDimensions(columns, rows);
  const cellCount = (columns - 1) * (rows - 1);
  const indexCount = cellCount * 6;
  if (!Number.isSafeInteger(indexCount)) {
    throw new Error('terrain index count exceeds safe integer arithmetic');
  }

  const indices =
    vertexCount <= 65_536
      ? new Uint16Array(indexCount)
      : new Uint32Array(indexCount);
  let offset = 0;
  for (let row = 0; row < rows - 1; row += 1) {
    for (let column = 0; column < columns - 1; column += 1) {
      const a = row * columns + column;
      const b = a + 1;
      const c = a + columns;
      const d = c + 1;
      indices[offset++] = a;
      indices[offset++] = c;
      indices[offset++] = b;
      indices[offset++] = b;
      indices[offset++] = c;
      indices[offset++] = d;
    }
  }
  return indices;
}
