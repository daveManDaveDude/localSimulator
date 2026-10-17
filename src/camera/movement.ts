export interface Vec3Like {
  x: number;
  y: number;
  z: number;
}

export interface FlightInput {
  forward: number;
  strafe: number;
  vertical: number;
  boost: boolean;
}

export interface FlightBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
  minZ: number;
  maxZ: number;
}

export interface FlightConfig {
  speedMetersPerSecond: number;
  boostMultiplier: number;
  maxFrameStepSeconds: number;
}

export interface FlightStep {
  position: Vec3Like;
  hitBoundary: boolean;
  distanceMeters: number;
}

export const DEFAULT_FLIGHT_CONFIG: FlightConfig = {
  speedMetersPerSecond: 7.5,
  boostMultiplier: 2.75,
  maxFrameStepSeconds: 0.1,
};

const EPSILON = 1e-9;

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.max(minimum, Math.min(maximum, value));
}

function finiteAxis(value: number): number {
  return Number.isFinite(value) ? clamp(value, -1, 1) : 0;
}

function normalized(vector: Vec3Like, fallback: Vec3Like): Vec3Like {
  const length = Math.hypot(vector.x, vector.y, vector.z);

  if (length < EPSILON) {
    return { ...fallback };
  }

  return {
    x: vector.x / length,
    y: vector.y / length,
    z: vector.z / length,
  };
}

/**
 * Advances a free-fly position in metre-based world coordinates.
 * Forward follows the complete camera look vector; strafing stays level.
 */
export function advanceFreeFlyPosition(
  position: Readonly<Vec3Like>,
  lookDirection: Readonly<Vec3Like>,
  input: Readonly<FlightInput>,
  elapsedSeconds: number,
  bounds: Readonly<FlightBounds>,
  config: Readonly<FlightConfig> = DEFAULT_FLIGHT_CONFIG,
): FlightStep {
  const forward = normalized(lookDirection, { x: 0, y: 0, z: -1 });
  const right = normalized(
    { x: -forward.z, y: 0, z: forward.x },
    { x: 1, y: 0, z: 0 },
  );

  const forwardInput = finiteAxis(input.forward);
  const strafeInput = finiteAxis(input.strafe);
  const verticalInput = finiteAxis(input.vertical);
  const direction = normalized(
    {
      x: forward.x * forwardInput + right.x * strafeInput,
      y: forward.y * forwardInput + verticalInput,
      z: forward.z * forwardInput + right.z * strafeInput,
    },
    { x: 0, y: 0, z: 0 },
  );

  const elapsed = Number.isFinite(elapsedSeconds)
    ? Math.max(0, elapsedSeconds)
    : 0;
  const frameStep = Math.min(elapsed, config.maxFrameStepSeconds);
  const speed =
    config.speedMetersPerSecond * (input.boost ? config.boostMultiplier : 1);
  const distanceMeters = speed * frameStep;
  const rawPosition = {
    x: position.x + direction.x * distanceMeters,
    y: position.y + direction.y * distanceMeters,
    z: position.z + direction.z * distanceMeters,
  };
  const nextPosition = {
    x: clamp(rawPosition.x, bounds.minX, bounds.maxX),
    y: clamp(rawPosition.y, bounds.minY, bounds.maxY),
    z: clamp(rawPosition.z, bounds.minZ, bounds.maxZ),
  };

  return {
    position: nextPosition,
    hitBoundary:
      Math.abs(rawPosition.x - nextPosition.x) > EPSILON ||
      Math.abs(rawPosition.y - nextPosition.y) > EPSILON ||
      Math.abs(rawPosition.z - nextPosition.z) > EPSILON,
    distanceMeters,
  };
}

/** Returns a fresh copy for a controller's exact spawn-position reset. */
export function copySpawnPosition(spawnPosition: Readonly<Vec3Like>): Vec3Like {
  return { x: spawnPosition.x, y: spawnPosition.y, z: spawnPosition.z };
}
