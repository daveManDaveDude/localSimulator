import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { copySharePublicAssets } from '../../scripts/share-assets';

const temporaryRoots: string[] = [];

function makePublicFixture(): { publicRoot: string; buildRoot: string } {
  const root = mkdtempSync(join(tmpdir(), 'torquay-share-assets-'));
  temporaryRoots.push(root);
  const publicRoot = join(root, 'public');
  const buildRoot = join(root, 'dist-share');
  const files: Record<string, string> = {
    'favicon.svg': '<svg />',
    'project-progress.json': '{"mode":"synthetic"}',
    'worlds/synthetic-heightfield/manifest.json': '{"worldType":"synthetic"}',
    'worlds/synthetic-heightfield/heightfield.f32': 'fixture-binary',
    'worlds/synthetic-heightfield/pipeline-intermediate.json': 'private QA',
    'worlds/synthetic-terrain-demo/manifest.json': '{"worldType":"synthetic"}',
    'worlds/synthetic-terrain-demo/heightfield.f32': 'demo-binary',
    'worlds/.torquay-poc-001-2km.stage-recovery-test/manifest.json':
      'real stage',
    'worlds/.torquay-poc-001-2km.stage-recovery-test/roads-intermediate.json':
      'GIS intermediate',
    'worlds/torquay-poc-001/manifest.json': 'historical real package',
    'worlds/torquay-poc-001-2km/releases/abc/manifest.json':
      'current real release',
  };
  for (const [path, contents] of Object.entries(files)) {
    const target = join(publicRoot, path);
    mkdirSync(join(target, '..'), { recursive: true });
    writeFileSync(target, contents);
  }
  return { publicRoot, buildRoot };
}

afterEach(() => {
  for (const root of temporaryRoots.splice(0)) {
    // The temporary public fixture is scoped to this test and is disposable.
    rmSync(root, { recursive: true, force: true });
  }
});

describe('share public asset allowlist', () => {
  it('copies only the reviewed synthetic files and never recovery or GIS data', () => {
    const { publicRoot, buildRoot } = makePublicFixture();
    copySharePublicAssets(publicRoot, buildRoot);

    expect(
      readFileSync(
        join(buildRoot, 'worlds/synthetic-heightfield/manifest.json'),
        'utf8',
      ),
    ).toContain('synthetic');
    expect(
      readFileSync(
        join(buildRoot, 'worlds/synthetic-terrain-demo/heightfield.f32'),
        'utf8',
      ),
    ).toBe('demo-binary');
    expect(() =>
      readFileSync(
        join(
          buildRoot,
          'worlds/.torquay-poc-001-2km.stage-recovery-test/manifest.json',
        ),
      ),
    ).toThrow();
    expect(() =>
      readFileSync(
        join(
          buildRoot,
          'worlds/.torquay-poc-001-2km.stage-recovery-test/roads-intermediate.json',
        ),
      ),
    ).toThrow();
    expect(() =>
      readFileSync(
        join(
          buildRoot,
          'worlds/synthetic-heightfield/pipeline-intermediate.json',
        ),
      ),
    ).toThrow();
    expect(() =>
      readFileSync(join(buildRoot, 'worlds/torquay-poc-001/manifest.json')),
    ).toThrow();
    expect(() =>
      readFileSync(
        join(
          buildRoot,
          'worlds/torquay-poc-001-2km/releases/abc/manifest.json',
        ),
      ),
    ).toThrow();
  });
});
