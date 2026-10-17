import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const fixtureDirectory = resolve(
  projectRoot,
  'public/worlds/synthetic-heightfield',
);

async function writeWorldFixture({
  directory,
  id,
  name,
  columns,
  rows,
  spacingM,
  heightAt,
  generatorVersion,
  note,
}) {
  const values = [];
  for (let row = 0; row < rows; row += 1) {
    const z = row * spacingM - ((rows - 1) * spacingM) / 2;
    for (let column = 0; column < columns; column += 1) {
      const x = column * spacingM - ((columns - 1) * spacingM) / 2;
      values.push(heightAt(x, z, values.length));
    }
  }

  const heightfieldBytes = Buffer.alloc(
    values.length * Float32Array.BYTES_PER_ELEMENT,
  );
  values.forEach((value, index) => {
    heightfieldBytes.writeFloatLE(
      value,
      index * Float32Array.BYTES_PER_ELEMENT,
    );
  });

  const sha256 = createHash('sha256').update(heightfieldBytes).digest('hex');
  const manifest = {
    formatVersion: 1,
    id,
    name,
    worldType: 'synthetic',
    sourceCrs: 'LOCAL_SYNTHETIC',
    axisConvention: '+X east, +Y up, -Z north',
    origin: { eastingM: 0, northingM: 0, elevationM: 0 },
    extentM: {
      width: (columns - 1) * spacingM,
      depth: (rows - 1) * spacingM,
    },
    heightfield: {
      path: 'heightfield.f32',
      columns,
      rows,
      spacingM,
      rowOrder: 'north-to-south',
      byteOrder: 'little-endian',
      encoding: 'float32',
      valueMeaning: 'world Y in metres relative to origin elevation',
      sha256,
    },
    provenance: {
      kind: 'synthetic',
      generator: 'scripts/generate-synthetic-heightfield.mjs',
      generatorVersion,
      note,
    },
  };

  await mkdir(directory, { recursive: true });
  await writeFile(resolve(directory, 'heightfield.f32'), heightfieldBytes);
  await writeFile(
    resolve(directory, 'manifest.json'),
    `${JSON.stringify(manifest, null, 2)}\n`,
  );

  return { id, rows, columns, byteLength: heightfieldBytes.byteLength, sha256 };
}

const fixtures = await Promise.all([
  writeWorldFixture({
    directory: fixtureDirectory,
    id: 'synthetic-heightfield-3x3',
    name: 'Synthetic 3 × 3 Heightfield Fixture',
    columns: 3,
    rows: 3,
    spacingM: 2,
    heightAt: (_x, _z, index) =>
      [-2.5, 0, 1.25, 10, 11.5, 12, 20, 21, 22.75][index],
    generatorVersion: '1.0.0',
    note: 'Fictional test values only; no geographic measurements.',
  }),
  writeWorldFixture({
    directory: resolve(projectRoot, 'public/worlds/synthetic-terrain-demo'),
    id: 'synthetic-terrain-demo',
    name: 'Synthetic Hill and Ridge Demo',
    columns: 25,
    rows: 19,
    spacingM: 2,
    heightAt: (x, z) => {
      const slope = 0.025 * x + 0.018 * z;
      const hill =
        4.8 * Math.exp(-0.5 * (((x + 8) / 6) ** 2 + ((z + 2) / 5) ** 2));
      const ridge =
        3.4 *
        Math.exp(-0.5 * ((x - 9) / 1.8) ** 2) *
        (0.65 + 0.35 * Math.exp(-0.5 * (z / 11) ** 2));
      return slope + hill + ridge;
    },
    generatorVersion: '1.0.0',
    note: 'Fictional deterministic base slope, Gaussian hill, and narrow ridge; not measured terrain.',
  }),
]);

for (const fixture of fixtures) {
  process.stdout.write(
    `Generated ${fixture.id} (${fixture.columns} × ${fixture.rows}, ${fixture.byteLength} bytes, SHA-256 ${fixture.sha256}).\n`,
  );
}
