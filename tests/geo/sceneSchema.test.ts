import { describe, expect, it } from 'vitest';
import {
  MAX_HEIGHTFIELD_SAMPLES,
  validateSceneManifest,
} from '../../src/geo/sceneSchema';
import { createValidManifest, readSyntheticFixtureManifest } from './fixtures';

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
    ['worldType', 'real', 'worldType'],
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
});
