import {
  BufferAttribute,
  BufferGeometry,
  CylinderGeometry,
  DoubleSide,
  Group,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  SphereGeometry,
} from 'three';
import {
  ROAD_GROUPS,
  ROAD_SURFACE_OFFSET_M,
  type LoadedRoadPackage,
  type RoadDisplayGroup,
} from '../geo/roadSchema';
import type { TerrainGrid } from '../geo/terrainGrid';
import { disposeSceneResources } from './disposeSceneResources';

const MATERIALS: Record<
  RoadDisplayGroup,
  { color: string; roughness: number }
> = {
  vehicular: { color: '#b98845', roughness: 0.94 },
  cycleway: { color: '#379f8a', roughness: 0.9 },
  path: { color: '#c0cce0', roughness: 0.95 },
};

function inTerrainTriangle(
  x: number,
  z: number,
  row: number,
  column: number,
  triangle: 0 | 1,
  grid: TerrainGrid,
): boolean {
  const u = (x + grid.widthM / 2) / grid.spacingM - column;
  const v = (z + grid.depthM / 2) / grid.spacingM - row;
  return (
    u >= -1e-6 &&
    u <= 1 + 1e-6 &&
    v >= -1e-6 &&
    v <= 1 + 1e-6 &&
    (triangle === 0 ? u + v <= 1 + 1e-6 : u + v >= 1 - 1e-6)
  );
}

function assertFiniteAttribute(values: Float32Array, feature: string): void {
  for (let index = 0; index < values.length; index += 1) {
    if (!Number.isFinite(values[index])) {
      throw new Error(
        `${feature}: road geometry contains a non-finite Float32 attribute`,
      );
    }
  }
}

/** Build validated road ribbons on the exact same piecewise-linear grid as terrain. */
export function createRoads(
  roads: LoadedRoadPackage,
  grid: TerrainGrid,
): Group {
  const root = new Group();
  root.name = 'OSM road surfaces · estimated visual widths';
  const ownedGeometries: BufferGeometry[] = [];
  const ownedMaterials: MeshStandardMaterial[] = [];

  try {
    for (const groupName of ROAD_GROUPS) {
      const batch = roads.batches[groupName];
      if (batch.indices.length === 0) continue;
      const positions = new Float32Array(batch.verticesXZ.length * 3);
      for (let index = 0; index < batch.verticesXZ.length; index += 1) {
        const [x, z] = batch.verticesXZ[index]!;
        const ground = grid.sampleHeight(x, z);
        if (ground === null) {
          throw new Error(
            `${groupName}: road vertex ${index} lies outside sampled terrain`,
          );
        }
        const y = ground + ROAD_SURFACE_OFFSET_M;
        const fx = Math.fround(x);
        const fy = Math.fround(y);
        const fz = Math.fround(z);
        if (
          !Number.isFinite(fx) ||
          !Number.isFinite(fy) ||
          !Number.isFinite(fz) ||
          Math.abs(fx - x) > 0.001 ||
          Math.abs(fy - y) > 0.001 ||
          Math.abs(fz - z) > 0.001
        ) {
          throw new Error(
            `${groupName}: road vertex ${index} exceeds Float32 terrain drape tolerance`,
          );
        }
        positions[index * 3] = fx;
        positions[index * 3 + 1] = fy;
        positions[index * 3 + 2] = fz;
      }

      const indices = new Uint32Array(batch.indices.length * 3);
      for (
        let faceIndex = 0;
        faceIndex < batch.indices.length;
        faceIndex += 1
      ) {
        const face = batch.indices[faceIndex]!;
        const [row, column, triangle] = batch.terrainTriangles[faceIndex]!;
        if (row >= grid.rows - 1 || column >= grid.columns - 1) {
          throw new Error(
            `${groupName}: face ${faceIndex} terrain cell is outside the loaded grid`,
          );
        }
        const facePositions: Array<[number, number, number]> = [];
        for (let corner = 0; corner < 3; corner += 1) {
          const vertexIndex = face[corner]!;
          if (
            !Number.isSafeInteger(vertexIndex) ||
            vertexIndex < 0 ||
            vertexIndex >= batch.verticesXZ.length
          ) {
            throw new Error(
              `${groupName}: face ${faceIndex} has an out-of-range vertex index`,
            );
          }
          const [x, z] = batch.verticesXZ[vertexIndex]!;
          if (!inTerrainTriangle(x, z, row, column, triangle, grid)) {
            throw new Error(
              `${groupName}: face ${faceIndex} crosses its claimed terrain triangle`,
            );
          }
          facePositions.push([
            positions[vertexIndex * 3]!,
            positions[vertexIndex * 3 + 1]!,
            positions[vertexIndex * 3 + 2]!,
          ]);
          indices[faceIndex * 3 + corner] = vertexIndex;
        }
        const centroidX =
          (facePositions[0]![0] + facePositions[1]![0] + facePositions[2]![0]) /
          3;
        const centroidZ =
          (facePositions[0]![2] + facePositions[1]![2] + facePositions[2]![2]) /
          3;
        const sampled = grid.sampleHeight(centroidX, centroidZ);
        const linearY =
          (facePositions[0]![1] + facePositions[1]![1] + facePositions[2]![1]) /
          3;
        if (
          sampled === null ||
          Math.abs(linearY - (sampled + ROAD_SURFACE_OFFSET_M)) > 0.001
        ) {
          throw new Error(
            `${groupName}: face ${faceIndex} exceeds the 1 mm terrain-triangle drape tolerance`,
          );
        }
      }

      const geometry = new BufferGeometry();
      ownedGeometries.push(geometry);
      geometry.setAttribute('position', new BufferAttribute(positions, 3));
      geometry.setIndex(new BufferAttribute(indices, 1));
      geometry.computeVertexNormals();
      geometry.computeBoundingBox();
      geometry.computeBoundingSphere();
      const normals = geometry.getAttribute('normal').array as Float32Array;
      assertFiniteAttribute(positions, `${groupName} positions`);
      assertFiniteAttribute(normals, `${groupName} normals`);
      for (let index = 0; index < normals.length; index += 3) {
        if (normals[index + 1]! <= 0) {
          throw new Error(
            `${groupName}: road vertex normal ${index / 3} is not upward-facing`,
          );
        }
      }
      if (
        geometry.boundingBox === null ||
        geometry.boundingSphere === null ||
        !Number.isFinite(geometry.boundingSphere.radius) ||
        geometry.boundingSphere.radius <= 0
      ) {
        throw new Error(`${groupName}: road geometry bounds are invalid`);
      }
      const material = new MeshStandardMaterial({
        color: MATERIALS[groupName].color,
        roughness: MATERIALS[groupName].roughness,
        metalness: 0,
        side: DoubleSide,
      });
      ownedMaterials.push(material);
      const mesh = new Mesh(geometry, material);
      mesh.name = `OSM ${groupName} road surfaces`;
      mesh.userData.displayGroup = groupName;
      mesh.userData.estimatedWidth = true;
      root.add(mesh);
    }
    return root;
  } catch (error) {
    disposeSceneResources(root);
    for (const geometry of ownedGeometries) geometry.dispose();
    for (const material of ownedMaterials) material.dispose();
    throw error;
  }
}

/** Add a small local debug marker; its coordinate remains a QA context point. */
export function createRoadLandmarkMarker(
  position: readonly [number, number],
  label: string,
  grid: TerrainGrid,
): Group {
  const [x, z] = position;
  const ground = grid.sampleHeight(x, z);
  if (ground === null) {
    throw new Error(`${label}: debug context point lies outside the terrain`);
  }
  const marker = new Group();
  marker.name = `Road QA context marker · ${label}`;
  marker.userData.qaContextOnly = true;
  marker.userData.label = label;
  const stem = new Mesh(
    new CylinderGeometry(0.12, 0.12, 2.2, 8),
    new MeshBasicMaterial({ color: '#102a43' }),
  );
  stem.position.set(x, ground + 1.1, z);
  marker.add(stem);
  const head = new Mesh(
    new SphereGeometry(1.15, 10, 8),
    new MeshBasicMaterial({ color: '#ff4d6d' }),
  );
  head.position.set(x, ground + 2.8, z);
  marker.add(head);
  return marker;
}
