import {
  BufferAttribute,
  BufferGeometry,
  DoubleSide,
  Group,
  Mesh,
  MeshStandardMaterial,
  ShapeUtils,
  Vector2,
} from 'three';
import {
  maximumTerrainHeightUnderFeature,
  subdivideTerrainBoundary,
} from '../geo/buildingGeometry';
import type {
  BuildingFeature,
  BuildingHeightConfidence,
  BuildingPolygon,
  LoadedBuildingPackage,
  XzPosition,
} from '../geo/buildingSchema';
import { WALL_BASE_BURIAL_M } from '../geo/buildingSchema';
import type { TerrainGrid } from '../geo/terrainGrid';
import { disposeSceneResources } from './disposeSceneResources';

type MaterialKey = BuildingHeightConfidence;

interface GeometryBuffers {
  roofPositions: number[];
  roofIndices: number[];
  wallPositions: number[];
  buildingCount: number;
}

const MATERIALS: Record<MaterialKey, { color: string; roughness: number }> = {
  tagged_but_unverified: { color: '#89b8c7', roughness: 0.82 },
  estimated_from_tagged_levels: { color: '#d5b06c', roughness: 0.86 },
  visual_default_estimate: { color: '#bd8570', roughness: 0.9 },
};

function openRing(ring: XzPosition[]): XzPosition[] {
  return ring.slice(0, -1);
}

function signedArea(ring: XzPosition[]): number {
  let twiceArea = 0;
  for (let index = 0; index < ring.length; index += 1) {
    const point = ring[index]!;
    const next = ring[(index + 1) % ring.length]!;
    twiceArea += point[0] * next[1] - next[0] * point[1];
  }
  return twiceArea / 2;
}

function componentArea(polygon: BuildingPolygon): number {
  return (
    Math.abs(signedArea(openRing(polygon.exteriorXZ))) -
    polygon.interiorRingsXZ.reduce(
      (sum, ring) => sum + Math.abs(signedArea(openRing(ring))),
      0,
    )
  );
}

function addRoof(
  feature: BuildingFeature,
  polygon: BuildingPolygon,
  roofY: number,
  buffers: GeometryBuffers,
): void {
  const contour = openRing(polygon.exteriorXZ);
  const holes = polygon.interiorRingsXZ.map(openRing);
  const contours2d = contour.map(([x, z]) => new Vector2(x, z));
  const holes2d = holes.map((ring) => ring.map(([x, z]) => new Vector2(x, z)));
  let triangles: number[][];
  try {
    triangles = ShapeUtils.triangulateShape(contours2d, holes2d);
  } catch (error) {
    throw new Error(
      `${feature.id}: roof triangulation failed: ${error instanceof Error ? error.message : String(error)}`,
      { cause: error },
    );
  }
  const flattened = [...contour, ...holes.flat()];
  const expectedArea = componentArea(polygon);
  if (
    !Number.isFinite(expectedArea) ||
    expectedArea <= 0 ||
    triangles.length === 0
  ) {
    throw new Error(
      `${feature.id}: roof triangulation produced no positive-area triangles`,
    );
  }
  let triangleArea = 0;
  const positionBase = buffers.roofPositions.length / 3;
  for (const [x, z] of flattened) {
    buffers.roofPositions.push(x, roofY, z);
  }
  for (let index = 0; index < triangles.length; index += 1) {
    const triangle = triangles[index]!;
    if (
      triangle.length !== 3 ||
      triangle.some(
        (vertex) =>
          !Number.isSafeInteger(vertex) ||
          vertex < 0 ||
          vertex >= flattened.length,
      )
    ) {
      throw new Error(
        `${feature.id}: triangulator returned an invalid roof index`,
      );
    }
    const first = triangle[0]!;
    let second = triangle[1]!;
    let third = triangle[2]!;
    const a = flattened[first]!;
    const b = flattened[second]!;
    const c = flattened[third]!;
    const twiceArea =
      (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
    const area = Math.abs(twiceArea) / 2;
    if (!Number.isFinite(area) || area <= 1e-10) {
      throw new Error(
        `${feature.id}: roof triangulation contains a degenerate triangle`,
      );
    }
    triangleArea += area;
    // In XZ coordinates positive signed area maps to a downward Three.js normal.
    if (twiceArea > 0) [second, third] = [third, second];
    buffers.roofIndices.push(
      positionBase + first,
      positionBase + second,
      positionBase + third,
    );
  }
  if (
    Math.abs(triangleArea - expectedArea) > Math.max(0.01, expectedArea * 1e-6)
  ) {
    throw new Error(
      `${feature.id}: roof triangulation area ${triangleArea} does not match footprint area ${expectedArea}`,
    );
  }
}

function faceNormal(
  a: readonly [number, number, number],
  b: readonly [number, number, number],
  c: readonly [number, number, number],
): readonly [number, number, number] {
  const abx = b[0] - a[0];
  const aby = b[1] - a[1];
  const abz = b[2] - a[2];
  const acx = c[0] - a[0];
  const acy = c[1] - a[1];
  const acz = c[2] - a[2];
  return [aby * acz - abz * acy, abz * acx - abx * acz, abx * acy - aby * acx];
}

function pushOrientedTriangle(
  positions: number[],
  a: readonly [number, number, number],
  b: readonly [number, number, number],
  c: readonly [number, number, number],
  outward: readonly [number, number, number],
  featureId: string,
): void {
  let second = b;
  let third = c;
  const normal = faceNormal(a, second, third);
  const dot =
    normal[0] * outward[0] + normal[1] * outward[1] + normal[2] * outward[2];
  if (!Number.isFinite(dot) || Math.abs(dot) <= 1e-12) {
    throw new Error(`${featureId}: wall contains a degenerate face`);
  }
  if (dot < 0) [second, third] = [third, second];
  positions.push(...a, ...second, ...third);
}

function addRingWalls(
  feature: BuildingFeature,
  ring: XzPosition[],
  roofY: number,
  buffers: GeometryBuffers,
  grid: TerrainGrid,
): void {
  const points = subdivideTerrainBoundary(
    ring,
    grid,
    `${feature.id} wall boundary`,
  );
  for (let index = 0; index < points.length - 1; index += 1) {
    const a = points[index]!;
    const b = points[index + 1]!;
    const dx = b.x - a.x;
    const dz = b.z - a.z;
    const outward: readonly [number, number, number] = [dz, 0, -dx];
    const bottomA: readonly [number, number, number] = [
      a.x,
      a.groundY - WALL_BASE_BURIAL_M,
      a.z,
    ];
    const bottomB: readonly [number, number, number] = [
      b.x,
      b.groundY - WALL_BASE_BURIAL_M,
      b.z,
    ];
    const topA: readonly [number, number, number] = [a.x, roofY, a.z];
    const topB: readonly [number, number, number] = [b.x, roofY, b.z];
    if (roofY <= Math.max(bottomA[1], bottomB[1])) {
      throw new Error(
        `${feature.id}: roof is not above its sampled terrain wall bases`,
      );
    }
    pushOrientedTriangle(
      buffers.wallPositions,
      bottomA,
      topB,
      bottomB,
      outward,
      feature.id,
    );
    pushOrientedTriangle(
      buffers.wallPositions,
      bottomA,
      topA,
      topB,
      outward,
      feature.id,
    );
  }
}

function assertFiniteUnitNormals(
  geometry: BufferGeometry,
  label: string,
  requireUp = false,
): void {
  const positions = geometry.getAttribute('position');
  const normals = geometry.getAttribute('normal');
  if (!positions || !normals || positions.count !== normals.count) {
    throw new Error(
      `${label}: generated mesh is missing matched positions/normals`,
    );
  }
  for (let vertex = 0; vertex < positions.count; vertex += 1) {
    const x = positions.getX(vertex);
    const y = positions.getY(vertex);
    const z = positions.getZ(vertex);
    const nx = normals.getX(vertex);
    const ny = normals.getY(vertex);
    const nz = normals.getZ(vertex);
    if (![x, y, z, nx, ny, nz].every(Number.isFinite)) {
      throw new Error(
        `${label}: generated mesh contains non-finite attributes`,
      );
    }
    const length = Math.hypot(nx, ny, nz);
    if (Math.abs(length - 1) > 1e-4 || (requireUp && ny < 0.999)) {
      throw new Error(
        `${label}: generated face normal is not finite, unit, and correctly oriented`,
      );
    }
  }
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  if (!geometry.boundingBox || !geometry.boundingSphere) {
    throw new Error(`${label}: generated mesh bounds are unavailable`);
  }
}

function makeGeometry(
  buffers: GeometryBuffers,
  label: string,
  indexed: boolean,
): BufferGeometry {
  const geometry = new BufferGeometry();
  try {
    geometry.setAttribute(
      'position',
      new BufferAttribute(
        new Float32Array(
          indexed ? buffers.roofPositions : buffers.wallPositions,
        ),
        3,
      ),
    );
    if (indexed)
      geometry.setIndex(
        new BufferAttribute(new Uint32Array(buffers.roofIndices), 1),
      );
    geometry.computeVertexNormals();
    assertFiniteUnitNormals(geometry, label, indexed);
    return geometry;
  } catch (error) {
    geometry.dispose();
    throw error;
  }
}

function createBufferSet(): GeometryBuffers {
  return {
    roofPositions: [],
    roofIndices: [],
    wallPositions: [],
    buildingCount: 0,
  };
}

function validateFloat32VertexCount(count: number, label: string): void {
  if (!Number.isSafeInteger(count) || count <= 0 || count > 20_000_000) {
    throw new Error(
      `${label}: vertex count exceeds the safe mesh allocation limit`,
    );
  }
}

/** Create shared-confidence roof and terrain-following wall meshes. */
export function createBuildings(
  packageData: LoadedBuildingPackage,
  grid: TerrainGrid,
): Group {
  const group = new Group();
  group.name = 'Local OSM building footprints on EA terrain';
  const buffers: Record<MaterialKey, GeometryBuffers> = {
    tagged_but_unverified: createBufferSet(),
    estimated_from_tagged_levels: createBufferSet(),
    visual_default_estimate: createBufferSet(),
  };
  const materials = new Map<MaterialKey, MeshStandardMaterial>();
  const ownedGeometries: BufferGeometry[] = [];
  for (const [confidence, material] of Object.entries(MATERIALS) as [
    MaterialKey,
    (typeof MATERIALS)[MaterialKey],
  ][]) {
    materials.set(
      confidence,
      new MeshStandardMaterial({
        color: material.color,
        roughness: material.roughness,
        metalness: 0,
        side: DoubleSide,
      }),
    );
  }

  try {
    for (const feature of packageData.features) {
      const featureBuffers = buffers[feature.heightConfidence];
      const maximumTerrain = maximumTerrainHeightUnderFeature(feature, grid);
      const roofY = maximumTerrain + feature.heightM;
      if (!Number.isFinite(roofY) || !Number.isFinite(Math.fround(roofY))) {
        throw new Error(
          `${feature.id}: roof height is not representable by the renderer`,
        );
      }
      for (const polygon of feature.geometry.polygons) {
        addRoof(feature, polygon, roofY, featureBuffers);
        addRingWalls(feature, polygon.exteriorXZ, roofY, featureBuffers, grid);
        for (const hole of polygon.interiorRingsXZ) {
          addRingWalls(feature, hole, roofY, featureBuffers, grid);
        }
      }
      featureBuffers.buildingCount += 1;
    }

    for (const [confidence, featureBuffers] of Object.entries(buffers) as [
      MaterialKey,
      GeometryBuffers,
    ][]) {
      if (featureBuffers.buildingCount === 0) continue;
      validateFloat32VertexCount(
        featureBuffers.roofPositions.length / 3,
        `${confidence} roofs`,
      );
      validateFloat32VertexCount(
        featureBuffers.wallPositions.length / 3,
        `${confidence} walls`,
      );
      const roofGeometry = makeGeometry(
        featureBuffers,
        `${confidence} roofs`,
        true,
      );
      ownedGeometries.push(roofGeometry);
      const roofMesh = new Mesh(roofGeometry, materials.get(confidence)!);
      roofMesh.name = `${confidence} flat roofs`;
      roofMesh.userData.buildingCount = featureBuffers.buildingCount;
      group.add(roofMesh);

      const wallGeometry = new BufferGeometry();
      try {
        wallGeometry.setAttribute(
          'position',
          new BufferAttribute(
            new Float32Array(featureBuffers.wallPositions),
            3,
          ),
        );
        wallGeometry.computeVertexNormals();
        assertFiniteUnitNormals(wallGeometry, `${confidence} walls`);
      } catch (error) {
        wallGeometry.dispose();
        throw error;
      }
      ownedGeometries.push(wallGeometry);
      const wallMesh = new Mesh(wallGeometry, materials.get(confidence)!);
      wallMesh.name = `${confidence} terrain-following walls`;
      wallMesh.userData.buildingCount = featureBuffers.buildingCount;
      group.add(wallMesh);
    }
    group.userData.featureCount = packageData.features.length;
    group.userData.componentCount = packageData.componentCount;
    group.userData.holeCount = packageData.holeCount;
    group.userData.heightMethodCounts = packageData.heightMethodCounts;
    group.userData.roofReferencePolicy =
      'Per feature: maximum sampled terrain height under all components, excluding hole interiors, plus validated heightM; visual placement convention only.';
    group.userData.wallBaseBurialM = WALL_BASE_BURIAL_M;
    return group;
  } catch (error) {
    disposeSceneResources(group);
    for (const geometry of ownedGeometries) {
      if (
        !group.children.some((child) => (child as Mesh).geometry === geometry)
      )
        geometry.dispose();
    }
    for (const material of materials.values()) material.dispose();
    throw error;
  }
}
