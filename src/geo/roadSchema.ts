import type { RealTerrainSceneManifest } from './sceneSchema';

export const MAX_ROAD_MANIFEST_BYTES = 64 * 1024;
export const MAX_ROAD_QA_BYTES = 2 * 1024 * 1024;
export const MAX_ROADS_BYTES = 32 * 1024 * 1024;
export const MAX_ROAD_WAYS = 100_000;
export const MAX_ROAD_VERTICES = 1_000_000;
export const MAX_ROAD_TRIANGLES = 1_000_000;
export const ROAD_SURFACE_OFFSET_M = 0.05;
export const ROAD_FLOAT32_SLIVER_POLICY =
  'Cull triangles only when fewer than three distinct [x,z] coordinates remain after Float32 conversion; report the count and omitted area, bounded to 1e-6 m2.';
export const ROAD_ESTIMATED_WIDTHS_M: Readonly<Record<string, number>> = {
  motorway: 12,
  trunk: 12,
  primary: 10,
  secondary: 8,
  tertiary: 7,
  unclassified: 6,
  residential: 6,
  motorway_link: 6,
  trunk_link: 6,
  primary_link: 6,
  secondary_link: 6,
  tertiary_link: 6,
  living_street: 5,
  road: 5,
  service: 3.5,
  track: 3,
  pedestrian: 3,
  cycleway: 2,
  bridleway: 2.5,
  footway: 1.5,
  path: 1.5,
};
export const ROAD_PATH_CLASSES = new Set([
  'track',
  'pedestrian',
  'cycleway',
  'bridleway',
  'footway',
  'path',
]);
export const ROAD_GROUPS = ['vehicular', 'cycleway', 'path'] as const;
export type RoadDisplayGroup = (typeof ROAD_GROUPS)[number];

export interface RoadPackageManifest {
  formatVersion: 1;
  worldId: string;
  name: string;
  packageType: 'osm-road-ribbons';
  sourceCrs: 'EPSG:27700';
  axisConvention: '+X east, +Y up, -Z north';
  units: 'metres';
  aoi: {
    crs: 'EPSG:27700';
    boundsM: [number, number, number, number];
    centerBngM: [number, number];
    widthM: number;
    heightM: number;
    boundaryWgs84: {
      crs: 'EPSG:4326';
      coordinateOrder: 'longitude-latitude';
      closedRing: true;
      ring: [number, number][];
    };
    selectionStatus: 'selected_pending_coverage';
    coverageStatus: 'not_checked';
  };
  terrainIdentity: {
    worldId: string;
    origin: { eastingM: number; northingM: number; elevationM: number };
    heightfieldPath: string;
    heightfieldSha256: string;
    heightfieldByteLength: number;
    heightfieldDimensions: [number, number];
    verticalReference: string;
    manifestSha256: string;
    extentM: { width: number; depth: number };
    columns: number;
    rows: number;
    spacingM: number;
    axisConvention: '+X east, +Y up, -Z north';
  };
  coordinateOperation: {
    axisOrder: string;
    wgs84ToBng: {
      name: string;
      definition: string;
      reported_accuracy_m: number;
      accuracy_m: number;
      uses_grids: false;
      best_available: false;
      grid_status: string;
      preferred_missing_operations: Array<{
        name: string;
        reported_accuracy_m: number;
        grids: Array<{ short_name: string; available: false; url: string }>;
      }>;
    };
    bngToWgs84: {
      name: string;
      definition: string;
      reported_accuracy_m: number;
      accuracy_m: number;
      uses_grids: false;
      best_available: false;
      grid_status: string;
      preferred_missing_operations: Array<{
        name: string;
        reported_accuracy_m: number;
        grids: Array<{ short_name: string; available: false; url: string }>;
      }>;
    };
  };
  source: {
    publisher: string;
    product: string;
    downloadPageUrl: string;
    fileUrl: string;
    checksumUrl: string;
    acquisitionDate: string;
    acquiredAtUtc: string;
    filename: string;
    sizeBytes: number;
    sha256: string;
    publisherMd5: string;
    extractTimestamp: string;
    replicationSequence: string;
    generator: string;
    boundsWgs84LonLat: [number, number, number, number];
    licence: string;
    licenceUrl: string;
    attribution: string;
    attributionRequirement: string;
    sourceStorage: string;
  };
  policies: {
    version: 1;
    acquisitionBufferM: number;
    coordinateQuantizationM: number;
    minimumRibbonAreaM2: number;
    fullWidthsM: Record<string, number>;
    pathClasses: string[];
    excludedClasses: string[];
    groundAssumption: Record<string, string>;
    areaSurfacePolicy: string;
    buffer: Record<string, unknown>;
    clip: string;
    displayPriority: string[];
    triangulation: string;
    surfaceOffsetM: number;
    float32SliverPolicy: string;
  };
  generator: {
    name: string;
    version: string;
    shapelyVersion: string;
    geosVersion: string;
  };
  limits: {
    maxManifestBytes: number;
    maxQaBytes: number;
    maxPayloadBytes: number;
    maxWays: number;
    maxVertices: number;
    maxTriangles: number;
  };
  counts: Record<string, number>;
  assets: {
    roads: { path: 'roads.json'; byteLength: number; sha256: string };
    qa: { path: 'qa.json'; byteLength: number; sha256: string };
  };
  coverage: {
    selectionStatus: 'selected_pending_coverage';
    coverageStatus: 'not_checked';
    note: string;
  };
  attribution: {
    text: string;
    licence: string;
    licenceUrl: string;
    geofabrikCredit: string;
    environmentAgency: string;
    environmentAgencySourceUrl: string;
  };
}

export interface RoadFeature {
  id: string;
  source: {
    dataset: 'OpenStreetMap';
    objectType: 'way';
    osmId: number;
    version: number;
    timestamp: string | null;
    nodeIds: number[];
  };
  highway: string;
  displayGroup: RoadDisplayGroup;
  estimatedWidthM: number;
  widthMethod: 'configured_visual_estimate';
  widthEvidence: {
    rawWidth: string | null;
    rawLanes: string | null;
    usedRawTags: false;
    note: string;
  };
  groundAssumption: 'ground_assumed_from_absent_or_explicit_no_vertical_tags';
  sourceTags: Record<string, string>;
  centerlinePartsXZ: [number, number][][];
  partIds: string[];
  clippedToAoi: true;
  duplicateWayIds: number[];
  ribbonAreaM2: number;
  ribbonPartIds: string[];
}

export interface RoadSurfaceBatch {
  verticesXZ: [number, number][];
  indices: [number, number, number][];
  terrainTriangles: [number, number, 0 | 1][];
}

export interface RoadQaSummary {
  formatVersion: 1;
  worldId: string;
  status: 'pass';
  selectionStatus: 'selected_pending_coverage';
  coverageStatus: 'not_checked';
  source: RoadPackageManifest['source'];
  counts: Record<string, number>;
  displayBatches: Record<
    RoadDisplayGroup,
    {
      uniqueWayCount: number;
      clippedCenterlinePartCount: number;
      vertexCount: number;
      triangleCount: number;
      surfaceAreaM2: number;
      bufferedAreaBeforePriorityM2: number;
    }
  >;
  areas: {
    byDisplayGroupM2: Record<RoadDisplayGroup, number>;
    totalDisjointSurfaceM2: number;
    overlayPriority: string[];
    areaDifferenceWithinDeclaredTolerance: true;
  };
  meshNumerics: {
    float32CollapsedSliverTriangleCount: number;
    float32CollapsedSliverAreaM2: number;
    maximumOmittedAreaM2: 1e-6;
    policy: string;
  };
  coordinateOperation: RoadPackageManifest['coordinateOperation'];
  surfacePolicy: Record<string, unknown>;
  landmarkContexts: Array<{
    id: string;
    label: string;
    buildingWayId: number;
    pointRole: string;
    buildingRepresentativeLocalXZ: [number, number];
    targetRoadNames: string[];
    targetRoadNamePresent: boolean;
    nearestRoad: null | {
      wayId: number;
      name: string | null;
      highway: string;
      nodeIds: number[];
      nearestPointLocalXZ: [number, number];
      distanceFromBuildingRepresentativeM: number;
    };
    observation: string;
    limitations?: string;
  }>;
  interpretation: string;
}

export interface RoadValidationIssue {
  path: string;
  message: string;
}

export interface LoadedRoadPackage {
  manifest: RoadPackageManifest;
  features: RoadFeature[];
  batches: Record<RoadDisplayGroup, RoadSurfaceBatch>;
  qa: RoadQaSummary;
  partCount: number;
  countsByGroup: Record<RoadDisplayGroup, number>;
}

export type RoadValidationResult<T> =
  { ok: true; value: T } | { ok: false; issues: RoadValidationIssue[] };

type ObjectRecord = Record<string, unknown>;

function isRecord(value: unknown): value is ObjectRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function isPositiveInteger(value: unknown): value is number {
  return Number.isSafeInteger(value) && (value as number) > 0;
}

function isStringRecord(value: unknown): value is Record<string, string> {
  return (
    isRecord(value) &&
    Object.values(value).every((item) => typeof item === 'string')
  );
}

function equalNumber(left: unknown, right: number, tolerance = 1e-7): boolean {
  return isFiniteNumber(left) && Math.abs(left - right) <= tolerance;
}

function sameJson(left: unknown, right: unknown): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

function point(value: unknown): value is [number, number] {
  return (
    Array.isArray(value) &&
    value.length === 2 &&
    isFiniteNumber(value[0]) &&
    isFiniteNumber(value[1])
  );
}

function addIssue(
  issues: RoadValidationIssue[],
  path: string,
  message: string,
): void {
  issues.push({ path, message });
}

function expectedGroup(highway: string): RoadDisplayGroup {
  if (highway === 'cycleway') return 'cycleway';
  return ROAD_PATH_CLASSES.has(highway) ? 'path' : 'vehicular';
}

function validateOperation(
  value: unknown,
  terrain: RealTerrainSceneManifest,
  issues: RoadValidationIssue[],
): void {
  const path = 'coordinateOperation';
  if (!isRecord(value) || typeof value.axisOrder !== 'string') {
    addIssue(
      issues,
      path,
      'must include a documented axisOrder and both pinned operations',
    );
    return;
  }
  for (const direction of ['wgs84ToBng', 'bngToWgs84'] as const) {
    const operation = value[direction];
    const opPath = `${path}.${direction}`;
    if (!isRecord(operation)) {
      addIssue(issues, opPath, 'must be an operation metadata object');
      continue;
    }
    if (operation.name !== 'EPSG:1314 + EPSG:19916') {
      addIssue(
        issues,
        `${opPath}.name`,
        'must use the pinned EPSG:1314 + EPSG:19916 candidate',
      );
    }
    if (direction === 'wgs84ToBng') {
      const expected = terrain.provenance.coordinateOperation;
      if (
        operation.name !== expected.name ||
        operation.definition !== expected.definition ||
        operation.reported_accuracy_m !== expected.reportedAccuracyM ||
        operation.accuracy_m !== expected.reportedAccuracyM ||
        operation.uses_grids !== expected.selectedUsesGrids ||
        operation.best_available !== expected.bestAvailable ||
        !Array.isArray(operation.preferred_missing_operations) ||
        !operation.preferred_missing_operations.some(
          (item) =>
            isRecord(item) &&
            Array.isArray(item.grids) &&
            item.grids.some(
              (grid) =>
                isRecord(grid) &&
                expected.preferredMissingGridNames.includes(
                  String(grid.short_name),
                ),
            ),
        )
      ) {
        addIssue(
          issues,
          opPath,
          'does not match the loaded terrain manifest pinned operation and grid caveat',
        );
      }
    }
    if (
      typeof operation.definition !== 'string' ||
      !operation.definition.startsWith('proj=pipeline') ||
      !operation.definition.includes('x=446.448 y=-125.157 z=542.06') ||
      !operation.definition.includes('lon_0=-2') ||
      !operation.definition.includes('x_0=400000 y_0=-100000')
    ) {
      addIssue(
        issues,
        `${opPath}.definition`,
        'does not match the locally pinned coordinate operation',
      );
    }
    if (operation.reported_accuracy_m !== 2 || operation.accuracy_m !== 2) {
      addIssue(
        issues,
        `${opPath}.accuracy_m`,
        'must preserve the pinned 2 m reported accuracy',
      );
    }
    if (operation.uses_grids !== false || operation.best_available !== false) {
      addIssue(
        issues,
        `${opPath}.uses_grids`,
        'must record the selected no-grid operation and missing preferred grid',
      );
    }
    if (
      typeof operation.grid_status !== 'string' ||
      !operation.grid_status.includes('uses no grid files')
    ) {
      addIssue(
        issues,
        `${opPath}.grid_status`,
        'must disclose that the selected operation uses no grid files',
      );
    }
    if (
      !Array.isArray(operation.preferred_missing_operations) ||
      !operation.preferred_missing_operations.some(
        (item) =>
          isRecord(item) &&
          Array.isArray(item.grids) &&
          item.grids.some(
            (grid) =>
              isRecord(grid) &&
              grid.short_name === 'uk_os_OSTN15_NTv2_OSGBtoETRS.tif' &&
              grid.available === false,
          ),
      )
    ) {
      addIssue(
        issues,
        `${opPath}.preferred_missing_operations`,
        'must disclose the unavailable preferred OSTN15 grid',
      );
    }
  }
}

/** Unknown-safe real road manifest validation bound to the loaded terrain. */
export function validateRoadManifest(
  input: unknown,
  terrain: RealTerrainSceneManifest,
): RoadValidationResult<RoadPackageManifest> {
  const issues: RoadValidationIssue[] = [];
  if (!isRecord(input)) {
    return {
      ok: false,
      issues: [{ path: 'manifest', message: 'must be an object' }],
    };
  }
  if (input.formatVersion !== 1 || input.worldId !== 'torquay-poc-001') {
    addIssue(
      issues,
      'formatVersion/worldId',
      'must identify v1 torquay-poc-001 roads',
    );
  }
  if (input.packageType !== 'osm-road-ribbons')
    addIssue(issues, 'packageType', 'must be osm-road-ribbons');
  if (
    input.sourceCrs !== 'EPSG:27700' ||
    input.axisConvention !== '+X east, +Y up, -Z north' ||
    input.units !== 'metres'
  ) {
    addIssue(
      issues,
      'sourceCrs/axisConvention/units',
      'must use local BNG metres with +X east, +Y up, -Z north',
    );
  }
  if (!isRecord(input.aoi)) {
    addIssue(issues, 'aoi', 'must describe the exact pending terrain AOI');
  } else {
    const aoi = input.aoi;
    if (
      aoi.crs !== 'EPSG:27700' ||
      aoi.selectionStatus !== 'selected_pending_coverage' ||
      aoi.coverageStatus !== 'not_checked'
    ) {
      addIssue(
        issues,
        'aoi',
        'must preserve EPSG:27700 and pending/not_checked status',
      );
    }
    if (
      !sameJson(aoi.boundsM, terrain.aoi.boundsM) ||
      !equalNumber(aoi.widthM, terrain.aoi.widthM) ||
      !equalNumber(aoi.heightM, terrain.aoi.heightM) ||
      !sameJson(aoi.centerBngM, terrain.aoi.centerBngM)
    ) {
      addIssue(
        issues,
        'aoi.boundsM',
        'must match the loaded terrain AOI bounds, center, and extents',
      );
    }
    const boundary = aoi.boundaryWgs84;
    if (
      !isRecord(boundary) ||
      boundary.crs !== 'EPSG:4326' ||
      boundary.coordinateOrder !== 'longitude-latitude' ||
      boundary.closedRing !== true ||
      !sameJson(boundary.ring, terrain.aoi.boundaryWgs84.ring)
    ) {
      addIssue(
        issues,
        'aoi.boundaryWgs84',
        'must match the loaded terrain generated WGS84 AOI ring',
      );
    }
  }
  if (!isRecord(input.terrainIdentity)) {
    addIssue(
      issues,
      'terrainIdentity',
      'must bind to the loaded terrain package',
    );
  } else {
    const identity = input.terrainIdentity;
    if (
      identity.worldId !== terrain.id ||
      !isRecord(identity.origin) ||
      !equalNumber(identity.origin.eastingM, terrain.origin.eastingM) ||
      !equalNumber(identity.origin.northingM, terrain.origin.northingM) ||
      !equalNumber(identity.origin.elevationM, terrain.origin.elevationM) ||
      identity.heightfieldPath !== terrain.heightfield.path ||
      identity.heightfieldSha256 !== terrain.heightfield.sha256 ||
      identity.heightfieldByteLength !== terrain.heightfield.byteLength ||
      !sameJson(identity.heightfieldDimensions, [
        terrain.heightfield.columns,
        terrain.heightfield.rows,
      ]) ||
      !equalNumber(
        (identity.extentM as ObjectRecord | undefined)?.width,
        terrain.extentM.width,
      ) ||
      !equalNumber(
        (identity.extentM as ObjectRecord | undefined)?.depth,
        terrain.extentM.depth,
      ) ||
      identity.columns !== terrain.heightfield.columns ||
      identity.rows !== terrain.heightfield.rows ||
      !equalNumber(identity.spacingM, terrain.heightfield.spacingM) ||
      identity.axisConvention !== terrain.axisConvention ||
      identity.verticalReference !== terrain.provenance.verticalReference ||
      typeof identity.manifestSha256 !== 'string' ||
      !/^[a-f0-9]{64}$/.test(identity.manifestSha256)
    ) {
      addIssue(
        issues,
        'terrainIdentity',
        'does not match the loaded terrain origin, heightfield hash/size/grid, vertical reference, or manifest binding',
      );
    }
  }
  validateOperation(input.coordinateOperation, terrain, issues);
  const source = input.source;
  if (
    !isRecord(source) ||
    source.filename !== 'devon-261016.osm.pbf' ||
    source.sha256 !==
      '52942b39636e1cb002e5d78a004668996cb469ee9c9e9b9b93049c66b9ac2cd5' ||
    source.licence !== 'Open Database Licence 1.0 (ODbL)' ||
    source.licenceUrl !== 'https://www.openstreetmap.org/copyright' ||
    !isPositiveInteger(source.sizeBytes) ||
    typeof source.extractTimestamp !== 'string' ||
    typeof source.fileUrl !== 'string' ||
    typeof source.downloadPageUrl !== 'string'
  ) {
    addIssue(
      issues,
      'source',
      'must preserve the verified dated Devon PBF provenance and ODbL attribution',
    );
  }
  if (!isRecord(input.policies)) {
    addIssue(
      issues,
      'policies',
      'must include the effective versioned road derivation policy',
    );
  } else {
    const policy = input.policies;
    const configuredWidths = isRecord(policy.fullWidthsM)
      ? policy.fullWidthsM
      : undefined;
    const widthsMatch =
      configuredWidths !== undefined &&
      Object.keys(configuredWidths).length ===
        Object.keys(ROAD_ESTIMATED_WIDTHS_M).length &&
      Object.entries(ROAD_ESTIMATED_WIDTHS_M).every(([highway, width]) =>
        equalNumber(configuredWidths[highway], width),
      );
    if (
      policy.version !== 1 ||
      !equalNumber(policy.acquisitionBufferM, 50) ||
      !equalNumber(policy.coordinateQuantizationM, 0.001) ||
      !equalNumber(policy.minimumRibbonAreaM2, 0.01) ||
      !equalNumber(policy.surfaceOffsetM, ROAD_SURFACE_OFFSET_M) ||
      policy.float32SliverPolicy !== ROAD_FLOAT32_SLIVER_POLICY ||
      !widthsMatch ||
      !sameJson(policy.pathClasses, [...ROAD_PATH_CLASSES].sort()) ||
      !Array.isArray(policy.displayPriority) ||
      !sameJson(policy.displayPriority, ['vehicular', 'cycleway', 'path'])
    ) {
      addIssue(
        issues,
        'policies',
        'does not match the supported widths, classification, clipping, or surface-offset policy',
      );
    }
  }
  if (
    !isRecord(input.generator) ||
    typeof input.generator.version !== 'string' ||
    input.generator.name !== 'torquay_pipeline.road_export' ||
    typeof input.generator.shapelyVersion !== 'string' ||
    typeof input.generator.geosVersion !== 'string'
  ) {
    addIssue(
      issues,
      'generator',
      'must identify the exporter, Shapely, and GEOS versions',
    );
  }
  if (
    !isRecord(input.limits) ||
    input.limits.maxManifestBytes !== MAX_ROAD_MANIFEST_BYTES ||
    input.limits.maxQaBytes !== MAX_ROAD_QA_BYTES ||
    input.limits.maxPayloadBytes !== MAX_ROADS_BYTES ||
    input.limits.maxWays !== MAX_ROAD_WAYS ||
    input.limits.maxVertices !== MAX_ROAD_VERTICES ||
    input.limits.maxTriangles !== MAX_ROAD_TRIANGLES
  ) {
    addIssue(
      issues,
      'limits',
      'must match the enforced road package safety limits',
    );
  }
  if (
    !isRecord(input.coverage) ||
    input.coverage.selectionStatus !== 'selected_pending_coverage' ||
    input.coverage.coverageStatus !== 'not_checked'
  ) {
    addIssue(
      issues,
      'coverage',
      'must remain selected_pending_coverage / not_checked',
    );
  }
  if (
    !isRecord(input.attribution) ||
    input.attribution.licenceUrl !==
      'https://www.openstreetmap.org/copyright' ||
    typeof input.attribution.geofabrikCredit !== 'string' ||
    !String(input.attribution.text).includes('OpenStreetMap contributors')
  ) {
    addIssue(
      issues,
      'attribution',
      'must provide OSM ODbL and Geofabrik credit',
    );
  }
  if (!isRecord(input.assets)) {
    addIssue(issues, 'assets', 'must integrity-bind both local JSON assets');
  } else {
    for (const [name, limit] of [
      ['roads', MAX_ROADS_BYTES],
      ['qa', MAX_ROAD_QA_BYTES],
    ] as const) {
      const asset = input.assets[name];
      if (
        !isRecord(asset) ||
        asset.path !== `${name}.json` ||
        !isPositiveInteger(asset.byteLength) ||
        asset.byteLength > limit ||
        typeof asset.sha256 !== 'string' ||
        !/^[a-f0-9]{64}$/.test(asset.sha256)
      ) {
        addIssue(
          issues,
          `assets.${name}`,
          `must be a package-local JSON descriptor within ${limit} bytes`,
        );
      }
    }
  }
  if (issues.length > 0) return { ok: false, issues };
  return { ok: true, value: input as unknown as RoadPackageManifest };
}

function validateFeature(
  value: unknown,
  index: number,
  manifest: RoadPackageManifest,
  issues: RoadValidationIssue[],
): RoadFeature | undefined {
  const path = `roads.features[${index}]`;
  if (!isRecord(value)) {
    addIssue(issues, path, 'must be an object');
    return undefined;
  }
  const highway = value.highway;
  if (
    typeof highway !== 'string' ||
    ROAD_ESTIMATED_WIDTHS_M[highway] === undefined
  ) {
    addIssue(
      issues,
      `${path}.highway`,
      'is not an included configured highway class',
    );
    return undefined;
  }
  const source = value.source;
  if (
    !isRecord(source) ||
    source.dataset !== 'OpenStreetMap' ||
    source.objectType !== 'way' ||
    !isPositiveInteger(source.osmId) ||
    !isPositiveInteger(source.version) ||
    (source.timestamp !== null && typeof source.timestamp !== 'string') ||
    !Array.isArray(source.nodeIds) ||
    source.nodeIds.length < 2 ||
    !source.nodeIds.every(isPositiveInteger)
  ) {
    addIssue(
      issues,
      `${path}.source`,
      'must preserve a valid OSM way identity, version, timestamp, and node references',
    );
  }
  if (value.id !== `way/${isRecord(source) ? source.osmId : ''}`)
    addIssue(issues, `${path}.id`, 'must match its OSM way identifier');
  const group = expectedGroup(highway);
  if (value.displayGroup !== group)
    addIssue(
      issues,
      `${path}.displayGroup`,
      'does not match the configured highway class grouping',
    );
  if (!equalNumber(value.estimatedWidthM, ROAD_ESTIMATED_WIDTHS_M[highway]!))
    addIssue(
      issues,
      `${path}.estimatedWidthM`,
      'must match the configured visual width estimate',
    );
  if (
    value.widthMethod !== 'configured_visual_estimate' ||
    !isRecord(value.widthEvidence) ||
    value.widthEvidence.usedRawTags !== false ||
    (value.widthEvidence.rawWidth !== null &&
      typeof value.widthEvidence.rawWidth !== 'string') ||
    (value.widthEvidence.rawLanes !== null &&
      typeof value.widthEvidence.rawLanes !== 'string')
  ) {
    addIssue(
      issues,
      `${path}.widthEvidence`,
      'must disclose configured estimated width and retain unused raw width/lanes tags',
    );
  }
  if (
    value.groundAssumption !==
      'ground_assumed_from_absent_or_explicit_no_vertical_tags' ||
    value.clippedToAoi !== true
  )
    addIssue(
      issues,
      path,
      'must disclose the ground assumption and exact AOI clipping',
    );
  if (
    !isRecord(source) ||
    !Array.isArray(value.centerlinePartsXZ) ||
    !Array.isArray(value.partIds) ||
    value.partIds.length !== value.centerlinePartsXZ.length ||
    !value.partIds.every(
      (id, part) =>
        id === `way/${source.osmId}/part/${String(part).padStart(3, '0')}`,
    )
  ) {
    addIssue(
      issues,
      `${path}.centerlinePartsXZ`,
      'must include stable IDs for every clipped line part',
    );
  } else {
    value.centerlinePartsXZ.forEach((part, partIndex) => {
      if (!Array.isArray(part) || part.length < 2 || !part.every(point)) {
        addIssue(
          issues,
          `${path}.centerlinePartsXZ[${partIndex}]`,
          'must contain at least two finite [x,z] coordinates',
        );
        return;
      }
      for (const [x, z] of part as [number, number][]) {
        if (
          Math.abs(x) > manifest.aoi.widthM / 2 + 1e-6 ||
          Math.abs(z) > manifest.aoi.heightM / 2 + 1e-6
        ) {
          addIssue(
            issues,
            `${path}.centerlinePartsXZ[${partIndex}]`,
            'contains a point outside the exact local AOI',
          );
          break;
        }
      }
      for (let i = 1; i < part.length; i += 1) {
        if (part[i]![0] === part[i - 1]![0] && part[i]![1] === part[i - 1]![1])
          addIssue(
            issues,
            `${path}.centerlinePartsXZ[${partIndex}]`,
            'contains consecutive duplicate points',
          );
      }
    });
  }
  if (!isStringRecord(value.sourceTags) || value.sourceTags.highway !== highway)
    addIssue(
      issues,
      `${path}.sourceTags`,
      'must retain string tags including its highway class',
    );
  if (
    !Array.isArray(value.duplicateWayIds) ||
    !value.duplicateWayIds.every(isPositiveInteger) ||
    !isFiniteNumber(value.ribbonAreaM2) ||
    value.ribbonAreaM2 <= 0 ||
    !Array.isArray(value.ribbonPartIds) ||
    !value.ribbonPartIds.every(
      (id, part) =>
        id === `${value.id}/ribbon/${String(part).padStart(3, '0')}`,
    )
  )
    addIssue(
      issues,
      path,
      'duplicate references and buffered ribbon metadata are invalid',
    );
  return value as unknown as RoadFeature;
}

/** Validate road records, QA reconciliation, indexed mesh ownership and bounds. */
export function validateRoadPayload(
  input: unknown,
  qaInput: unknown,
  manifest: RoadPackageManifest,
): RoadValidationResult<LoadedRoadPackage> {
  const issues: RoadValidationIssue[] = [];
  if (
    !isRecord(input) ||
    input.formatVersion !== 1 ||
    input.worldId !== manifest.worldId ||
    !Array.isArray(input.features) ||
    !isRecord(input.surfaceBatches)
  ) {
    return {
      ok: false,
      issues: [
        {
          path: 'roads',
          message:
            'must be a v1 payload with matching worldId, features, and surface batches',
        },
      ],
    };
  }
  if (!isRecord(qaInput))
    return {
      ok: false,
      issues: [{ path: 'qa', message: 'must be a QA object' }],
    };
  const qa = qaInput;
  if (
    qa.formatVersion !== 1 ||
    qa.worldId !== manifest.worldId ||
    qa.status !== 'pass' ||
    qa.selectionStatus !== 'selected_pending_coverage' ||
    qa.coverageStatus !== 'not_checked'
  )
    addIssue(
      issues,
      'qa',
      'must be a passing package QA report that preserves pending AOI status',
    );
  if (
    !sameJson(qa.source, manifest.source) ||
    !sameJson(qa.coordinateOperation, manifest.coordinateOperation)
  )
    addIssue(
      issues,
      'qa.source/coordinateOperation',
      'must match manifest provenance and coordinate operation',
    );
  if (!isRecord(qa.counts) || !sameJson(qa.counts, manifest.counts))
    addIssue(issues, 'qa.counts', 'must match manifest counts');
  if (
    !isRecord(qa.meshNumerics) ||
    !Number.isSafeInteger(
      qa.meshNumerics.float32CollapsedSliverTriangleCount,
    ) ||
    Number(qa.meshNumerics.float32CollapsedSliverTriangleCount) < 0 ||
    qa.meshNumerics.float32CollapsedSliverTriangleCount !==
      manifest.counts.float32CollapsedSliverTriangleCount ||
    !isFiniteNumber(qa.meshNumerics.float32CollapsedSliverAreaM2) ||
    qa.meshNumerics.float32CollapsedSliverAreaM2 < 0 ||
    qa.meshNumerics.float32CollapsedSliverAreaM2 > 1e-6 ||
    qa.meshNumerics.maximumOmittedAreaM2 !== 1e-6 ||
    qa.meshNumerics.policy !== ROAD_FLOAT32_SLIVER_POLICY ||
    !isRecord(qa.surfacePolicy) ||
    qa.surfacePolicy.float32SliverPolicy !== ROAD_FLOAT32_SLIVER_POLICY
  ) {
    addIssue(
      issues,
      'qa.meshNumerics/surfacePolicy',
      'must audit Float32-collapsed sliver triangles within the supported area limit',
    );
  }
  if (!isRecord(qa.displayBatches) || !isRecord(qa.areas))
    addIssue(
      issues,
      'qa.displayBatches/areas',
      'must describe each validated display batch',
    );
  if (!Array.isArray(qa.landmarkContexts) || qa.landmarkContexts.length !== 3)
    addIssue(
      issues,
      'qa.landmarkContexts',
      'must record the three existing source-backed building contexts',
    );
  else {
    const landmarkIds = new Set<string>();
    qa.landmarkContexts.forEach((item, index) => {
      if (
        !isRecord(item) ||
        typeof item.id !== 'string' ||
        landmarkIds.has(item.id) ||
        !isPositiveInteger(item.buildingWayId) ||
        !point(item.buildingRepresentativeLocalXZ) ||
        !Array.isArray(item.targetRoadNames) ||
        !item.targetRoadNames.every((name) => typeof name === 'string') ||
        typeof item.targetRoadNamePresent !== 'boolean' ||
        typeof item.observation !== 'string'
      ) {
        addIssue(
          issues,
          `qa.landmarkContexts[${index}]`,
          'must preserve a unique building-context marker and bounded source observation',
        );
      } else {
        landmarkIds.add(item.id);
        if (
          item.nearestRoad !== null &&
          (!isRecord(item.nearestRoad) ||
            !isPositiveInteger(item.nearestRoad.wayId) ||
            !point(item.nearestRoad.nearestPointLocalXZ) ||
            !isFiniteNumber(
              item.nearestRoad.distanceFromBuildingRepresentativeM,
            ) ||
            item.nearestRoad.distanceFromBuildingRepresentativeM < 0 ||
            !Array.isArray(item.nearestRoad.nodeIds) ||
            !item.nearestRoad.nodeIds.every(isPositiveInteger))
        ) {
          addIssue(
            issues,
            `qa.landmarkContexts[${index}].nearestRoad`,
            'must identify an actual way/node pair and finite local closest point',
          );
        }
      }
    });
  }

  const features: RoadFeature[] = [];
  const ids = new Set<string>();
  const countsByGroup: Record<RoadDisplayGroup, number> = {
    vehicular: 0,
    cycleway: 0,
    path: 0,
  };
  let partCount = 0;
  input.features.forEach((feature, index) => {
    const parsed = validateFeature(feature, index, manifest, issues);
    if (parsed === undefined) return;
    if (ids.has(parsed.id))
      addIssue(
        issues,
        `roads.features[${index}].id`,
        'duplicates another way identifier',
      );
    ids.add(parsed.id);
    countsByGroup[parsed.displayGroup] += 1;
    partCount += parsed.centerlinePartsXZ.length;
    features.push(parsed);
  });
  if (features.length > MAX_ROAD_WAYS)
    addIssue(issues, 'roads.features', 'exceeds the maximum source-way count');

  const batches = {} as Record<RoadDisplayGroup, RoadSurfaceBatch>;
  let totalVertices = 0;
  let totalTriangles = 0;
  const columns = manifest.terrainIdentity.columns;
  const rows = manifest.terrainIdentity.rows;
  const spacing = manifest.terrainIdentity.spacingM;
  const halfWidth = manifest.terrainIdentity.extentM.width / 2;
  const halfDepth = manifest.terrainIdentity.extentM.depth / 2;
  for (const group of ROAD_GROUPS) {
    const batch = input.surfaceBatches[group];
    const path = `roads.surfaceBatches.${group}`;
    if (
      !isRecord(batch) ||
      !Array.isArray(batch.verticesXZ) ||
      !Array.isArray(batch.indices) ||
      !Array.isArray(batch.terrainTriangles)
    ) {
      addIssue(
        issues,
        path,
        'must contain indexed vertices and terrain-cell identity',
      );
      continue;
    }
    if (!batch.verticesXZ.every(point))
      addIssue(issues, `${path}.verticesXZ`, 'must contain finite [x,z] pairs');
    const vertices = batch.verticesXZ as [number, number][];
    const indices = batch.indices as unknown[];
    const terrainTriangles = batch.terrainTriangles as unknown[];
    if (
      vertices.some(
        ([x, z]) =>
          Math.abs(x) > halfWidth + 1e-6 || Math.abs(z) > halfDepth + 1e-6,
      )
    )
      addIssue(
        issues,
        `${path}.verticesXZ`,
        'contains a vertex outside terrain bounds',
      );
    if (indices.length !== terrainTriangles.length)
      addIssue(
        issues,
        `${path}.terrainTriangles`,
        'must provide a cell/triangle for every mesh face',
      );
    const uniqueFaces = new Set<string>();
    indices.forEach((face, index) => {
      if (
        !Array.isArray(face) ||
        face.length !== 3 ||
        !face.every(
          (item) =>
            Number.isSafeInteger(item) && item >= 0 && item < vertices.length,
        )
      ) {
        addIssue(
          issues,
          `${path}.indices[${index}]`,
          'must contain three in-range integer vertex indices',
        );
        return;
      }
      if (new Set(face).size !== 3)
        addIssue(
          issues,
          `${path}.indices[${index}]`,
          'must not repeat a vertex',
        );
      const key = [...face].sort((a, b) => a - b).join(':');
      if (uniqueFaces.has(key))
        addIssue(
          issues,
          `${path}.indices[${index}]`,
          'duplicates another triangle',
        );
      uniqueFaces.add(key);
      const [a, b, c] = face.map((vertex) => vertices[vertex]!) as [
        [number, number],
        [number, number],
        [number, number],
      ];
      const cross =
        (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
      if (!Number.isFinite(cross) || cross >= -1e-12)
        addIssue(
          issues,
          `${path}.indices[${index}]`,
          'must be a nondegenerate upward-wound XZ triangle',
        );
      const cell = terrainTriangles[index];
      if (
        !Array.isArray(cell) ||
        cell.length !== 3 ||
        !Number.isSafeInteger(cell[0]) ||
        !Number.isSafeInteger(cell[1]) ||
        (cell[2] !== 0 && cell[2] !== 1) ||
        cell[0] < 0 ||
        cell[0] >= rows - 1 ||
        cell[1] < 0 ||
        cell[1] >= columns - 1
      ) {
        addIssue(
          issues,
          `${path}.terrainTriangles[${index}]`,
          'must identify an in-range terrain cell and fixed triangle',
        );
        return;
      }
      for (const [x, z] of [a, b, c]) {
        const u = (x + halfWidth) / spacing - cell[1];
        const v = (z + halfDepth) / spacing - cell[0];
        const inCell =
          u >= -1e-7 && u <= 1 + 1e-7 && v >= -1e-7 && v <= 1 + 1e-7;
        const inTriangle =
          cell[2] === 0 ? u + v <= 1 + 1e-7 : u + v >= 1 - 1e-7;
        if (!inCell || !inTriangle) {
          addIssue(
            issues,
            `${path}.terrainTriangles[${index}]`,
            'face vertex lies outside its claimed fixed terrain triangle',
          );
          break;
        }
      }
    });
    totalVertices += vertices.length;
    totalTriangles += indices.length;
    batches[group] = batch as unknown as RoadSurfaceBatch;
  }
  if (totalVertices > MAX_ROAD_VERTICES || totalTriangles > MAX_ROAD_TRIANGLES)
    addIssue(issues, 'roads.surfaceBatches', 'exceeds safe render limits');
  const counts = isRecord(qa.counts) ? qa.counts : {};
  if (
    counts.uniqueExportedWays !== features.length ||
    counts.unique_exported_ways !== features.length ||
    counts.uniquePartIds !== partCount ||
    counts.renderVertexCount !== totalVertices ||
    counts.renderTriangleCount !== totalTriangles
  )
    addIssue(
      issues,
      'qa.counts',
      'feature, line-part, vertex, or triangle totals do not reconcile',
    );
  if (isRecord(qa.displayBatches)) {
    for (const group of ROAD_GROUPS) {
      const summary = qa.displayBatches[group];
      const batch = batches[group];
      if (
        !isRecord(summary) ||
        !batch ||
        summary.uniqueWayCount !== countsByGroup[group] ||
        summary.clippedCenterlinePartCount !==
          features
            .filter((feature) => feature.displayGroup === group)
            .reduce(
              (total, feature) => total + feature.centerlinePartsXZ.length,
              0,
            ) ||
        summary.vertexCount !== batch.verticesXZ.length ||
        summary.triangleCount !== batch.indices.length ||
        !isFiniteNumber(summary.surfaceAreaM2) ||
        !isFiniteNumber(summary.bufferedAreaBeforePriorityM2)
      ) {
        addIssue(
          issues,
          `qa.displayBatches.${group}`,
          'does not reconcile with validated features and render geometry',
        );
      }
    }
  }
  if (issues.length > 0) return { ok: false, issues };
  return {
    ok: true,
    value: {
      manifest,
      features,
      batches,
      qa: qaInput as unknown as RoadQaSummary,
      partCount,
      countsByGroup,
    },
  };
}

export function formatRoadIssues(issues: RoadValidationIssue[]): string {
  return issues.map(({ path, message }) => `${path}: ${message}`).join('; ');
}
