import type {
  BuildingFeature,
  BuildingPackageManifest,
} from '../../src/geo/buildingSchema';
import type { RealTerrainSceneManifest } from '../../src/geo/sceneSchema';

export type JsonRecord = Record<string, unknown>;

export async function sha256Hex(bytes: ArrayBuffer): Promise<string> {
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
}

export function createFeature(
  overrides: Partial<BuildingFeature> = {},
): BuildingFeature {
  return {
    id: 'osm:way:1',
    source: {
      dataset: 'Geofabrik Devon OpenStreetMap extract',
      objectType: 'way',
      osmId: 1,
      version: 1,
      timestamp: '2026-10-17 12:00:00+00:00',
    },
    geometry: {
      type: 'MultiPolygon',
      polygons: [
        {
          exteriorXZ: [
            [-1, -1],
            [1, -1],
            [1, 1],
            [-1, 1],
            [-1, -1],
          ],
          interiorRingsXZ: [],
        },
      ],
    },
    heightM: 8,
    heightMethod: 'estimated_default',
    heightConfidence: 'visual_default_estimate',
    heightProvenance: {
      heightM: 8,
      method: 'estimated_default',
      confidence: 'visual_default_estimate',
      rawHeight: null,
      parsedHeightM: null,
      parsedUnit: null,
      rawLevels: null,
      clamp: null,
      fallbackReason: 'no usable height or building:levels tag',
    },
    footprintAreaM2: 4,
    clippedToAoi: false,
    qualityFlags: [],
    duplicateReferences: [],
    tags: { building: 'yes' },
    ...overrides,
  };
}

export function createBuildingPayload(
  features: BuildingFeature[] = [createFeature()],
): JsonRecord {
  return {
    formatVersion: 1,
    worldId: 'torquay-poc-001',
    axisConvention: '+X east, +Y up, -Z north',
    units: 'metres',
    geometryCoordinates:
      'local XZ metres; no absolute BNG coordinates per vertex',
    buildings: features,
  };
}

export function createBuildingQa(
  features: BuildingFeature[] = [createFeature()],
): JsonRecord {
  const methods: Record<string, number> = {};
  const clamps: Record<string, number> = {};
  for (const feature of features) {
    methods[feature.heightMethod] = (methods[feature.heightMethod] ?? 0) + 1;
    const clamp = feature.heightProvenance.clamp;
    if (clamp) clamps[clamp] = (clamps[clamp] ?? 0) + 1;
  }
  const areas = features.reduce(
    (sum, feature) => sum + feature.footprintAreaM2,
    0,
  );
  const heights = features.map((feature) => feature.heightM);
  return {
    formatVersion: 1,
    aoiId: 'torquay-poc-001',
    selectionStatus: 'selected_pending_coverage',
    coverageStatus: 'not_checked',
    counts: {
      exported_buildings: features.length,
      exported_components: features.reduce(
        (sum, f) => sum + f.geometry.polygons.length,
        0,
      ),
      exported_holes: features.reduce(
        (sum, f) =>
          sum +
          f.geometry.polygons.reduce(
            (count, p) => count + p.interiorRingsXZ.length,
            0,
          ),
        0,
      ),
    },
    quality: {
      heightMethodCounts: methods,
      heightClampCounts: clamps,
      taggedHeightsAreUnverified: true,
    },
    summary: {
      buildingFootprintAreaM2: areas,
      minimumHeightM: Math.min(...heights),
      maximumHeightM: Math.max(...heights),
      meanHeightM:
        heights.reduce((sum, height) => sum + height, 0) / heights.length,
      densityInterpretation:
        'Mapped OSM coverage only; this is not a completeness estimate.',
    },
  };
}

export async function createPackageManifest(
  terrain: RealTerrainSceneManifest,
  payloadBytes: ArrayBuffer,
  qaBytes: ArrayBuffer,
  featureCount = 1,
): Promise<BuildingPackageManifest> {
  const coordinate = terrain.provenance.coordinateOperation;
  return {
    formatVersion: 1,
    worldId: terrain.id,
    name: 'Torquay candidate OSM building footprint package',
    sourceCrs: 'EPSG:27700',
    axisConvention: '+X east, +Y up, -Z north',
    units: 'metres',
    aoi: {
      crs: 'EPSG:27700',
      boundsM: [...terrain.aoi.boundsM],
      widthM: terrain.aoi.widthM,
      heightM: terrain.aoi.heightM,
      boundaryWgs84: {
        crs: terrain.aoi.boundaryWgs84.crs,
        coordinateOrder: terrain.aoi.boundaryWgs84.coordinateOrder,
        closedRing: true,
        ring: structuredClone(terrain.aoi.boundaryWgs84.ring),
      },
      selectionStatus: 'selected_pending_coverage',
      coverageStatus: 'not_checked',
    },
    terrainIdentity: {
      worldId: terrain.id,
      origin: { ...terrain.origin },
      heightfieldPath: terrain.heightfield.path,
      heightfieldSha256: terrain.heightfield.sha256,
      heightfieldByteLength: terrain.heightfield.byteLength,
      heightfieldDimensions: [
        terrain.heightfield.columns,
        terrain.heightfield.rows,
      ],
      verticalReference: terrain.provenance.verticalReference,
    },
    coordinateOperation: {
      axisOrder:
        'longitude-latitude for geographic input; easting-northing for BNG',
      wgs84ToBng: {
        name: coordinate.name,
        definition: coordinate.definition,
        reported_accuracy_m: coordinate.reportedAccuracyM,
        accuracy_m: coordinate.reportedAccuracyM,
        uses_grids: coordinate.selectedUsesGrids,
        best_available: coordinate.bestAvailable,
        preferred_missing_operations: [
          {
            name: 'Inverse of OSGB36 to WGS 84 (9) + British National Grid',
            grids: coordinate.preferredMissingGridNames.map((short_name) => ({
              short_name,
              available: false,
            })),
          },
        ],
        grid_status:
          'selected EPSG:1314 + EPSG:19916 operation uses no grid files',
      },
    },
    policies: {
      height: {
        version: 1,
        levelsToMetres: 3,
        defaultHeightM: 8,
        minimumHeightM: 1,
        maximumHeightM: 150,
        precedence: ['height', 'building:levels', 'configured_default'],
        taggedHeightConfidence: 'tagged_but_unverified',
        defaultConfidence: 'visual_default_estimate',
      },
      geometry: {
        version: 1,
        acquisitionBufferM: 50,
        minimumClippedAreaM2: 1,
        coordinateQuantizationM: 0.001,
        exteriorWinding: 'counter-clockwise in local XZ coordinates',
        interiorWinding: 'clockwise in local XZ coordinates',
        invalidGeometryPolicy: 'reject without automatic repair',
        duplicatePolicy:
          'prefer relation then stable identity; collapse exact canonical geometry',
        nearOverlapPolicy: 'report; do not merge',
      },
    },
    provenance: {
      publisher:
        'OpenStreetMap contributors; extract prepared by Geofabrik GmbH',
      product: 'OpenStreetMap regional extract — Devon',
      downloadUrl:
        'https://download.geofabrik.de/europe/united-kingdom/england/devon.html',
      fileUrl:
        'https://download.geofabrik.de/europe/united-kingdom/england/devon-261016.osm.pbf',
      downloadDate: '2026-10-17',
      filename: 'devon-261016.osm.pbf',
      sizeBytes: 58_254_938,
      sha256: '5'.repeat(64),
      licence: 'Open Database Licence 1.0 (ODbL)',
      licenceUrl: 'https://www.openstreetmap.org/copyright',
      attribution:
        '© OpenStreetMap contributors · Open Database License 1.0 · https://www.openstreetmap.org/copyright · Geofabrik Devon extract',
      geofabrikCredit:
        'Data © OpenStreetMap contributors; extract provided by Geofabrik GmbH.',
      notes: [
        'Tagged heights are not verified.',
        'Mapped counts are not a completeness estimate.',
      ],
    },
    generator: {
      name: 'torquay_pipeline.building_export',
      version: '0.1.0',
      geosVersion: '3.14.1',
    },
    coverage: {
      selectionStatus: 'selected_pending_coverage',
      coverageStatus: 'not_checked',
      note: 'Building extraction counts describe mapped OSM features, not completeness.',
    },
    buildings: {
      path: 'buildings.json',
      byteLength: payloadBytes.byteLength,
      sha256: await sha256Hex(payloadBytes),
      count: featureCount,
    },
    qaReport: {
      path: 'qa.json',
      byteLength: qaBytes.byteLength,
      sha256: await sha256Hex(qaBytes),
    },
  };
}
