import { Group } from 'three';
import type { LoadedWorld } from '../app/worldLoader';
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
  isReal: boolean;
  verticalReference: string;
  attribution: string;
  sourceDetailsUrl?: string;
  licenceUrl?: string;
  cameraFar: number;
}

/** Assemble a validated local package into a mesh and terrain-following guides. */
export function createHeightfieldWorld(loaded: LoadedWorld): HeightfieldWorld {
  const { manifest, heights } = loaded;
  const { columns, rows, spacingM } = manifest.heightfield;
  const isReal = manifest.worldType === 'real';
  const grid = createTerrainGrid({
    columns,
    rows,
    spacingM,
    widthM: manifest.extentM.width,
    depthM: manifest.extentM.depth,
    heights,
  });
  const group = new Group();
  group.name = `${isReal ? 'REAL LOCAL EA DTM' : 'SYNTHETIC'} — ${manifest.name}`;
  const gridAndCompass = new Group();
  gridAndCompass.name = 'Terrain grid, axes, and north cue';
  try {
    const terrain = createTerrain(grid, isReal ? 'real' : 'synthetic');
    terrain.name = manifest.name;
    group.add(terrain);

    const heightAt = (x: number, z: number): number =>
      grid.sampleHeight(x, z) ?? 0;
    const guideSpacing = isReal ? 100 : spacingM;
    const guideScale = isReal ? 12 : 1;
    gridAndCompass.add(
      createDrapedGrid(grid.widthM, grid.depthM, guideSpacing, heightAt),
      ...createWorldAxes(heightAt, isReal ? 80 : 14),
      createNorthArrow(
        heightAt,
        isReal ? { x: -430, z: -420 } : { x: -5, z: 0 },
        guideScale,
      ),
    );
    group.add(gridAndCompass);

    let minimumHeight = Number.POSITIVE_INFINITY;
    let maximumHeight = Number.NEGATIVE_INFINITY;
    for (const height of grid.heights) {
      minimumHeight = Math.min(minimumHeight, height);
      maximumHeight = Math.max(maximumHeight, height);
    }
    const realProvenance = isReal ? manifest.provenance : undefined;

    return {
      group,
      terrain,
      grid,
      gridAndCompass,
      bounds: {
        minX: -grid.widthM / 2,
        maxX: grid.widthM / 2,
        minY: isReal ? minimumHeight - 25 : -5,
        maxY: isReal ? maximumHeight + 180 : 24,
        minZ: -grid.depthM / 2,
        maxZ: grid.depthM / 2,
      },
      spawnPosition: isReal
        ? { x: 0, y: maximumHeight + 120, z: 360 }
        : { x: 0, y: 9, z: 15 },
      spawnLookAt: isReal ? { x: 0, y: 0, z: 0 } : { x: 0, y: 1, z: -6 },
      isReal,
      verticalReference: isReal
        ? (realProvenance?.verticalReference ?? 'UNVERIFIED VERTICAL REFERENCE')
        : 'LOCAL FICTIONAL HEIGHTS',
      attribution: isReal
        ? (realProvenance?.attribution ??
          'Environment Agency source attribution unavailable.')
        : 'Fictional local fixture; no geographic data.',
      ...(isReal && realProvenance
        ? {
            sourceDetailsUrl: realProvenance.catalogueUrl,
            licenceUrl: realProvenance.licenceUrl,
          }
        : {}),
      cameraFar: isReal ? 2200 : 180,
    };
  } catch (error) {
    disposeSceneResources(group);
    throw error;
  }
}
