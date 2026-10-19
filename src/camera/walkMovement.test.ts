import { describe, expect, it } from 'vitest';
import {
  advanceWalkAcquisition,
  advanceWalkPosition,
  DEFAULT_WALK_CONFIG,
  prepareWalkAcquisition,
} from './walkMovement';
import { boundedFrameSteps } from './movement';
import type { FlightBounds, Vec3Like } from './movement';
import { Euler, PerspectiveCamera } from 'three';
import { advanceCameraWalkPosition } from './walkMovement';

const bounds: FlightBounds = {
  minX: -5,
  maxX: 5,
  minY: -20,
  maxY: 30,
  minZ: -5,
  maxZ: 5,
};

const position: Vec3Like = { x: 0, y: 1.7, z: 0 };
const plane = (x: number, z: number): number => 0.4 * x - 0.2 * z - 3;

describe('advanceWalkPosition', () => {
  it('follows negative terrain and maintains 1.7 m clearance on slopes', () => {
    const step = advanceWalkPosition(
      position,
      0,
      { forward: 1, strafe: 0, boost: false },
      0.05,
      bounds,
      plane,
    );

    expect(step.validSample).toBe(true);
    expect(step.position.z).toBeCloseTo(-0.75, 10);
    expect(step.groundHeight).toBeCloseTo(plane(0, step.position.z), 10);
    expect(step.position.y - step.groundHeight!).toBeCloseTo(1.7, 10);
  });

  it('normalizes diagonal movement and applies the 41.25 m/s boost speed', () => {
    const diagonal = advanceWalkPosition(
      position,
      0,
      { forward: 1, strafe: 1, boost: false },
      0.05,
      bounds,
      () => -4,
    );
    expect(Math.hypot(diagonal.position.x, diagonal.position.z)).toBeCloseTo(
      0.75,
      10,
    );

    const boosted = advanceWalkPosition(
      position,
      0,
      { forward: 1, strafe: 0, boost: true },
      0.05,
      bounds,
      () => -4,
    );
    expect(position.z - boosted.position.z).toBeCloseTo(2.0625, 10);
    expect(DEFAULT_WALK_CONFIG.speedMetersPerSecond).toBe(15);
    expect(
      DEFAULT_WALK_CONFIG.speedMetersPerSecond *
        DEFAULT_WALK_CONFIG.boostMultiplier,
    ).toBeCloseTo(41.25, 10);
  });

  it('uses yaw rather than pitch for horizontal movement', () => {
    const yaw = Math.PI / 2;
    const east = advanceWalkPosition(
      position,
      yaw,
      { forward: 1, strafe: 0, boost: false },
      0.05,
      bounds,
      () => 2,
    );
    expect(east.position.x).toBeCloseTo(0.75, 10);
    expect(east.position.z).toBeCloseTo(0, 10);
  });

  it('clamps before sampling at exact bounds and holds the prior pose on invalid samples', () => {
    const sampled: Array<[number, number]> = [];
    const edge = advanceWalkPosition(
      { x: 4.9, y: 2, z: 0 },
      Math.PI / 2,
      { forward: 1, strafe: 0, boost: false },
      0.05,
      bounds,
      (x, z) => {
        sampled.push([x, z]);
        return -1;
      },
    );
    expect(edge.position.x).toBe(5);
    expect(sampled.at(-1)?.[0]).toBe(5);
    expect(edge.hitBoundary).toBe(true);

    const invalid = advanceWalkPosition(
      position,
      0,
      { forward: 1, strafe: 0, boost: false },
      0.05,
      bounds,
      () => null,
    );
    expect(invalid.validSample).toBe(false);
    expect(invalid.position).toEqual(position);
  });

  it('maintains the sampled clearance at all four world corners', () => {
    const corners = [
      { x: bounds.minX, z: bounds.minZ },
      { x: bounds.minX, z: bounds.maxZ },
      { x: bounds.maxX, z: bounds.minZ },
      { x: bounds.maxX, z: bounds.maxZ },
    ];
    for (const corner of corners) {
      const expectedGround = 0.1 * (corner.x - corner.z) - 2;
      const result = advanceWalkPosition(
        { ...corner, y: 0 },
        0,
        { forward: 0, strafe: 0, boost: false },
        0.05,
        bounds,
        (x, z) => 0.1 * (x - z) - 2,
      );
      expect(result.validSample).toBe(true);
      expect(result.groundHeight).toBe(expectedGround);
      expect(result.position.y - expectedGround).toBeCloseTo(1.7, 10);
    }
  });

  it('rejects malformed bounds, non-finite positions and out-of-bounds eye targets', () => {
    const malformedBounds = { ...bounds, minX: 6 };
    const malformed = advanceWalkPosition(
      position,
      0,
      { forward: 1, strafe: 0, boost: false },
      0.05,
      malformedBounds,
      () => 0,
    );
    expect(malformed.validSample).toBe(false);
    expect(malformed.position).toEqual(position);

    const invalidPosition = advanceWalkPosition(
      { ...position, x: Number.NaN },
      0,
      { forward: 1, strafe: 0, boost: false },
      0.05,
      bounds,
      () => 0,
    );
    expect(invalidPosition.validSample).toBe(false);

    const tooHigh = prepareWalkAcquisition(
      { x: 0, y: 30, z: 0 },
      bounds,
      () => 30,
    );
    expect(tooHigh.accepted).toBe(false);
    expect(tooHigh.reason).toBe('outside-y-bounds');
  });
});

describe('walking heading from camera orientation', () => {
  it.each([
    [-Math.PI / 2 + 1e-10, 30],
    [-Math.PI / 2, 30],
    [Math.PI / 2 - 1e-10, 30],
    [Math.PI / 2, 30],
    [-Math.PI / 2 + 1e-10, 45],
    [-Math.PI / 2, 45],
    [Math.PI / 2 - 1e-10, 45],
    [Math.PI / 2, 45],
  ] as const)(
    'keeps yaw at vertical pitch %s and heading %i degrees',
    (pitch, headingDegrees) => {
      const camera = new PerspectiveCamera();
      const heading = (headingDegrees * Math.PI) / 180;
      camera.quaternion.setFromEuler(new Euler(pitch, -heading, 0, 'YXZ'));

      const step = advanceCameraWalkPosition(
        camera,
        position,
        { forward: 1, strafe: 0, boost: false },
        0.05,
        bounds,
        () => -2,
      );

      expect(step.position.x).toBeCloseTo(0.75 * Math.sin(heading), 10);
      expect(step.position.z).toBeCloseTo(-0.75 * Math.cos(heading), 10);
    },
  );
});

describe('walk-mode acquisition and frame partitioning', () => {
  it('plans walk acquisition without changing position and rejects below-ground entry', () => {
    const start = { x: 1, y: 10, z: 2 };
    const target = prepareWalkAcquisition(start, bounds, (x, z) => plane(x, z));
    expect(target.accepted).toBe(true);
    expect(target.targetY).toBeCloseTo(plane(1, 2) + 1.7, 10);
    expect(start).toEqual({ x: 1, y: 10, z: 2 });

    const below = prepareWalkAcquisition(
      { x: 0, y: -4, z: 0 },
      bounds,
      () => -3,
    );
    expect(below.accepted).toBe(false);
    expect(below.reason).toBe('below-terrain');
    expect(
      prepareWalkAcquisition(position, bounds, () => Number.POSITIVE_INFINITY)
        .reason,
    ).toBe('invalid-sample');
    expect(
      prepareWalkAcquisition({ ...position, x: 6 }, bounds, () => 0).accepted,
    ).toBe(false);
  });

  it('approaches eye height monotonically at no more than 20 m/s and preserves XZ', () => {
    let current: Vec3Like = { x: 2, y: 12, z: -3 };
    const targetY = 2;
    const sequence: number[] = [];
    for (let index = 0; index < 4; index += 1) {
      const next = advanceWalkAcquisition(current, targetY, 0.05);
      expect(Math.abs(next.y - current.y)).toBeLessThanOrEqual(1 + 1e-10);
      expect(next.x).toBe(2);
      expect(next.z).toBe(-3);
      sequence.push(next.y);
      current = next;
    }
    expect(sequence).toEqual([11, 10, 9, 8]);

    const ascending = advanceWalkAcquisition({ x: -1, y: 0.5, z: 3 }, 2, 0.05);
    expect(ascending).toEqual({ x: -1, y: 1.5, z: 3 });
  });

  it.each([6, 30, 60, 144])(
    'produces equivalent one-second walking travel at %i Hz',
    (frequency) => {
      let current = { ...position };
      const broadBounds = { ...bounds, minZ: -20, maxZ: 20 };
      const frameDelta = 1 / frequency;
      for (let frame = 0; frame < frequency; frame += 1) {
        for (const step of boundedFrameSteps(frameDelta)) {
          current = advanceWalkPosition(
            current,
            0,
            { forward: 1, strafe: 0, boost: false },
            step,
            broadBounds,
            () => -2,
          ).position;
        }
      }
      expect(position.z - current.z).toBeCloseTo(15, 7);
      expect(current.y).toBeCloseTo(-0.3, 10);
    },
  );

  it('deliberately discards frame time beyond the 0.25-second budget', () => {
    const steps = boundedFrameSteps(1);
    expect(steps.reduce((sum, value) => sum + value, 0)).toBeCloseTo(0.25, 10);
    expect(Math.max(...steps)).toBeLessThanOrEqual(0.05);
  });
});
