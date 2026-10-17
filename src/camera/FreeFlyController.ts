import { Vector3, type Camera } from 'three';
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js';
import {
  advanceFreeFlyPosition,
  copySpawnPosition,
  DEFAULT_FLIGHT_CONFIG,
  type FlightBounds,
  type Vec3Like,
} from './movement';

export interface FreeFlyControllerCallbacks {
  onPointerLockChange: (locked: boolean) => void;
  onBoundaryChange: (atBoundary: boolean) => void;
  onLockError: (message: string) => void;
  onLockRequest: () => void;
  onReset: () => void;
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

export class FreeFlyController {
  private readonly controls: PointerLockControls;
  private readonly camera: Camera;
  private readonly bounds: FlightBounds;
  private readonly callbacks: FreeFlyControllerCallbacks;
  private readonly spawnPosition: Vec3Like;
  private readonly spawnOrientation: Camera['quaternion'];
  private readonly lookDirection = new Vector3();
  private readonly keys = new Set<string>();
  private lockErrorTimer: number | undefined;
  private atBoundary = false;
  private disposed = false;

  constructor(
    camera: Camera,
    domElement: HTMLCanvasElement,
    spawnPosition: Readonly<Vec3Like>,
    bounds: FlightBounds,
    callbacks: FreeFlyControllerCallbacks,
  ) {
    this.camera = camera;
    this.bounds = bounds;
    this.callbacks = callbacks;
    this.spawnPosition = copySpawnPosition(spawnPosition);
    this.spawnOrientation = camera.quaternion.clone();
    this.controls = new PointerLockControls(camera, domElement);
    this.controls.pointerSpeed = 0.72;
    this.controls.addEventListener('lock', this.handleLock);
    this.controls.addEventListener('unlock', this.handleUnlock);

    window.addEventListener('keydown', this.handleKeyDown);
    window.addEventListener('keyup', this.handleKeyUp);
    window.addEventListener('blur', this.clearKeys);
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
    document.addEventListener('pointerlockerror', this.handlePointerLockError);
  }

  get isLocked(): boolean {
    return this.controls.isLocked;
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
    return (
      DEFAULT_FLIGHT_CONFIG.speedMetersPerSecond *
      (this.isBoosting ? DEFAULT_FLIGHT_CONFIG.boostMultiplier : 1)
    );
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

  update(elapsedSeconds: number): void {
    if (!this.controls.isLocked) {
      return;
    }

    this.controls.getDirection(this.lookDirection);
    const result = advanceFreeFlyPosition(
      this.camera.position,
      this.lookDirection,
      {
        forward: Number(this.keys.has('KeyW')) - Number(this.keys.has('KeyS')),
        strafe: Number(this.keys.has('KeyD')) - Number(this.keys.has('KeyA')),
        vertical:
          Number(this.keys.has('Space')) -
          Number(this.keys.has('ControlLeft') || this.keys.has('ControlRight')),
        boost: this.keys.has('ShiftLeft') || this.keys.has('ShiftRight'),
      },
      elapsedSeconds,
      this.bounds,
      DEFAULT_FLIGHT_CONFIG,
    );

    this.camera.position.set(
      result.position.x,
      result.position.y,
      result.position.z,
    );

    if (result.hitBoundary !== this.atBoundary) {
      this.atBoundary = result.hitBoundary;
      this.callbacks.onBoundaryChange(this.atBoundary);
    }
  }

  reset(): void {
    this.clearKeys();
    this.camera.position.set(
      this.spawnPosition.x,
      this.spawnPosition.y,
      this.spawnPosition.z,
    );
    this.camera.quaternion.copy(this.spawnOrientation);
    this.setAtBoundary(false);
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
    window.removeEventListener('blur', this.clearKeys);
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
      // Make Escape explicit app behavior as well as the browser's native
      // pointer-lock release gesture. This keeps the advertised control
      // reliable in browsers that deliver Escape to the page first.
      this.controls.unlock();
      return;
    }

    if (event.code === 'KeyR' && !event.repeat) {
      event.preventDefault();
      this.reset();
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
    if (document.hidden) {
      this.clearKeys();
    }
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

  private setAtBoundary(atBoundary: boolean): void {
    if (atBoundary === this.atBoundary) {
      return;
    }

    this.atBoundary = atBoundary;
    this.callbacks.onBoundaryChange(atBoundary);
  }

  private clearLockErrorTimer(): void {
    if (this.lockErrorTimer !== undefined) {
      window.clearTimeout(this.lockErrorTimer);
      this.lockErrorTimer = undefined;
    }
  }
}
