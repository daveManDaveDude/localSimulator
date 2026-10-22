import { describe, expect, it, vi } from 'vitest';
import type { LoadedRealWorld } from '../../src/app/worldLoader';
import { createRealManifest } from '../geo/fixtures';
import { createHeightfieldWorld } from '../../src/scene/createHeightfieldWorld';
import { disposeSceneResources } from '../../src/scene/disposeSceneResources';

vi.mock('../../src/scene/debugHelpers', async () => {
  const { Group: SceneGroup } = await import('three');
  return {
    createDrapedGrid: () => new SceneGroup(),
    createNorthArrow: () => new SceneGroup(),
    createWorldAxes: () => [new SceneGroup()],
  };
});

function current2kmFixture(): LoadedRealWorld {
  const manifest = createRealManifest();
  manifest.sceneProfile = 'current_2km';
  manifest.extentM = { width: 4, depth: 4 };
  manifest.heightfield.columns = 3;
  manifest.heightfield.rows = 3;
  manifest.heightfield.spacingM = 2;
  manifest.heightfield.byteLength = 36;
  return {
    manifest,
    heights: new Float32Array([0, 1, 2, 3, 4, 5, 6, 7, 8]),
    manifestSha256: 'a'.repeat(64),
  };
}

describe('createHeightfieldWorld display terrain', () => {
  it('uses a derivative for the shared display grid without mutating source bytes', () => {
    const loaded = current2kmFixture();
    const original = loaded.heights.slice();
    const derivative = new Float32Array([8, 7, 6, 5, 4, 3, 2, 1, 0]);
    const world = createHeightfieldWorld(loaded, derivative);

    try {
      expect(world.grid.heights).toEqual(derivative);
      expect(loaded.heights).toEqual(original);
      expect(world.grid.sampleHeight(0, 0)).toBe(4);
      expect(world.terrain.geometry.getAttribute('position').getY(4)).toBe(4);
      expect(world.terrain.geometry.getAttribute('position').count).toBe(9);
    } finally {
      disposeSceneResources(world.group);
    }
  });

  it('rejects derivatives for historical profiles', () => {
    const loaded = current2kmFixture();
    loaded.manifest.sceneProfile = 'historical_1km';

    expect(() => createHeightfieldWorld(loaded, new Float32Array(9))).toThrow(
      'display terrain derivatives are supported only for current_2km',
    );
  });
});
