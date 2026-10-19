import { createRealManifest } from './fixtures';
import type {
  OverviewFeatureCollection,
  OverviewManifest,
} from '../../src/geo/overviewSchema';

export const fixtureTerrain = createRealManifest();
export const fixtureTerrainSha256 = 'f'.repeat(64);

export function createOverviewFeatures(): OverviewFeatureCollection {
  const ring = structuredClone(fixtureTerrain.aoi.boundaryWgs84.ring);
  return {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        id: 'aoi:torquay-poc-001',
        properties: {
          role: 'aoi',
          name: 'TQ1 4HN candidate AOI',
          selectionStatus: 'selected_pending_coverage',
          coverageStatus: 'not_checked',
        },
        geometry: { type: 'Polygon', coordinates: [ring] },
      },
    ],
  };
}

function operation() {
  return {
    name: 'EPSG:1314 + EPSG:19916',
    reported_accuracy_m: 2,
    uses_grids: false,
    best_available: false,
    preferred_missing_operations: [
      {
        name: 'OSTN15 preferred operation',
        grids: [
          {
            short_name: 'uk_os_OSTN15_NTv2_OSGBtoETRS.tif',
            available: false,
          },
        ],
      },
    ],
  };
}

export function createOverviewManifest(
  featureByteLength: number,
  featureSha256: string,
): OverviewManifest {
  const terrain = fixtureTerrain;
  const ring = structuredClone(terrain.aoi.boundaryWgs84.ring);
  const longitudes = ring.map(([longitude]) => longitude);
  const latitudes = ring.map(([, latitude]) => latitude);
  const bounds = [
    Math.min(...longitudes),
    Math.min(...latitudes),
    Math.max(...longitudes),
    Math.max(...latitudes),
  ] as const;
  return {
    formatVersion: 1,
    worldId: 'torquay-poc-001',
    worldType: 'real',
    packageType: 'torquay-geographic-overview',
    projection: 'mercator',
    aoi: {
      crs: 'EPSG:27700',
      boundsM: terrain.aoi.boundsM,
      centerBngM: terrain.aoi.centerBngM,
      boundaryWgs84: {
        crs: 'EPSG:4326',
        coordinateOrder: 'longitude-latitude',
        ring,
      },
      selectionStatus: 'selected_pending_coverage',
      coverageStatus: 'not_checked',
    },
    mapView: {
      centerWgs84: [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2],
      boundsWgs84: [...bounds],
      bearingDegrees: 0,
      pitchDegrees: 0,
      fitPaddingPx: 18,
    },
    includedLayers: ['aoi'],
    terrainIdentity: {
      worldId: terrain.id,
      manifestSha256: fixtureTerrainSha256,
      heightfield: {
        path: terrain.heightfield.path,
        byteLength: terrain.heightfield.byteLength,
        sha256: terrain.heightfield.sha256,
      },
      origin: terrain.origin,
      extentM: terrain.extentM,
      grid: { columns: 501, rows: 501, spacingM: 2 },
      axisConvention: '+X east, +Y up, -Z north',
      verticalReference: terrain.provenance.verticalReference,
      provenance: terrain.provenance,
    },
    optionalLayerIdentities: {},
    coordinateOperation: {
      axisOrder:
        'longitude-latitude for geographic input; easting-northing for BNG',
      bngToWgs84: operation(),
      wgs84ToBng: operation(),
      coordinateMeaning: 'Numerical inverse-transform consistency only.',
    },
    coordinatePolicy: {
      localToBng: 'E=eastingOrigin+x; N=northingOrigin-z',
      precisionDecimalPlaces: 9,
      maximumObservedRoundTripErrorM: 0.001,
      maximumAcceptedRoundTripErrorM: 0.02,
      aoiContainmentToleranceDegrees: 1e-6,
      interpretation:
        'Numerical consistency only; the pinned operation is not survey-accurate.',
    },
    omissions: {
      roadsWithoutAoiCenterline: 0,
      roadsPolicy: 'No clipped centerline records are represented.',
    },
    counts: {
      featuresByRole: { aoi: 1, roads: 0, buildings: 0, total: 1 },
      positionsByRole: {
        aoi: ring.length,
        roads: 0,
        buildings: 0,
        total: ring.length,
      },
    },
    features: {
      path: 'features.geojson',
      byteLength: featureByteLength,
      sha256: featureSha256,
    },
    limits: {
      manifestMaxBytes: 128 * 1024,
      featuresMaxBytes: 8 * 1024 * 1024,
      maxFeatures: 10_000,
      maxPositions: 250_000,
    },
    generator: { name: 'overview fixture', version: '1.0.0' },
    sources: {
      terrain: { publisher: 'Environment Agency', product: 'fixture only' },
      mapLibre: { licence: 'BSD 3-Clause' },
    },
    coverage: {
      selectionStatus: 'selected_pending_coverage',
      coverageStatus: 'not_checked',
      note: 'These mapped items do not establish completeness.',
    },
  };
}

export async function sha256Hex(bytes: Uint8Array): Promise<string> {
  const digest = await globalThis.crypto.subtle.digest(
    'SHA-256',
    bytes.slice().buffer,
  );
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
}

export async function createOverviewResponseBytes(): Promise<{
  manifest: OverviewManifest;
  manifestBytes: Uint8Array;
  featureBytes: Uint8Array;
}> {
  const featureBytes = new TextEncoder().encode(
    `${JSON.stringify(createOverviewFeatures())}\n`,
  );
  const manifest = createOverviewManifest(
    featureBytes.byteLength,
    await sha256Hex(featureBytes),
  );
  return {
    manifest,
    manifestBytes: new TextEncoder().encode(`${JSON.stringify(manifest)}\n`),
    featureBytes,
  };
}
