import { Group } from 'three';
import type { LoadedSyntheticWorld } from '../app/worldLoader';
import type { FlightBounds, Vec3Like } from '../camera/movement';
import { createTerrainGrid } from '../geo/terrainGrid';
import { createTerrain } from './createTerrain';
import { disposeSceneResources } from './disposeSceneResources';
import {
  createDrapedGrid,
  createNorthArrow,
  createWorldAxes,
} from './debugHelpers';

export interface HeightfieldWorld {
  group: Group;
  bounds: FlightBounds;
  spawnPosition: Vec3Like;
  spawnLookAt: Vec3Like;
  terrain: ReturnType<typeof createTerrain>;
  grid: ReturnType<typeof createTerrainGrid>;
  gridAndCompass: Group;
}

/** Assemble a loaded synthetic package into a terrain mesh and terrain-following guides. */
export function createHeightfieldWorld(
  loaded: LoadedSyntheticWorld,
): HeightfieldWorld {
  const { manifest, heights } = loaded;
  const { columns, rows, spacingM } = manifest.heightfield;
  const grid = createTerrainGrid({
    columns,
    rows,
    spacingM,
    widthM: manifest.extentM.width,
    depthM: manifest.extentM.depth,
    heights,
  });
  const group = new Group();
  group.name = `SYNTHETIC — ${manifest.name}`;
  const gridAndCompass = new Group();
  gridAndCompass.name = 'Terrain grid, axes, and north cue';
  try {
    const terrain = createTerrain(grid);
    terrain.name = manifest.name;
    group.add(terrain);

    const heightAt = (x: number, z: number): number =>
      grid.sampleHeight(x, z) ?? 0;
    gridAndCompass.add(
      createDrapedGrid(grid.widthM, grid.depthM, spacingM, heightAt),
      ...createWorldAxes(heightAt),
      createNorthArrow(heightAt, { x: -5, z: 0 }),
    );
    group.add(gridAndCompass);

    return {
      group,
      terrain,
      grid,
      gridAndCompass,
      bounds: {
        minX: -grid.widthM / 2,
        maxX: grid.widthM / 2,
        minY: -5,
        maxY: 24,
        minZ: -grid.depthM / 2,
        maxZ: grid.depthM / 2,
      },
      spawnPosition: { x: 0, y: 9, z: 15 },
      spawnLookAt: { x: 0, y: 1, z: -6 },
    };
  } catch (error) {
    disposeSceneResources(group);
    throw error;
  }
}
