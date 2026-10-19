import type {
  OverviewFeatureCollection,
  OverviewManifest,
} from '../geo/overviewSchema';
import type { ErrorEvent } from 'maplibre-gl';

export interface OverviewMapHandle {
  setData: (data: OverviewFeatureCollection) => void;
  resize: () => void;
  dispose: () => void;
}

interface OverviewMapOptions {
  container: HTMLElement;
  manifest: OverviewManifest;
  data: OverviewFeatureCollection;
  onError: (error: Error) => void;
  signal?: AbortSignal;
}

function overviewStyle(
  data: OverviewFeatureCollection,
): import('maplibre-gl').StyleSpecification {
  return {
    version: 8,
    name: 'Local Torquay package overview',
    projection: { type: 'mercator' },
    sources: {
      overview: {
        type: 'geojson',
        data: data as never,
      },
    },
    layers: [
      {
        id: 'overview-background',
        type: 'background',
        paint: { 'background-color': '#17211f' },
      },
      {
        id: 'overview-buildings',
        type: 'fill',
        source: 'overview',
        filter: ['==', ['get', 'role'], 'building'],
        paint: {
          'fill-color': '#d18c71',
          'fill-opacity': 0.78,
          'fill-outline-color': '#f2c6a8',
        },
      },
      {
        id: 'overview-roads',
        type: 'line',
        source: 'overview',
        filter: ['==', ['get', 'role'], 'road'],
        paint: {
          'line-color': '#f2d59b',
          'line-width': 2.2,
          'line-opacity': 0.95,
        },
      },
      {
        id: 'overview-aoi',
        type: 'line',
        source: 'overview',
        filter: ['==', ['get', 'role'], 'aoi'],
        paint: {
          'line-color': '#73dfc0',
          'line-width': 2.5,
          'line-dasharray': [2, 1.5],
        },
      },
    ],
  };
}

/** Create a fixed offline MapLibre map after the user explicitly opens the overview. */
export async function createOverviewMap({
  container,
  manifest,
  data,
  onError,
  signal,
}: OverviewMapOptions): Promise<OverviewMapHandle> {
  await import('maplibre-gl/dist/maplibre-gl.css');
  const maplibre = await import('maplibre-gl');
  const workerModule =
    await import('maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url');
  if (signal?.aborted)
    throw new DOMException('Overview map load was cancelled', 'AbortError');
  maplibre.setWorkerUrl(workerModule.default);
  const map = new maplibre.Map({
    container,
    style: overviewStyle(data),
    center: manifest.mapView.centerWgs84,
    zoom: 12,
    bearing: 0,
    pitch: 0,
    interactive: false,
    attributionControl: false,
    fadeDuration: 0,
  });
  map.addControl(
    new maplibre.ScaleControl({ unit: 'metric', maxWidth: 112 }),
    'bottom-left',
  );
  map.addControl(
    new maplibre.AttributionControl({
      compact: false,
      customAttribution: 'MapLibre GL JS · BSD 3-Clause',
    }),
    'bottom-right',
  );
  let loaded = false;
  let readyReject: (error: Error) => void = () => undefined;
  const onMapError = (event: ErrorEvent): void => {
    const error = new Error(event.error.message);
    onError(error);
    if (!loaded) readyReject(error);
  };
  map.on('error', onMapError);
  let disposed = false;
  let observer: ResizeObserver | undefined;
  const resize = (): void => {
    if (disposed) return;
    map.resize();
    map.fitBounds(
      [
        [manifest.mapView.boundsWgs84[0], manifest.mapView.boundsWgs84[1]],
        [manifest.mapView.boundsWgs84[2], manifest.mapView.boundsWgs84[3]],
      ],
      {
        padding: manifest.mapView.fitPaddingPx,
        bearing: 0,
        pitch: 0,
        duration: 0,
      },
    );
  };
  let readyResolve: () => void = () => undefined;
  const ready = new Promise<void>((resolve, reject) => {
    readyResolve = resolve;
    readyReject = reject;
  });
  const onLoad = (): void => {
    if (disposed) return;
    loaded = true;
    resize();
    if (typeof ResizeObserver !== 'undefined') {
      observer = new ResizeObserver(resize);
      observer.observe(container);
    }
    readyResolve();
  };
  map.once('load', onLoad);
  const onAbort = (): void => {
    map.remove();
    readyReject(
      new DOMException('Overview map load was cancelled', 'AbortError'),
    );
  };
  if (signal?.aborted) onAbort();
  else signal?.addEventListener('abort', onAbort, { once: true });
  try {
    await ready;
  } catch (error) {
    map.off('load', onLoad);
    observer?.disconnect();
    map.off('error', onMapError);
    map.remove();
    signal?.removeEventListener('abort', onAbort);
    throw error;
  }
  signal?.removeEventListener('abort', onAbort);
  return {
    setData: (next) => {
      if (disposed) return;
      const source = map.getSource('overview');
      if (source instanceof maplibre.GeoJSONSource)
        source.setData(next as never);
    },
    resize,
    dispose: () => {
      if (disposed) return;
      disposed = true;
      observer?.disconnect();
      map.off('error', onMapError);
      map.remove();
    },
  };
}
