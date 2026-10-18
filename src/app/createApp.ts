import {
  Group,
  PerspectiveCamera,
  Scene,
  Timer,
  Vector3,
  WebGLRenderer,
} from 'three';
import { FreeFlyController } from '../camera/FreeFlyController';
import type { FlightBounds, Vec3Like } from '../camera/movement';
import { loadWorld } from './worldLoader';
import { loadBuildingPackage } from './buildingLoader';
import type { RealTerrainSceneManifest } from '../geo/sceneSchema';
import type { TerrainGrid } from '../geo/terrainGrid';
import { createScene } from '../scene/createScene';
import {
  createSyntheticWorld,
  terrainHeightAt,
} from '../scene/createSyntheticWorld';
import { createHeightfieldWorld } from '../scene/createHeightfieldWorld';
import { createBuildings } from '../scene/createBuildings';
import { disposeSceneResources } from '../scene/disposeSceneResources';
import type { HeightfieldWorld } from '../scene/createHeightfieldWorld';

const TERRAIN_MANIFEST_URL = '/worlds/synthetic-terrain-demo/manifest.json';
const REAL_TERRAIN_MANIFEST_URL = '/worlds/torquay-poc-001/manifest.json';
const REAL_BUILDINGS_MANIFEST_URL =
  '/worlds/torquay-poc-001/buildings/manifest.json';

type GroundSampler = (x: number, z: number) => number | null;

interface ViewerWorld {
  group: Scene['children'][number];
  name: string;
  bounds: FlightBounds;
  spawnPosition: Vec3Like;
  spawnLookAt: Vec3Like;
  sampleHeight: GroundSampler;
  dimensions: string;
  sourceMode: 'analytic' | 'heightfield';
  worldId: string;
  isReal: boolean;
  verticalReference: string;
  attribution: string;
  sourceDetailsUrl?: string;
  licenceUrl?: string;
  originElevationM?: number;
  cameraFar: number;
  columns?: number;
  rows?: number;
  terrain?: HeightfieldWorld['terrain'];
  gridAndCompass?: HeightfieldWorld['gridAndCompass'];
  terrainGrid?: TerrainGrid;
  realManifest?: RealTerrainSceneManifest;
}

export interface AppHandle {
  dispose: () => void;
}

export function createApp(container: HTMLElement): AppHandle {
  const requestedWorld = new URLSearchParams(window.location.search).get(
    'world',
  );
  const m0Mode = requestedWorld === 'm0';
  const initialRealMode = requestedWorld === 'torquay-poc-001';
  const initialBuildingsMode =
    initialRealMode &&
    new URLSearchParams(window.location.search).get('buildings') === '1';
  container.innerHTML = `
    <main class="viewer-shell" data-world-mode="${m0Mode ? 'm0' : initialRealMode ? 'real' : 'synthetic'}" data-load-state="loading" data-renderer-ready="false">
      <canvas class="viewer-canvas" aria-label="Terrain free-fly world"></canvas>
      <div class="viewer-ui">
        <div class="viewer-topline">
          <p class="synthetic-badge" data-testid="provenance-badge"><span aria-hidden="true"></span>${initialRealMode ? 'REAL DATA · EA DTM 2022 composite' : 'SYNTHETIC · FICTIONAL LOCAL DATA'}</p>
          <p class="flight-status" role="status" aria-live="polite" data-testid="flight-status-message">${m0Mode ? 'Starting the M0 synthetic demo…' : initialRealMode ? 'Loading the local Environment Agency DTM…' : 'Loading the local synthetic heightfield…'}</p>
        </div>
        <nav class="world-selector" aria-label="Choose a local world">
          <button type="button" data-testid="world-select-synthetic" aria-pressed="${!m0Mode && !initialRealMode}">Synthetic terrain</button>
          <button type="button" data-testid="world-select-real" aria-pressed="${initialRealMode}">EA terrain</button>
          <a href="?world=torquay-poc-001&amp;buildings=1" data-testid="world-select-buildings">EA terrain + OSM buildings</a>
          <a href="?world=m0" data-testid="world-select-m0">M0 synthetic demo</a>
        </nav>
        <p class="terrain-loading" data-testid="terrain-loading" role="status"${m0Mode ? ' hidden' : ''}>${initialRealMode ? 'Loading and validating the local Environment Agency terrain package…' : 'Loading and validating the synthetic terrain package…'}</p>
        <section class="world-error" data-testid="world-load-error" role="alert" hidden>
          <h2>World could not be loaded</h2>
          <p data-testid="world-error-message"></p>
          <div class="world-error-actions">
            <button type="button" data-testid="retry-world">Retry world load</button>
            <button type="button" data-testid="recover-synthetic">Return to synthetic terrain</button>
            <a href="?world=m0" data-testid="return-m0">Open M0 analytic demo</a>
          </div>
        </section>
        <section class="debug-hud" aria-label="Flight telemetry" data-testid="debug-hud">
          <div class="debug-hud-heading">
            <h2>LIVE TELEMETRY</h2>
            <div class="debug-actions" aria-label="Viewer actions">
              <button type="button" data-testid="reset-button">Reset view</button>
              <button type="button" data-testid="help-toggle" aria-controls="controls-help" aria-expanded="false">Show controls</button>
            </div>
          </div>
          <dl>
            <div><dt>World</dt><dd data-testid="world-type" data-world-id="">Loading synthetic terrain…</dd></div>
            <div><dt>Source mode</dt><dd data-testid="world-source-mode">HEIGHTFIELD</dd></div>
            <div><dt>Provenance</dt><dd data-testid="world-provenance">SYNTHETIC · LOCAL FIXTURE</dd></div>
            <div><dt>Vertical reference</dt><dd data-testid="vertical-reference">LOCAL FICTIONAL HEIGHTS</dd></div>
            <div><dt>Attribution</dt><dd data-testid="world-attribution">Fictional local fixture; no geographic data.</dd></div>
            <div class="provenance-links" data-testid="provenance-links" hidden><dt>Source and licence</dt><dd><a data-testid="source-details-link" target="_blank" rel="noopener noreferrer" hidden>Publisher catalogue</a><a data-testid="licence-details-link" target="_blank" rel="noopener noreferrer" hidden>Open Government Licence v3.0</a></dd></div>
            <div><dt>Grid</dt><dd data-testid="terrain-details" data-columns="" data-rows="">Loading…</dd></div>
            <div><dt>Ground height</dt><dd><output data-testid="ground-height" data-outside="false" data-height-meters="">Waiting for terrain</output></dd></div>
            <div><dt>Flight</dt><dd><output data-testid="flight-state" aria-live="off" data-locked="false">POINTER UNLOCKED · FREE FLY</output></dd></div>
            <div><dt>Camera position</dt><dd><output data-testid="camera-position" aria-live="off" aria-label="Camera position in metres" data-x="0" data-y="0" data-z="0">X 0.0 · Y 0.0 · Z 0.0 m</output></dd></div>
            <div><dt>Bearing / pitch</dt><dd><output data-testid="camera-orientation" aria-live="off" aria-label="Camera bearing and pitch" data-bearing-degrees="0" data-pitch-degrees="0">Bearing 000.0° · Pitch 0.0°</output></dd></div>
            <div><dt>Speed</dt><dd><output data-testid="flight-speed" aria-live="off" aria-label="Flight speed in metres per second" data-meters-per-second="0" data-boosting="false">0.0 m/s</output></dd></div>
            <div><dt>FPS</dt><dd><output data-testid="frames-per-second" aria-live="off" data-fps="0">Waiting for first frame</output></dd></div>
            <div><dt>Bounds</dt><dd><output data-testid="boundary-state" aria-live="off" data-at-boundary="false">WITHIN DEMO BOUNDS</output></dd></div>
          </dl>
          <div class="terrain-actions" data-testid="terrain-actions"${m0Mode ? ' hidden' : ''}>
            <button type="button" data-testid="grid-toggle" aria-pressed="true">Terrain grid: on <kbd>G</kbd></button>
            <button type="button" data-testid="wireframe-toggle" aria-pressed="false">Wireframe: off</button>
          </div>
        </section>
        <section class="building-controls" data-testid="building-controls" aria-label="Optional OSM building layer" hidden>
          <div class="building-actions">
            <button type="button" data-testid="buildings-toggle" aria-pressed="false">Load OSM buildings</button>
            <button type="button" data-testid="buildings-retry" hidden>Retry building load</button>
            <button type="button" data-testid="buildings-terrain-only" hidden>Continue with terrain only</button>
          </div>
          <p data-testid="building-status" role="status" aria-live="polite" data-state="off" data-building-count="0" data-component-count="0">Optional local OSM layer is off.</p>
          <p data-testid="building-extract-vintage">OSM extract vintage: not loaded.</p>
          <div class="building-error" data-testid="building-error" role="alert" hidden>
            <p data-testid="building-error-message"></p>
          </div>
          <p class="building-policy" data-testid="building-policy">Footprints use level roofs at the highest sampled terrain under each feature plus its tagged or estimated height. This is a visual placement convention, not a verified roof or foundation height; wall bases are buried 0.02 m to avoid seams. Tagged OSM heights are unverified; remaining values are estimates.</p>
          <p class="building-attribution" data-testid="building-attribution">© OpenStreetMap contributors · extract provided by Geofabrik GmbH · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">ODbL 1.0 attribution and licence</a></p>
          <p class="building-completeness">Mapped counts do not establish completeness. Road and remaining feature checks are outstanding; the candidate AOI remains pending.</p>
        </section>
        <aside id="controls-help" class="controls-help" aria-labelledby="controls-title" data-testid="controls-help" hidden>
          <h2 id="controls-title">IN-FLIGHT CONTROLS</h2>
          <p><kbd>Mouse</kbd><span>Look around</span></p>
          <p><kbd>W</kbd><kbd>S</kbd><span>Fly along the camera direction</span></p>
          <p><kbd>A</kbd><kbd>D</kbd><span>Strafe left / right</span></p>
          <p><kbd>Space</kbd><kbd>Ctrl</kbd><span>Rise / descend</span></p>
          <p><kbd>Shift</kbd><span>Move faster</span><kbd>R</kbd><span>Reset view</span><kbd>H</kbd><span>Toggle help</span><kbd>Esc</kbd><span>Release pointer</span></p>
          <p class="terrain-key-hint"${m0Mode ? ' hidden' : ''}><kbd>G</kbd><span>Toggle terrain grid and north cues</span></p>
        </aside>
        <section class="start-card" aria-labelledby="page-title">
          <p class="eyebrow">LOCAL BROWSER PROOF OF CONCEPT</p>
          <h1 id="page-title">Torquay <span>Virtual World</span></h1>
          <p class="welcome-copy" data-testid="welcome-copy">${m0Mode ? 'M0 ANALYTIC DEMO · fictional slope and blocks; no Torquay measurements or map data are used.' : initialRealMode ? 'REAL EA LIDAR · local, verified 2 m heightfield for the pending candidate AOI. OSM/OS feature coverage remains unchecked.' : 'SYNTHETIC HEIGHTFIELD · fictional slope, hill, and ridge loaded from a local Float32 fixture; no Torquay measurements or map data are used.'}</p>
          <button class="start-button" type="button" data-testid="start-button"${m0Mode ? '' : ' disabled'}>Start exploring</button>
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
  const provenanceBadge = container.querySelector<HTMLElement>(
    '[data-testid="provenance-badge"]',
  );
  const syntheticWorldButton = container.querySelector<HTMLButtonElement>(
    '[data-testid="world-select-synthetic"]',
  );
  const realWorldButton = container.querySelector<HTMLButtonElement>(
    '[data-testid="world-select-real"]',
  );
  const recoverSyntheticButton = container.querySelector<HTMLButtonElement>(
    '[data-testid="recover-synthetic"]',
  );
  const loadingState = container.querySelector<HTMLElement>(
    '[data-testid="terrain-loading"]',
  );
  const errorPanel = container.querySelector<HTMLElement>(
    '[data-testid="world-load-error"]',
  );
  const errorMessage = container.querySelector<HTMLElement>(
    '[data-testid="world-error-message"]',
  );
  const retryButton = container.querySelector<HTMLButtonElement>(
    '[data-testid="retry-world"]',
  );
  const controlsHelp = container.querySelector<HTMLElement>('.controls-help');
  const helpToggle = container.querySelector<HTMLButtonElement>(
    '[data-testid="help-toggle"]',
  );
  const resetButton = container.querySelector<HTMLButtonElement>(
    '[data-testid="reset-button"]',
  );
  const gridToggle = container.querySelector<HTMLButtonElement>(
    '[data-testid="grid-toggle"]',
  );
  const wireframeToggle = container.querySelector<HTMLButtonElement>(
    '[data-testid="wireframe-toggle"]',
  );
  const terrainActions = container.querySelector<HTMLElement>(
    '[data-testid="terrain-actions"]',
  );
  const buildingControls = container.querySelector<HTMLElement>(
    '[data-testid="building-controls"]',
  );
  const buildingsToggle = container.querySelector<HTMLButtonElement>(
    '[data-testid="buildings-toggle"]',
  );
  const buildingsRetry = container.querySelector<HTMLButtonElement>(
    '[data-testid="buildings-retry"]',
  );
  const buildingsTerrainOnly = container.querySelector<HTMLButtonElement>(
    '[data-testid="buildings-terrain-only"]',
  );
  const buildingStatus = container.querySelector<HTMLElement>(
    '[data-testid="building-status"]',
  );
  const buildingVintage = container.querySelector<HTMLElement>(
    '[data-testid="building-extract-vintage"]',
  );
  const buildingError = container.querySelector<HTMLElement>(
    '[data-testid="building-error"]',
  );
  const buildingErrorMessage = container.querySelector<HTMLElement>(
    '[data-testid="building-error-message"]',
  );
  const fpsOutput = container.querySelector<HTMLOutputElement>(
    '[data-testid="frames-per-second"]',
  );
  const worldType = container.querySelector<HTMLElement>(
    '[data-testid="world-type"]',
  );
  const sourceMode = container.querySelector<HTMLElement>(
    '[data-testid="world-source-mode"]',
  );
  const worldProvenance = container.querySelector<HTMLElement>(
    '[data-testid="world-provenance"]',
  );
  const verticalReference = container.querySelector<HTMLElement>(
    '[data-testid="vertical-reference"]',
  );
  const worldAttribution = container.querySelector<HTMLElement>(
    '[data-testid="world-attribution"]',
  );
  const provenanceLinks = container.querySelector<HTMLElement>(
    '[data-testid="provenance-links"]',
  );
  const sourceDetailsLink = container.querySelector<HTMLAnchorElement>(
    '[data-testid="source-details-link"]',
  );
  const licenceDetailsLink = container.querySelector<HTMLAnchorElement>(
    '[data-testid="licence-details-link"]',
  );
  const terrainDetails = container.querySelector<HTMLElement>(
    '[data-testid="terrain-details"]',
  );
  const groundHeight = container.querySelector<HTMLOutputElement>(
    '[data-testid="ground-height"]',
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
    !provenanceBadge ||
    !syntheticWorldButton ||
    !realWorldButton ||
    !recoverSyntheticButton ||
    !loadingState ||
    !errorPanel ||
    !errorMessage ||
    !retryButton ||
    !controlsHelp ||
    !helpToggle ||
    !resetButton ||
    !gridToggle ||
    !wireframeToggle ||
    !terrainActions ||
    !buildingControls ||
    !buildingsToggle ||
    !buildingsRetry ||
    !buildingsTerrainOnly ||
    !buildingStatus ||
    !buildingVintage ||
    !buildingError ||
    !buildingErrorMessage ||
    !fpsOutput ||
    !worldType ||
    !sourceMode ||
    !worldProvenance ||
    !verticalReference ||
    !worldAttribution ||
    !provenanceLinks ||
    !sourceDetailsLink ||
    !licenceDetailsLink ||
    !terrainDetails ||
    !groundHeight ||
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
    shell.dataset.loadState = 'error';
    startButton.disabled = true;
    return { dispose: () => container.replaceChildren() };
  }

  const scene = createScene();
  const camera = new PerspectiveCamera(54, 1, 0.1, 180);
  camera.up.set(0, 1, 0);
  let controller: FreeFlyController | undefined;
  let currentSampleHeight: GroundSampler | undefined;
  let currentOriginElevationM = 0;
  let currentTerrain: HeightfieldWorld['terrain'] | undefined;
  let currentGridAndCompass: HeightfieldWorld['gridAndCompass'] | undefined;
  let currentTerrainGrid: TerrainGrid | undefined;
  let currentTerrainManifest: RealTerrainSceneManifest | undefined;
  let currentBuildingGroup: Group | undefined;
  let buildingsRequested = initialBuildingsMode;
  let buildingLoad: AbortController | undefined;
  let buildingAttempt = 0;
  let buildingMethodSummary = '';
  let pointerLocked = false;
  let disposed = false;
  let hasLoadedWorld = false;
  let framesPerSecond = 0;
  let activeLoad: AbortController | undefined;
  let loadAttempt = 0;
  let selectedWorldMode: 'synthetic' | 'real' = initialRealMode
    ? 'real'
    : 'synthetic';
  let currentWorldGroup: Scene['children'][number] | undefined;
  let resizeRenderer: () => void = () => undefined;

  const setWorldSelection = (mode: 'synthetic' | 'real' | 'm0'): void => {
    shell.dataset.worldMode = mode;
    syntheticWorldButton.setAttribute(
      'aria-pressed',
      String(mode === 'synthetic'),
    );
    realWorldButton.setAttribute('aria-pressed', String(mode === 'real'));
  };

  const clearCurrentWorld = (): void => {
    clearBuildingLayer();
    controller?.dispose();
    controller = undefined;
    if (currentWorldGroup) {
      scene.remove(currentWorldGroup);
      disposeSceneResources(currentWorldGroup);
      currentWorldGroup = undefined;
    }
    currentSampleHeight = undefined;
    currentOriginElevationM = 0;
    currentTerrain = undefined;
    currentGridAndCompass = undefined;
    currentTerrainGrid = undefined;
    currentTerrainManifest = undefined;
    buildingControls.hidden = true;
    hasLoadedWorld = false;
  };

  const clearBuildingLayer = (): void => {
    buildingAttempt += 1;
    buildingLoad?.abort();
    buildingLoad = undefined;
    if (currentBuildingGroup) {
      scene.remove(currentBuildingGroup);
      disposeSceneResources(currentBuildingGroup);
      currentBuildingGroup = undefined;
    }
    shell.dataset.buildingState = 'off';
    shell.dataset.buildingCount = '0';
    shell.dataset.buildingComponents = '0';
    shell.dataset.buildingMeshCount = '0';
    shell.dataset.buildingVisible = 'false';
    buildingStatus.dataset.state = 'off';
    buildingStatus.dataset.buildingCount = '0';
    buildingStatus.dataset.componentCount = '0';
    buildingStatus.textContent = 'Optional local OSM layer is off.';
    buildingVintage.textContent = 'OSM extract vintage: not loaded.';
    buildingMethodSummary = '';
    buildingsToggle.disabled = false;
    buildingsToggle.setAttribute('aria-pressed', 'false');
    buildingsToggle.textContent = 'Load OSM buildings';
    buildingsRetry.hidden = true;
    buildingsTerrainOnly.hidden = true;
    buildingError.hidden = true;
  };

  const setControlsHelpVisible = (visible: boolean): void => {
    controlsHelp.hidden = !visible;
    helpToggle.textContent = visible ? 'Hide controls' : 'Show controls';
    helpToggle.setAttribute('aria-expanded', String(visible));
  };

  const setGridVisible = (visible: boolean): void => {
    if (!currentGridAndCompass) return;
    currentGridAndCompass.visible = visible;
    shell.dataset.gridVisible = String(currentGridAndCompass.visible);
    gridToggle.setAttribute('aria-pressed', String(visible));
    gridToggle.innerHTML = `Terrain grid: ${visible ? 'on' : 'off'} <kbd>G</kbd>`;
  };

  const setWireframeVisible = (visible: boolean): void => {
    if (!currentTerrain) return;
    currentTerrain.material.wireframe = visible;
    currentTerrain.material.needsUpdate = true;
    shell.dataset.wireframeVisible = String(currentTerrain.material.wireframe);
    wireframeToggle.setAttribute('aria-pressed', String(visible));
    wireframeToggle.textContent = `Wireframe: ${visible ? 'on' : 'off'}`;
  };

  const setBuildingRoute = (enabled: boolean): void => {
    const url = new URL(window.location.href);
    if (enabled) {
      url.searchParams.set('world', 'torquay-poc-001');
      url.searchParams.set('buildings', '1');
    } else {
      url.searchParams.delete('buildings');
    }
    window.history.pushState({}, '', url);
  };

  const startBuildingLoad = async (): Promise<void> => {
    if (!currentTerrainManifest || !currentTerrainGrid || !hasLoadedWorld) {
      return;
    }
    clearBuildingLayer();
    buildingsRequested = true;
    const attempt = buildingAttempt;
    const abortController = new AbortController();
    buildingLoad = abortController;
    shell.dataset.buildingState = 'loading';
    buildingStatus.dataset.state = 'loading';
    buildingStatus.textContent =
      'Loading and validating the local OSM package…';
    buildingsToggle.disabled = true;
    buildingsToggle.textContent = 'Loading OSM buildings…';
    buildingsRetry.hidden = true;
    buildingsTerrainOnly.hidden = true;
    buildingError.hidden = true;
    try {
      const packageData = await loadBuildingPackage(
        REAL_BUILDINGS_MANIFEST_URL,
        currentTerrainManifest,
        undefined,
        abortController.signal,
      );
      if (
        disposed ||
        attempt !== buildingAttempt ||
        abortController.signal.aborted ||
        !currentTerrainGrid
      ) {
        return;
      }
      const group = createBuildings(packageData, currentTerrainGrid);
      if (
        disposed ||
        attempt !== buildingAttempt ||
        abortController.signal.aborted
      ) {
        disposeSceneResources(group);
        return;
      }
      currentBuildingGroup = group;
      scene.add(group);
      shell.dataset.buildingState = 'loaded';
      shell.dataset.buildingCount = String(packageData.features.length);
      shell.dataset.buildingComponents = String(packageData.componentCount);
      shell.dataset.buildingMeshCount = String(group.children.length);
      shell.dataset.buildingVisible = 'true';
      buildingStatus.dataset.state = 'loaded';
      buildingStatus.dataset.buildingCount = String(
        packageData.features.length,
      );
      buildingStatus.dataset.componentCount = String(
        packageData.componentCount,
      );
      const methods = packageData.heightMethodCounts;
      buildingMethodSummary =
        `${methods.osm_height.toLocaleString()} tagged-but-unverified heights, ` +
        `${methods.estimated_levels.toLocaleString()} level estimates, ` +
        `${methods.estimated_default.toLocaleString()} default estimates`;
      buildingStatus.dataset.heightMethodSummary = buildingMethodSummary;
      buildingStatus.textContent =
        `Loaded ${packageData.features.length.toLocaleString()} footprints / ` +
        `${packageData.componentCount.toLocaleString()} components · ` +
        `${buildingMethodSummary}.`;
      buildingVintage.textContent = `OSM extract vintage: ${packageData.manifest.provenance.extractTimestamp}.`;
      buildingsToggle.disabled = false;
      buildingsToggle.setAttribute('aria-pressed', 'true');
      buildingsToggle.textContent = 'Hide OSM buildings';
      buildingsRetry.hidden = true;
      buildingsTerrainOnly.hidden = true;
      buildingError.hidden = true;
      status.textContent =
        'Terrain and local OSM footprints ready. Heights are unverified or estimated.';
    } catch (error) {
      if (
        disposed ||
        attempt !== buildingAttempt ||
        abortController.signal.aborted
      ) {
        return;
      }
      const detail = error instanceof Error ? error.message : String(error);
      const publishCommand =
        'From the pipeline folder run .\\.venv\\Scripts\\python.exe -m torquay_pipeline.cli publish-buildings.';
      buildingErrorMessage.textContent = `${detail} ${publishCommand} The terrain remains available; no buildings are shown.`;
      buildingError.hidden = false;
      shell.dataset.buildingState = 'error';
      buildingStatus.dataset.state = 'error';
      buildingStatus.textContent =
        'Building layer failed to load; terrain is still usable.';
      buildingsToggle.disabled = false;
      buildingsToggle.setAttribute('aria-pressed', 'false');
      buildingsToggle.textContent = 'Load OSM buildings';
      buildingsRetry.hidden = false;
      buildingsTerrainOnly.hidden = false;
      status.textContent =
        'Building package unavailable. Retry or continue with terrain only.';
    }
  };

  const toggleBuildings = (): void => {
    if (currentBuildingGroup) {
      const visible = !currentBuildingGroup.visible;
      currentBuildingGroup.visible = visible;
      buildingsRequested = visible;
      setBuildingRoute(visible);
      shell.dataset.buildingVisible = String(visible);
      buildingsToggle.setAttribute('aria-pressed', String(visible));
      buildingsToggle.textContent = visible
        ? 'Hide OSM buildings'
        : 'Show OSM buildings';
      buildingStatus.dataset.state = visible ? 'loaded' : 'hidden';
      buildingStatus.textContent =
        `Local OSM layer ${visible ? 'visible' : 'loaded but hidden'} · ` +
        `${Number(buildingStatus.dataset.buildingCount).toLocaleString()} footprints / ` +
        `${Number(buildingStatus.dataset.componentCount).toLocaleString()} components · ` +
        `${buildingMethodSummary}.`;
      return;
    }
    setBuildingRoute(true);
    void startBuildingLoad();
  };

  const continueTerrainOnly = (): void => {
    buildingsRequested = false;
    clearBuildingLayer();
    setBuildingRoute(false);
    shell.dataset.buildingVisible = 'false';
    status.textContent = 'EA terrain only. The pending AOI remains unapproved.';
  };

  const setBoundaryFeedback = (atBoundary: boolean): void => {
    shell.classList.toggle('at-boundary', atBoundary);
    if (atBoundary) {
      status.textContent =
        selectedWorldMode === 'real'
          ? 'Candidate AOI edge reached. Turn back to remain inside the local terrain.'
          : 'Demo edge reached. Turn back to stay within the synthetic terrain.';
    } else if (pointerLocked) {
      status.textContent = 'FREE FLY · WASD moves · Esc releases the pointer';
    }
  };

  const controllerCallbacks = {
    onPointerLockChange: (locked: boolean): void => {
      pointerLocked = locked;
      shell.classList.toggle('is-locked', locked);
      if (locked) setControlsHelpVisible(true);
      if (locked) {
        startButton.textContent = 'Start exploring';
        status.textContent = 'FREE FLY · WASD moves · Esc releases the pointer';
      } else {
        startButton.textContent = 'Resume flying';
        status.textContent = 'Mouse unlocked. Click Resume flying to continue.';
      }
    },
    onBoundaryChange: setBoundaryFeedback,
    onLockError: (message: string): void => {
      shell.classList.add('lock-error');
      startButton.textContent = 'Try again';
      status.textContent = message;
    },
    onLockRequest: (): void => {
      shell.classList.remove('lock-error');
      status.textContent = 'Requesting mouse look…';
    },
    onReset: (): void => {
      status.textContent = pointerLocked
        ? 'Spawn position and view reset · Esc releases the pointer'
        : 'Spawn position and view reset. Click Start to fly.';
    },
  };

  const installWorld = (world: ViewerWorld): void => {
    if (disposed) {
      disposeSceneResources(world.group);
      return;
    }
    clearCurrentWorld();
    scene.add(world.group);
    currentWorldGroup = world.group;
    camera.position.set(
      world.spawnPosition.x,
      world.spawnPosition.y,
      world.spawnPosition.z,
    );
    camera.lookAt(
      world.spawnLookAt.x,
      world.spawnLookAt.y,
      world.spawnLookAt.z,
    );
    camera.far = world.cameraFar;
    camera.updateProjectionMatrix();
    currentSampleHeight = world.sampleHeight;
    currentOriginElevationM = world.originElevationM ?? 0;
    currentTerrain = world.terrain;
    currentGridAndCompass = world.gridAndCompass;
    currentTerrainGrid = world.terrainGrid;
    currentTerrainManifest = world.realManifest;
    buildingControls.hidden = !world.isReal;
    shell.dataset.buildingVisible = 'false';
    shell.dataset.buildingState = 'off';
    if (world.isReal) {
      buildingStatus.textContent = 'Optional local OSM layer is off.';
      buildingStatus.dataset.state = 'off';
      buildingsToggle.disabled = false;
    }
    setGridVisible(true);
    setWireframeVisible(false);
    controller = new FreeFlyController(
      camera,
      canvas,
      world.spawnPosition,
      world.bounds,
      controllerCallbacks,
    );

    worldType.dataset.worldId = world.worldId;
    worldType.textContent = world.name;
    sourceMode.textContent = world.isReal
      ? 'LOCAL HEIGHTFIELD · EPSG:27700'
      : world.sourceMode === 'heightfield'
        ? 'LOCAL HEIGHTFIELD · SYNTHETIC'
        : 'M0 ANALYTIC · SYNTHETIC';
    worldProvenance.textContent = world.isReal
      ? 'REAL DATA · EA DTM 2022 composite'
      : 'SYNTHETIC · LOCAL FICTIONAL DATA';
    verticalReference.textContent = world.verticalReference;
    worldAttribution.textContent = world.attribution;
    sourceDetailsLink.href = world.sourceDetailsUrl ?? '';
    sourceDetailsLink.hidden = world.sourceDetailsUrl === undefined;
    licenceDetailsLink.href = world.licenceUrl ?? '';
    licenceDetailsLink.hidden = world.licenceUrl === undefined;
    provenanceLinks.hidden =
      world.sourceDetailsUrl === undefined && world.licenceUrl === undefined;
    const groundHeightLabel = groundHeight.closest('div')?.querySelector('dt');
    if (groundHeightLabel) {
      groundHeightLabel.textContent = world.isReal
        ? 'Ground height (local / Newlyn)'
        : 'Ground height';
    }
    provenanceBadge.innerHTML = `<span aria-hidden="true"></span>${world.isReal ? 'REAL DATA · EA DTM 2022 composite' : 'SYNTHETIC · FICTIONAL LOCAL DATA'}`;
    terrainDetails.dataset.columns = String(world.columns ?? '');
    terrainDetails.dataset.rows = String(world.rows ?? '');
    terrainDetails.textContent = world.dimensions;
    shell.dataset.worldSource = world.sourceMode;
    shell.dataset.worldName = world.name;
    shell.dataset.gridVisible = String(currentGridAndCompass?.visible ?? false);
    shell.dataset.wireframeVisible = String(
      currentTerrain?.material.wireframe ?? false,
    );
    terrainActions.hidden = world.sourceMode !== 'heightfield';
    canvas.setAttribute(
      'aria-label',
      world.isReal
        ? 'Environment Agency local terrain free-fly world'
        : world.sourceMode === 'heightfield'
          ? 'Synthetic hill and ridge terrain free-fly world'
          : 'M0 synthetic free-fly world',
    );
    setWorldSelection(
      world.isReal
        ? 'real'
        : world.sourceMode === 'analytic'
          ? 'm0'
          : 'synthetic',
    );
    loadingState.hidden = true;
    errorPanel.hidden = true;
    startButton.disabled = false;
    hasLoadedWorld = true;
    shell.dataset.loadState = 'loaded';
    status.textContent =
      'World ready. Click Start to capture the pointer; Esc releases it.';
    updateTelemetry();
    if (world.isReal && buildingsRequested) {
      void startBuildingLoad();
    }
  };

  const showLoadError = (error: unknown): void => {
    const detail = error instanceof Error ? error.message : String(error);
    errorMessage.textContent =
      selectedWorldMode === 'real'
        ? `${detail} To build the local package, restore the EA sources from docs/data-sources.md, then run .\\.venv\\Scripts\\python.exe -m torquay_pipeline.cli build-terrain from the pipeline folder. Synthetic terrain remains available.`
        : detail;
    errorPanel.hidden = false;
    loadingState.hidden = true;
    terrainActions.hidden = true;
    startButton.disabled = true;
    status.textContent =
      selectedWorldMode === 'real'
        ? 'Local EA terrain unavailable. Retry or return to synthetic terrain.'
        : 'Synthetic terrain load failed. Retry or choose another local world.';
    shell.dataset.loadState = 'error';
    shell.dataset.rendererReady = 'false';
    hasLoadedWorld = false;
  };

  const startWorldLoad = async (mode: 'synthetic' | 'real'): Promise<void> => {
    selectedWorldMode = mode;
    resizeRenderer();
    clearCurrentWorld();
    activeLoad?.abort();
    const attempt = ++loadAttempt;
    const abortController = new AbortController();
    activeLoad = abortController;
    hasLoadedWorld = false;
    shell.dataset.rendererReady = 'false';
    shell.dataset.loadState = 'loading';
    errorPanel.hidden = true;
    loadingState.hidden = false;
    const manifestUrl =
      mode === 'real' ? REAL_TERRAIN_MANIFEST_URL : TERRAIN_MANIFEST_URL;
    const worldLabel =
      mode === 'real'
        ? 'local Environment Agency DTM'
        : 'local synthetic heightfield';
    status.textContent = `Loading the ${worldLabel}…`;
    loadingState.textContent = `Loading and validating the ${worldLabel} package…`;
    setWorldSelection(mode);
    startButton.disabled = true;
    try {
      const loaded = await loadWorld(
        manifestUrl,
        undefined,
        abortController.signal,
      );
      if (
        disposed ||
        attempt !== loadAttempt ||
        abortController.signal.aborted
      ) {
        return;
      }
      if ((mode === 'real') !== (loaded.manifest.worldType === 'real')) {
        throw new Error(
          `manifest validation: ${manifestUrl} declared an unexpected world type`,
        );
      }
      let world: HeightfieldWorld;
      try {
        world = createHeightfieldWorld(loaded);
      } catch (error) {
        const detail = error instanceof Error ? error.message : String(error);
        throw new Error(`terrain geometry: ${detail}`, { cause: error });
      }
      installWorld({
        group: world.group,
        name: `${world.isReal ? 'REAL EA DTM' : 'SYNTHETIC'} · ${loaded.manifest.name}`,
        worldId: loaded.manifest.id,
        bounds: world.bounds,
        spawnPosition: world.spawnPosition,
        spawnLookAt: world.spawnLookAt,
        sampleHeight: (x, z) => world.grid.sampleHeight(x, z),
        dimensions: `${world.grid.columns} columns × ${world.grid.rows} rows · ${world.grid.spacingM} m spacing`,
        sourceMode: 'heightfield',
        isReal: world.isReal,
        verticalReference: world.verticalReference,
        attribution: world.attribution,
        ...(world.sourceDetailsUrl === undefined
          ? {}
          : { sourceDetailsUrl: world.sourceDetailsUrl }),
        ...(world.licenceUrl === undefined
          ? {}
          : { licenceUrl: world.licenceUrl }),
        originElevationM:
          loaded.manifest.worldType === 'real'
            ? loaded.manifest.origin.elevationM
            : 0,
        cameraFar: world.cameraFar,
        columns: world.grid.columns,
        rows: world.grid.rows,
        terrain: world.terrain,
        gridAndCompass: world.gridAndCompass,
        terrainGrid: world.grid,
        ...(loaded.manifest.worldType === 'real'
          ? { realManifest: loaded.manifest }
          : {}),
      });
    } catch (error) {
      if (
        disposed ||
        abortController.signal.aborted ||
        attempt !== loadAttempt
      ) {
        return;
      }
      showLoadError(error);
    }
  };

  const startM0World = (): void => {
    activeLoad?.abort();
    clearCurrentWorld();
    setWorldSelection('m0');
    const world = createSyntheticWorld();
    installWorld({
      group: world.group,
      name: 'SYNTHETIC · M0 ANALYTIC DEMO',
      worldId: 'm0',
      bounds: world.bounds,
      spawnPosition: world.spawnPosition,
      spawnLookAt: world.spawnLookAt,
      sampleHeight: (x, z) => terrainHeightAt(x, z),
      dimensions: '48 × 36 m · M0 analytic terrain',
      sourceMode: 'analytic',
      isReal: false,
      verticalReference: 'LOCAL FICTIONAL HEIGHTS',
      attribution: 'Fictional M0 demonstration; no geographic data.',
      cameraFar: 180,
    });
    shell.dataset.loadState = 'loaded';
  };

  const updateBrowserRoute = (mode: 'synthetic' | 'real' | 'm0'): void => {
    const url = new URL(window.location.href);
    url.searchParams.delete('buildings');
    if (mode === 'm0') {
      url.searchParams.set('world', 'm0');
    } else if (mode === 'real') {
      url.searchParams.set('world', 'torquay-poc-001');
    } else {
      url.searchParams.delete('world');
    }
    window.history.pushState({}, '', url);
  };
  const chooseWorld = (
    mode: 'synthetic' | 'real' | 'm0',
    updateRoute = true,
  ): void => {
    buildingsRequested = false;
    if (updateRoute) updateBrowserRoute(mode);
    if (mode === 'm0') {
      selectedWorldMode = 'synthetic';
      startM0World();
      return;
    }
    void startWorldLoad(mode);
  };

  const requestLockFromCanvas = (): void => {
    if (!controller?.isLocked) controller?.requestLock();
  };
  const requestLockFromButton = (): void => controller?.requestLock();
  const resetFromButton = (): void => controller?.reset();
  const toggleControlsHelp = (): void =>
    setControlsHelpVisible(controlsHelp.hidden !== false);
  const toggleGridFromButton = (): void =>
    setGridVisible(
      currentGridAndCompass ? !currentGridAndCompass.visible : false,
    );
  const toggleWireframeFromButton = (): void =>
    setWireframeVisible(
      currentTerrain ? !currentTerrain.material.wireframe : false,
    );
  const retryBuildingLoad = (): void => {
    setBuildingRoute(true);
    void startBuildingLoad();
  };
  const handleViewerShortcut = (event: KeyboardEvent): void => {
    if (event.code === 'KeyH' && !event.repeat) {
      event.preventDefault();
      setControlsHelpVisible(controlsHelp.hidden === true);
      return;
    }
    if (event.code === 'KeyG' && !event.repeat && currentGridAndCompass) {
      event.preventDefault();
      setGridVisible(!currentGridAndCompass.visible);
    }
  };

  startButton.addEventListener('click', requestLockFromButton);
  const selectSyntheticWorld = (): void => chooseWorld('synthetic');
  const selectRealWorld = (): void => chooseWorld('real');
  syntheticWorldButton.addEventListener('click', selectSyntheticWorld);
  realWorldButton.addEventListener('click', selectRealWorld);
  recoverSyntheticButton.addEventListener('click', selectSyntheticWorld);
  resetButton.addEventListener('click', resetFromButton);
  helpToggle.addEventListener('click', toggleControlsHelp);
  gridToggle.addEventListener('click', toggleGridFromButton);
  wireframeToggle.addEventListener('click', toggleWireframeFromButton);
  buildingsToggle.addEventListener('click', toggleBuildings);
  buildingsRetry.addEventListener('click', retryBuildingLoad);
  buildingsTerrainOnly.addEventListener('click', continueTerrainOnly);
  const retryWorldLoad = (): void => void startWorldLoad(selectedWorldMode);
  retryButton.addEventListener('click', retryWorldLoad);
  canvas.addEventListener('click', requestLockFromCanvas);
  window.addEventListener('keydown', handleViewerShortcut);
  const handlePopState = (): void => {
    const route = new URLSearchParams(window.location.search);
    const routeWorld = route.get('world');
    buildingsRequested =
      routeWorld === 'torquay-poc-001' && route.get('buildings') === '1';
    if (routeWorld === 'm0') {
      selectedWorldMode = 'synthetic';
      startM0World();
    } else {
      void startWorldLoad(
        routeWorld === 'torquay-poc-001' ? 'real' : 'synthetic',
      );
    }
  };
  window.addEventListener('popstate', handlePopState);

  const lookDirection = new Vector3();
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

    flightState.dataset.locked = String(controller?.isLocked ?? false);
    flightState.textContent = controller?.isLocked
      ? 'POINTER LOCKED · FREE FLY'
      : 'POINTER UNLOCKED · FREE FLY';
    flightSpeed.dataset.metersPerSecond = (
      controller?.speedMetersPerSecond ?? 0
    ).toFixed(2);
    flightSpeed.dataset.boosting = String(controller?.isBoosting ?? false);
    flightSpeed.textContent = controller
      ? `${controller.speedMetersPerSecond.toFixed(1)} m/s` +
        (controller.isBoosting ? ' · BOOST' : ' · CRUISE')
      : 'Waiting for terrain';

    fpsOutput.dataset.fps = framesPerSecond.toFixed(1);
    fpsOutput.textContent = framesPerSecond
      ? `${framesPerSecond.toFixed(1)} frames per second`
      : 'Waiting for first frame';
    boundaryState.dataset.atBoundary = String(
      controller?.isAtBoundary ?? false,
    );
    boundaryState.textContent = controller?.isAtBoundary
      ? 'EDGE · TURN BACK'
      : selectedWorldMode === 'real'
        ? 'WITHIN CANDIDATE AOI'
        : 'WITHIN DEMO BOUNDS';

    const height = currentSampleHeight?.(camera.position.x, camera.position.z);
    groundHeight.dataset.outside = String(
      height === null || height === undefined,
    );
    groundHeight.dataset.heightMeters =
      height === null || height === undefined ? '' : height.toFixed(4);
    groundHeight.textContent =
      height === null || height === undefined
        ? 'OUTSIDE TERRAIN'
        : `${height.toFixed(2)} m`;
    groundHeight.dataset.orthometricMeters =
      currentSampleHeight && height !== null && height !== undefined
        ? (height + currentOriginElevationM).toFixed(4)
        : '';
    if (
      height !== null &&
      height !== undefined &&
      currentOriginElevationM !== 0
    ) {
      groundHeight.textContent =
        `${height.toFixed(2)} m local · ` +
        `${(height + currentOriginElevationM).toFixed(2)} m Newlyn`;
    }
  };
  updateTelemetry();

  resizeRenderer = (): void => {
    const width = Math.max(1, shell.clientWidth);
    const height = Math.max(1, shell.clientHeight);
    const pixelRatioCap = selectedWorldMode === 'real' ? 1 : 2;
    renderer.setPixelRatio(
      Math.min(window.devicePixelRatio || 1, pixelRatioCap),
    );
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
  renderer.setAnimationLoop((timestamp) => {
    timer.update(timestamp);
    const elapsedSeconds = timer.getDelta();
    controller?.update(elapsedSeconds);
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
    shell.dataset.drawCalls = String(renderer.info.render.calls);
    shell.dataset.triangles = String(renderer.info.render.triangles);
    if (hasLoadedWorld && shell.dataset.rendererReady !== 'true') {
      shell.dataset.rendererReady = 'true';
    }
  });

  if (m0Mode) {
    loadingState.hidden = true;
    terrainActions.hidden = true;
    startM0World();
  } else {
    void startWorldLoad(initialRealMode ? 'real' : 'synthetic');
  }

  return {
    dispose: () => {
      if (disposed) return;
      disposed = true;
      activeLoad?.abort();
      buildingAttempt += 1;
      buildingLoad?.abort();
      controller?.dispose();
      renderer.setAnimationLoop(null);
      timer.dispose();
      resizeObserver.disconnect();
      window.removeEventListener('resize', resizeRenderer);
      window.removeEventListener('keydown', handleViewerShortcut);
      window.removeEventListener('popstate', handlePopState);
      syntheticWorldButton.removeEventListener('click', selectSyntheticWorld);
      realWorldButton.removeEventListener('click', selectRealWorld);
      recoverSyntheticButton.removeEventListener('click', selectSyntheticWorld);
      startButton.removeEventListener('click', requestLockFromButton);
      resetButton.removeEventListener('click', resetFromButton);
      helpToggle.removeEventListener('click', toggleControlsHelp);
      gridToggle.removeEventListener('click', toggleGridFromButton);
      wireframeToggle.removeEventListener('click', toggleWireframeFromButton);
      buildingsToggle.removeEventListener('click', toggleBuildings);
      buildingsRetry.removeEventListener('click', retryBuildingLoad);
      buildingsTerrainOnly.removeEventListener('click', continueTerrainOnly);
      retryButton.removeEventListener('click', retryWorldLoad);
      canvas.removeEventListener('click', requestLockFromCanvas);
      disposeSceneResources(scene);
      renderer.dispose();
      container.replaceChildren();
    },
  };
}
