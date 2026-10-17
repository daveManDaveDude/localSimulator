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
      rowOrder: 'north-to-south',
      byteOrder: 'little-endian',
      encoding: 'float32',
      valueMeaning: 'world Y in metres relative to origin elevation',
      sha256: heightfieldSha256,
    },
    provenance: {
      kind: 'real',
      publisher: 'Environment Agency',
      product: 'LIDAR Composite DTM 1 m (2022 composite)',
      licence: 'Open Government Licence v3.0',
      attribution:
        'Contains public sector information licensed under the Open Government Licence v3.0. © Environment Agency copyright and/or database right 2022.',
      verticalReference:
        'Ordnance Survey Newlyn using OSTN’15 and OSGM’15 transformation models',
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
      widthM: 1000,
      heightM: 1000,
      selectionStatus: 'selected_pending_coverage',
      coverageStatus: 'not_checked',
    },
  };
}
