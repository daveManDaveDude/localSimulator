import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { SyntheticSceneManifest } from '../../src/geo/sceneSchema';

export const syntheticFixtureDirectory = resolve(
  process.cwd(),
  'public/worlds/synthetic-heightfield',
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
