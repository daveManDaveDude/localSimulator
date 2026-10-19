import { Vector3, type Camera } from 'three';
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js';
import {
  advanceFreeFlyPosition,
  boundedFrameSteps,
  copySpawnPosition,
  DEFAULT_FLIGHT_CONFIG,
  type FlightBounds,
  type Vec3Like,
} from './movement';
import {
  advanceCameraWalkPosition,
  advanceWalkAcquisition,
  DEFAULT_WALK_CONFIG,
  prepareWalkAcquisition,
  type TerrainSampler,
} from './walkMovement';
import { NavigationLifecycle } from './navigationLifecycle';

export type NavigationMode = 'fly' | 'entering-walk' | 'walk';

export interface FreeFlyControllerCallbacks {
  onPointerLockChange: (locked: boolean) => void;
  onBoundaryChange: (atBoundary: boolean) => void;
  onLockError: (message: string) => void;
  onLockRequest: () => void;
  onReset: () => void;
  onNavigationModeChange: (mode: NavigationMode) => void;
  onNavigationFeedback: (message: string) => void;
}

const MOVEMENT_KEYS = new Set([
  'KeyW',
  'KeyA',
  'KeyS',
  'KeyD',
  'Space',
  'ControlLeft',
  'ControlRight',
  'ShiftLeft',
  'ShiftRight',
]);

const ACQUISITION_SPEED_METERS_PER_SECOND = 20;
const ACQUISITION_EPSILON_METERS = 0.001;

export class FreeFlyController {
  private readonly controls: PointerLockControls;
  private readonly camera: Camera;
  private readonly bounds: FlightBounds;
  private readonly callbacks: FreeFlyControllerCallbacks;
  private readonly spawnPosition: Vec3Like;
  private readonly spawnOrientation: Camera['quaternion'];
  private readonly sampleHeight: TerrainSampler;
  private readonly lookDirection = new Vector3();
  private readonly keys = new Set<string>();
  private readonly lifecycle = new NavigationLifecycle(
    window.document.hasFocus(),
    !document.hidden,
  );
  private lockErrorTimer: number | undefined;
  private atBoundary = false;
  private navigationMode: NavigationMode = 'fly';
  private acquisitionTargetY: number | null = null;
  private lastInvalidSampleFeedback = false;
  private disposed = false;

  constructor(
    camera: Camera,
    domElement: HTMLCanvasElement,
    spawnPosition: Readonly<Vec3Like>,
    bounds: FlightBounds,
    sampleHeight: TerrainSampler,
    callbacks: FreeFlyControllerCallbacks,
  ) {
    this.camera = camera;
    this.bounds = bounds;
    this.sampleHeight = sampleHeight;
    this.callbacks = callbacks;
    this.spawnPosition = copySpawnPosition(spawnPosition);
    this.spawnOrientation = camera.quaternion.clone();
    this.controls = new PointerLockControls(camera, domElement);
    this.controls.pointerSpeed = 0.72;
    this.controls.addEventListener('lock', this.handleLock);
    this.controls.addEventListener('unlock', this.handleUnlock);

    window.addEventListener('keydown', this.handleKeyDown);
    window.addEventListener('keyup', this.handleKeyUp);
    window.addEventListener('blur', this.handleWindowBlur);
    window.addEventListener('focus', this.handleWindowFocus);
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
    document.addEventListener('pointerlockerror', this.handlePointerLockError);
  }

  get isLocked(): boolean {
    return this.controls.isLocked;
  }

  get isNavigationSuspended(): boolean {
    return this.lifecycle.isSuspended;
  }

  get mode(): NavigationMode {
    return this.navigationMode;
  }

  get isAtBoundary(): boolean {
    return this.atBoundary;
  }

  get isBoosting(): boolean {
    return (
      this.controls.isLocked &&
      (this.keys.has('ShiftLeft') || this.keys.has('ShiftRight'))
    );
  }

  get speedMetersPerSecond(): number {
    const speed =
      this.navigationMode === 'fly'
        ? DEFAULT_FLIGHT_CONFIG.speedMetersPerSecond
        : DEFAULT_WALK_CONFIG.speedMetersPerSecond;
    return speed * (this.isBoosting ? DEFAULT_WALK_CONFIG.boostMultiplier : 1);
  }

  get groundHeight(): number | null {
    const height = this.sampleHeight(
      this.camera.position.x,
      this.camera.position.z,
    );
    return height !== null && Number.isFinite(height) ? height : null;
  }

  get eyeClearanceMeters(): number | null {
    const ground = this.groundHeight;
    return ground === null ? null : this.camera.position.y - ground;
  }

  get acquisitionRemainingMeters(): number | null {
    if (
      this.navigationMode !== 'entering-walk' ||
      this.acquisitionTargetY === null
    ) {
      return null;
    }
    return this.acquisitionTargetY - this.camera.position.y;
  }

  requestLock(): void {
    if (this.disposed || this.controls.isLocked) {
      return;
    }

    if (typeof this.controls.domElement?.requestPointerLock !== 'function') {
      this.callbacks.onLockError(
        'This browser does not support pointer lock. The scene is still available to view.',
      );
      return;
    }

    this.callbacks.onLockRequest();

    try {
      // PointerLockControls.lock() discards the Promise returned by newer
      // Pointer Lock APIs. Call the same browser API directly so a denied
      // request is handled here; PointerLockControls still owns the document
      // listeners that update its lock state and camera orientation.
      const lockRequest = this.controls.domElement.requestPointerLock({
        unadjustedMovement: false,
      });
      void Promise.resolve(lockRequest).catch(this.handlePointerLockError);

      this.clearLockErrorTimer();
      this.lockErrorTimer = window.setTimeout(() => {
        this.lockErrorTimer = undefined;
        if (!this.controls.isLocked) {
          this.callbacks.onLockError(
            'Pointer lock was blocked. Click Try again to request mouse look.',
          );
        }
      }, 1200);
    } catch {
      this.handlePointerLockError();
    }
  }

  toggleNavigationMode(): void {
    if (this.disposed) return;
    this.clearKeys();

    if (this.navigationMode === 'walk') {
      this.acquisitionTargetY = null;
      this.setNavigationMode('fly');
      this.callbacks.onNavigationFeedback(
        'Fly mode enabled. Position and view were preserved.',
      );
      return;
    }

    if (this.navigationMode === 'entering-walk') {
      this.acquisitionTargetY = null;
      this.setNavigationMode('fly');
      this.callbacks.onNavigationFeedback(
        'Walk acquisition cancelled. Current position and view were preserved.',
      );
      return;
    }

    const acquisition = prepareWalkAcquisition(
      this.camera.position,
      this.bounds,
      this.sampleHeight,
      DEFAULT_WALK_CONFIG.eyeClearanceMeters,
    );
    if (!acquisition.accepted || acquisition.targetY === null) {
      const message =
        acquisition.reason === 'below-terrain'
          ? 'Cannot enter walk mode below the sampled terrain. Fly above the ground first.'
          : acquisition.reason === 'outside-y-bounds'
            ? 'Cannot enter walk mode because the eye-height target is outside the world bounds.'
            : 'Cannot enter walk mode because this position has no valid terrain sample.';
      this.callbacks.onNavigationFeedback(message);
      return;
    }

    this.acquisitionTargetY = acquisition.targetY;
    this.lastInvalidSampleFeedback = false;
    if (
      Math.abs(this.camera.position.y - acquisition.targetY) <=
      ACQUISITION_EPSILON_METERS
    ) {
      this.camera.position.y = acquisition.targetY;
      this.acquisitionTargetY = null;
      this.setNavigationMode('walk');
      this.callbacks.onNavigationFeedback(
        'Walk mode enabled · 1.70 m eye clearance.',
      );
      return;
    }

    this.setNavigationMode('entering-walk');
    this.callbacks.onNavigationFeedback(
      'Entering walk mode. Moving vertically to 1.70 m above the sampled terrain.',
    );
  }

  update(elapsedSeconds: number): void {
    if (
      !this.controls.isLocked ||
      this.disposed ||
      this.lifecycle.shouldSkipUpdate()
    ) {
      return;
    }

    const steps = boundedFrameSteps(elapsedSeconds, DEFAULT_FLIGHT_CONFIG);
    for (const step of steps) {
      if (this.navigationMode === 'entering-walk') {
        this.updateWalkAcquisition(step);
      } else if (this.navigationMode === 'walk') {
        this.updateWalk(step);
      } else {
        this.updateFly(step);
      }
    }
  }

  reset(): void {
    this.clearKeys();
    if (this.navigationMode === 'walk') {
      const groundHeight = this.sampleHeight(
        this.spawnPosition.x,
        this.spawnPosition.z,
      );
      const targetY =
        groundHeight === null
          ? Number.NaN
          : groundHeight + DEFAULT_WALK_CONFIG.eyeClearanceMeters;
      if (
        groundHeight === null ||
        !Number.isFinite(groundHeight) ||
        !Number.isFinite(targetY) ||
        targetY < this.bounds.minY ||
        targetY > this.bounds.maxY
      ) {
        this.callbacks.onNavigationFeedback(
          'Walk reset was not applied because the spawn has no valid terrain eye-height sample.',
        );
        return;
      }
      this.camera.position.set(
        this.spawnPosition.x,
        targetY,
        this.spawnPosition.z,
      );
    } else {
      this.camera.position.set(
        this.spawnPosition.x,
        this.spawnPosition.y,
        this.spawnPosition.z,
      );
      if (this.navigationMode === 'entering-walk') {
        this.acquisitionTargetY = null;
        this.setNavigationMode('fly');
      }
    }
    this.camera.quaternion.copy(this.spawnOrientation);
    this.setAtBoundary(false);
    this.lastInvalidSampleFeedback = false;
    this.callbacks.onReset();
  }

  dispose(): void {
    if (this.disposed) {
      return;
    }

    this.disposed = true;
    this.clearLockErrorTimer();
    if (this.controls.isLocked) {
      this.controls.unlock();
    }

    this.controls.removeEventListener('lock', this.handleLock);
    this.controls.removeEventListener('unlock', this.handleUnlock);
    this.controls.dispose();
    window.removeEventListener('keydown', this.handleKeyDown);
    window.removeEventListener('keyup', this.handleKeyUp);
    window.removeEventListener('blur', this.handleWindowBlur);
    window.removeEventListener('focus', this.handleWindowFocus);
    document.removeEventListener(
      'visibilitychange',
      this.handleVisibilityChange,
    );
    document.removeEventListener(
      'pointerlockerror',
      this.handlePointerLockError,
    );
    this.clearKeys();
  }

  private updateFly(elapsedSeconds: number): void {
    this.controls.getDirection(this.lookDirection);
    const result = advanceFreeFlyPosition(
      this.camera.position,
      this.lookDirection,
      this.readFlightInput(),
      elapsedSeconds,
      this.bounds,
      DEFAULT_FLIGHT_CONFIG,
    );
    this.camera.position.set(
      result.position.x,
      result.position.y,
      result.position.z,
    );
    this.setAtBoundary(result.hitBoundary);
  }

  private updateWalk(elapsedSeconds: number): void {
    const result = advanceCameraWalkPosition(
      this.camera,
      this.camera.position,
      {
        forward: Number(this.keys.has('KeyW')) - Number(this.keys.has('KeyS')),
        strafe: Number(this.keys.has('KeyD')) - Number(this.keys.has('KeyA')),
        boost: this.keys.has('ShiftLeft') || this.keys.has('ShiftRight'),
      },
      elapsedSeconds,
      this.bounds,
      this.sampleHeight,
      DEFAULT_WALK_CONFIG,
    );

    if (!result.validSample) {
      this.reportInvalidWalkSample();
      return;
    }
    this.lastInvalidSampleFeedback = false;
    this.camera.position.set(
      result.position.x,
      result.position.y,
      result.position.z,
    );
    this.setAtBoundary(result.hitBoundary);
  }

  private updateWalkAcquisition(elapsedSeconds: number): void {
    const targetY = this.acquisitionTargetY;
    if (targetY === null) {
      this.setNavigationMode('fly');
      return;
    }
    const next = advanceWalkAcquisition(
      this.camera.position,
      targetY,
      elapsedSeconds,
      ACQUISITION_SPEED_METERS_PER_SECOND,
    );
    if (
      !Number.isFinite(next.y) ||
      next.y < this.bounds.minY ||
      next.y > this.bounds.maxY
    ) {
      this.reportInvalidWalkSample();
      this.acquisitionTargetY = null;
      this.setNavigationMode('fly');
      return;
    }
    this.camera.position.y = next.y;
    if (Math.abs(targetY - next.y) <= ACQUISITION_EPSILON_METERS) {
      this.camera.position.y = targetY;
      this.acquisitionTargetY = null;
      this.setNavigationMode('walk');
      this.callbacks.onNavigationFeedback(
        'Walk mode enabled · 1.70 m eye clearance.',
      );
    }
  }

  private readFlightInput() {
    return {
      forward: Number(this.keys.has('KeyW')) - Number(this.keys.has('KeyS')),
      strafe: Number(this.keys.has('KeyD')) - Number(this.keys.has('KeyA')),
      vertical:
        Number(this.keys.has('Space')) -
        Number(this.keys.has('ControlLeft') || this.keys.has('ControlRight')),
      boost: this.keys.has('ShiftLeft') || this.keys.has('ShiftRight'),
    };
  }

  private readonly handleLock = (): void => {
    this.clearLockErrorTimer();
    this.clearKeys();
    this.callbacks.onPointerLockChange(true);
  };

  private readonly handleUnlock = (): void => {
    this.clearLockErrorTimer();
    this.clearKeys();
    this.setAtBoundary(false);
    this.callbacks.onPointerLockChange(false);
  };

  private readonly handleKeyDown = (event: KeyboardEvent): void => {
    if (event.code === 'Escape' && this.controls.isLocked) {
      this.controls.unlock();
      return;
    }

    if (event.code === 'KeyR' && !event.repeat) {
      event.preventDefault();
      this.reset();
      return;
    }

    if (event.code === 'KeyF' && this.controls.isLocked && !event.repeat) {
      event.preventDefault();
      this.toggleNavigationMode();
      return;
    }

    if (!this.controls.isLocked || !MOVEMENT_KEYS.has(event.code)) {
      return;
    }

    if (event.code === 'Space' || event.code.startsWith('Control')) {
      event.preventDefault();
    }
    this.keys.add(event.code);
  };

  private readonly handleKeyUp = (event: KeyboardEvent): void => {
    this.keys.delete(event.code);
  };

  private readonly handleVisibilityChange = (): void => {
    this.lifecycle.setDocumentVisible(!document.hidden);
    this.clearKeys();
  };

  private readonly handleWindowBlur = (): void => {
    this.lifecycle.setWindowFocused(false);
    this.clearKeys();
  };

  private readonly handleWindowFocus = (): void => {
    this.lifecycle.setWindowFocused(true);
    this.clearKeys();
  };

  private readonly handlePointerLockError = (): void => {
    this.clearLockErrorTimer();
    this.clearKeys();
    this.callbacks.onLockError(
      'The browser denied pointer lock. Click Try again to request mouse look.',
    );
  };

  private readonly clearKeys = (): void => {
    this.keys.clear();
  };

  private setNavigationMode(mode: NavigationMode): void {
    if (this.navigationMode === mode) return;
    this.navigationMode = mode;
    this.callbacks.onNavigationModeChange(mode);
  }

  private setAtBoundary(atBoundary: boolean): void {
    if (atBoundary === this.atBoundary) return;
    this.atBoundary = atBoundary;
    this.callbacks.onBoundaryChange(atBoundary);
  }

  private reportInvalidWalkSample(): void {
    if (this.lastInvalidSampleFeedback) return;
    this.lastInvalidSampleFeedback = true;
    this.callbacks.onNavigationFeedback(
      'Walking paused: the current bounds do not have a finite terrain sample. The last valid pose was kept.',
    );
  }

  private clearLockErrorTimer(): void {
    if (this.lockErrorTimer !== undefined) {
      window.clearTimeout(this.lockErrorTimer);
      this.lockErrorTimer = undefined;
    }
  }
}
