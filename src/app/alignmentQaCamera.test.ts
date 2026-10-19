import { PerspectiveCamera } from 'three';
import { describe, expect, it } from 'vitest';
import { installAlignmentQaCamera } from './alignmentQaCamera';

describe('alignment QA camera hook', () => {
  it('does not expose a camera setter outside development builds', () => {
    const camera = new PerspectiveCamera();
    const target = {} as Window;

    const dispose = installAlignmentQaCamera(target, camera, false);

    expect(target.__torquayAlignmentQa).toBeUndefined();
    dispose();
    expect(target.__torquayAlignmentQa).toBeUndefined();
  });

  it('positions the real camera and removes the development hook on cleanup', () => {
    const camera = new PerspectiveCamera();
    const target = {} as Window;
    const dispose = installAlignmentQaCamera(target, camera, true);

    target.__torquayAlignmentQa?.setPose({
      x: 12,
      y: 40,
      z: -34,
      bearingDegrees: 120,
      pitchDegrees: -25,
    });
    camera.updateMatrixWorld(true);
    const direction = camera.getWorldDirection(camera.position.clone());

    expect(camera.position.toArray()).toEqual([12, 40, -34]);
    expect(direction.x).toBeCloseTo(
      Math.sin((120 * Math.PI) / 180) * Math.cos((-25 * Math.PI) / 180),
    );
    expect(direction.y).toBeCloseTo(Math.sin((-25 * Math.PI) / 180));
    expect(target.__torquayAlignmentQa).toBeDefined();

    dispose();
    expect(target.__torquayAlignmentQa).toBeUndefined();
  });
});
