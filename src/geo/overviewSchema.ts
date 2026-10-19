import type { RealTerrainSceneManifest } from './sceneSchema';

export const MAX_OVERVIEW_MANIFEST_BYTES = 128 * 1024;
export const MAX_OVERVIEW_GEOJSON_BYTES = 8 * 1024 * 1024;
export const MAX_OVERVIEW_FEATURES = 10_000;
export const MAX_OVERVIEW_POSITIONS = 250_000;
export const OVERVIEW_BOUNDARY_TOLERANCE_DEGREES = 1e-6;
export const OVERVIEW_AOI_BOUNDS_M = [
  290608.9018176432, 64853.48350844931, 291608.9018176432, 65853.48350844931,
] as const;
export const OVERVIEW_PINNED_OPERATION = 'EPSG:1314 + EPSG:19916';
export const OVERVIEW_MISSING_GRID = 'uk_os_OSTN15_NTv2_OSGBtoETRS.tif';

export interface OverviewAssetDescriptor {
  path: 'features.geojson';
  byteLength: number;
  sha256: string;
}

export interface OverviewLayerIdentity {
  manifestSha256: string;
  payload: { path: string; byteLength: number; sha256: string };
  qa: { path: string; byteLength: number; sha256: string };
  source: Record<string, unknown>;
  terrainManifestSha256: string;
}

export interface OverviewManifest {
  formatVersion: 1;
  worldId: 'torquay-poc-001';
  worldType: 'real';
  packageType: 'torquay-geographic-overview';
  projection: 'mercator';
  aoi: {
    crs: 'EPSG:27700';
    boundsM: [number, number, number, number];
    centerBngM: [number, number];
    boundaryWgs84: {
      crs: 'EPSG:4326';
      coordinateOrder: 'longitude-latitude';
      ring: [number, number][];
    };
    selectionStatus: 'selected_pending_coverage';
    coverageStatus: 'not_checked';
  };
  mapView: {
    centerWgs84: [number, number];
    boundsWgs84: [number, number, number, number];
    bearingDegrees: 0;
    pitchDegrees: 0;
    fitPaddingPx: number;
  };
  includedLayers: Array<'aoi' | 'roads' | 'buildings'>;
  terrainIdentity: {
    worldId: string;
    manifestSha256: string;
    heightfield: { path: string; byteLength: number; sha256: string };
    origin: { eastingM: number; northingM: number; elevationM: number };
    extentM: { width: number; depth: number };
    grid: { columns: number; rows: number; spacingM: number };
    axisConvention: '+X east, +Y up, -Z north';
    verticalReference: string;
    provenance: Record<string, unknown>;
  };
  optionalLayerIdentities: Partial<
    Record<'roads' | 'buildings', OverviewLayerIdentity>
  >;
  coordinateOperation: {
    axisOrder: string;
    bngToWgs84: Record<string, unknown>;
    wgs84ToBng: Record<string, unknown>;
    coordinateMeaning: string;
  };
  coordinatePolicy: {
    localToBng: string;
    precisionDecimalPlaces: number;
    maximumObservedRoundTripErrorM: number;
    maximumAcceptedRoundTripErrorM: number;
    aoiContainmentToleranceDegrees: number;
    interpretation: string;
  };
  omissions: {
    roadsWithoutAoiCenterline: number;
    roadsPolicy: string;
  };
  counts: {
    featuresByRole: {
      aoi: number;
      roads: number;
      buildings: number;
      total: number;
    };
    positionsByRole: {
      aoi: number;
      roads: number;
      buildings: number;
      total: number;
    };
  };
  features: OverviewAssetDescriptor;
  limits: {
    manifestMaxBytes: number;
    featuresMaxBytes: number;
    maxFeatures: number;
    maxPositions: number;
  };
  generator: Record<string, unknown>;
  sources: Record<string, unknown>;
  coverage: {
    selectionStatus: 'selected_pending_coverage';
    coverageStatus: 'not_checked';
    note: string;
  };
}

export interface OverviewGeoJsonFeature {
  type: 'Feature';
  id: string;
  properties: Record<string, unknown> & { role: 'aoi' | 'road' | 'building' };
  geometry:
    | { type: 'Polygon'; coordinates: [number, number][][] }
    | { type: 'MultiLineString'; coordinates: [number, number][][] }
    | { type: 'MultiPolygon'; coordinates: [number, number][][][] };
}

export interface OverviewFeatureCollection {
  type: 'FeatureCollection';
  features: OverviewGeoJsonFeature[];
}

export interface OverviewValidationIssue {
  path: string;
  message: string;
}

export type OverviewValidationResult<T> =
  { ok: true; value: T } | { ok: false; issues: OverviewValidationIssue[] };

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function isPositiveInteger(value: unknown): value is number {
  return Number.isSafeInteger(value) && (value as number) > 0;
}

function isDigest(value: unknown): value is string {
  return typeof value === 'string' && /^[a-f0-9]{64}$/i.test(value);
}

function addIssue(
  issues: OverviewValidationIssue[],
  path: string,
  message: string,
): void {
  issues.push({ path, message });
}

function equalNumber(left: unknown, right: number, tolerance = 1e-8): boolean {
  return isFiniteNumber(left) && Math.abs(left - right) <= tolerance;
}

function sameNumbers(left: unknown, right: readonly number[]): boolean {
  return (
    Array.isArray(left) &&
    left.length === right.length &&
    left.every((value, index) => equalNumber(value, right[index]!))
  );
}

function expectedMapBounds(
  ring: readonly (readonly number[])[],
): [number, number, number, number] {
  const longitudes = ring.map((position) => position[0]!);
  const latitudes = ring.map((position) => position[1]!);
  return [
    Math.min(...longitudes),
    Math.min(...latitudes),
    Math.max(...longitudes),
    Math.max(...latitudes),
  ];
}

function validateLayerIdentity(
  value: unknown,
  path: string,
  terrainSha: string,
  role: 'roads' | 'buildings',
  issues: OverviewValidationIssue[],
): OverviewLayerIdentity | undefined {
  if (!isRecord(value)) {
    addIssue(issues, path, 'must bind the currently loaded local package');
    return undefined;
  }
  const manifestSha256 = value.manifestSha256;
  const terrainManifestSha256 = value.terrainManifestSha256;
  if (!isDigest(manifestSha256))
    addIssue(issues, `${path}.manifestSha256`, 'must be a SHA-256 digest');
  if (terrainManifestSha256 !== terrainSha)
    addIssue(
      issues,
      `${path}.terrainManifestSha256`,
      'must match the terrain manifest',
    );
  const payload = value.payload;
  const qa = value.qa;
  for (const [name, descriptor] of [
    ['payload', payload],
    ['qa', qa],
  ] as const) {
    if (!isRecord(descriptor)) {
      addIssue(issues, `${path}.${name}`, 'must be an integrity descriptor');
      continue;
    }
    const expectedPath =
      name === 'payload'
        ? `${role === 'roads' ? 'roads' : 'buildings'}.json`
        : 'qa.json';
    if (descriptor.path !== expectedPath)
      addIssue(issues, `${path}.${name}.path`, `must be ${expectedPath}`);
    if (!isPositiveInteger(descriptor.byteLength))
      addIssue(
        issues,
        `${path}.${name}.byteLength`,
        'must be a positive safe integer',
      );
    if (!isDigest(descriptor.sha256))
      addIssue(issues, `${path}.${name}.sha256`, 'must be a SHA-256 digest');
  }
  if (!isRecord(value.source) || !isDigest(value.source.sha256))
    addIssue(
      issues,
      `${path}.source.sha256`,
      'must bind the verified OSM source digest',
    );
  if (
    !isDigest(manifestSha256) ||
    !isRecord(payload) ||
    !isRecord(qa) ||
    !isRecord(value.source)
  ) {
    return undefined;
  }
  return value as unknown as OverviewLayerIdentity;
}

export function validateOverviewManifest(
  input: unknown,
  terrain: RealTerrainSceneManifest,
  terrainManifestSha256: string,
): OverviewValidationResult<OverviewManifest> {
  const issues: OverviewValidationIssue[] = [];
  if (!isRecord(input)) {
    return {
      ok: false,
      issues: [{ path: 'manifest', message: 'must be a JSON object' }],
    };
  }
  if (input.formatVersion !== 1 || typeof input.formatVersion === 'boolean')
    addIssue(issues, 'manifest.formatVersion', 'must be integer 1');
  if (input.worldId !== terrain.id || input.worldId !== 'torquay-poc-001')
    addIssue(
      issues,
      'manifest.worldId',
      'must match the loaded real terrain world',
    );
  if (input.worldType !== 'real')
    addIssue(
      issues,
      'manifest.worldType',
      'must identify the geographic input as real',
    );
  if (input.packageType !== 'torquay-geographic-overview')
    addIssue(issues, 'manifest.packageType', 'is unsupported');
  if (input.projection !== 'mercator')
    addIssue(issues, 'manifest.projection', 'must be mercator');

  const aoi = input.aoi;
  const aoiRing = terrain.aoi.boundaryWgs84.ring;
  if (!isRecord(aoi)) {
    addIssue(issues, 'manifest.aoi', 'must be an object');
  } else {
    if (aoi.crs !== 'EPSG:27700')
      addIssue(issues, 'manifest.aoi.crs', 'must be EPSG:27700');
    if (!sameNumbers(aoi.boundsM, terrain.aoi.boundsM))
      addIssue(
        issues,
        'manifest.aoi.boundsM',
        'must match loaded terrain AOI bounds',
      );
    if (!sameNumbers(aoi.centerBngM, terrain.aoi.centerBngM))
      addIssue(
        issues,
        'manifest.aoi.centerBngM',
        'must match loaded terrain AOI centre',
      );
    if (aoi.selectionStatus !== 'selected_pending_coverage')
      addIssue(issues, 'manifest.aoi.selectionStatus', 'must remain pending');
    if (aoi.coverageStatus !== 'not_checked')
      addIssue(
        issues,
        'manifest.aoi.coverageStatus',
        'must remain not_checked',
      );
    const boundary = aoi.boundaryWgs84;
    if (!isRecord(boundary)) {
      addIssue(
        issues,
        'manifest.aoi.boundaryWgs84',
        'must contain the registered AOI ring',
      );
    } else {
      if (boundary.crs !== 'EPSG:4326')
        addIssue(issues, 'manifest.aoi.boundaryWgs84.crs', 'must be EPSG:4326');
      if (boundary.coordinateOrder !== 'longitude-latitude')
        addIssue(
          issues,
          'manifest.aoi.boundaryWgs84.coordinateOrder',
          'must be longitude-latitude',
        );
      if (
        !Array.isArray(boundary.ring) ||
        JSON.stringify(boundary.ring) !== JSON.stringify(aoiRing)
      )
        addIssue(
          issues,
          'manifest.aoi.boundaryWgs84.ring',
          'must exactly match the loaded AOI ring',
        );
    }
  }

  const mapView = input.mapView;
  if (!isRecord(mapView)) {
    addIssue(
      issues,
      'manifest.mapView',
      'must contain a derived fixed overview frame',
    );
  } else {
    const bounds = expectedMapBounds(aoiRing);
    if (!sameNumbers(mapView.boundsWgs84, bounds))
      addIssue(
        issues,
        'manifest.mapView.boundsWgs84',
        'must be derived from the registered AOI ring',
      );
    const center = mapView.centerWgs84;
    if (
      !Array.isArray(center) ||
      center.length !== 2 ||
      !equalNumber(center[0], (bounds[0] + bounds[2]) / 2) ||
      !equalNumber(center[1], (bounds[1] + bounds[3]) / 2)
    )
      addIssue(
        issues,
        'manifest.mapView.centerWgs84',
        'must be derived from geographic bounds',
      );
    if (mapView.bearingDegrees !== 0 || mapView.pitchDegrees !== 0)
      addIssue(
        issues,
        'manifest.mapView',
        'bearing and pitch must remain north-up and flat',
      );
    if (
      !isFiniteNumber(mapView.fitPaddingPx) ||
      mapView.fitPaddingPx < 0 ||
      mapView.fitPaddingPx > 64
    )
      addIssue(
        issues,
        'manifest.mapView.fitPaddingPx',
        'must be a bounded finite pixel value',
      );
  }

  const includedLayers = input.includedLayers;
  if (
    !Array.isArray(includedLayers) ||
    !includedLayers.includes('aoi') ||
    includedLayers.some(
      (layer) => !['aoi', 'roads', 'buildings'].includes(String(layer)),
    ) ||
    new Set(includedLayers).size !== includedLayers.length
  )
    addIssue(
      issues,
      'manifest.includedLayers',
      'must include aoi and unique supported optional layers',
    );

  const terrainIdentity = input.terrainIdentity;
  if (!isRecord(terrainIdentity)) {
    addIssue(
      issues,
      'manifest.terrainIdentity',
      'must bind the currently loaded terrain package',
    );
  } else {
    if (terrainIdentity.worldId !== terrain.id)
      addIssue(
        issues,
        'manifest.terrainIdentity.worldId',
        'must match the loaded terrain',
      );
    if (terrainIdentity.manifestSha256 !== terrainManifestSha256)
      addIssue(
        issues,
        'manifest.terrainIdentity.manifestSha256',
        'differs from the loaded terrain manifest',
      );
    const field = terrainIdentity.heightfield;
    if (!isRecord(field)) {
      addIssue(
        issues,
        'manifest.terrainIdentity.heightfield',
        'must bind the terrain binary',
      );
    } else {
      if (field.path !== terrain.heightfield.path)
        addIssue(
          issues,
          'manifest.terrainIdentity.heightfield.path',
          'differs from terrain manifest',
        );
      if (field.sha256 !== terrain.heightfield.sha256)
        addIssue(
          issues,
          'manifest.terrainIdentity.heightfield.sha256',
          'differs from terrain manifest',
        );
      if (field.byteLength !== terrain.heightfield.byteLength)
        addIssue(
          issues,
          'manifest.terrainIdentity.heightfield.byteLength',
          'differs from terrain manifest',
        );
    }
    if (
      !isRecord(terrainIdentity.origin) ||
      !equalNumber(terrainIdentity.origin.eastingM, terrain.origin.eastingM) ||
      !equalNumber(
        terrainIdentity.origin.northingM,
        terrain.origin.northingM,
      ) ||
      !equalNumber(terrainIdentity.origin.elevationM, terrain.origin.elevationM)
    )
      addIssue(
        issues,
        'manifest.terrainIdentity.origin',
        'must match loaded terrain origin',
      );
    if (terrainIdentity.axisConvention !== '+X east, +Y up, -Z north')
      addIssue(
        issues,
        'manifest.terrainIdentity.axisConvention',
        'is unsupported',
      );
  }

  const optionalIdentities = input.optionalLayerIdentities;
  if (!isRecord(optionalIdentities)) {
    addIssue(issues, 'manifest.optionalLayerIdentities', 'must be an object');
  } else {
    for (const role of ['roads', 'buildings'] as const) {
      if (Array.isArray(includedLayers) && includedLayers.includes(role)) {
        validateLayerIdentity(
          optionalIdentities[role],
          `manifest.optionalLayerIdentities.${role}`,
          terrainManifestSha256,
          role,
          issues,
        );
      } else if (optionalIdentities[role] !== undefined) {
        addIssue(
          issues,
          `manifest.optionalLayerIdentities.${role}`,
          'must be absent when the layer is not included',
        );
      }
    }
  }

  const coordinateOperation = input.coordinateOperation;
  if (!isRecord(coordinateOperation)) {
    addIssue(
      issues,
      'manifest.coordinateOperation',
      'must identify the pinned coordinate operation',
    );
  } else {
    if (
      coordinateOperation.axisOrder !==
      'longitude-latitude for geographic input; easting-northing for BNG'
    )
      addIssue(
        issues,
        'manifest.coordinateOperation.axisOrder',
        'is unsupported',
      );
    for (const direction of ['bngToWgs84', 'wgs84ToBng'] as const) {
      const operation = coordinateOperation[direction];
      const path = `manifest.coordinateOperation.${direction}`;
      if (!isRecord(operation)) {
        addIssue(
          issues,
          path,
          'must include the complete pinned operation metadata',
        );
        continue;
      }
      if (operation.name !== OVERVIEW_PINNED_OPERATION)
        addIssue(
          issues,
          `${path}.name`,
          'must identify the pinned EPSG operation',
        );
      if (
        !isFiniteNumber(operation.reported_accuracy_m) ||
        operation.reported_accuracy_m !== 2
      )
        addIssue(issues, `${path}.reported_accuracy_m`, 'must report 2 m');
      if (operation.uses_grids !== false || operation.best_available !== false)
        addIssue(
          issues,
          path,
          'must disclose the no-grid, non-best-available operation status',
        );
      const missing = operation.preferred_missing_operations;
      if (
        !Array.isArray(missing) ||
        !missing.some(
          (item) =>
            isRecord(item) &&
            Array.isArray(item.grids) &&
            item.grids.some(
              (grid) =>
                isRecord(grid) &&
                grid.short_name === OVERVIEW_MISSING_GRID &&
                grid.available === false,
            ),
        )
      )
        addIssue(
          issues,
          `${path}.preferred_missing_operations`,
          'must record the unavailable preferred OSTN15 grid',
        );
    }
  }

  const policy = input.coordinatePolicy;
  if (!isRecord(policy)) {
    addIssue(
      issues,
      'manifest.coordinatePolicy',
      'must document transform precision and caveat',
    );
  } else {
    if (policy.localToBng !== 'E=eastingOrigin+x; N=northingOrigin-z')
      addIssue(
        issues,
        'manifest.coordinatePolicy.localToBng',
        'must use the documented local axis mapping',
      );
    if (policy.precisionDecimalPlaces !== 9)
      addIssue(
        issues,
        'manifest.coordinatePolicy.precisionDecimalPlaces',
        'must be 9 decimal places',
      );
    if (
      !isFiniteNumber(policy.maximumObservedRoundTripErrorM) ||
      policy.maximumObservedRoundTripErrorM < 0 ||
      policy.maximumObservedRoundTripErrorM > 0.02
    )
      addIssue(
        issues,
        'manifest.coordinatePolicy.maximumObservedRoundTripErrorM',
        'must be finite and at most 0.02 m',
      );
    if (policy.maximumAcceptedRoundTripErrorM !== 0.02)
      addIssue(
        issues,
        'manifest.coordinatePolicy.maximumAcceptedRoundTripErrorM',
        'must be 0.02 m',
      );
    if (
      policy.aoiContainmentToleranceDegrees !==
      OVERVIEW_BOUNDARY_TOLERANCE_DEGREES
    )
      addIssue(
        issues,
        'manifest.coordinatePolicy.aoiContainmentToleranceDegrees',
        'must match the documented geographic boundary tolerance',
      );
    if (
      typeof policy.interpretation !== 'string' ||
      !policy.interpretation.toLowerCase().includes('not survey-accurate')
    )
      addIssue(
        issues,
        'manifest.coordinatePolicy.interpretation',
        'must distinguish numerical consistency from survey accuracy',
      );
  }

  const omissions = input.omissions;
  if (!isRecord(omissions)) {
    addIssue(
      issues,
      'manifest.omissions',
      'must disclose records omitted from the geographic overview',
    );
  } else {
    if (
      !Number.isSafeInteger(omissions.roadsWithoutAoiCenterline) ||
      (omissions.roadsWithoutAoiCenterline as number) < 0
    )
      addIssue(
        issues,
        'manifest.omissions.roadsWithoutAoiCenterline',
        'must be a nonnegative safe integer',
      );
    if (
      typeof omissions.roadsPolicy !== 'string' ||
      !omissions.roadsPolicy.toLowerCase().includes('no clipped centerline')
    )
      addIssue(
        issues,
        'manifest.omissions.roadsPolicy',
        'must explain centerline omissions',
      );
  }

  const counts = input.counts;
  if (
    !isRecord(counts) ||
    !isRecord(counts.featuresByRole) ||
    !isRecord(counts.positionsByRole)
  ) {
    addIssue(
      issues,
      'manifest.counts',
      'must contain feature and position counts by role',
    );
  } else {
    for (const path of ['featuresByRole', 'positionsByRole'] as const) {
      const values = counts[path];
      if (!isRecord(values)) continue;
      for (const key of ['aoi', 'roads', 'buildings', 'total']) {
        if (!Number.isSafeInteger(values[key]) || (values[key] as number) < 0)
          addIssue(
            issues,
            `manifest.counts.${path}.${key}`,
            'must be a nonnegative safe integer',
          );
      }
    }
    if (isRecord(counts.featuresByRole) && counts.featuresByRole.aoi !== 1)
      addIssue(
        issues,
        'manifest.counts.featuresByRole.aoi',
        'must be exactly one',
      );
    if (
      isRecord(counts.featuresByRole) &&
      counts.featuresByRole.total !==
        Number(counts.featuresByRole.aoi) +
          Number(counts.featuresByRole.roads) +
          Number(counts.featuresByRole.buildings)
    )
      addIssue(
        issues,
        'manifest.counts.featuresByRole.total',
        'must equal the role counts',
      );
    if (
      isRecord(counts.positionsByRole) &&
      counts.positionsByRole.total !==
        Number(counts.positionsByRole.aoi) +
          Number(counts.positionsByRole.roads) +
          Number(counts.positionsByRole.buildings)
    )
      addIssue(
        issues,
        'manifest.counts.positionsByRole.total',
        'must equal the role counts',
      );
    if (
      isRecord(counts.featuresByRole) &&
      Number(counts.featuresByRole.total) > MAX_OVERVIEW_FEATURES
    )
      addIssue(
        issues,
        'manifest.counts.featuresByRole.total',
        'exceeds the overview feature limit',
      );
    if (
      isRecord(counts.positionsByRole) &&
      Number(counts.positionsByRole.total) > MAX_OVERVIEW_POSITIONS
    )
      addIssue(
        issues,
        'manifest.counts.positionsByRole.total',
        'exceeds the overview position limit',
      );
  }

  const descriptor = input.features;
  if (!isRecord(descriptor)) {
    addIssue(
      issues,
      'manifest.features',
      'must describe the local GeoJSON asset',
    );
  } else {
    if (descriptor.path !== 'features.geojson')
      addIssue(
        issues,
        'manifest.features.path',
        'must be package-local features.geojson',
      );
    if (
      !isPositiveInteger(descriptor.byteLength) ||
      descriptor.byteLength > MAX_OVERVIEW_GEOJSON_BYTES
    )
      addIssue(
        issues,
        'manifest.features.byteLength',
        'must be within the 8 MiB limit',
      );
    if (!isDigest(descriptor.sha256))
      addIssue(issues, 'manifest.features.sha256', 'must be a SHA-256 digest');
  }
  if (
    !isRecord(input.coverage) ||
    input.coverage.selectionStatus !== 'selected_pending_coverage' ||
    input.coverage.coverageStatus !== 'not_checked' ||
    typeof input.coverage.note !== 'string' ||
    !input.coverage.note.toLowerCase().includes('do not establish')
  )
    addIssue(
      issues,
      'manifest.coverage',
      'must preserve pending status and the completeness caveat',
    );
  if (
    !isRecord(input.sources) ||
    !isRecord(input.sources.terrain) ||
    !isRecord(input.sources.mapLibre)
  )
    addIssue(
      issues,
      'manifest.sources',
      'must include terrain and MapLibre source details',
    );

  if (issues.length > 0) return { ok: false, issues };
  return { ok: true, value: input as unknown as OverviewManifest };
}

function pointInRing(
  point: readonly number[],
  ring: readonly (readonly number[])[],
): boolean {
  const [x, y] = point;
  if (x === undefined || y === undefined) return false;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i]?.[0];
    const yi = ring[i]?.[1];
    const xj = ring[j]?.[0];
    const yj = ring[j]?.[1];
    if (
      xi === undefined ||
      yi === undefined ||
      xj === undefined ||
      yj === undefined
    )
      continue;
    const crosses =
      yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (crosses) inside = !inside;
  }
  return inside;
}

function withinRingTolerance(
  point: readonly number[],
  ring: readonly (readonly number[])[],
): boolean {
  const [x, y] = point;
  if (x === undefined || y === undefined) return false;
  for (let index = 0; index < ring.length - 1; index += 1) {
    const left = ring[index];
    const right = ring[index + 1];
    if (!left || !right) continue;
    const dx = right[0]! - left[0]!;
    const dy = right[1]! - left[1]!;
    const lengthSquared = dx * dx + dy * dy;
    const t =
      lengthSquared === 0
        ? 0
        : Math.max(
            0,
            Math.min(
              1,
              ((x - left[0]!) * dx + (y - left[1]!) * dy) / lengthSquared,
            ),
          );
    const nearestX = left[0]! + t * dx;
    const nearestY = left[1]! + t * dy;
    if (
      Math.hypot(x - nearestX, y - nearestY) <=
      OVERVIEW_BOUNDARY_TOLERANCE_DEGREES
    )
      return true;
  }
  return false;
}

function coordinate(
  value: unknown,
  path: string,
  ring: readonly (readonly number[])[],
  issues: OverviewValidationIssue[],
): value is [number, number] {
  if (
    !Array.isArray(value) ||
    value.length !== 2 ||
    !isFiniteNumber(value[0]) ||
    !isFiniteNumber(value[1]) ||
    value[0] < -180 ||
    value[0] > 180 ||
    value[1] < -90 ||
    value[1] > 90
  ) {
    addIssue(issues, path, 'must be a finite WGS84 [longitude, latitude] pair');
    return false;
  }
  if (!pointInRing(value, ring)) {
    if (!withinRingTolerance(value, ring))
      addIssue(issues, path, 'lies outside the registered AOI');
  }
  return true;
}

function validateLine(
  value: unknown,
  path: string,
  ring: readonly (readonly number[])[],
  issues: OverviewValidationIssue[],
  count: { value: number },
): value is [number, number][] {
  if (!Array.isArray(value) || value.length < 2) {
    addIssue(issues, path, 'must contain at least two positions');
    return false;
  }
  value.forEach((point, index) => {
    coordinate(point, `${path}[${index}]`, ring, issues);
    count.value += 1;
  });
  return true;
}

function validateRing(
  value: unknown,
  path: string,
  exterior: boolean,
  ring: readonly (readonly number[])[],
  issues: OverviewValidationIssue[],
  count: { value: number },
): value is [number, number][] {
  if (!Array.isArray(value) || value.length < 4) {
    addIssue(issues, path, 'must contain at least four closed positions');
    return false;
  }
  const parsed: [number, number][] = [];
  value.forEach((point, index) => {
    if (coordinate(point, `${path}[${index}]`, ring, issues))
      parsed.push(point);
    count.value += 1;
  });
  if (
    parsed.length === value.length &&
    JSON.stringify(parsed[0]) !== JSON.stringify(parsed.at(-1))
  )
    addIssue(issues, path, 'must be closed');
  let area = 0;
  for (let index = 0; index < parsed.length - 1; index += 1) {
    const left = parsed[index]!;
    const right = parsed[index + 1]!;
    area += left[0] * right[1] - right[0] * left[1];
  }
  if (area > 0 !== exterior)
    addIssue(issues, path, 'has incorrect RFC 7946 winding');
  return parsed.length === value.length;
}

export function validateOverviewFeatureCollection(
  input: unknown,
  manifest: OverviewManifest,
): OverviewValidationResult<OverviewFeatureCollection> {
  const issues: OverviewValidationIssue[] = [];
  if (
    !isRecord(input) ||
    input.type !== 'FeatureCollection' ||
    !Array.isArray(input.features)
  ) {
    return {
      ok: false,
      issues: [
        { path: 'features', message: 'must be a GeoJSON FeatureCollection' },
      ],
    };
  }
  if (input.features.length !== manifest.counts.featuresByRole.total)
    addIssue(
      issues,
      'features.features',
      'count differs from the integrity-bound manifest',
    );
  if (input.features.length > MAX_OVERVIEW_FEATURES)
    addIssue(issues, 'features.features', 'exceeds the 10,000-feature limit');
  const aoiRing = manifest.aoi.boundaryWgs84.ring;
  const seen = new Set<string>();
  const roleCounts = { aoi: 0, roads: 0, buildings: 0 };
  const positions = { aoi: 0, roads: 0, buildings: 0 };
  const parsed: OverviewGeoJsonFeature[] = [];
  input.features.forEach((raw, index) => {
    const path = `features.features[${index}]`;
    if (
      !isRecord(raw) ||
      raw.type !== 'Feature' ||
      typeof raw.id !== 'string' ||
      !isRecord(raw.properties) ||
      !isRecord(raw.geometry)
    ) {
      addIssue(
        issues,
        path,
        'must be a GeoJSON Feature with an ID, properties and geometry',
      );
      return;
    }
    if (seen.has(raw.id)) addIssue(issues, `${path}.id`, 'must be unique');
    seen.add(raw.id);
    const role = raw.properties.role;
    if (role !== 'aoi' && role !== 'road' && role !== 'building') {
      addIssue(
        issues,
        `${path}.properties.role`,
        'must be aoi, road, or building',
      );
      return;
    }
    roleCounts[
      role === 'road' ? 'roads' : role === 'building' ? 'buildings' : 'aoi'
    ] += 1;
    const geometry = raw.geometry;
    let parsedGeometry: OverviewGeoJsonFeature['geometry'] | undefined;
    const count = { value: 0 };
    if (role === 'aoi') {
      if (
        raw.id !== 'aoi:torquay-poc-001' ||
        geometry.type !== 'Polygon' ||
        !Array.isArray(geometry.coordinates) ||
        JSON.stringify(geometry.coordinates) !== JSON.stringify([aoiRing])
      )
        addIssue(
          issues,
          `${path}.geometry`,
          'must preserve the exact registered AOI polygon',
        );
      positions.aoi += aoiRing.length;
      parsedGeometry = { type: 'Polygon', coordinates: [aoiRing] };
    } else if (role === 'road') {
      if (
        !raw.id.startsWith('road:') ||
        geometry.type !== 'MultiLineString' ||
        !Array.isArray(geometry.coordinates) ||
        geometry.coordinates.length === 0
      ) {
        addIssue(
          issues,
          `${path}.geometry`,
          'road must be a namespaced MultiLineString',
        );
      } else {
        const lines: [number, number][][] = [];
        geometry.coordinates.forEach((line, lineIndex) => {
          if (
            validateLine(
              line,
              `${path}.geometry.coordinates[${lineIndex}]`,
              aoiRing,
              issues,
              count,
            )
          )
            lines.push(line);
        });
        positions.roads += count.value;
        parsedGeometry = { type: 'MultiLineString', coordinates: lines };
      }
      if (
        typeof raw.properties.sourceId !== 'string' ||
        !raw.id.endsWith(raw.properties.sourceId)
      )
        addIssue(
          issues,
          `${path}.properties.sourceId`,
          'must match the stable source ID',
        );
      if (
        raw.properties.name !== null &&
        typeof raw.properties.name !== 'string'
      )
        addIssue(issues, `${path}.properties.name`, 'must be text or null');
      if (
        typeof raw.properties.highway !== 'string' ||
        typeof raw.properties.displayGroup !== 'string'
      )
        addIssue(
          issues,
          `${path}.properties`,
          'must retain the road class and display group',
        );
    } else {
      if (
        !raw.id.startsWith('building:') ||
        geometry.type !== 'MultiPolygon' ||
        !Array.isArray(geometry.coordinates) ||
        geometry.coordinates.length === 0
      ) {
        addIssue(
          issues,
          `${path}.geometry`,
          'building must be a namespaced MultiPolygon',
        );
      } else {
        const polygons: [number, number][][][] = [];
        geometry.coordinates.forEach((polygon, polygonIndex) => {
          if (!Array.isArray(polygon) || polygon.length === 0) {
            addIssue(
              issues,
              `${path}.geometry.coordinates[${polygonIndex}]`,
              'must contain an exterior ring',
            );
            return;
          }
          const rings: [number, number][][] = [];
          polygon.forEach((ring, ringIndex) => {
            if (
              validateRing(
                ring,
                `${path}.geometry.coordinates[${polygonIndex}][${ringIndex}]`,
                ringIndex === 0,
                aoiRing,
                issues,
                count,
              )
            )
              rings.push(ring);
          });
          if (rings.length > 0) polygons.push(rings);
        });
        positions.buildings += count.value;
        parsedGeometry = { type: 'MultiPolygon', coordinates: polygons };
      }
      if (
        typeof raw.properties.sourceId !== 'string' ||
        !raw.id.endsWith(raw.properties.sourceId)
      )
        addIssue(
          issues,
          `${path}.properties.sourceId`,
          'must match the stable source ID',
        );
      if (!Number.isSafeInteger(raw.properties.osmId))
        addIssue(
          issues,
          `${path}.properties.osmId`,
          'must be the source OSM identity',
        );
    }
    if (
      role === 'aoi' &&
      raw.properties.selectionStatus !== 'selected_pending_coverage'
    )
      addIssue(
        issues,
        `${path}.properties.selectionStatus`,
        'must preserve pending AOI status',
      );
    if (role === 'aoi' && raw.properties.coverageStatus !== 'not_checked')
      addIssue(
        issues,
        `${path}.properties.coverageStatus`,
        'must remain not_checked',
      );
    if (parsedGeometry) {
      parsed.push({
        type: 'Feature',
        id: raw.id,
        properties: raw.properties as OverviewGeoJsonFeature['properties'],
        geometry: parsedGeometry,
      });
    }
  });
  if (roleCounts.aoi !== 1)
    addIssue(
      issues,
      'features.features',
      'must contain exactly one AOI feature',
    );
  for (const key of ['roads', 'buildings'] as const) {
    if (roleCounts[key] !== manifest.counts.featuresByRole[key])
      addIssue(
        issues,
        `features.features.${key}`,
        'does not match the manifest role count',
      );
    if (positions[key] !== manifest.counts.positionsByRole[key])
      addIssue(
        issues,
        `features.features.${key}`,
        'position count does not match the manifest',
      );
  }
  if (positions.aoi !== manifest.counts.positionsByRole.aoi)
    addIssue(
      issues,
      'features.features.aoi',
      'AOI position count does not match the manifest',
    );
  const positionTotal = positions.aoi + positions.roads + positions.buildings;
  if (positionTotal > MAX_OVERVIEW_POSITIONS)
    addIssue(issues, 'features.features', 'exceeds the 250,000-position limit');
  if (issues.length > 0) return { ok: false, issues };
  return { ok: true, value: { type: 'FeatureCollection', features: parsed } };
}

export function formatOverviewIssues(
  issues: OverviewValidationIssue[],
): string {
  return issues.map(({ path, message }) => `${path}: ${message}`).join('; ');
}
