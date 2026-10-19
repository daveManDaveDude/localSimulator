import type { LoadedBuildingPackage } from '../geo/buildingSchema';
import {
  selectOverviewLayers,
  type OverviewLayerState,
} from '../geo/overviewLayerState';
import type { LoadedRoadPackage } from '../geo/roadSchema';
import type { RealTerrainSceneManifest } from '../geo/sceneSchema';
import {
  loadOverviewPackage,
  OverviewLoadError,
  REAL_OVERVIEW_MANIFEST_URL,
  type LoadedOverviewPackage,
} from './overviewLoader';
import { createOverviewMap, type OverviewMapHandle } from './createOverviewMap';

export interface OverviewContext {
  isReal: boolean;
  terrain?: RealTerrainSceneManifest;
  terrainManifestSha256?: string;
  roads?: LoadedRoadPackage;
  roadsVisible: boolean;
  buildings?: LoadedBuildingPackage;
  buildingsVisible: boolean;
}

interface OverviewElements {
  openButton: HTMLButtonElement;
  closeButton: HTMLButtonElement;
  retryButton: HTMLButtonElement;
  panel: HTMLElement;
  status: HTMLElement;
  layerStatus: HTMLElement;
  disclaimer: HTMLElement;
  mapContainer: HTMLElement;
  osmAttribution: HTMLElement;
  getContext: () => OverviewContext;
}

export interface OverviewController {
  setContext: () => void;
  refreshLayers: () => void;
  resize: () => void;
  dispose: () => void;
}

type OverviewState =
  | 'closed'
  | 'loading'
  | 'ready'
  | 'unavailable'
  | 'missing'
  | 'corrupt'
  | 'identity-mismatch'
  | 'webgl-unavailable';

function layerSummary(state: OverviewLayerState): string {
  const describe = (name: string, value: string): string => {
    switch (value) {
      case 'visible':
        return `${name} visible`;
      case 'hidden':
        return `${name} hidden in the main viewer`;
      case 'not-loaded':
        return `${name} not loaded in the main viewer`;
      case 'not-included':
        return `${name} not included in this overview package`;
      case 'identity-mismatch':
        return `${name} identity mismatch; excluded`;
      default:
        return `${name} state unavailable`;
    }
  };
  return `${describe('Roads', state.roads)} · ${describe('Buildings', state.buildings)}`;
}

function initialMessage(state: OverviewState): string {
  switch (state) {
    case 'closed':
      return 'Overview closed.';
    case 'loading':
      return 'Loading and validating the local geographic overview…';
    case 'ready':
      return 'Local package overview ready. No live camera position is shown.';
    case 'unavailable':
      return 'Geographic overview unavailable for synthetic worlds. No real-world coordinates are assigned.';
    case 'missing':
      return 'Local overview package is missing. Build and publish it from the pipeline folder, then retry.';
    case 'corrupt':
      return 'Local overview package failed validation. Rebuild and publish the verified local package, then retry.';
    case 'identity-mismatch':
      return 'Overview loaded with a source identity mismatch. Conflicting layers are hidden; rebuild the overview package.';
    case 'webgl-unavailable':
      return 'MapLibre could not initialize WebGL. The main 3D viewer remains available.';
  }
}

export function createOverviewController(
  elements: OverviewElements,
): OverviewController {
  let open = false;
  let disposed = false;
  let attempt = 0;
  let request: AbortController | undefined;
  let map: OverviewMapHandle | undefined;
  let loaded: LoadedOverviewPackage | undefined;
  let loadedTerrainSha: string | undefined;
  let layerState: OverviewLayerState | undefined;

  const setState = (state: OverviewState, detail?: string): void => {
    elements.panel.dataset.state = state;
    elements.status.textContent = detail ?? initialMessage(state);
    elements.retryButton.hidden = ![
      'missing',
      'corrupt',
      'identity-mismatch',
      'webgl-unavailable',
    ].includes(state);
    if (state === 'closed') {
      elements.openButton.setAttribute('aria-expanded', 'false');
      elements.openButton.textContent = 'Open overview';
    } else if (open) {
      elements.openButton.setAttribute('aria-expanded', 'true');
      elements.openButton.textContent = 'Overview open';
    }
  };

  const removeMap = (): void => {
    map?.dispose();
    map = undefined;
    elements.mapContainer.replaceChildren();
    elements.panel.dataset.mapEngine = 'none';
  };

  const getLayerState = (
    packageData: LoadedOverviewPackage,
  ): OverviewLayerState => {
    const context = elements.getContext();
    return selectOverviewLayers(packageData.manifest, packageData.features, {
      ...(context.roads ? { roads: context.roads } : {}),
      roadsVisible: context.roadsVisible,
      ...(context.buildings ? { buildings: context.buildings } : {}),
      buildingsVisible: context.buildingsVisible,
    });
  };

  const applyLayerState = (): void => {
    if (!loaded) return;
    layerState = getLayerState(loaded);
    map?.setData(layerState.visibleCollection);
    elements.layerStatus.textContent = layerSummary(layerState);
    elements.osmAttribution.hidden =
      layerState.roads !== 'visible' && layerState.buildings !== 'visible';
    if (open && map) {
      setState(
        layerState.identityMismatches.length > 0
          ? 'identity-mismatch'
          : 'ready',
        layerState.identityMismatches.length > 0
          ? `${initialMessage('identity-mismatch')} ${layerSummary(layerState)}`
          : `${initialMessage('ready')} ${layerSummary(layerState)}`,
      );
    }
  };

  const openForContext = async (force = false): Promise<void> => {
    if (disposed || !open) return;
    const context = elements.getContext();
    if (!context.isReal) {
      request?.abort();
      request = undefined;
      attempt += 1;
      removeMap();
      loaded = undefined;
      loadedTerrainSha = undefined;
      elements.osmAttribution.hidden = true;
      elements.layerStatus.textContent =
        'No geographic data is shown for synthetic worlds.';
      elements.disclaimer.textContent =
        'This fixed geographic view is available only for the local real-world candidate package. Synthetic scenes have no assigned real-world coordinates. AOI selection remains pending; coverage is not checked.';
      setState('unavailable');
      return;
    }
    if (!context.terrain || !context.terrainManifestSha256) {
      setState(
        'loading',
        'Waiting for the verified real terrain package before opening its overview…',
      );
      return;
    }
    if (
      loadedTerrainSha &&
      loadedTerrainSha !== context.terrainManifestSha256
    ) {
      loaded = undefined;
      loadedTerrainSha = undefined;
      removeMap();
    }
    request?.abort();
    const currentAttempt = ++attempt;
    const abortController = new AbortController();
    request = abortController;
    setState('loading', initialMessage('loading'));
    try {
      if (force) loaded = undefined;
      const packageData =
        loaded ??
        (await loadOverviewPackage(
          REAL_OVERVIEW_MANIFEST_URL,
          context.terrain,
          context.terrainManifestSha256,
          undefined,
          abortController.signal,
        ));
      if (
        disposed ||
        !open ||
        currentAttempt !== attempt ||
        abortController.signal.aborted
      )
        return;
      loaded = packageData;
      loadedTerrainSha = context.terrainManifestSha256;
      layerState = getLayerState(packageData);
      elements.layerStatus.textContent = layerSummary(layerState);
      elements.disclaimer.textContent =
        'Local package overview; no live camera position and no terrain raster. AOI selection remains pending; coverage is not checked.';
      elements.osmAttribution.hidden =
        layerState.roads !== 'visible' && layerState.buildings !== 'visible';
      // Clear any failed/previous map before constructing into the map container.
      // Clearing after creation would remove MapLibre's newly attached canvas.
      removeMap();
      const createdMap = await createOverviewMap({
        container: elements.mapContainer,
        manifest: packageData.manifest,
        data: layerState.visibleCollection,
        signal: abortController.signal,
        onError: (error) => {
          if (currentAttempt !== attempt || !open) return;
          setState(
            'webgl-unavailable',
            `${initialMessage('webgl-unavailable')} ${error.message}`,
          );
        },
      });
      if (
        disposed ||
        !open ||
        currentAttempt !== attempt ||
        abortController.signal.aborted
      ) {
        createdMap.dispose();
        return;
      }
      map = createdMap;
      elements.panel.dataset.mapEngine = 'maplibre-gl';
      applyLayerState();
    } catch (error) {
      if (
        disposed ||
        !open ||
        currentAttempt !== attempt ||
        abortController.signal.aborted
      )
        return;
      const detail = error instanceof Error ? error.message : String(error);
      removeMap();
      if (error instanceof OverviewLoadError && error.statusCode === 404) {
        setState('missing', `${initialMessage('missing')} ${detail}`);
      } else if (error instanceof OverviewLoadError) {
        setState('corrupt', `${initialMessage('corrupt')} ${detail}`);
      } else {
        setState(
          'webgl-unavailable',
          `${initialMessage('webgl-unavailable')} ${detail}`,
        );
      }
    }
  };

  const openPanel = (): void => {
    if (disposed || open) return;
    open = true;
    elements.panel.hidden = false;
    elements.openButton.setAttribute('aria-expanded', 'true');
    elements.openButton.textContent = 'Overview open';
    void openForContext();
  };
  const closePanel = (): void => {
    open = false;
    attempt += 1;
    request?.abort();
    request = undefined;
    removeMap();
    elements.panel.hidden = true;
    elements.osmAttribution.hidden = true;
    setState('closed');
  };
  const retry = (): void => {
    if (!open) return;
    void openForContext(true);
  };
  const onOpen = (): void => openPanel();
  const onClose = (): void => closePanel();
  const onRetry = (): void => retry();
  elements.openButton.addEventListener('click', onOpen);
  elements.closeButton.addEventListener('click', onClose);
  elements.retryButton.addEventListener('click', onRetry);
  elements.panel.hidden = true;
  elements.panel.dataset.mapEngine = 'none';
  setState('closed');

  return {
    setContext: () => {
      if (!open || disposed) return;
      const context = elements.getContext();
      if (!context.isReal) {
        void openForContext();
        return;
      }
      if (
        loadedTerrainSha &&
        context.terrainManifestSha256 !== loadedTerrainSha
      ) {
        loaded = undefined;
        loadedTerrainSha = undefined;
        removeMap();
      }
      if (context.terrain && context.terrainManifestSha256 && !map) {
        void openForContext();
      } else if (loaded && map) {
        applyLayerState();
      }
    },
    refreshLayers: () => {
      if (loaded && map) applyLayerState();
    },
    resize: () => map?.resize(),
    dispose: () => {
      if (disposed) return;
      disposed = true;
      open = false;
      attempt += 1;
      request?.abort();
      request = undefined;
      removeMap();
      elements.openButton.removeEventListener('click', onOpen);
      elements.closeButton.removeEventListener('click', onClose);
      elements.retryButton.removeEventListener('click', onRetry);
      elements.panel.hidden = true;
      elements.osmAttribution.hidden = true;
      setState('closed');
    },
  };
}
