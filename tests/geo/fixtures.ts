import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type {
  RealTerrainSceneManifest,
  SyntheticSceneManifest,
} from '../../src/geo/sceneSchema';

export const syntheticFixtureDirectory = resolve(
  process.cwd(),
  'public/worlds/synthetic-heightfield',
);
export const syntheticTerrainDemoDirectory = resolve(
  process.cwd(),
  'public/worlds/synthetic-terrain-demo',
);

export function readSyntheticFixtureManifest(): unknown {
  const text = readFileSync(
    resolve(syntheticFixtureDirectory, 'manifest.json'),
    'utf8',
  );
  return JSON.parse(text) as unknown;
}

export function readSyntheticFixtureBytes(): ArrayBuffer {
  const source = readFileSync(
    resolve(syntheticFixtureDirectory, 'heightfield.f32'),
  );
  const copy = new Uint8Array(source.byteLength);
  copy.set(source);
  return copy.buffer;
}

export function readSyntheticTerrainDemoManifest(): unknown {
  const text = readFileSync(
    resolve(syntheticTerrainDemoDirectory, 'manifest.json'),
    'utf8',
  );
  return JSON.parse(text) as unknown;
}

export function readSyntheticTerrainDemoBytes(): ArrayBuffer {
  const source = readFileSync(
    resolve(syntheticTerrainDemoDirectory, 'heightfield.f32'),
  );
  const copy = new Uint8Array(source.byteLength);
  copy.set(source);
  return copy.buffer;
}

export function createValidManifest(): SyntheticSceneManifest {
  return {
    formatVersion: 1,
    id: 'fixture-for-tests',
    name: 'Synthetic test manifest',
    worldType: 'synthetic',
    sourceCrs: 'LOCAL_SYNTHETIC',
    axisConvention: '+X east, +Y up, -Z north',
    origin: { eastingM: 0, northingM: 0, elevationM: 0 },
    extentM: { width: 4, depth: 4 },
    heightfield: {
      path: 'heightfield.f32',
      columns: 3,
      rows: 3,
      spacingM: 2,
      rowOrder: 'north-to-south',
      byteOrder: 'little-endian',
      encoding: 'float32',
      valueMeaning: 'world Y in metres relative to origin elevation',
      sha256: 'a'.repeat(64),
    },
    provenance: {
      kind: 'synthetic',
      generator: 'tests/geo/fixtures.ts',
      generatorVersion: '1.0.0',
      note: 'Fictional test manifest.',
    },
  };
}

export function createRealManifest(
  heightfieldSha256 = 'b'.repeat(64),
): RealTerrainSceneManifest {
  return {
    formatVersion: 1,
    id: 'torquay-poc-001',
    name: 'TQ1 4HN candidate area of interest',
    worldType: 'real',
    sceneProfile: 'historical_1km',
    sourceCrs: 'EPSG:27700',
    axisConvention: '+X east, +Y up, -Z north',
    origin: {
      eastingM: 291108.9018176432,
      northingM: 65353.48350844931,
      elevationM: 47.59241548392676,
    },
    extentM: { width: 1000, depth: 1000 },
    heightfield: {
      path: 'heightfield.f32',
      columns: 501,
      rows: 501,
      spacingM: 2,
      byteLength: 1_004_004,
      rowOrder: 'north-to-south',
      byteOrder: 'little-endian',
      encoding: 'float32',
      valueMeaning: 'world Y in metres relative to origin elevation',
      sha256: heightfieldSha256,
    },
    provenance: {
      kind: 'real',
      generator: 'torquay_pipeline.terrain_export',
      generatorVersion: '0.1.0',
      publisher: 'Environment Agency',
      product: 'LIDAR Composite DTM 1 m (2022 composite)',
      licence: 'Open Government Licence v3.0',
      attribution:
        'Contains public sector information licensed under the Open Government Licence v3.0. © Environment Agency copyright and/or database right 2022.',
      verticalReference:
        'Ordnance Survey Newlyn using OSTN’15 and OSGM’15 transformation models',
      licenceUrl:
        'https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/',
      catalogueUrl:
        'https://www.data.gov.uk/dataset/01b3ee39-da3f-47b6-83da-dc98e73a461f/lidar-composite-dtm-2022-1m',
      productSurveyPeriod:
        '2000-06-06 through 2022-04-02 (publisher-wide catalogue dates)',
      xmlCopyrightConflict:
        'TIFF XML useLimit requires 2022 attribution; idCredit says 2020. The explicit reuse instruction is followed.',
      coordinateOperation: {
        name: 'EPSG:1314 + EPSG:19916',
        authorityCodes: ['EPSG:1314', 'EPSG:19916'],
        definition:
          'proj=pipeline step proj=unitconvert xy_in=deg xy_out=rad step proj=push v_3 step proj=cart ellps=WGS84 step inv proj=helmert x=446.448 y=-125.157 z=542.06 rx=0.15 ry=0.247 rz=0.842 s=-20.489 convention=position_vector step inv proj=cart ellps=airy step proj=pop v_3 step proj=tmerc lat_0=49 lon_0=-2 k=0.9996012717 x_0=400000 y_0=-100000 ellps=airy',
        reportedAccuracyM: 2,
        selectedUsesGrids: false,
        bestAvailable: false,
        preferredMissingGridNames: ['uk_os_OSTN15_NTv2_OSGBtoETRS.tif'],
        missingPreferredGridCaveat:
          'PROJ_NETWORK=OFF; preferred operation unavailable because uk_os_OSTN15_NTv2_OSGBtoETRS.tif is unavailable.',
      },
      sources: [
        {
          tileName: 'SX96nw',
          archiveFilename: 'lidar_composite_dtm-2022-1-SX96nw.zip',
          archiveSizeBytes: 68662575,
          archiveSha256: 'c'.repeat(64),
          archiveDownloadUrl:
            'https://environment.data.gov.uk/tiles/collections/survey/lidar_composite_dtm/2022/1/SX9065',
          downloadDate: '2026-10-17',
          archiveRasterMember: 'SX96nw_DTM_1m.tif',
          archiveXmlMember: 'SX96nw_DTM_1m.tif.xml',
          rasterFilename: 'SX96nw_DTM_1m.tif',
          rasterSizeBytes: 69538064,
          rasterSha256: 'd'.repeat(64),
          rasterCrs: 'EPSG:27700',
          rasterTransform: [1, 0, 290000, 0, -1, 70000],
          rasterBoundsM: [290000, 65000, 295000, 70000],
          rasterWidthPixels: 5000,
          rasterHeightPixels: 5000,
          rasterResolutionM: [1, 1],
          rasterDtype: 'float32',
          rasterNodata: -3.4028234663852886e38,
          xmlFilename: 'SX96nw_DTM_1m.tif.xml',
          xmlSizeBytes: 20545,
          xmlSha256: 'e'.repeat(64),
          tileSurveyPeriod: '2003-02-14 through 2022-05-05',
          xmlVerticalReference:
            'Ordnance Survey Newlyn using OSTN 15 and OSGM 15 transformation models',
        },
      ],
      selectionStatus: 'selected_pending_coverage',
      coverageStatus: 'not_checked',
      resampling: 'bilinear between source 1 m area-pixel centers',
      fillPolicy:
        'none; every positive-weight source contributor must be valid',
      qa: {
        sampling: 'bilinear between source 1 m area-pixel centers',
        maximumObservedResamplingErrorM: 0,
        maximumObservedFloat32QuantizationErrorM: 0.000001,
      },
    },
    aoi: {
      crs: 'EPSG:27700',
      boundsM: [
        290608.9018176432, 64853.48350844931, 291608.9018176432,
        65853.48350844931,
      ],
      centerBngM: [291108.9018176432, 65353.48350844931],
      widthM: 1000,
      heightM: 1000,
      anchorWgs84: {
        postcode: 'TQ1 4HN',
        crs: 'EPSG:4326',
        longitude: -3.536013,
        latitude: 50.477853,
        coordinateMeaning: 'Postcode centroid; not a property or survey point.',
        quality: 1,
        sourceName: 'Postcodes.io',
        sourceUrl: 'https://api.postcodes.io/postcodes/TQ1%204HN',
        sourceLicense: 'OS OpenData licence (provider documentation)',
        retrievedDate: '2026-10-17',
      },
      boundaryWgs84: {
        crs: 'EPSG:4326',
        coordinateOrder: 'longitude-latitude',
        geometryType: 'Polygon',
        ring: [
          [-3.542910651853897, 50.47326489870257],
          [-3.528823875124863, 50.473450849062345],
          [-3.5291139928135884, 50.48244068998469],
          [-3.5432034396837033, 50.48225468056402],
          [-3.542910651853897, 50.47326489870257],
        ],
      },
      selectionStatus: 'selected_pending_coverage',
      coverageStatus: 'not_checked',
    },
  };
}

export function createCurrent2kmRealManifest(
  heightfieldSha256 = 'f'.repeat(64),
): RealTerrainSceneManifest {
  const manifest = structuredClone(
    createRealManifest(heightfieldSha256),
  ) as RealTerrainSceneManifest;
  return {
    ...manifest,
    sceneProfile: 'current_2km',
    name: 'TQ1 4HN current 2 km candidate area of interest',
    extentM: { width: 2000, depth: 2000 },
    heightfield: {
      ...manifest.heightfield,
      columns: 1001,
      rows: 1001,
      byteLength: 4_008_004,
    },
    aoi: {
      ...manifest.aoi,
      boundsM: [
        290108.9018176432, 64353.48350844931, 292108.9018176432,
        66353.48350844931,
      ],
      widthM: 2000,
      heightM: 2000,
      boundaryWgs84: {
        ...manifest.aoi.boundaryWgs84,
        ring: [
          [-3.5498069791321853, 50.46867640263527],
          [-3.5216360951366497, 50.4690482443],
          [-3.5222136603237235, 50.48702798479993],
          [-3.5503952248835833, 50.48665590689169],
          [-3.5498069791321853, 50.46867640263527],
        ],
      },
    },
  };
}
