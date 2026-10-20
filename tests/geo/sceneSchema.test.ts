import { describe, expect, it } from 'vitest';
import {
  MAX_HEIGHTFIELD_SAMPLES,
  validateSceneManifest,
} from '../../src/geo/sceneSchema';
import {
  createCurrent2kmRealManifest,
  createRealManifest,
  createValidManifest,
  readSyntheticFixtureManifest,
} from './fixtures';

type TestRecord = Record<string, unknown>;

function isTestRecord(value: unknown): value is TestRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function withValue(path: string, value: unknown): unknown {
  const input = structuredClone(createValidManifest()) as unknown as TestRecord;
  const segments = path.split('.');
  let current = input;
  for (const segment of segments.slice(0, -1)) {
    const child = current[segment];
    if (!isTestRecord(child)) throw new Error(`Missing test path ${segment}`);
    current = child;
  }
  current[segments[segments.length - 1]!] = value;
  return input;
}

function withoutValue(path: string): unknown {
  const input = structuredClone(createValidManifest()) as unknown as TestRecord;
  const segments = path.split('.');
  let current = input;
  for (const segment of segments.slice(0, -1)) {
    const child = current[segment];
    if (!isTestRecord(child)) throw new Error(`Missing test path ${segment}`);
    current = child;
  }
  delete current[segments[segments.length - 1]!];
  return input;
}

function withRealValue(path: string, value: unknown): unknown {
  const input = structuredClone(createRealManifest()) as unknown as TestRecord;
  const segments = path.replaceAll('[', '.').replaceAll(']', '').split('.');
  let current: unknown = input;
  for (const segment of segments.slice(0, -1)) {
    if (Array.isArray(current)) current = current[Number(segment)];
    else if (isTestRecord(current)) current = current[segment];
    else throw new Error(`Missing test path ${segment}`);
  }
  const finalSegment = segments.at(-1)!;
  if (Array.isArray(current)) current[Number(finalSegment)] = value;
  else if (isTestRecord(current)) current[finalSegment] = value;
  else throw new Error(`Missing test path ${finalSegment}`);
  return input;
}

function withoutRealValue(path: string): unknown {
  const input = structuredClone(createRealManifest()) as unknown as TestRecord;
  const segments = path.replaceAll('[', '.').replaceAll(']', '').split('.');
  let current: unknown = input;
  for (const segment of segments.slice(0, -1)) {
    if (Array.isArray(current)) current = current[Number(segment)];
    else if (isTestRecord(current)) current = current[segment];
    else throw new Error(`Missing test path ${segment}`);
  }
  const finalSegment = segments.at(-1)!;
  if (Array.isArray(current)) delete current[Number(finalSegment)];
  else if (isTestRecord(current)) delete current[finalSegment];
  else throw new Error(`Missing test path ${finalSegment}`);
  return input;
}

describe('validateSceneManifest', () => {
  it('accepts the generated 3 × 3 synthetic fixture', () => {
    const result = validateSceneManifest(readSyntheticFixtureManifest());
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.manifest.worldType).toBe('synthetic');
      expect(result.manifest.sourceCrs).toBe('LOCAL_SYNTHETIC');
      expect(result.manifest.heightfield.columns).toBe(3);
      expect(result.manifest.heightfield.rows).toBe(3);
      expect(result.manifest.extentM).toEqual({ width: 4, depth: 4 });
    }
  });

  it.each([
    ['formatVersion', 2, 'formatVersion'],
    ['id', '   ', 'id'],
    ['name', null, 'name'],
    ['worldType', 'unknown', 'worldType'],
    ['sourceCrs', 'EPSG:27700', 'sourceCrs'],
    ['axisConvention', '+X east, +Y up, +Z north', 'axisConvention'],
    ['origin', null, 'origin'],
    ['origin.eastingM', Number.NaN, 'origin.eastingM'],
    ['origin.northingM', Number.POSITIVE_INFINITY, 'origin.northingM'],
    ['extentM.width', 0, 'extentM.width'],
    ['extentM.depth', Number.NEGATIVE_INFINITY, 'extentM.depth'],
    ['heightfield.path', '../outside.f32', 'heightfield.path'],
    ['heightfield.columns', 1, 'heightfield.columns'],
    ['heightfield.rows', 2.5, 'heightfield.rows'],
    ['heightfield.spacingM', 0, 'heightfield.spacingM'],
    ['heightfield.rowOrder', 'south-to-north', 'heightfield.rowOrder'],
    ['heightfield.byteOrder', 'big-endian', 'heightfield.byteOrder'],
    ['heightfield.encoding', 'float64', 'heightfield.encoding'],
    [
      'heightfield.valueMeaning',
      'absolute elevation',
      'heightfield.valueMeaning',
    ],
    ['heightfield.sha256', 'not-a-hash', 'heightfield.sha256'],
    ['provenance.kind', 'measured', 'provenance.kind'],
    ['provenance.generatorVersion', '', 'provenance.generatorVersion'],
    ['roads', 'https://example.test/roads.json', 'roads'],
    ['buildings', 'C:\\data\\buildings.json', 'buildings'],
  ])('rejects invalid %s', (path, value, expectedIssuePath) => {
    const result = validateSceneManifest(withValue(path, value));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.issues.map((issue) => issue.path)).toContain(
        expectedIssuePath,
      );
    }
  });

  it.each(['id', 'heightfield.path', 'provenance.note'])(
    'reports missing required field %s',
    (path) => {
      const result = validateSceneManifest(withoutValue(path));
      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.issues.map((issue) => issue.path)).toContain(path);
      }
    },
  );

  it.each([null, [], 'manifest', 4])('rejects non-object input %j', (value) => {
    const result = validateSceneManifest(value);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.issues[0]?.path).toBe('$');
  });

  it('checks grid extents with a small documented relative tolerance', () => {
    const near = withValue('extentM.width', 4 + 1e-10);
    expect(validateSceneManifest(near).ok).toBe(true);

    const far = withValue('extentM.width', 4.01);
    const result = validateSceneManifest(far);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(
        result.issues.some((issue) => issue.path === 'extentM.width'),
      ).toBe(true);
    }
  });

  it.each([
    {
      axis: 'width',
      expectedPath: 'extentM.width',
      columns: 3,
      rows: 2,
      width: 1,
      depth: 1e308,
    },
    {
      axis: 'depth',
      expectedPath: 'extentM.depth',
      columns: 2,
      rows: 3,
      width: 1e308,
      depth: 1,
    },
  ])(
    'rejects a non-finite computed grid $axis extent',
    ({ expectedPath, columns, rows, width, depth }) => {
      const manifest = structuredClone(createValidManifest());
      manifest.heightfield.columns = columns;
      manifest.heightfield.rows = rows;
      manifest.heightfield.spacingM = 1e308;
      manifest.extentM.width = width;
      manifest.extentM.depth = depth;

      const result = validateSceneManifest(manifest);
      expect(result.ok).toBe(false);
      if (!result.ok) {
        const issue = result.issues.find(({ path }) => path === expectedPath);
        expect(issue?.message).toContain('computed grid extent');
        expect(issue?.message).toContain('must be finite');
      }
    },
  );

  it('accepts a very large finite computed grid extent', () => {
    const manifest = structuredClone(createValidManifest());
    manifest.heightfield.spacingM = Number.MAX_VALUE / 2;
    manifest.extentM.width = Number.MAX_VALUE;
    manifest.extentM.depth = Number.MAX_VALUE;

    expect(validateSceneManifest(manifest).ok).toBe(true);
  });

  it('rejects sample-count overflow and caps allocations at 16 million samples', () => {
    const unsafe = withValue('heightfield.columns', Number.MAX_SAFE_INTEGER);
    const unsafeResult = validateSceneManifest(unsafe);
    expect(unsafeResult.ok).toBe(false);
    if (!unsafeResult.ok) {
      expect(
        unsafeResult.issues.some((issue) =>
          issue.message.includes('safe integer arithmetic'),
        ),
      ).toBe(true);
    }

    const tooLarge = structuredClone(createValidManifest());
    tooLarge.heightfield.columns = MAX_HEIGHTFIELD_SAMPLES / 2 + 1;
    tooLarge.extentM.width = (tooLarge.heightfield.columns - 1) * 2;
    const largeResult = validateSceneManifest(tooLarge);
    expect(largeResult.ok).toBe(false);
    if (!largeResult.ok) {
      expect(
        largeResult.issues.some((issue) =>
          issue.message.includes('sample limit'),
        ),
      ).toBe(true);
    }
  });

  it('allows optional local buildings and roads references without defining their schemas', () => {
    const manifest = createValidManifest();
    manifest.buildings = 'buildings.json';
    manifest.roads = 'roads/data.json';
    const result = validateSceneManifest(manifest);
    expect(result.ok).toBe(true);
  });

  it('accepts a fully attributed, pending real EA terrain manifest', () => {
    const result = validateSceneManifest(createRealManifest());

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.manifest.worldType).toBe('real');
      expect(result.manifest.sourceCrs).toBe('EPSG:27700');
      if (result.manifest.worldType === 'real') {
        expect(result.manifest.provenance.sources[0]?.archiveRasterMember).toBe(
          'SX96nw_DTM_1m.tif',
        );
        expect(result.manifest.aoi.coverageStatus).toBe('not_checked');
        expect(result.manifest.heightfield.byteLength).toBe(1_004_004);
        expect(result.manifest.aoi.centerBngM).toEqual([
          291108.9018176432, 65353.48350844931,
        ]);
        expect(result.manifest.aoi.boundaryWgs84).toEqual({
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
        });
      }
    }
  });

  it('accepts the explicit 1001 by 1001 current 2 km terrain profile', () => {
    const result = validateSceneManifest(createCurrent2kmRealManifest());
    expect(result.ok).toBe(true);
    if (result.ok && result.manifest.worldType === 'real') {
      expect(result.manifest.sceneProfile).toBe('current_2km');
      expect(result.manifest.extentM).toEqual({ width: 2000, depth: 2000 });
      expect(result.manifest.heightfield).toMatchObject({
        columns: 1001,
        rows: 1001,
        spacingM: 2,
        byteLength: 4_008_004,
      });
    }
  });

  it.each([
    ['old boundary', 'aoi.boundaryWgs84.ring[1][0]', -3.528823875124863],
    ['old extent', 'extentM.width', 1000],
    ['old grid', 'heightfield.columns', 501],
  ])('rejects current_2km profile mixed with %s', (_label, path, value) => {
    const input = structuredClone(
      createCurrent2kmRealManifest(),
    ) as unknown as TestRecord;
    const segments = path.replaceAll('[', '.').replaceAll(']', '').split('.');
    let current: unknown = input;
    for (const segment of segments.slice(0, -1)) {
      if (Array.isArray(current)) current = current[Number(segment)];
      else if (isTestRecord(current)) current = current[segment];
      else throw new Error(`Missing test path ${segment}`);
    }
    const finalSegment = segments.at(-1)!;
    if (Array.isArray(current)) current[Number(finalSegment)] = value;
    else if (isTestRecord(current)) current[finalSegment] = value;
    else throw new Error(`Missing test path ${finalSegment}`);
    const result = validateSceneManifest(input);
    expect(result.ok).toBe(false);
  });

  it('accepts whitespace-normalized full pinned coordinate-operation metadata', () => {
    const manifest = createRealManifest();
    manifest.provenance.coordinateOperation.definition = `  ${manifest.provenance.coordinateOperation.definition.replaceAll(' step ', '   step  ')}  `;

    const result = validateSceneManifest(manifest);

    expect(result.ok).toBe(true);
  });

  it.each([
    ['central meridian', 'lon_0=-2', 'lon_0=20'],
    ['Helmert translation', 'x=446.448', 'x=446.4489'],
  ])(
    'rejects a changed pinned coordinate-operation %s parameter',
    (_label, original, changed) => {
      const definition =
        createRealManifest().provenance.coordinateOperation.definition;
      const result = validateSceneManifest(
        withRealValue(
          'provenance.coordinateOperation.definition',
          definition.replace(original, changed),
        ),
      );

      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(
          result.issues.some(
            (issue) =>
              issue.path === 'provenance.coordinateOperation.definition',
          ),
        ).toBe(true);
      }
    },
  );

  it('rejects a missing geographic AOI boundary', () => {
    const result = validateSceneManifest(withoutRealValue('aoi.boundaryWgs84'));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(
        result.issues.some((issue) => issue.path === 'aoi.boundaryWgs84'),
      ).toBe(true);
    }
  });

  it.each([
    ['malformed coordinate pair', 'aoi.boundaryWgs84.ring', [[-3, 50]]],
    ['non-finite coordinate', 'aoi.boundaryWgs84.ring[2][1]', Number.NaN],
    ['out-of-range longitude', 'aoi.boundaryWgs84.ring[0][0]', 181],
    ['unclosed ring', 'aoi.boundaryWgs84.ring[4][1]', 50.48],
    [
      'ring inconsistent with the configured bounds',
      'aoi.boundaryWgs84.ring[1][0]',
      -3.5279,
    ],
  ])('rejects a %s', (_label, path, value) => {
    const result = validateSceneManifest(withRealValue(path, value));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(
        result.issues.some((issue) =>
          issue.path.startsWith('aoi.boundaryWgs84.ring'),
        ),
      ).toBe(true);
    }
  });

  it.each([
    ['aoi.boundaryWgs84.crs', 'EPSG:3857'],
    ['aoi.boundaryWgs84.coordinateOrder', 'latitude-longitude'],
    ['aoi.boundaryWgs84.geometryType', 'MultiPolygon'],
  ])('rejects invalid geographic boundary metadata %s', (path, value) => {
    const result = validateSceneManifest(withRealValue(path, value));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.issues.some((issue) => issue.path === path)).toBe(true);
    }
  });

  it.each([
    ['width', 'extentM.width', 500, 'heightfield.columns', 251],
    ['depth', 'extentM.depth', 500, 'heightfield.rows', 251],
  ])(
    'rejects a real grid whose %s extent no longer matches the reviewed AOI',
    (_axis, extentPath, extent, dimensionPath, dimension) => {
      let manifest = withRealValue(extentPath, extent);
      manifest = withRealValueFrom(manifest, dimensionPath, dimension);
      const result = validateSceneManifest(manifest);
      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.issues.some((issue) => issue.path === extentPath)).toBe(
          true,
        );
      }
    },
  );

  it.each([
    ['easting bounds overflow', 'aoi.boundsM', [-1e308, 64853, 1e308, 65853]],
    [
      'northing bounds overflow',
      'aoi.boundsM',
      [290608, -1e308, 291608, 1e308],
    ],
  ])(
    'rejects finite coordinates whose %s span overflows',
    (_label, path, value) => {
      const result = validateSceneManifest(withRealValue(path, value));
      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(
          result.issues.some((issue) => issue.path === 'aoi.boundsM'),
        ).toBe(true);
      }
    },
  );

  it.each([
    ['heightfield.byteLength', 1_004_000],
    ['provenance.generator', null],
    ['provenance.generatorVersion', ''],
    ['provenance.generator', 'other-exporter'],
    ['provenance.generatorVersion', 'latest'],
    ['provenance.generatorVersion', '0.1.1'],
    ['provenance.licenceUrl', 'http://example.invalid/licence'],
    ['provenance.catalogueUrl', null],
    ['provenance.productSurveyPeriod', ''],
    ['provenance.xmlCopyrightConflict', 'only useLimit says 2022'],
    ['provenance.coordinateOperation.name', 'automatic operation'],
    ['provenance.coordinateOperation.definition', ''],
    [
      'provenance.coordinateOperation.definition',
      'proj=pipeline step proj=helmert',
    ],
    ['provenance.coordinateOperation.reportedAccuracyM', 1],
    ['provenance.coordinateOperation.selectedUsesGrids', true],
    ['provenance.coordinateOperation.preferredMissingGridNames', null],
    [
      'provenance.coordinateOperation.missingPreferredGridCaveat',
      'grid unavailable',
    ],
    ['aoi.anchorWgs84.crs', 'EPSG:3857'],
    ['aoi.anchorWgs84.longitude', 181],
    ['aoi.anchorWgs84.latitude', '50.477853'],
    ['aoi.anchorWgs84.postcode', 'TQ1 4HX'],
    ['aoi.anchorWgs84.retrievedDate', '2026-10-18'],
    ['aoi.anchorWgs84.sourceName', 'Other provider'],
    ['aoi.anchorWgs84.sourceUrl', 'https://example.invalid/lookup'],
    ['provenance.productSurveyPeriod', '2003-2022 only'],
    ['aoi.centerBngM', [0, 0]],
    [
      'aoi.boundsM',
      [
        290608.9018176432 + 1000,
        64853.48350844931,
        291608.9018176432 + 1000,
        65853.48350844931,
      ],
    ],
  ])('rejects malformed real provenance field %s', (path, value) => {
    const result = validateSceneManifest(withRealValue(path, value));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.issues.some((issue) => issue.path === path)).toBe(true);
    }
  });

  it.each([
    'heightfield.byteLength',
    'provenance.generator',
    'provenance.generatorVersion',
    'provenance.licenceUrl',
    'provenance.catalogueUrl',
    'provenance.productSurveyPeriod',
    'provenance.xmlCopyrightConflict',
    'provenance.coordinateOperation',
    'aoi.centerBngM',
    'aoi.anchorWgs84',
    'aoi.boundaryWgs84',
  ])('rejects missing real provenance field %s', (path) => {
    const result = validateSceneManifest(withoutRealValue(path));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(
        result.issues.some(
          (issue) => issue.path === path || issue.path.startsWith(`${path}.`),
        ),
      ).toBe(true);
    }
  });

  it.each([
    ['provenance.attribution', ''],
    ['provenance.verticalReference', ''],
    ['provenance.selectionStatus', 'approved'],
    ['provenance.coverageStatus', 'pass'],
    ['provenance.sources[0].archiveSha256', 'invalid'],
    ['aoi.boundsM', [0, 0, 1000, 1000]],
  ])('rejects invalid real manifest field %s', (path, value) => {
    const manifest: unknown = structuredClone(createRealManifest());
    const segments = path.replaceAll('[', '.').replaceAll(']', '').split('.');
    let current: unknown = manifest;
    for (const segment of segments.slice(0, -1)) {
      if (Array.isArray(current)) {
        current = current[Number(segment)];
      } else if (isTestRecord(current)) {
        current = current[segment];
      } else {
        throw new Error(`Missing test path ${segment}`);
      }
    }
    const finalSegment = segments.at(-1)!;
    if (Array.isArray(current)) {
      current[Number(finalSegment)] = value;
    } else if (isTestRecord(current)) {
      current[finalSegment] = value;
    } else {
      throw new Error(`Missing test path ${finalSegment}`);
    }

    const result = validateSceneManifest(manifest);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.issues.map(({ path: issuePath }) => issuePath)).toContain(
        path,
      );
    }
  });
});

function withRealValueFrom(
  input: unknown,
  path: string,
  value: unknown,
): unknown {
  const segments = path.replaceAll('[', '.').replaceAll(']', '').split('.');
  let current: unknown = input;
  for (const segment of segments.slice(0, -1)) {
    if (Array.isArray(current)) current = current[Number(segment)];
    else if (isTestRecord(current)) current = current[segment];
    else throw new Error(`Missing test path ${segment}`);
  }
  const finalSegment = segments.at(-1)!;
  if (Array.isArray(current)) current[Number(finalSegment)] = value;
  else if (isTestRecord(current)) current[finalSegment] = value;
  else throw new Error(`Missing test path ${finalSegment}`);
  return input;
}
