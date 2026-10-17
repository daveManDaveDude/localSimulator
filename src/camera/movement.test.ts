import { describe, expect, it } from 'vitest';
import {
  advanceFreeFlyPosition,
  copySpawnPosition,
  type FlightBounds,
  type FlightConfig,
  type FlightInput,
  type Vec3Like,
} from './movement';

const bounds: FlightBounds = {
  minX: -10,
  maxX: 10,
  minY: 1,
  maxY: 20,
  minZ: -10,
  maxZ: 10,
};

const config: FlightConfig = {
  speedMetersPerSecond: 10,
  boostMultiplier: 3,
  maxFrameStepSeconds: 0.1,
};

const start: Vec3Like = { x: 0, y: 5, z: 0 };
const north: Vec3Like = { x: 0, y: 0, z: -1 };
const forward: FlightInput = {
  forward: 1,
  strafe: 0,
  vertical: 0,
  boost: false,
};

describe('advanceFreeFlyPosition', () => {
  it('moves by elapsed time rather than by frame count', () => {
    const oneStep = advanceFreeFlyPosition(
      start,
      north,
      forward,
      0.1,
      bounds,
      config,
    );
    const firstHalf = advanceFreeFlyPosition(
      start,
      north,
      forward,
      0.05,
      bounds,
      config,
    );
    const secondHalf = advanceFreeFlyPosition(
      firstHalf.position,
      north,
      forward,
      0.05,
      bounds,
      config,
    );

    expect(oneStep.position.z).toBeCloseTo(secondHalf.position.z, 10);
    expect(oneStep.position.z).toBeCloseTo(-1, 10);
  });

  it('clamps long and negative frame steps', () => {
    const longStep = advanceFreeFlyPosition(
      start,
      north,
      forward,
      4,
      bounds,
      config,
    );
    const negativeStep = advanceFreeFlyPosition(
      start,
      north,
      forward,
      -1,
      bounds,
      config,
    );

    expect(longStep.position.z).toBeCloseTo(-1, 10);
    expect(negativeStep.position).toEqual(start);
  });

  it('normalizes combined forward and strafe input', () => {
    const diagonal = advanceFreeFlyPosition(
      start,
      north,
      { forward: 1, strafe: 1, vertical: 0, boost: false },
      0.1,
      bounds,
      config,
    );

    expect(Math.hypot(diagonal.position.x, diagonal.position.z)).toBeCloseTo(
      1,
      10,
    );
    expect(diagonal.position.x).toBeCloseTo(Math.SQRT1_2, 10);
    expect(diagonal.position.z).toBeCloseTo(-Math.SQRT1_2, 10);
  });

  it('follows the full camera look direction when flying forward', () => {
    const pitchedForward = advanceFreeFlyPosition(
      start,
      { x: 0, y: Math.SQRT1_2, z: -Math.SQRT1_2 },
      forward,
      0.1,
      bounds,
      config,
    );

    expect(pitchedForward.position.y).toBeCloseTo(5 + Math.SQRT1_2, 10);
    expect(pitchedForward.position.z).toBeCloseTo(-Math.SQRT1_2, 10);
  });

  it('applies the configured speed boost', () => {
    const boosted = advanceFreeFlyPosition(
      start,
      north,
      { ...forward, boost: true },
      0.1,
      bounds,
      config,
    );

    expect(boosted.position.z).toBeCloseTo(-3, 10);
  });

  it('moves vertically in world Y without needing a camera pitch', () => {
    const up = advanceFreeFlyPosition(
      start,
      north,
      { forward: 0, strafe: 0, vertical: 1, boost: false },
      0.1,
      bounds,
      config,
    );
    const down = advanceFreeFlyPosition(
      start,
      north,
      { forward: 0, strafe: 0, vertical: -1, boost: false },
      0.1,
      bounds,
      config,
    );

    expect(up.position.y).toBeCloseTo(6, 10);
    expect(down.position.y).toBeCloseTo(4, 10);
  });

  it('clamps positions at the finite world bounds and reports contact', () => {
    const edge = advanceFreeFlyPosition(
      { x: 9.8, y: 5, z: 0 },
      north,
      { forward: 0, strafe: 1, vertical: 0, boost: false },
      0.1,
      bounds,
      config,
    );

    expect(edge.position.x).toBe(10);
    expect(edge.hitBoundary).toBe(true);
  });

  it('copies the spawn position for a reset without sharing its object', () => {
    const spawn: Vec3Like = { x: 1, y: 8, z: 14 };
    const resetPosition = copySpawnPosition(spawn);

    expect(resetPosition).toEqual(spawn);
    expect(resetPosition).not.toBe(spawn);
  });
});
