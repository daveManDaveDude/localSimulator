import type { RealSceneProfile } from '../geo/sceneSchema';
import type { SceneReleaseIntegrity } from './sceneRelease';

export interface RealSceneProfileConfig {
  profile: RealSceneProfile;
  worldQuery: 'torquay-poc-001' | 'torquay-poc-001-2km';
  terrainManifestUrl: string;
  buildingsManifestUrl: string;
  roadsManifestUrl: string;
  route: string;
  label: string;
}

export const HISTORICAL_1KM_SCENE: RealSceneProfileConfig = {
  profile: 'historical_1km',
  worldQuery: 'torquay-poc-001',
  terrainManifestUrl: '/worlds/torquay-poc-001/manifest.json',
  buildingsManifestUrl: '/worlds/torquay-poc-001/buildings/manifest.json',
  roadsManifestUrl: '/worlds/torquay-poc-001/roads/manifest.json',
  route: '?world=torquay-poc-001&buildings=1&roads=1',
  label: 'Historical 1 km package',
};

export const CURRENT_2KM_SCENE: RealSceneProfileConfig = {
  profile: 'current_2km',
  worldQuery: 'torquay-poc-001-2km',
  terrainManifestUrl: '/worlds/torquay-poc-001-2km/manifest.json',
  buildingsManifestUrl: '/worlds/torquay-poc-001-2km/buildings/manifest.json',
  roadsManifestUrl: '/worlds/torquay-poc-001-2km/roads/manifest.json',
  route: '?world=torquay-poc-001-2km&buildings=1&roads=1',
  label: 'Current 2 km candidate package',
};

export function realSceneProfileForRoute(
  worldQuery: string | null,
): RealSceneProfileConfig | undefined {
  if (worldQuery === CURRENT_2KM_SCENE.worldQuery) return CURRENT_2KM_SCENE;
  if (worldQuery === HISTORICAL_1KM_SCENE.worldQuery)
    return HISTORICAL_1KM_SCENE;
  return undefined;
}

export function realSceneProfileForTerrain(
  profile: RealSceneProfile,
): RealSceneProfileConfig {
  return profile === 'current_2km' ? CURRENT_2KM_SCENE : HISTORICAL_1KM_SCENE;
}

/** Return fixed package URLs under one already validated immutable release. */
export function current2kmSceneForRelease(
  release: SceneReleaseIntegrity,
): RealSceneProfileConfig {
  const root = release.releaseRootUrl;
  return {
    ...CURRENT_2KM_SCENE,
    terrainManifestUrl: new URL('manifest.json', root).href,
    buildingsManifestUrl: new URL('buildings/manifest.json', root).href,
    roadsManifestUrl: new URL('roads/manifest.json', root).href,
  };
}
