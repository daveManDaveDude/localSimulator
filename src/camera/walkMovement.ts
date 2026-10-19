import type { FlightBounds, Vec3Like } from './movement';

export type TerrainSampler = (x: number, z: number) => number | null;

export interface WalkInput {
  forward: number;
  strafe: number;
  boost: boolean;
}

export interface WalkConfig {
  speedMetersPerSecond: number;
  boostMultiplier: number;
  eyeClearanceMeters: number;
}

export interface WalkStep {
  position: Vec3Like;
  hitBoundary: boolean;
  groundHeight: number | null;
  validSample: boolean;
}

export interface WalkAcquisition {
  accepted: boolean;
  targetY: number | null;
  groundHeight: number | null;
  reason?: 'invalid-sample' | 'below-terrain' | 'outside-y-bounds';
}

export const DEFAULT_WALK_CONFIG: WalkConfig = {
  speedMetersPerSecond: 15,
  boostMultiplier: 2.75,
  eyeClearanceMeters: 1.7,
};

const EPSILON = 1e-9;

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.max(minimum, Math.min(maximum, value));
}

function axis(value: number): number {
  return Number.isFinite(value) ? clamp(value, -1, 1) : 0;
}

function validBounds(bounds: Readonly<FlightBounds>): boolean {
  return (
    Number.isFinite(bounds.minX) &&
    Number.isFinite(bounds.maxX) &&
    Number.isFinite(bounds.minY) &&
    Number.isFinite(bounds.maxY) &&
    Number.isFinite(bounds.minZ) &&
    Number.isFinite(bounds.maxZ) &&
    bounds.minX <= bounds.maxX &&
    bounds.minY <= bounds.maxY &&
    bounds.minZ <= bounds.maxZ
  );
}

/**
 * Moves horizontally from yaw, clamps before terrain sampling, then places the
 * camera exactly at sampled terrain plus the configured eye clearance.
 */
export function advanceWalkPosition(
  position: Readonly<Vec3Like>,
  yawRadians: number,
  input: Readonly<WalkInput>,
  elapsedSeconds: number,
  bounds: Readonly<FlightBounds>,
  sampleHeight: TerrainSampler,
  config: Readonly<WalkConfig> = DEFAULT_WALK_CONFIG,
): WalkStep {
  const unchanged = { x: position.x, y: position.y, z: position.z };
  if (
    !validBounds(bounds) ||
    !Number.isFinite(position.x) ||
    !Number.isFinite(position.y) ||
    !Number.isFinite(position.z) ||
    !Number.isFinite(yawRadians) ||
    !Number.isFinite(elapsedSeconds) ||
    elapsedSeconds <= 0 ||
    !Number.isFinite(config.speedMetersPerSecond) ||
    config.speedMetersPerSecond <= 0 ||
    !Number.isFinite(config.boostMultiplier) ||
    config.boostMultiplier <= 0 ||
    !Number.isFinite(config.eyeClearanceMeters) ||
    config.eyeClearanceMeters <= 0
  ) {
    return {
      position: unchanged,
      hitBoundary: false,
      groundHeight: null,
      validSample: false,
    };
  }

  const forwardInput = axis(input.forward);
  const strafeInput = axis(input.strafe);
  const length = Math.hypot(forwardInput, strafeInput);
  const forward = length > EPSILON ? forwardInput / length : 0;
  const strafe = length > EPSILON ? strafeInput / length : 0;
  const distance =
    config.speedMetersPerSecond *
    (input.boost ? config.boostMultiplier : 1) *
    elapsedSeconds;
  const sin = Math.sin(yawRadians);
  const cos = Math.cos(yawRadians);
  const rawX = position.x + (sin * forward + cos * strafe) * distance;
  const rawZ = position.z + (-cos * forward + sin * strafe) * distance;
  const x = clamp(rawX, bounds.minX, bounds.maxX);
  const z = clamp(rawZ, bounds.minZ, bounds.maxZ);
  const groundHeight = sampleHeight(x, z);
  const nextY =
    groundHeight === null
      ? Number.NaN
      : groundHeight + config.eyeClearanceMeters;

  if (
    groundHeight === null ||
    !Number.isFinite(groundHeight) ||
    !Number.isFinite(nextY) ||
    nextY < bounds.minY ||
    nextY > bounds.maxY
  ) {
    return {
      position: unchanged,
      hitBoundary: false,
      groundHeight: Number.isFinite(groundHeight) ? groundHeight : null,
      validSample: false,
    };
  }

  return {
    position: { x, y: nextY, z },
    hitBoundary: Math.abs(rawX - x) > EPSILON || Math.abs(rawZ - z) > EPSILON,
    groundHeight,
    validSample: true,
  };
}

/** Validate walk entry without moving the camera or correcting its position. */
export function prepareWalkAcquisition(
  position: Readonly<Vec3Like>,
  bounds: Readonly<FlightBounds>,
  sampleHeight: TerrainSampler,
  eyeClearanceMeters = DEFAULT_WALK_CONFIG.eyeClearanceMeters,
): WalkAcquisition {
  if (
    !validBounds(bounds) ||
    !Number.isFinite(position.x) ||
    !Number.isFinite(position.y) ||
    !Number.isFinite(position.z) ||
    !Number.isFinite(eyeClearanceMeters) ||
    eyeClearanceMeters <= 0
  ) {
    return {
      accepted: false,
      targetY: null,
      groundHeight: null,
      reason: 'invalid-sample',
    };
  }

  const x = clamp(position.x, bounds.minX, bounds.maxX);
  const z = clamp(position.z, bounds.minZ, bounds.maxZ);
  if (x !== position.x || z !== position.z) {
    return {
      accepted: false,
      targetY: null,
      groundHeight: null,
      reason: 'invalid-sample',
    };
  }
  const groundHeight = sampleHeight(x, z);
  if (groundHeight === null || !Number.isFinite(groundHeight)) {
    return {
      accepted: false,
      targetY: null,
      groundHeight: null,
      reason: 'invalid-sample',
    };
  }
  if (position.y < groundHeight - 1e-6) {
    return {
      accepted: false,
      targetY: null,
      groundHeight,
      reason: 'below-terrain',
    };
  }
  const targetY = groundHeight + eyeClearanceMeters;
  if (
    !Number.isFinite(targetY) ||
    targetY < bounds.minY ||
    targetY > bounds.maxY
  ) {
    return {
      accepted: false,
      targetY: null,
      groundHeight,
      reason: 'outside-y-bounds',
    };
  }
  return { accepted: true, targetY, groundHeight };
}

/** Move vertically toward the acquisition target at no more than 20 m/s. */
export function advanceWalkAcquisition(
  position: Readonly<Vec3Like>,
  targetY: number,
  elapsedSeconds: number,
  maxVerticalSpeedMetersPerSecond = 20,
): Vec3Like {
  if (
    !Number.isFinite(position.y) ||
    !Number.isFinite(targetY) ||
    !Number.isFinite(elapsedSeconds) ||
    elapsedSeconds <= 0 ||
    !Number.isFinite(maxVerticalSpeedMetersPerSecond) ||
    maxVerticalSpeedMetersPerSecond <= 0
  ) {
    return { ...position };
  }
  const maxStep = maxVerticalSpeedMetersPerSecond * elapsedSeconds;
  const difference = targetY - position.y;
  const movement = clamp(difference, -maxStep, maxStep);
  return { x: position.x, y: position.y + movement, z: position.z };
}
