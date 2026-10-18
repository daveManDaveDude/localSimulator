import type {
  BuildingFeature,
  BuildingPolygon,
  XzPosition,
} from './buildingSchema';
import type { TerrainGrid } from './terrainGrid';

export interface TerrainBoundaryPoint {
  x: number;
  z: number;
  groundY: number;
}

const PARAMETER_EPSILON = 1e-10;

function closePoint(a: XzPosition, b: XzPosition, epsilon = 1e-9): boolean {
  return Math.abs(a[0] - b[0]) <= epsilon && Math.abs(a[1] - b[1]) <= epsilon;
}

function pointOnSegment(p: XzPosition, a: XzPosition, b: XzPosition): boolean {
  const cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]);
  return (
    Math.abs(cross) <= 1e-9 &&
    p[0] >= Math.min(a[0], b[0]) - 1e-9 &&
    p[0] <= Math.max(a[0], b[0]) + 1e-9 &&
    p[1] >= Math.min(a[1], b[1]) - 1e-9 &&
    p[1] <= Math.max(a[1], b[1]) + 1e-9
  );
}

function pointInRing(point: XzPosition, ring: XzPosition[]): boolean {
  let inside = false;
  for (
    let index = 0, previous = ring.length - 2;
    index < ring.length - 1;
    previous = index++
  ) {
    const current = ring[index]!;
    const prior = ring[previous]!;
    if (pointOnSegment(point, current, prior)) return true;
    if (
      current[1] > point[1] !== prior[1] > point[1] &&
      point[0] <
        ((prior[0] - current[0]) * (point[1] - current[1])) /
          (prior[1] - current[1]) +
          current[0]
    ) {
      inside = !inside;
    }
  }
  return inside;
}

function pointInPolygon(point: XzPosition, polygon: BuildingPolygon): boolean {
  return (
    pointInRing(point, polygon.exteriorXZ) &&
    !polygon.interiorRingsXZ.some((ring) => pointInRing(point, ring))
  );
}

function uniqueSorted(values: number[]): number[] {
  const sorted = values.sort((a, b) => a - b);
  const unique: number[] = [];
  for (const value of sorted) {
    if (
      unique.length === 0 ||
      Math.abs(value - unique[unique.length - 1]!) > PARAMETER_EPSILON
    ) {
      unique.push(value);
    }
  }
  return unique;
}

function cellIndex(
  value: number,
  halfExtent: number,
  spacing: number,
  count: number,
): number {
  const index = Math.floor((value + halfExtent) / spacing);
  return Math.max(0, Math.min(count - 2, index));
}

function boundaryParameters(
  start: XzPosition,
  end: XzPosition,
  grid: TerrainGrid,
): number[] {
  const dx = end[0] - start[0];
  const dz = end[1] - start[1];
  const values = [0, 1];
  if (Math.abs(dx) > Number.EPSILON) {
    const first = Math.max(
      0,
      Math.ceil((Math.min(start[0], end[0]) + grid.widthM / 2) / grid.spacingM),
    );
    const last = Math.min(
      grid.columns - 1,
      Math.floor(
        (Math.max(start[0], end[0]) + grid.widthM / 2) / grid.spacingM,
      ),
    );
    for (let column = first; column <= last; column += 1) {
      const x = column * grid.spacingM - grid.widthM / 2;
      const t = (x - start[0]) / dx;
      if (t > PARAMETER_EPSILON && t < 1 - PARAMETER_EPSILON) values.push(t);
    }
  }
  if (Math.abs(dz) > Number.EPSILON) {
    const first = Math.max(
      0,
      Math.ceil((Math.min(start[1], end[1]) + grid.depthM / 2) / grid.spacingM),
    );
    const last = Math.min(
      grid.rows - 1,
      Math.floor(
        (Math.max(start[1], end[1]) + grid.depthM / 2) / grid.spacingM,
      ),
    );
    for (let row = first; row <= last; row += 1) {
      const z = row * grid.spacingM - grid.depthM / 2;
      const t = (z - start[1]) / dz;
      if (t > PARAMETER_EPSILON && t < 1 - PARAMETER_EPSILON) values.push(t);
    }
  }

  const gridLineParameters = uniqueSorted(values);
  const diagonals: number[] = [];
  const denominator = dx + dz;
  if (Math.abs(denominator) > Number.EPSILON) {
    for (
      let interval = 0;
      interval < gridLineParameters.length - 1;
      interval += 1
    ) {
      const lower = gridLineParameters[interval]!;
      const upper = gridLineParameters[interval + 1]!;
      const midpoint = (lower + upper) / 2;
      const midX = start[0] + dx * midpoint;
      const midZ = start[1] + dz * midpoint;
      const column = cellIndex(
        midX,
        grid.widthM / 2,
        grid.spacingM,
        grid.columns,
      );
      const row = cellIndex(midZ, grid.depthM / 2, grid.spacingM, grid.rows);
      const northwest = grid.vertexAt(row, column);
      const diagonal = northwest.x + northwest.z + grid.spacingM;
      const t = (diagonal - start[0] - start[1]) / denominator;
      if (t > lower + PARAMETER_EPSILON && t < upper - PARAMETER_EPSILON) {
        diagonals.push(t);
      }
    }
  }
  return uniqueSorted([...gridLineParameters, ...diagonals]);
}

/** Split a closed footprint ring at every terrain grid line and cell diagonal. */
export function subdivideTerrainBoundary(
  ring: XzPosition[],
  grid: TerrainGrid,
  context = 'building boundary',
): TerrainBoundaryPoint[] {
  if (
    !Array.isArray(ring) ||
    ring.length < 4 ||
    !closePoint(ring[0]!, ring.at(-1)!)
  ) {
    throw new Error(`${context}: expected a closed polygon ring`);
  }
  const points: TerrainBoundaryPoint[] = [];
  for (let edge = 0; edge < ring.length - 1; edge += 1) {
    const start = ring[edge]!;
    const end = ring[edge + 1]!;
    if (closePoint(start, end))
      throw new Error(`${context}: edge ${edge} is degenerate`);
    for (const t of boundaryParameters(start, end, grid)) {
      if (t >= 1 - PARAMETER_EPSILON) continue;
      const x = start[0] + (end[0] - start[0]) * t;
      const z = start[1] + (end[1] - start[1]) * t;
      const groundY = grid.sampleHeight(x, z);
      if (groundY === null || !Number.isFinite(groundY)) {
        throw new Error(
          `${context}: terrain is unavailable at boundary edge ${edge} (${x}, ${z})`,
        );
      }
      const previous = points.at(-1);
      if (!previous || !closePoint([previous.x, previous.z], [x, z])) {
        points.push({ x, z, groundY });
      }
    }
  }
  if (points.length < 3)
    throw new Error(
      `${context}: boundary subdivision produced fewer than three points`,
    );
  const first = points[0]!;
  points.push({ ...first });
  return points;
}

function addHeight(
  value: number | null,
  context: string,
  coordinate: XzPosition,
): number {
  if (value === null || !Number.isFinite(value)) {
    throw new Error(
      `${context}: terrain is unavailable at (${coordinate[0]}, ${coordinate[1]})`,
    );
  }
  return value;
}

/**
 * Exact maximum over the piecewise-planar terrain beneath the complete
 * polygon. Boundary/diagonal intersections and interior grid vertices contain
 * every possible terrain maximum; points inside holes are excluded.
 */
export function maximumTerrainHeightUnderFeature(
  feature: BuildingFeature,
  grid: TerrainGrid,
): number {
  let maximum = Number.NEGATIVE_INFINITY;
  const sample = (x: number, z: number, context: string): void => {
    maximum = Math.max(
      maximum,
      addHeight(grid.sampleHeight(x, z), context, [x, z]),
    );
  };

  for (
    let polygonIndex = 0;
    polygonIndex < feature.geometry.polygons.length;
    polygonIndex += 1
  ) {
    const polygon = feature.geometry.polygons[polygonIndex]!;
    const context = `${feature.id} polygon ${polygonIndex}`;
    for (const ring of [polygon.exteriorXZ, ...polygon.interiorRingsXZ]) {
      const boundary = subdivideTerrainBoundary(ring, grid, context);
      for (const point of boundary) sample(point.x, point.z, context);
    }

    const coordinates = polygon.exteriorXZ;
    const minX = Math.min(...coordinates.map(([x]) => x));
    const maxX = Math.max(...coordinates.map(([x]) => x));
    const minZ = Math.min(...coordinates.map(([, z]) => z));
    const maxZ = Math.max(...coordinates.map(([, z]) => z));
    const firstColumn = Math.max(
      0,
      Math.ceil((minX + grid.widthM / 2) / grid.spacingM),
    );
    const lastColumn = Math.min(
      grid.columns - 1,
      Math.floor((maxX + grid.widthM / 2) / grid.spacingM),
    );
    const firstRow = Math.max(
      0,
      Math.ceil((minZ + grid.depthM / 2) / grid.spacingM),
    );
    const lastRow = Math.min(
      grid.rows - 1,
      Math.floor((maxZ + grid.depthM / 2) / grid.spacingM),
    );
    for (let row = firstRow; row <= lastRow; row += 1) {
      for (let column = firstColumn; column <= lastColumn; column += 1) {
        const vertex = grid.vertexAt(row, column);
        if (pointInPolygon([vertex.x, vertex.z], polygon)) {
          sample(vertex.x, vertex.z, context);
        }
      }
    }
  }

  if (!Number.isFinite(maximum))
    throw new Error(
      `${feature.id}: no terrain samples fell under the footprint`,
    );
  return maximum;
}
