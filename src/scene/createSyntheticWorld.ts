import {
  BoxGeometry,
  EdgesGeometry,
  Group,
  LineBasicMaterial,
  LineSegments,
  Mesh,
  MeshStandardMaterial,
  PlaneGeometry,
  Vector3,
} from 'three';
import type { FlightBounds, Vec3Like } from '../camera/movement';
import {
  createDrapedGrid,
  createNorthArrow,
  createWorldAxes,
} from './debugHelpers';

const TERRAIN_WIDTH = 48;
const TERRAIN_DEPTH = 36;
const TERRAIN_SEGMENTS_X = 72;
const TERRAIN_SEGMENTS_Z = 54;

interface SyntheticBlock {
  x: number;
  z: number;
  width: number;
  depth: number;
  height: number;
  color: string;
}

export interface SyntheticWorld {
  group: Group;
  bounds: FlightBounds;
  spawnPosition: Vec3Like;
  spawnLookAt: Vec3Like;
}

export function terrainHeightAt(x: number, z: number): number {
  return 0.045 * x + 0.026 * z + 0.13 * Math.sin(x * 0.18) * Math.cos(z * 0.22);
}

function createTerrain(): Mesh {
  const terrainGeometry = new PlaneGeometry(
    TERRAIN_WIDTH,
    TERRAIN_DEPTH,
    TERRAIN_SEGMENTS_X,
    TERRAIN_SEGMENTS_Z,
  );
  terrainGeometry.rotateX(-Math.PI / 2);

  const positions = terrainGeometry.getAttribute('position');

  for (let index = 0; index < positions.count; index += 1) {
    const x = positions.getX(index);
    const z = positions.getZ(index);
    positions.setY(index, terrainHeightAt(x, z));
  }

  positions.needsUpdate = true;
  terrainGeometry.computeVertexNormals();

  const material = new MeshStandardMaterial({
    color: '#607a70',
    roughness: 0.96,
    metalness: 0,
    flatShading: false,
  });
  const terrain = new Mesh(terrainGeometry, material);
  terrain.receiveShadow = false;
  terrain.name = 'Synthetic sloped ground';
  return terrain;
}

function surfaceNormalAt(x: number, z: number): Vector3 {
  const sampleOffset = 0.05;
  const slopeX =
    (terrainHeightAt(x + sampleOffset, z) -
      terrainHeightAt(x - sampleOffset, z)) /
    (2 * sampleOffset);
  const slopeZ =
    (terrainHeightAt(x, z + sampleOffset) -
      terrainHeightAt(x, z - sampleOffset)) /
    (2 * sampleOffset);

  return new Vector3(-slopeX, 1, -slopeZ).normalize();
}

function createBlocks(): Group {
  const group = new Group();
  group.name = 'Synthetic block fixtures';
  const blocks: SyntheticBlock[] = [
    { x: -9, z: -6, width: 4.2, depth: 3.6, height: 3.5, color: '#cf9f78' },
    { x: -2.1, z: -8.4, width: 5.2, depth: 4.4, height: 4.8, color: '#91aaa2' },
    { x: 6.6, z: -5.4, width: 3.8, depth: 5.1, height: 5.7, color: '#d18272' },
    { x: -5.2, z: 2.3, width: 4.6, depth: 3.7, height: 4.2, color: '#8ca6bd' },
    { x: 7.2, z: 2.1, width: 5.5, depth: 4.2, height: 3.2, color: '#c8b785' },
  ];

  for (const block of blocks) {
    const normal = surfaceNormalAt(block.x, block.z);
    const mesh = new Mesh(
      new BoxGeometry(block.width, block.height, block.depth),
      new MeshStandardMaterial({
        color: block.color,
        roughness: 0.78,
        metalness: 0.02,
        flatShading: true,
      }),
    );
    mesh.position
      .set(block.x, terrainHeightAt(block.x, block.z), block.z)
      .addScaledVector(normal, block.height / 2);
    mesh.quaternion.setFromUnitVectors(new Vector3(0, 1, 0), normal);
    mesh.castShadow = false;
    mesh.name = 'Synthetic block';

    const outline = new LineSegments(
      new EdgesGeometry(mesh.geometry),
      new LineBasicMaterial({
        color: '#f4eee4',
        transparent: true,
        opacity: 0.38,
      }),
    );
    mesh.add(outline);
    group.add(mesh);
  }

  return group;
}

export function createSyntheticWorld(): SyntheticWorld {
  const group = new Group();
  group.name = 'SYNTHETIC — illustrative geometry, not Torquay data';
  const terrain = createTerrain();
  group.add(terrain);
  group.add(createDrapedGrid(TERRAIN_WIDTH, TERRAIN_DEPTH, 2, terrainHeightAt));
  group.add(...createWorldAxes(terrainHeightAt));
  group.add(createNorthArrow(terrainHeightAt));
  group.add(createBlocks());

  return {
    group,
    bounds: {
      minX: -22,
      maxX: 22,
      minY: 1.9,
      maxY: 22,
      minZ: -16,
      maxZ: 16,
    },
    spawnPosition: { x: 0, y: 8.5, z: 15.2 },
    spawnLookAt: { x: 0, y: 0.2, z: -1.5 },
  };
}
