import type { LoadedBuildingPackage } from './buildingSchema';
import type {
  OverviewFeatureCollection,
  OverviewManifest,
} from './overviewSchema';
import type { LoadedRoadPackage } from './roadSchema';

export interface OverviewLayerInputs {
  roads?: LoadedRoadPackage;
  roadsVisible: boolean;
  buildings?: LoadedBuildingPackage;
  buildingsVisible: boolean;
}

export interface OverviewLayerState {
  roads:
    'not-included' | 'not-loaded' | 'hidden' | 'visible' | 'identity-mismatch';
  buildings:
    'not-included' | 'not-loaded' | 'hidden' | 'visible' | 'identity-mismatch';
  visibleCollection: OverviewFeatureCollection;
  identityMismatches: Array<'roads' | 'buildings'>;
}

function sameDescriptor(
  declared: { path: string; byteLength: number; sha256: string },
  actual: { path: string; byteLength: number; sha256: string },
): boolean {
  return (
    declared.path === actual.path &&
    declared.byteLength === actual.byteLength &&
    declared.sha256 === actual.sha256
  );
}

function roadsMatch(
  manifest: OverviewManifest,
  roadPackage: LoadedRoadPackage,
): boolean {
  const expected = manifest.optionalLayerIdentities.roads;
  const actual = roadPackage.manifest;
  const source = expected?.source;
  return Boolean(
    expected &&
    roadPackage.manifestSha256 &&
    expected.manifestSha256 === roadPackage.manifestSha256 &&
    sameDescriptor(expected.payload, {
      path: actual.assets.roads.path,
      byteLength: actual.assets.roads.byteLength,
      sha256: actual.assets.roads.sha256,
    }) &&
    sameDescriptor(expected.qa, {
      path: actual.assets.qa.path,
      byteLength: actual.assets.qa.byteLength,
      sha256: actual.assets.qa.sha256,
    }) &&
    source?.sha256 === actual.source.sha256 &&
    expected.terrainManifestSha256 === manifest.terrainIdentity.manifestSha256,
  );
}

function buildingsMatch(
  manifest: OverviewManifest,
  buildingPackage: LoadedBuildingPackage,
): boolean {
  const expected = manifest.optionalLayerIdentities.buildings;
  const actual = buildingPackage.manifest;
  const source = expected?.source;
  return Boolean(
    expected &&
    buildingPackage.manifestSha256 &&
    expected.manifestSha256 === buildingPackage.manifestSha256 &&
    sameDescriptor(expected.payload, {
      path: actual.buildings.path,
      byteLength: actual.buildings.byteLength,
      sha256: actual.buildings.sha256,
    }) &&
    sameDescriptor(expected.qa, {
      path: actual.qaReport.path,
      byteLength: actual.qaReport.byteLength,
      sha256: actual.qaReport.sha256,
    }) &&
    source?.sha256 === actual.provenance.sha256 &&
    expected.terrainManifestSha256 === manifest.terrainIdentity.manifestSha256,
  );
}

/** Display optional overview geometry only when its main-viewer source is visible and identical. */
export function selectOverviewLayers(
  overview: OverviewManifest,
  features: OverviewFeatureCollection,
  inputs: OverviewLayerInputs,
): OverviewLayerState {
  let roads: OverviewLayerState['roads'] = 'not-included';
  if (overview.includedLayers.includes('roads')) {
    roads = !inputs.roads
      ? 'not-loaded'
      : !inputs.roadsVisible
        ? 'hidden'
        : roadsMatch(overview, inputs.roads)
          ? 'visible'
          : 'identity-mismatch';
  }
  let buildings: OverviewLayerState['buildings'] = 'not-included';
  if (overview.includedLayers.includes('buildings')) {
    buildings = !inputs.buildings
      ? 'not-loaded'
      : !inputs.buildingsVisible
        ? 'hidden'
        : buildingsMatch(overview, inputs.buildings)
          ? 'visible'
          : 'identity-mismatch';
  }
  const visibleRoles = new Set(['aoi']);
  if (roads === 'visible') visibleRoles.add('road');
  if (buildings === 'visible') visibleRoles.add('building');
  return {
    roads,
    buildings,
    visibleCollection: {
      type: 'FeatureCollection',
      features: features.features.filter((feature) =>
        visibleRoles.has(feature.properties.role),
      ),
    },
    identityMismatches: [
      ...(roads === 'identity-mismatch' ? (['roads'] as const) : []),
      ...(buildings === 'identity-mismatch' ? (['buildings'] as const) : []),
    ],
  };
}
