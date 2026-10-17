import {
  BufferAttribute,
  BufferGeometry,
  Color,
  FrontSide,
  InterleavedBufferAttribute,
  Mesh,
  MeshStandardMaterial,
} from 'three';
import { createTerrainIndices, type TerrainGrid } from '../geo/terrainGrid';

function assertFiniteArray(
  attribute: BufferAttribute | InterleavedBufferAttribute,
  label: string,
): void {
  const values = attribute.array;
  for (let index = 0; index < values.length; index += 1) {
    if (!Number.isFinite(values[index])) {
      throw new Error(`terrain ${label} attribute contains a non-finite value`);
    }
  }
}

function assertPositiveGridSeparation(
  positions: Float32Array,
  columns: number,
  rows: number,
): void {
  for (let row = 0; row < rows; row += 1) {
    for (let column = 1; column < columns; column += 1) {
      const previous = positions[(row * columns + column - 1) * 3]!;
      const current = positions[(row * columns + column) * 3]!;
      if (!(current > previous)) {
        throw new Error(
          `terrain Float32 positions collapse adjacent columns at row ${row}`,
        );
      }
    }
  }

  for (let row = 1; row < rows; row += 1) {
    for (let column = 0; column < columns; column += 1) {
      const previous = positions[((row - 1) * columns + column) * 3 + 2]!;
      const current = positions[(row * columns + column) * 3 + 2]!;
      if (!(current > previous)) {
        throw new Error(
          `terrain Float32 positions collapse adjacent rows at column ${column}`,
        );
      }
    }
  }
}

function assertUnitNormals(
  attribute: BufferAttribute | InterleavedBufferAttribute,
): void {
  for (let vertex = 0; vertex < attribute.count; vertex += 1) {
    const length = Math.hypot(
      attribute.getX(vertex),
      attribute.getY(vertex),
      attribute.getZ(vertex),
    );
    if (!Number.isFinite(length) || Math.abs(length - 1) > 1e-4) {
      throw new Error(
        `terrain normal at vertex ${vertex} must be nonzero and unit length`,
      );
    }
  }
}

/** Build one indexed vertex per height sample with upward-wound grid triangles. */
export function createTerrain(
  grid: TerrainGrid,
  appearance: 'synthetic' | 'real' = 'synthetic',
): Mesh<BufferGeometry, MeshStandardMaterial> {
  const vertexCount = grid.columns * grid.rows;
  const coordinateCount = vertexCount * 3;
  if (!Number.isSafeInteger(coordinateCount)) {
    throw new Error(
      'terrain position attribute length exceeds safe arithmetic',
    );
  }

  const positions = new Float32Array(coordinateCount);
  const colors =
    appearance === 'real' ? new Float32Array(coordinateCount) : undefined;
  let minimumHeight = Number.POSITIVE_INFINITY;
  let maximumHeight = Number.NEGATIVE_INFINITY;
  if (colors) {
    for (const height of grid.heights) {
      minimumHeight = Math.min(minimumHeight, height);
      maximumHeight = Math.max(maximumHeight, height);
    }
  }
  const lowColor = new Color('#254b4d');
  const middleColor = new Color('#6c9875');
  const highColor = new Color('#ded0a0');
  let offset = 0;
  const halfWidth = grid.widthM / 2;
  const halfDepth = grid.depthM / 2;
  for (let row = 0; row < grid.rows; row += 1) {
    for (let column = 0; column < grid.columns; column += 1) {
      const sampleIndex = row * grid.columns + column;
      positions[offset++] = column * grid.spacingM - halfWidth;
      positions[offset++] = grid.heights[sampleIndex]!;
      positions[offset++] = row * grid.spacingM - halfDepth;
      if (colors) {
        const span = maximumHeight - minimumHeight || 1;
        const amount = Math.max(
          0,
          Math.min(1, (grid.heights[sampleIndex]! - minimumHeight) / span),
        );
        const color =
          amount < 0.55
            ? lowColor.clone().lerp(middleColor, amount / 0.55)
            : middleColor.clone().lerp(highColor, (amount - 0.55) / 0.45);
        colors[sampleIndex * 3] = color.r;
        colors[sampleIndex * 3 + 1] = color.g;
        colors[sampleIndex * 3 + 2] = color.b;
      }
    }
  }

  const geometry = new BufferGeometry();
  const material = new MeshStandardMaterial(
    appearance === 'real'
      ? {
          color: '#ffffff',
          vertexColors: true,
          roughness: 0.96,
          metalness: 0,
          side: FrontSide,
        }
      : {
          color: '#708d7a',
          roughness: 0.94,
          metalness: 0,
          side: FrontSide,
        },
  );

  try {
    assertPositiveGridSeparation(positions, grid.columns, grid.rows);
    geometry.setAttribute('position', new BufferAttribute(positions, 3));
    if (colors) geometry.setAttribute('color', new BufferAttribute(colors, 3));
    geometry.setIndex(
      new BufferAttribute(createTerrainIndices(grid.columns, grid.rows), 1),
    );
    geometry.computeVertexNormals();
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();

    const position = geometry.getAttribute('position');
    const normal = geometry.getAttribute('normal');
    if (!position || !normal || geometry.index === null) {
      throw new Error(
        'terrain geometry is missing positions, normals, or indices',
      );
    }
    assertFiniteArray(position, 'position');
    assertFiniteArray(normal, 'normal');
    if (colors) assertFiniteArray(geometry.getAttribute('color'), 'color');
    assertUnitNormals(normal);
    if (!geometry.boundingBox || !geometry.boundingSphere) {
      throw new Error('terrain geometry bounds could not be computed');
    }
    for (const value of [
      geometry.boundingBox.min.x,
      geometry.boundingBox.min.y,
      geometry.boundingBox.min.z,
      geometry.boundingBox.max.x,
      geometry.boundingBox.max.y,
      geometry.boundingBox.max.z,
      geometry.boundingSphere.center.x,
      geometry.boundingSphere.center.y,
      geometry.boundingSphere.center.z,
      geometry.boundingSphere.radius,
    ]) {
      if (!Number.isFinite(value)) {
        throw new Error('terrain geometry bounds contain a non-finite value');
      }
    }
  } catch (error) {
    geometry.dispose();
    material.dispose();
    throw error;
  }

  const terrain = new Mesh(geometry, material);
  terrain.name = 'Synthetic heightfield terrain';
  terrain.receiveShadow = true;
  return terrain;
}
