import {
  BufferGeometry,
  Material,
  PerspectiveCamera,
  Scene,
  Texture,
  Timer,
  Vector3,
  WebGLRenderer,
} from 'three';
import { FreeFlyController } from '../camera/FreeFlyController';
import { createScene } from '../scene/createScene';
import { createSyntheticWorld } from '../scene/createSyntheticWorld';

export interface AppHandle {
  dispose: () => void;
}

export function createApp(container: HTMLElement): AppHandle {
  container.innerHTML = `
      <main class="viewer-shell" data-renderer-ready="false">
      <canvas class="viewer-canvas" aria-label="Synthetic free-fly world"></canvas>
      <div class="viewer-ui">
        <div class="viewer-topline">
          <p class="synthetic-badge"><span aria-hidden="true"></span>SYNTHETIC · NOT GEOGRAPHIC DATA</p>
          <p class="flight-status" role="status" aria-live="polite" data-testid="flight-status-message">Click Start to capture the pointer. Esc releases it.</p>
        </div>
        <section class="debug-hud" aria-label="Flight telemetry" data-testid="debug-hud">
          <div class="debug-hud-heading">
            <h2>LIVE TELEMETRY</h2>
            <div class="debug-actions" aria-label="Viewer actions">
              <button type="button" data-testid="reset-button">Reset view</button>
              <button type="button" data-testid="help-toggle" aria-controls="controls-help" aria-expanded="false">Show controls</button>
            </div>
          </div>
          <dl>
            <div><dt>World</dt><dd data-testid="world-type">SYNTHETIC · FICTIONAL FIXTURE</dd></div>
            <div><dt>Flight</dt><dd><output data-testid="flight-state" aria-live="off" data-locked="false">POINTER UNLOCKED · FREE FLY</output></dd></div>
            <div><dt>Camera position</dt><dd><output data-testid="camera-position" aria-live="off" aria-label="Camera position in metres" data-x="0" data-y="0" data-z="0">X 0.0 · Y 0.0 · Z 0.0 m</output></dd></div>
            <div><dt>Bearing / pitch</dt><dd><output data-testid="camera-orientation" aria-live="off" aria-label="Camera bearing and pitch" data-bearing-degrees="0" data-pitch-degrees="0">Bearing 000.0° · Pitch 0.0°</output></dd></div>
            <div><dt>Speed</dt><dd><output data-testid="flight-speed" aria-live="off" aria-label="Flight speed in metres per second" data-meters-per-second="0" data-boosting="false">0.0 m/s</output></dd></div>
            <div><dt>FPS</dt><dd><output data-testid="frames-per-second" aria-live="off" data-fps="0">Waiting for first frame</output></dd></div>
            <div><dt>Bounds</dt><dd><output data-testid="boundary-state" aria-live="off" data-at-boundary="false">WITHIN DEMO BOUNDS</output></dd></div>
          </dl>
        </section>
        <aside id="controls-help" class="controls-help" aria-labelledby="controls-title" data-testid="controls-help" hidden>
          <h2 id="controls-title">IN-FLIGHT CONTROLS</h2>
          <p><kbd>Mouse</kbd><span>Look around</span></p>
          <p><kbd>W</kbd><kbd>S</kbd><span>Fly along the camera direction</span></p>
          <p><kbd>A</kbd><kbd>D</kbd><span>Strafe left / right</span></p>
          <p><kbd>Space</kbd><kbd>Ctrl</kbd><span>Rise / descend</span></p>
          <p><kbd>Shift</kbd><span>Move faster</span><kbd>R</kbd><span>Reset view</span><kbd>Esc</kbd><span>Release pointer</span></p>
        </aside>
        <section class="start-card" aria-labelledby="page-title">
          <p class="eyebrow">LOCAL BROWSER PROOF OF CONCEPT</p>
          <h1 id="page-title">Torquay <span>Virtual World</span></h1>
          <p class="welcome-copy">Explore a small, fictional test landscape. Its slopes and blocks are generated geometry; no Torquay measurements or map data are used.</p>
          <button class="start-button" type="button">Start exploring</button>
          <div class="control-hints" aria-label="Free-flight controls">
            <p><kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd><span>Fly in the camera direction</span></p>
            <p><kbd>Space</kbd><kbd>Ctrl</kbd><span>Rise / descend</span></p>
            <p><kbd>Shift</kbd><span>Move faster</span><kbd>R</kbd><span>Reset view</span></p>
          </div>
          <p class="unlock-hint">Mouse looks around · press <kbd>Esc</kbd> to release the pointer</p>
        </section>
        <p class="corner-note">WORLD UNITS: METRES · NORTH: −Z</p>
      </div>
    </main>
  `;

  const shell = container.querySelector<HTMLElement>('.viewer-shell');
  const canvas = container.querySelector<HTMLCanvasElement>('.viewer-canvas');
  const startButton =
    container.querySelector<HTMLButtonElement>('.start-button');
  const status = container.querySelector<HTMLElement>('.flight-status');
  const controlsHelp = container.querySelector<HTMLElement>('.controls-help');
  const helpToggle = container.querySelector<HTMLButtonElement>(
    '[data-testid="help-toggle"]',
  );
  const resetButton = container.querySelector<HTMLButtonElement>(
    '[data-testid="reset-button"]',
  );
  const fpsOutput = container.querySelector<HTMLOutputElement>(
    '[data-testid="frames-per-second"]',
  );
  const worldType = container.querySelector<HTMLElement>(
    '[data-testid="world-type"]',
  );
  const flightState = container.querySelector<HTMLOutputElement>(
    '[data-testid="flight-state"]',
  );
  const cameraPosition = container.querySelector<HTMLOutputElement>(
    '[data-testid="camera-position"]',
  );
  const cameraOrientation = container.querySelector<HTMLOutputElement>(
    '[data-testid="camera-orientation"]',
  );
  const flightSpeed = container.querySelector<HTMLOutputElement>(
    '[data-testid="flight-speed"]',
  );
  const boundaryState = container.querySelector<HTMLOutputElement>(
    '[data-testid="boundary-state"]',
  );

  if (
    !shell ||
    !canvas ||
    !startButton ||
    !status ||
    !controlsHelp ||
    !helpToggle ||
    !resetButton ||
    !fpsOutput ||
    !worldType ||
    !flightState ||
    !cameraPosition ||
    !cameraOrientation ||
    !flightSpeed ||
    !boundaryState
  ) {
    throw new Error('The viewer interface could not be initialized.');
  }

  let renderer: WebGLRenderer;

  try {
    renderer = new WebGLRenderer({
      canvas,
      antialias: true,
      alpha: false,
      powerPreference: 'high-performance',
    });
  } catch (error) {
    const detail = error instanceof Error ? ` ${error.message}` : '';
    const message = document.createElement('p');
    message.className = 'renderer-error';
    message.setAttribute('role', 'alert');
    message.textContent = `This browser could not start WebGL.${detail} Try a recent desktop browser with WebGL enabled.`;
    shell.querySelector('.start-card')?.prepend(message);
    status.textContent = 'The 3D renderer is unavailable.';
    startButton.disabled = true;
    return { dispose: () => undefined };
  }

  const scene = createScene();
  const world = createSyntheticWorld();
  scene.add(world.group);

  const camera = new PerspectiveCamera(54, 1, 0.1, 150);
  camera.up.set(0, 1, 0);
  camera.position.set(
    world.spawnPosition.x,
    world.spawnPosition.y,
    world.spawnPosition.z,
  );
  camera.lookAt(world.spawnLookAt.x, world.spawnLookAt.y, world.spawnLookAt.z);

  let pointerLocked = false;
  const setBoundaryFeedback = (atBoundary: boolean): void => {
    shell.classList.toggle('at-boundary', atBoundary);
    if (atBoundary) {
      status.textContent =
        'Demo edge reached. Turn back to stay within the test area.';
    } else if (pointerLocked) {
      status.textContent = 'FREE FLY · WASD moves · Esc releases the pointer';
    }
  };

  const setControlsHelpVisible = (visible: boolean): void => {
    controlsHelp.hidden = !visible;
    helpToggle.textContent = visible ? 'Hide controls' : 'Show controls';
    helpToggle.setAttribute('aria-expanded', String(visible));
  };

  const controller = new FreeFlyController(
    camera,
    canvas,
    world.spawnPosition,
    world.bounds,
    {
      onPointerLockChange: (locked) => {
        pointerLocked = locked;
        shell.classList.toggle('is-locked', locked);
        if (locked) setControlsHelpVisible(true);
        if (locked) {
          startButton.textContent = 'Start exploring';
          status.textContent =
            'FREE FLY · WASD moves · Esc releases the pointer';
        } else {
          startButton.textContent = 'Resume flying';
          status.textContent =
            'Mouse unlocked. Click Resume flying to continue.';
        }
      },
      onBoundaryChange: setBoundaryFeedback,
      onLockError: (message) => {
        shell.classList.add('lock-error');
        startButton.textContent = 'Try again';
        status.textContent = message;
      },
      onLockRequest: () => {
        shell.classList.remove('lock-error');
        status.textContent = 'Requesting mouse look…';
      },
      onReset: () => {
        status.textContent = pointerLocked
          ? 'Spawn position and view reset · Esc releases the pointer'
          : 'Spawn position and view reset. Click Start to fly.';
      },
    },
  );

  const requestLockFromCanvas = (): void => {
    if (!controller.isLocked) {
      controller.requestLock();
    }
  };
  const requestLockFromButton = (): void => controller.requestLock();
  const resetFromButton = (): void => controller.reset();
  const toggleControlsHelp = (): void =>
    setControlsHelpVisible(controlsHelp.hidden !== false);
  startButton.addEventListener('click', requestLockFromButton);
  resetButton.addEventListener('click', resetFromButton);
  helpToggle.addEventListener('click', toggleControlsHelp);
  canvas.addEventListener('click', requestLockFromCanvas);

  const lookDirection = new Vector3();
  let framesPerSecond = 0;
  const updateTelemetry = (): void => {
    camera.getWorldDirection(lookDirection);
    const bearingDegrees =
      (Math.atan2(lookDirection.x, -lookDirection.z) * (180 / Math.PI) + 360) %
      360;
    const pitchDegrees =
      Math.asin(Math.max(-1, Math.min(1, lookDirection.y))) * (180 / Math.PI);

    cameraPosition.dataset.x = camera.position.x.toFixed(2);
    cameraPosition.dataset.y = camera.position.y.toFixed(2);
    cameraPosition.dataset.z = camera.position.z.toFixed(2);
    cameraPosition.textContent =
      `X ${camera.position.x.toFixed(1)} · ` +
      `Y ${camera.position.y.toFixed(1)} · ` +
      `Z ${camera.position.z.toFixed(1)} m`;

    cameraOrientation.dataset.bearingDegrees = bearingDegrees.toFixed(1);
    cameraOrientation.dataset.pitchDegrees = pitchDegrees.toFixed(1);
    cameraOrientation.textContent =
      `Bearing ${bearingDegrees.toFixed(1)}° · ` +
      `Pitch ${pitchDegrees.toFixed(1)}°`;

    flightState.dataset.locked = String(controller.isLocked);
    flightState.textContent = controller.isLocked
      ? 'POINTER LOCKED · FREE FLY'
      : 'POINTER UNLOCKED · FREE FLY';

    flightSpeed.dataset.metersPerSecond =
      controller.speedMetersPerSecond.toFixed(2);
    flightSpeed.dataset.boosting = String(controller.isBoosting);
    flightSpeed.textContent =
      `${controller.speedMetersPerSecond.toFixed(1)} m/s` +
      (controller.isBoosting ? ' · BOOST' : ' · CRUISE');

    fpsOutput.dataset.fps = framesPerSecond.toFixed(1);
    fpsOutput.textContent = framesPerSecond
      ? `${framesPerSecond.toFixed(1)} frames per second`
      : 'Waiting for first frame';

    boundaryState.dataset.atBoundary = String(controller.isAtBoundary);
    boundaryState.textContent = controller.isAtBoundary
      ? 'EDGE · TURN BACK'
      : 'WITHIN DEMO BOUNDS';
  };
  updateTelemetry();

  const resizeRenderer = (): void => {
    const width = Math.max(1, shell.clientWidth);
    const height = Math.max(1, shell.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };

  const resizeObserver = new ResizeObserver(resizeRenderer);
  resizeObserver.observe(shell);
  window.addEventListener('resize', resizeRenderer);
  resizeRenderer();

  const timer = new Timer();
  timer.connect(document);
  let telemetryElapsed = 0;
  let fpsElapsed = 0;
  let fpsFrames = 0;
  let rendererReady = false;
  renderer.setAnimationLoop((timestamp) => {
    timer.update(timestamp);
    const elapsedSeconds = timer.getDelta();
    controller.update(elapsedSeconds);
    fpsElapsed += elapsedSeconds;
    fpsFrames += 1;
    if (fpsElapsed >= 0.5) {
      framesPerSecond = fpsFrames / fpsElapsed;
      fpsElapsed = 0;
      fpsFrames = 0;
    }
    telemetryElapsed += elapsedSeconds;
    if (telemetryElapsed >= 0.1) {
      telemetryElapsed %= 0.1;
      updateTelemetry();
    }
    renderer.render(scene, camera);
    if (!rendererReady) {
      rendererReady = true;
      shell.dataset.rendererReady = 'true';
    }
  });

  return {
    dispose: () => {
      renderer.setAnimationLoop(null);
      timer.dispose();
      resizeObserver.disconnect();
      window.removeEventListener('resize', resizeRenderer);
      startButton.removeEventListener('click', requestLockFromButton);
      resetButton.removeEventListener('click', resetFromButton);
      helpToggle.removeEventListener('click', toggleControlsHelp);
      canvas.removeEventListener('click', requestLockFromCanvas);
      controller.dispose();
      disposeScene(scene);
      renderer.dispose();
      container.replaceChildren();
    },
  };
}

function disposeScene(scene: Scene): void {
  scene.traverse((object) => {
    const renderable = object as typeof object & {
      geometry?: BufferGeometry;
      material?: Material | Material[];
    };

    renderable.geometry?.dispose();
    const materials = renderable.material
      ? Array.isArray(renderable.material)
        ? renderable.material
        : [renderable.material]
      : [];

    for (const material of materials) {
      const mappedMaterial = material as Material & { map?: Texture | null };
      mappedMaterial.map?.dispose();
      material.dispose();
    }
  });
}
