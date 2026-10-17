import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const outputDirectory = resolve(
  projectRoot,
  'public/worlds/synthetic-heightfield',
);
const values = [-2.5, 0, 1.25, 10, 11.5, 12, 20, 21, 22.75];
const heightfieldBytes = Buffer.alloc(
  values.length * Float32Array.BYTES_PER_ELEMENT,
);

values.forEach((value, index) => {
  heightfieldBytes.writeFloatLE(value, index * Float32Array.BYTES_PER_ELEMENT);
});

const sha256 = createHash('sha256').update(heightfieldBytes).digest('hex');
const manifest = {
  formatVersion: 1,
  id: 'synthetic-heightfield-3x3',
  name: 'Synthetic 3 × 3 Heightfield Fixture',
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
    sha256,
  },
  provenance: {
    kind: 'synthetic',
    generator: 'scripts/generate-synthetic-heightfield.mjs',
    generatorVersion: '1.0.0',
    note: 'Fictional test values only; no geographic measurements.',
  },
};

await mkdir(outputDirectory, { recursive: true });
await writeFile(resolve(outputDirectory, 'heightfield.f32'), heightfieldBytes);
await writeFile(
  resolve(outputDirectory, 'manifest.json'),
  `${JSON.stringify(manifest, null, 2)}\n`,
);

process.stdout.write(
  `Generated 3 × 3 synthetic fixture (${heightfieldBytes.byteLength} bytes, SHA-256 ${sha256}).\n`,
);
