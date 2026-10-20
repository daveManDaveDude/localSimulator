import { describe, expect, it } from 'vitest';
import {
  CURRENT_2KM_SCENE,
  HISTORICAL_1KM_SCENE,
  current2kmSceneForRelease,
  realSceneProfileForRoute,
  realSceneProfileForTerrain,
} from '../../src/app/realSceneProfiles';
import { buildingPackageLimits } from '../../src/geo/buildingSchema';
import { roadPackageLimits } from '../../src/geo/roadSchema';
import type { SceneReleaseIntegrity } from '../../src/app/sceneRelease';

describe('fixed real scene profiles', () => {
  it('keeps the existing 1 km route and its package paths explicit', () => {
    expect(realSceneProfileForRoute('torquay-poc-001')).toBe(
      HISTORICAL_1KM_SCENE,
    );
    expect(HISTORICAL_1KM_SCENE.terrainManifestUrl).toBe(
      '/worlds/torquay-poc-001/manifest.json',
    );
    expect(HISTORICAL_1KM_SCENE.buildingsManifestUrl).toBe(
      '/worlds/torquay-poc-001/buildings/manifest.json',
    );
    expect(HISTORICAL_1KM_SCENE.roadsManifestUrl).toBe(
      '/worlds/torquay-poc-001/roads/manifest.json',
    );
  });

  it('selects only the fixed 2 km profile for its explicit route', () => {
    expect(realSceneProfileForRoute('torquay-poc-001-2km')).toBe(
      CURRENT_2KM_SCENE,
    );
    expect(CURRENT_2KM_SCENE.route).toBe(
      '?world=torquay-poc-001-2km&buildings=1&roads=1',
    );
    expect(CURRENT_2KM_SCENE.terrainManifestUrl).toBe(
      '/worlds/torquay-poc-001-2km/manifest.json',
    );
    expect(CURRENT_2KM_SCENE.buildingsManifestUrl).toBe(
      '/worlds/torquay-poc-001-2km/buildings/manifest.json',
    );
    expect(CURRENT_2KM_SCENE.roadsManifestUrl).toBe(
      '/worlds/torquay-poc-001-2km/roads/manifest.json',
    );
  });

  it('derives every current 2 km runtime package URL from one release identity', () => {
    const releaseId = 'a'.repeat(64);
    const release = {
      releaseId,
      releaseRootUrl: new URL(
        `http://localhost/worlds/torquay-poc-001-2km/releases/${releaseId}/`,
      ),
    } as const;
    const profile = current2kmSceneForRelease(
      release as unknown as SceneReleaseIntegrity,
    );
    expect(profile.profile).toBe('current_2km');
    expect(profile.route).toBe(CURRENT_2KM_SCENE.route);
    expect(profile.terrainManifestUrl).toBe(
      `${release.releaseRootUrl.href}manifest.json`,
    );
    expect(profile.buildingsManifestUrl).toBe(
      `${release.releaseRootUrl.href}buildings/manifest.json`,
    );
    expect(profile.roadsManifestUrl).toBe(
      `${release.releaseRootUrl.href}roads/manifest.json`,
    );
  });

  it('does not resolve arbitrary route names or asset URL input', () => {
    expect(realSceneProfileForRoute('other')).toBeUndefined();
    expect(realSceneProfileForRoute(null)).toBeUndefined();
  });

  it('binds layer selection to the terrain profile', () => {
    expect(realSceneProfileForTerrain('current_2km')).toBe(CURRENT_2KM_SCENE);
    expect(realSceneProfileForTerrain('historical_1km')).toBe(
      HISTORICAL_1KM_SCENE,
    );
    expect(buildingPackageLimits('historical_1km').payloadBytes).toBe(
      16 * 1024 * 1024,
    );
    expect(buildingPackageLimits('current_2km').payloadBytes).toBe(
      64 * 1024 * 1024,
    );
    expect(roadPackageLimits('historical_1km').payloadBytes).toBe(
      32 * 1024 * 1024,
    );
    expect(roadPackageLimits('current_2km').payloadBytes).toBe(
      128 * 1024 * 1024,
    );
  });
});
