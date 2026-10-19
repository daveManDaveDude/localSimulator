import {
  isSafeLocalAssetPath,
  type RealTerrainSceneManifest,
} from './sceneSchema';

export const MAX_BUILDING_FEATURES = 5_000;
export const MAX_BUILDING_COORDINATES = 2_000_000;
export const MAX_BUILDINGS_BYTES = 16 * 1024 * 1024;
export const MAX_BUILDING_QA_BYTES = 2 * 1024 * 1024;
export const MAX_BUILDING_MANIFEST_BYTES = 256 * 1024;
export const WALL_BASE_BURIAL_M = 0.02;

export type BuildingHeightMethod =
  'osm_height' | 'estimated_levels' | 'estimated_default';
export type BuildingHeightConfidence =
  | 'tagged_but_unverified'
  | 'estimated_from_tagged_levels'
  | 'visual_default_estimate';
export type XzPosition = readonly [x: number, z: number];

export interface BuildingAoiBoundaryWgs84 {
  crs: 'EPSG:4326';
  coordinateOrder: 'longitude-latitude';
  closedRing: true;
  ring: Array<[longitude: number, latitude: number]>;
}

export interface BuildingPolygon {
  exteriorXZ: XzPosition[];
  interiorRingsXZ: XzPosition[][];
}

export interface BuildingFeature {
  id: string;
  source: {
    dataset: string;
    objectType: 'way' | 'relation';
    osmId: number;
    version: number;
    timestamp: string;
  };
  geometry: { type: 'MultiPolygon'; polygons: BuildingPolygon[] };
  heightM: number;
  heightMethod: BuildingHeightMethod;
  heightConfidence: BuildingHeightConfidence;
  heightProvenance: {
    heightM: number;
    method: BuildingHeightMethod;
    confidence: BuildingHeightConfidence;
    rawHeight: string | null;
    parsedHeightM: number | null;
    parsedUnit: string | null;
    rawLevels: string | null;
    clamp: string | null;
    fallbackReason: string | null;
  };
  footprintAreaM2: number;
  clippedToAoi: boolean;
  qualityFlags: string[];
  duplicateReferences: string[];
  tags: Record<string, string>;
}

export interface BuildingPackageManifest {
  formatVersion: 1;
  worldId: string;
  name: string;
  sourceCrs: 'EPSG:27700';
  axisConvention: '+X east, +Y up, -Z north';
  units: 'metres';
  aoi: {
    crs: 'EPSG:27700';
    boundsM: [number, number, number, number];
    widthM: number;
    heightM: number;
    boundaryWgs84: BuildingAoiBoundaryWgs84;
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
  };
  policies: {
    height: {
      version: number;
      levelsToMetres: number;
      defaultHeightM: number;
      minimumHeightM: number;
      maximumHeightM: number;
      precedence: string[];
      taggedHeightConfidence: string;
      defaultConfidence: string;
    };
    geometry: {
      version: number;
      acquisitionBufferM: number;
      minimumClippedAreaM2: number;
      coordinateQuantizationM: number;
      exteriorWinding: string;
      interiorWinding: string;
      invalidGeometryPolicy: string;
      duplicatePolicy: string;
      nearOverlapPolicy: string;
    };
  };
  coordinateOperation: {
    axisOrder: string;
    wgs84ToBng: {
      name: string;
      definition: string;
      reported_accuracy_m: number;
      accuracy_m: number;
      uses_grids: boolean;
      best_available: boolean;
      preferred_missing_operations: Array<{
        name: string;
        grids: Array<{ short_name: string; available: boolean }>;
      }>;
      grid_status: string;
    };
  };
  provenance: {
    publisher: string;
    product: string;
    downloadUrl: string;
    fileUrl: string;
    downloadDate: string;
    extractTimestamp: string;
    filename: string;
    sizeBytes: number;
    sha256: string;
    licence: string;
    licenceUrl: string;
    attribution: string;
    geofabrikCredit: string;
    notes: string[];
  };
  generator: { name: string; version: string; geosVersion: string };
  coverage: {
    selectionStatus: 'selected_pending_coverage';
    coverageStatus: 'not_checked';
    note: string;
  };
  buildings: {
    path: 'buildings.json';
    byteLength: number;
    sha256: string;
    count: number;
  };
  qaReport: { path: 'qa.json'; byteLength: number; sha256: string };
}

export interface BuildingQaSummary {
  formatVersion: 1;
  aoiId: string;
  selectionStatus: 'selected_pending_coverage';
  coverageStatus: 'not_checked';
  counts: {
    exported_buildings: number;
    exported_components: number;
    exported_holes: number;
  };
  quality: {
    heightMethodCounts: Partial<Record<BuildingHeightMethod, number>>;
    heightClampCounts: Record<string, number>;
    taggedHeightsAreUnverified: true;
  };
  summary: {
    buildingFootprintAreaM2: number;
    minimumHeightM: number;
    maximumHeightM: number;
    meanHeightM: number;
    densityInterpretation: string;
  };
  package: {
    worldId: string;
    manifestPath: 'manifest.json';
    buildingsPath: 'buildings.json';
    buildingsByteLength: number;
    buildingsSha256: string;
  };
}

export interface LoadedBuildingPackage {
  manifest: BuildingPackageManifest;
  features: BuildingFeature[];
  qa: BuildingQaSummary;
  componentCount: number;
  holeCount: number;
  heightMethodCounts: Record<BuildingHeightMethod, number>;
}

export interface BuildingValidationIssue {
  path: string;
  message: string;
}

export type BuildingValidationResult<T> =
  { ok: true; value: T } | { ok: false; issues: BuildingValidationIssue[] };

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function isPositiveInteger(value: unknown): value is number {
  return Number.isSafeInteger(value) && (value as number) > 0;
}

function isString(value: unknown): value is string {
  return typeof value === 'string';
}

function nonempty(value: unknown): value is string {
  return isString(value) && value.trim().length > 0;
}

function sameNumber(left: unknown, right: number, tolerance = 1e-7): boolean {
  return isNumber(left) && Math.abs(left - right) <= tolerance;
}

function sameBounds(left: unknown, right: readonly number[]): boolean {
  return (
    Array.isArray(left) &&
    left.length === right.length &&
    left.every((value, index) => sameNumber(value, right[index]!))
  );
}

function addIssue(
  issues: BuildingValidationIssue[],
  path: string,
  message: string,
): void {
  issues.push({ path, message });
}

function parseHeight(raw: string): { metres: number; unit: string } | null {
  const metric = /^\s*(\d+(?:\.\d+)?)\s*(m|metres?|meters?)?\s*$/i.exec(raw);
  if (metric) {
    const value = Number(metric[1]);
    return Number.isFinite(value) && value > 0
      ? { metres: value, unit: 'metres' }
      : null;
  }
  const simpleUnit = [
    [/^\s*(\d+(?:\.\d+)?)\s*(ft|feet|foot)\s*$/i, 0.3048, 'feet'],
    [/^\s*(\d+(?:\.\d+)?)\s*(in|inch|inches)\s*$/i, 0.0254, 'inches'],
  ] as const;
  for (const [pattern, multiplier, unit] of simpleUnit) {
    const match = pattern.exec(raw);
    if (match) {
      const value = Number(match[1]);
      return Number.isFinite(value) && value > 0
        ? { metres: value * multiplier, unit }
        : null;
    }
  }
  const imperial =
    /^\s*(\d+(?:\.\d+)?)\s*(?:ft|feet|foot|')\s*(?:(\d+(?:\.\d+)?)\s*(?:in|inches|inch|"))?\s*$/i.exec(
      raw,
    );
  if (imperial) {
    const feet = Number(imperial[1]);
    const inches = Number(imperial[2] ?? 0);
    if (Number.isFinite(feet) && feet > 0 && inches >= 0 && inches < 12) {
      return { metres: feet * 0.3048 + inches * 0.0254, unit: 'feet_inches' };
    }
  }
  return null;
}

function resolveHeight(
  tags: Record<string, string>,
  policy: BuildingPackageManifest['policies']['height'],
): BuildingFeature['heightProvenance'] {
  const rawHeight = tags.height ?? null;
  const rawLevels = tags['building:levels'] ?? null;
  let parsedHeightM: number | null = null;
  let parsedUnit: string | null = null;
  let failure: string | null = null;

  if (rawHeight !== null) {
    const parsed = parseHeight(rawHeight);
    if (parsed) {
      parsedHeightM = parsed.metres;
      parsedUnit = parsed.unit;
      const heightM = Math.min(
        Math.max(parsedHeightM, policy.minimumHeightM),
        policy.maximumHeightM,
      );
      return {
        heightM,
        method: 'osm_height',
        confidence: 'tagged_but_unverified',
        rawHeight,
        parsedHeightM,
        parsedUnit,
        rawLevels,
        clamp:
          heightM === parsedHeightM
            ? null
            : heightM < parsedHeightM
              ? 'clamped_high'
              : 'clamped_low',
        fallbackReason: null,
      };
    }
    failure = 'height tag is nonpositive, malformed, nonfinite, or ambiguous';
  }

  if (rawLevels !== null) {
    if (/^[1-9]\d*$/.test(rawLevels.trim())) {
      const levels = Number(rawLevels);
      const candidate = levels * policy.levelsToMetres;
      if (Number.isFinite(candidate) && candidate > 0) {
        const heightM = Math.min(
          Math.max(candidate, policy.minimumHeightM),
          policy.maximumHeightM,
        );
        return {
          heightM,
          method: 'estimated_levels',
          confidence: 'estimated_from_tagged_levels',
          rawHeight,
          parsedHeightM,
          parsedUnit,
          rawLevels,
          clamp:
            heightM === candidate
              ? null
              : heightM < candidate
                ? 'clamped_high'
                : 'clamped_low',
          fallbackReason: failure,
        };
      }
    }
    failure = `${failure ? `${failure}; ` : ''}building:levels must be a positive integer`;
  }

  const heightM = Math.min(
    Math.max(policy.defaultHeightM, policy.minimumHeightM),
    policy.maximumHeightM,
  );
  return {
    heightM,
    method: 'estimated_default',
    confidence: 'visual_default_estimate',
    rawHeight,
    parsedHeightM,
    parsedUnit,
    rawLevels,
    clamp:
      heightM === policy.defaultHeightM
        ? null
        : heightM < policy.defaultHeightM
          ? 'clamped_high'
          : 'clamped_low',
    fallbackReason: failure ?? 'no usable height or building:levels tag',
  };
}

function signedArea(ring: XzPosition[]): number {
  let sum = 0;
  for (let index = 0; index < ring.length - 1; index += 1) {
    const point = ring[index]!;
    const next = ring[index + 1]!;
    sum += point[0] * next[1] - next[0] * point[1];
  }
  return sum / 2;
}

function samePoint(a: XzPosition, b: XzPosition, epsilon = 1e-9): boolean {
  return Math.abs(a[0] - b[0]) <= epsilon && Math.abs(a[1] - b[1]) <= epsilon;
}

function orientation(a: XzPosition, b: XzPosition, c: XzPosition): number {
  return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
}

function onSegment(a: XzPosition, b: XzPosition, p: XzPosition): boolean {
  return (
    Math.abs(orientation(a, b, p)) <= 1e-10 &&
    p[0] >= Math.min(a[0], b[0]) - 1e-10 &&
    p[0] <= Math.max(a[0], b[0]) + 1e-10 &&
    p[1] >= Math.min(a[1], b[1]) - 1e-10 &&
    p[1] <= Math.max(a[1], b[1]) + 1e-10
  );
}

function segmentsIntersect(
  a: XzPosition,
  b: XzPosition,
  c: XzPosition,
  d: XzPosition,
): boolean {
  const abC = orientation(a, b, c);
  const abD = orientation(a, b, d);
  const cdA = orientation(c, d, a);
  const cdB = orientation(c, d, b);
  if (abC * abD < 0 && cdA * cdB < 0) return true;
  return (
    (Math.abs(abC) <= 1e-10 && onSegment(a, b, c)) ||
    (Math.abs(abD) <= 1e-10 && onSegment(a, b, d)) ||
    (Math.abs(cdA) <= 1e-10 && onSegment(c, d, a)) ||
    (Math.abs(cdB) <= 1e-10 && onSegment(c, d, b))
  );
}

function isSimpleRing(ring: XzPosition[]): boolean {
  const edgeCount = ring.length - 1;
  for (let first = 0; first < edgeCount; first += 1) {
    for (let second = first + 1; second < edgeCount; second += 1) {
      if (second === first + 1 || (first === 0 && second === edgeCount - 1)) {
        continue;
      }
      if (
        segmentsIntersect(
          ring[first]!,
          ring[first + 1]!,
          ring[second]!,
          ring[second + 1]!,
        )
      ) {
        return false;
      }
    }
  }
  return true;
}

function pointInRing(point: XzPosition, ring: XzPosition[]): boolean {
  let inside = false;
  for (
    let index = 0, previous = ring.length - 2;
    index < ring.length - 1;
    previous = index++
  ) {
    const a = ring[index]!;
    const b = ring[previous]!;
    if (onSegment(a, b, point)) return true;
    if (
      a[1] > point[1] !== b[1] > point[1] &&
      point[0] < ((b[0] - a[0]) * (point[1] - a[1])) / (b[1] - a[1]) + a[0]
    ) {
      inside = !inside;
    }
  }
  return inside;
}

function pointInRingInterior(point: XzPosition, ring: XzPosition[]): boolean {
  if (!pointInRing(point, ring)) return false;
  for (let index = 0; index < ring.length - 1; index += 1) {
    if (onSegment(ring[index]!, ring[index + 1]!, point)) return false;
  }
  return true;
}

function ringEdges(ring: XzPosition[]): Array<[XzPosition, XzPosition]> {
  return Array.from({ length: ring.length - 1 }, (_, index) => [
    ring[index]!,
    ring[index + 1]!,
  ]);
}

function hasForbiddenRingIntersection(
  first: XzPosition[],
  second: XzPosition[],
  allowPointContacts: boolean,
): boolean {
  for (const [a, b] of ringEdges(first)) {
    for (const [c, d] of ringEdges(second)) {
      if (!segmentsIntersect(a, b, c, d)) continue;
      const abC = orientation(a, b, c);
      const abD = orientation(a, b, d);
      const cdA = orientation(c, d, a);
      const cdB = orientation(c, d, b);
      const properCrossing =
        ((abC > 1e-10 && abD < -1e-10) || (abC < -1e-10 && abD > 1e-10)) &&
        ((cdA > 1e-10 && cdB < -1e-10) || (cdA < -1e-10 && cdB > 1e-10));
      if (!allowPointContacts || properCrossing) {
        return true;
      }
    }
  }
  return false;
}

function pointInPolygonInterior(
  point: XzPosition,
  polygon: BuildingPolygon,
): boolean {
  return (
    pointInRingInterior(point, polygon.exteriorXZ) &&
    !polygon.interiorRingsXZ.some((hole) => pointInRing(point, hole))
  );
}

function findPolygonInteriorPoint(polygon: BuildingPolygon): XzPosition | null {
  const rings = [polygon.exteriorXZ, ...polygon.interiorRingsXZ];
  const ordinates = [
    ...new Set(
      rings.flatMap((ring) => ring.slice(0, -1).map((point) => point[1])),
    ),
  ].sort((first, second) => first - second);
  for (let index = 0; index < ordinates.length - 1; index += 1) {
    const south = ordinates[index]!;
    const north = ordinates[index + 1]!;
    if (north - south <= 1e-10) continue;
    const z = (south + north) / 2;
    const crossings = rings
      .flatMap((ring) =>
        ringEdges(ring).flatMap(([a, b]) => {
          if (a[1] > z === b[1] > z) return [];
          return [a[0] + ((z - a[1]) * (b[0] - a[0])) / (b[1] - a[1])];
        }),
      )
      .sort((first, second) => first - second);
    for (let crossing = 0; crossing < crossings.length - 1; crossing += 1) {
      const west = crossings[crossing]!;
      const east = crossings[crossing + 1]!;
      if (east - west <= 1e-10) continue;
      const candidate: XzPosition = [(west + east) / 2, z];
      if (pointInPolygonInterior(candidate, polygon)) return candidate;
    }
  }
  return null;
}

function segmentIntersectionParameters(
  a: XzPosition,
  b: XzPosition,
  c: XzPosition,
  d: XzPosition,
): number[] {
  const abX = b[0] - a[0];
  const abZ = b[1] - a[1];
  const cdX = d[0] - c[0];
  const cdZ = d[1] - c[1];
  const denominator = abX * cdZ - abZ * cdX;
  const acX = c[0] - a[0];
  const acZ = c[1] - a[1];
  if (Math.abs(denominator) <= 1e-12) {
    if (Math.abs(acX * abZ - acZ * abX) > 1e-10) return [];
    const lengthSquared = abX * abX + abZ * abZ;
    if (lengthSquared <= 1e-20) return [];
    const cParameter = (acX * abX + acZ * abZ) / lengthSquared;
    const dParameter =
      ((d[0] - a[0]) * abX + (d[1] - a[1]) * abZ) / lengthSquared;
    const start = Math.max(0, Math.min(cParameter, dParameter));
    const end = Math.min(1, Math.max(cParameter, dParameter));
    if (start > end + 1e-10) return [];
    return [Math.min(1, Math.max(0, start)), Math.min(1, Math.max(0, end))];
  }

  const t = (acX * cdZ - acZ * cdX) / denominator;
  const u = (acX * abZ - acZ * abX) / denominator;
  if (t < -1e-10 || t > 1 + 1e-10 || u < -1e-10 || u > 1 + 1e-10) {
    return [];
  }
  return [Math.min(1, Math.max(0, t))];
}

function hasBoundaryIntervalInsidePolygon(
  ring: XzPosition[],
  polygon: BuildingPolygon,
): boolean {
  const boundaryRings = [polygon.exteriorXZ, ...polygon.interiorRingsXZ];
  for (const [a, b] of ringEdges(ring)) {
    const cuts = [0, 1];
    for (const boundaryRing of boundaryRings) {
      for (const [c, d] of ringEdges(boundaryRing)) {
        cuts.push(...segmentIntersectionParameters(a, b, c, d));
      }
    }
    cuts.sort((first, second) => first - second);
    const uniqueCuts = cuts.filter(
      (value, index) =>
        index === 0 || Math.abs(value - cuts[index - 1]!) > 1e-10,
    );
    for (let index = 0; index < uniqueCuts.length - 1; index += 1) {
      const start = uniqueCuts[index]!;
      const end = uniqueCuts[index + 1]!;
      if (end - start <= 1e-10) continue;
      const parameter = (start + end) / 2;
      const point: XzPosition = [
        a[0] + (b[0] - a[0]) * parameter,
        a[1] + (b[1] - a[1]) * parameter,
      ];
      if (pointInPolygonInterior(point, polygon)) return true;
    }
  }
  return false;
}

function polygonsOverlap(
  first: BuildingPolygon,
  second: BuildingPolygon,
): boolean {
  const firstRings = [first.exteriorXZ, ...first.interiorRingsXZ];
  const secondRings = [second.exteriorXZ, ...second.interiorRingsXZ];
  for (const firstRing of firstRings) {
    for (const secondRing of secondRings) {
      if (hasForbiddenRingIntersection(firstRing, secondRing, true)) {
        return true;
      }
    }
  }
  const firstInterior = findPolygonInteriorPoint(first);
  const secondInterior = findPolygonInteriorPoint(second);
  return (
    (firstInterior !== null && pointInPolygonInterior(firstInterior, second)) ||
    (secondInterior !== null &&
      pointInPolygonInterior(secondInterior, first)) ||
    firstRings.some((ring) => hasBoundaryIntervalInsidePolygon(ring, second)) ||
    secondRings.some((ring) => hasBoundaryIntervalInsidePolygon(ring, first)) ||
    first.exteriorXZ
      .slice(0, -1)
      .some((point) => pointInPolygonInterior(point, second)) ||
    second.exteriorXZ
      .slice(0, -1)
      .some((point) => pointInPolygonInterior(point, first))
  );
}

function canonicalizeRing(ring: XzPosition[]): XzPosition[] {
  const open = ring.slice(0, -1);
  let start = 0;
  for (let index = 1; index < open.length; index += 1) {
    const current = open[index]!;
    const candidate = open[start]!;
    if (
      current[0] < candidate[0] ||
      (current[0] === candidate[0] && current[1] < candidate[1])
    ) {
      start = index;
    }
  }
  const ordered = [...open.slice(start), ...open.slice(0, start)];
  ordered.push([...ordered[0]!] as XzPosition);
  return ordered;
}

function canonicalRingKey(ring: XzPosition[]): string {
  return JSON.stringify(ring);
}

function parseRing(
  value: unknown,
  path: string,
  exterior: boolean,
  issues: BuildingValidationIssue[],
  counter: { coordinates: number },
): XzPosition[] | undefined {
  if (!Array.isArray(value) || value.length < 4) {
    addIssue(
      issues,
      path,
      'must be a closed ring with at least three distinct points',
    );
    return undefined;
  }
  const ring: XzPosition[] = [];
  for (let index = 0; index < value.length; index += 1) {
    const point = value[index];
    if (
      !Array.isArray(point) ||
      point.length !== 2 ||
      !isNumber(point[0]) ||
      !isNumber(point[1])
    ) {
      addIssue(
        issues,
        `${path}[${index}]`,
        'must be a finite [x, z] metre coordinate',
      );
      return undefined;
    }
    ring.push([point[0], point[1]]);
    counter.coordinates += 1;
    if (counter.coordinates > MAX_BUILDING_COORDINATES) {
      addIssue(
        issues,
        path,
        `exceeds the ${MAX_BUILDING_COORDINATES} coordinate safety limit`,
      );
      return undefined;
    }
  }
  if (!samePoint(ring[0]!, ring.at(-1)!)) {
    addIssue(issues, path, 'must close by repeating its first coordinate');
    return undefined;
  }
  const distinct = new Set(ring.slice(0, -1).map(([x, z]) => `${x},${z}`));
  const area = signedArea(ring);
  if (distinct.size < 3 || !Number.isFinite(area) || Math.abs(area) <= 1e-8) {
    addIssue(
      issues,
      path,
      'must contain at least three distinct points and positive area',
    );
    return undefined;
  }
  if (!isSimpleRing(ring)) {
    addIssue(
      issues,
      path,
      'self-intersection is not allowed; geometry is never auto-repaired',
    );
  }
  for (let index = 0; index < ring.length - 1; index += 1) {
    if (samePoint(ring[index]!, ring[index + 1]!)) {
      addIssue(
        issues,
        `${path}[${index}]`,
        'adjacent coordinates must be distinct',
      );
      return undefined;
    }
  }
  const wantsPositive = exterior;
  const correctlyWound = wantsPositive ? area > 0 : area < 0;
  const open = ring.slice(0, -1);
  const normalizedOpen = correctlyWound ? open : open.reverse();
  return canonicalizeRing([
    ...normalizedOpen,
    [...normalizedOpen[0]!] as XzPosition,
  ]);
}

function validateManifest(
  input: unknown,
  terrain: RealTerrainSceneManifest,
): BuildingValidationResult<BuildingPackageManifest> {
  const issues: BuildingValidationIssue[] = [];
  if (!isRecord(input)) {
    return {
      ok: false,
      issues: [{ path: 'manifest', message: 'must be an object' }],
    };
  }
  const aoi = input.aoi;
  const terrainIdentity = input.terrainIdentity;
  const policies = input.policies;
  const heightPolicy = isRecord(policies) ? policies.height : undefined;
  const provenance = input.provenance;
  const buildingDescriptor = input.buildings;
  const qaDescriptor = input.qaReport;

  if (input.formatVersion !== 1 || typeof input.formatVersion === 'boolean') {
    addIssue(issues, 'formatVersion', 'must be integer 1');
  }
  if (input.worldId !== terrain.id || input.worldId !== 'torquay-poc-001') {
    addIssue(
      issues,
      'worldId',
      'must match the currently loaded Torquay terrain',
    );
  }
  if (!nonempty(input.name)) addIssue(issues, 'name', 'must be non-empty');
  if (input.sourceCrs !== 'EPSG:27700')
    addIssue(issues, 'sourceCrs', 'must be EPSG:27700');
  if (input.axisConvention !== '+X east, +Y up, -Z north') {
    addIssue(
      issues,
      'axisConvention',
      'must use the validated local terrain axes',
    );
  }
  if (input.units !== 'metres') addIssue(issues, 'units', 'must be metres');

  if (!isRecord(aoi)) {
    addIssue(issues, 'aoi', 'must identify the selected pending candidate AOI');
  } else {
    if (aoi.crs !== terrain.aoi.crs)
      addIssue(issues, 'aoi.crs', 'must match terrain AOI CRS');
    if (!sameBounds(aoi.boundsM, terrain.aoi.boundsM)) {
      addIssue(
        issues,
        'aoi.boundsM',
        'must exactly match the validated terrain AOI bounds',
      );
    }
    if (!sameNumber(aoi.widthM, terrain.aoi.widthM)) {
      addIssue(issues, 'aoi.widthM', 'must match the terrain AOI width');
    }
    if (!sameNumber(aoi.heightM, terrain.aoi.heightM)) {
      addIssue(issues, 'aoi.heightM', 'must match the terrain AOI height');
    }
    const boundary = aoi.boundaryWgs84;
    if (!isRecord(boundary)) {
      addIssue(
        issues,
        'aoi.boundaryWgs84',
        'must match the validated terrain AOI WGS84 polygon',
      );
    } else {
      if (boundary.crs !== terrain.aoi.boundaryWgs84.crs) {
        addIssue(
          issues,
          'aoi.boundaryWgs84.crs',
          'must match the terrain boundary CRS',
        );
      }
      if (
        boundary.coordinateOrder !== terrain.aoi.boundaryWgs84.coordinateOrder
      ) {
        addIssue(
          issues,
          'aoi.boundaryWgs84.coordinateOrder',
          'must match the terrain boundary longitude-latitude order',
        );
      }
      if (boundary.closedRing !== true) {
        addIssue(
          issues,
          'aoi.boundaryWgs84.closedRing',
          'must be true for the stored geographic AOI boundary ring',
        );
      }
      const expectedRing = terrain.aoi.boundaryWgs84.ring;
      if (
        !Array.isArray(boundary.ring) ||
        boundary.ring.length !== expectedRing.length
      ) {
        addIssue(
          issues,
          'aoi.boundaryWgs84.ring',
          `must contain the ${expectedRing.length - 1} AOI corners and a closing coordinate`,
        );
      } else {
        for (let index = 0; index < expectedRing.length; index += 1) {
          const coordinate: unknown = boundary.ring[index];
          if (
            !Array.isArray(coordinate) ||
            coordinate.length !== 2 ||
            !isNumber(coordinate[0]) ||
            !isNumber(coordinate[1])
          ) {
            addIssue(
              issues,
              `aoi.boundaryWgs84.ring[${index}]`,
              'must be a finite [longitude, latitude] coordinate',
            );
            continue;
          }
          const expected = expectedRing[index]!;
          if (
            Math.abs(coordinate[0] - expected[0]) > 1e-10 ||
            Math.abs(coordinate[1] - expected[1]) > 1e-10
          ) {
            addIssue(
              issues,
              `aoi.boundaryWgs84.ring[${index}]`,
              'does not match the validated terrain AOI boundary',
            );
          }
        }
        const first: unknown = boundary.ring[0];
        const last: unknown = boundary.ring.at(-1);
        if (
          !Array.isArray(first) ||
          !Array.isArray(last) ||
          first.length !== 2 ||
          last.length !== 2 ||
          !isNumber(first[0]) ||
          !isNumber(first[1]) ||
          !isNumber(last[0]) ||
          !isNumber(last[1]) ||
          first[0] !== last[0] ||
          first[1] !== last[1]
        ) {
          addIssue(
            issues,
            'aoi.boundaryWgs84.ring',
            'must be a closed ring whose last coordinate repeats the first',
          );
        }
      }
    }
    if (aoi.selectionStatus !== 'selected_pending_coverage') {
      addIssue(
        issues,
        'aoi.selectionStatus',
        'must preserve pending candidate status',
      );
    }
    if (aoi.coverageStatus !== 'not_checked') {
      addIssue(
        issues,
        'aoi.coverageStatus',
        'mapped feature counts do not approve coverage',
      );
    }
  }

  if (!isRecord(terrainIdentity)) {
    addIssue(
      issues,
      'terrainIdentity',
      'must bind this package to the validated terrain',
    );
  } else {
    const origin = terrainIdentity.origin;
    if (!isRecord(origin)) {
      addIssue(
        issues,
        'terrainIdentity.origin',
        'must match the loaded terrain origin',
      );
    } else {
      for (const key of ['eastingM', 'northingM', 'elevationM'] as const) {
        if (!sameNumber(origin[key], terrain.origin[key])) {
          addIssue(
            issues,
            `terrainIdentity.origin.${key}`,
            'does not match loaded terrain',
          );
        }
      }
    }
    if (terrainIdentity.worldId !== terrain.id) {
      addIssue(
        issues,
        'terrainIdentity.worldId',
        'does not match loaded terrain',
      );
    }
    if (terrainIdentity.heightfieldPath !== terrain.heightfield.path) {
      addIssue(
        issues,
        'terrainIdentity.heightfieldPath',
        'does not match loaded terrain',
      );
    }
    if (terrainIdentity.heightfieldSha256 !== terrain.heightfield.sha256) {
      addIssue(
        issues,
        'terrainIdentity.heightfieldSha256',
        'does not match loaded terrain',
      );
    }
    if (
      terrainIdentity.heightfieldByteLength !== terrain.heightfield.byteLength
    ) {
      addIssue(
        issues,
        'terrainIdentity.heightfieldByteLength',
        'does not match loaded terrain',
      );
    }
    if (
      !Array.isArray(terrainIdentity.heightfieldDimensions) ||
      terrainIdentity.heightfieldDimensions.length !== 2 ||
      terrainIdentity.heightfieldDimensions[0] !==
        terrain.heightfield.columns ||
      terrainIdentity.heightfieldDimensions[1] !== terrain.heightfield.rows
    ) {
      addIssue(
        issues,
        'terrainIdentity.heightfieldDimensions',
        'does not match loaded terrain',
      );
    }
    if (
      terrainIdentity.verticalReference !== terrain.provenance.verticalReference
    ) {
      addIssue(
        issues,
        'terrainIdentity.verticalReference',
        'does not match loaded terrain',
      );
    }
  }

  if (!isRecord(heightPolicy)) {
    addIssue(
      issues,
      'policies.height',
      'must contain the validated feature-height policy',
    );
  } else {
    for (const key of ['version'] as const) {
      if (!isPositiveInteger(heightPolicy[key]))
        addIssue(
          issues,
          `policies.height.${key}`,
          'must be a positive integer',
        );
    }
    for (const key of [
      'levelsToMetres',
      'defaultHeightM',
      'minimumHeightM',
      'maximumHeightM',
    ] as const) {
      if (!isNumber(heightPolicy[key]) || heightPolicy[key] <= 0) {
        addIssue(
          issues,
          `policies.height.${key}`,
          'must be a positive finite number',
        );
      }
    }
    if (
      !Array.isArray(heightPolicy.precedence) ||
      heightPolicy.precedence.join('|') !==
        'height|building:levels|configured_default'
    ) {
      addIssue(
        issues,
        'policies.height.precedence',
        'must match the documented height precedence',
      );
    }
  }

  const geometryPolicy = isRecord(policies) ? policies.geometry : undefined;
  if (!isRecord(geometryPolicy)) {
    addIssue(
      issues,
      'policies.geometry',
      'must record the effective footprint processing policy',
    );
  } else {
    if (!isPositiveInteger(geometryPolicy.version))
      addIssue(
        issues,
        'policies.geometry.version',
        'must be a positive integer',
      );
    for (const key of [
      'acquisitionBufferM',
      'minimumClippedAreaM2',
      'coordinateQuantizationM',
    ] as const) {
      if (!isNumber(geometryPolicy[key]) || geometryPolicy[key] <= 0)
        addIssue(
          issues,
          `policies.geometry.${key}`,
          'must be a positive finite number',
        );
    }
    if (
      geometryPolicy.exteriorWinding !==
      'counter-clockwise in local XZ coordinates'
    )
      addIssue(
        issues,
        'policies.geometry.exteriorWinding',
        'must match the stored exterior winding',
      );
    if (geometryPolicy.interiorWinding !== 'clockwise in local XZ coordinates')
      addIssue(
        issues,
        'policies.geometry.interiorWinding',
        'must match the stored hole winding',
      );
    for (const key of [
      'invalidGeometryPolicy',
      'duplicatePolicy',
      'nearOverlapPolicy',
    ] as const) {
      if (!nonempty(geometryPolicy[key]))
        addIssue(
          issues,
          `policies.geometry.${key}`,
          'must document the effective geometry policy',
        );
    }
  }

  const operation = isRecord(input.coordinateOperation)
    ? input.coordinateOperation
    : undefined;
  const selectedOperation =
    operation && isRecord(operation.wgs84ToBng)
      ? operation.wgs84ToBng
      : undefined;
  const terrainOperation = terrain.provenance.coordinateOperation;
  if (!operation) {
    addIssue(
      issues,
      'coordinateOperation',
      'must record the pinned BNG transform',
    );
  } else {
    if (
      operation.axisOrder !==
      'longitude-latitude for geographic input; easting-northing for BNG'
    )
      addIssue(
        issues,
        'coordinateOperation.axisOrder',
        'must declare explicit XY order',
      );
    if (!selectedOperation) {
      addIssue(
        issues,
        'coordinateOperation.wgs84ToBng',
        'must record the selected transform',
      );
    } else {
      const normalizeDefinition = (definition: string): string =>
        definition.trim().split(/\s+/).join(' ');
      if (selectedOperation.name !== terrainOperation.name)
        addIssue(
          issues,
          'coordinateOperation.wgs84ToBng.name',
          'does not match the terrain package operation',
        );
      if (
        !isString(selectedOperation.definition) ||
        normalizeDefinition(selectedOperation.definition) !==
          normalizeDefinition(terrainOperation.definition)
      )
        addIssue(
          issues,
          'coordinateOperation.wgs84ToBng.definition',
          'does not match the exact pinned terrain operation',
        );
      if (
        !sameNumber(
          selectedOperation.reported_accuracy_m,
          terrainOperation.reportedAccuracyM,
        ) ||
        !sameNumber(
          selectedOperation.accuracy_m,
          terrainOperation.reportedAccuracyM,
        )
      )
        addIssue(
          issues,
          'coordinateOperation.wgs84ToBng.reported_accuracy_m',
          'does not match the selected operation accuracy',
        );
      if (selectedOperation.uses_grids !== terrainOperation.selectedUsesGrids)
        addIssue(
          issues,
          'coordinateOperation.wgs84ToBng.uses_grids',
          'does not match the selected operation grid state',
        );
      if (selectedOperation.best_available !== terrainOperation.bestAvailable)
        addIssue(
          issues,
          'coordinateOperation.wgs84ToBng.best_available',
          'does not match the selected terrain operation',
        );
      if (
        !nonempty(selectedOperation.grid_status) ||
        !selectedOperation.grid_status.includes('no grid')
      )
        addIssue(
          issues,
          'coordinateOperation.wgs84ToBng.grid_status',
          'must disclose that the selected operation uses no grids',
        );
      const missing = selectedOperation.preferred_missing_operations;
      const missingGridNames = Array.isArray(missing)
        ? missing.flatMap((item) =>
            isRecord(item) && Array.isArray(item.grids)
              ? item.grids.filter(isRecord).map((grid) => grid.short_name)
              : [],
          )
        : [];
      if (
        !terrainOperation.preferredMissingGridNames.every((name) =>
          missingGridNames.includes(name),
        )
      ) {
        addIssue(
          issues,
          'coordinateOperation.wgs84ToBng.preferred_missing_operations',
          'must retain the terrain operation preferred-grid caveat',
        );
      }
    }
  }

  if (!isRecord(provenance)) {
    addIssue(
      issues,
      'provenance',
      'must identify the retained OSM source and licence',
    );
  } else {
    for (const key of [
      'publisher',
      'product',
      'downloadUrl',
      'fileUrl',
      'downloadDate',
      'extractTimestamp',
      'filename',
      'sha256',
      'licence',
      'licenceUrl',
      'attribution',
      'geofabrikCredit',
    ] as const) {
      if (!nonempty(provenance[key]))
        addIssue(issues, `provenance.${key}`, 'must be a non-empty string');
    }
    if (!isPositiveInteger(provenance.sizeBytes))
      addIssue(issues, 'provenance.sizeBytes', 'must be a positive integer');
    if (!isHash(provenance.sha256))
      addIssue(
        issues,
        'provenance.sha256',
        'must be a 64-character SHA-256 digest',
      );
    if (
      !Array.isArray(provenance.notes) ||
      provenance.notes.some((note) => !nonempty(note))
    )
      addIssue(
        issues,
        'provenance.notes',
        'must retain the source and ODbL limitations',
      );
    const extractTimestamp = provenance.extractTimestamp;
    if (
      !nonempty(extractTimestamp) ||
      !Number.isFinite(Date.parse(extractTimestamp))
    ) {
      addIssue(
        issues,
        'provenance.extractTimestamp',
        'must be a valid extract timestamp from the source manifest',
      );
    }
    if (!isString(provenance.licence) || !provenance.licence.includes('ODbL')) {
      addIssue(
        issues,
        'provenance.licence',
        'must identify the ODbL source licence',
      );
    }
    if (
      !isString(provenance.attribution) ||
      !provenance.attribution.includes('OpenStreetMap contributors')
    ) {
      addIssue(issues, 'provenance.attribution', 'must retain OSM attribution');
    }
  }

  const generator = input.generator;
  if (!isRecord(generator)) {
    addIssue(
      issues,
      'generator',
      'must identify the exporter and processing version',
    );
  } else {
    for (const key of ['name', 'version', 'geosVersion'] as const) {
      if (!nonempty(generator[key]))
        addIssue(
          issues,
          `generator.${key}`,
          'must be a non-empty versioned value',
        );
    }
  }
  const coverage = input.coverage;
  if (!isRecord(coverage)) {
    addIssue(issues, 'coverage', 'must preserve the pending AOI status');
  } else {
    if (coverage.selectionStatus !== 'selected_pending_coverage')
      addIssue(issues, 'coverage.selectionStatus', 'must remain pending');
    if (coverage.coverageStatus !== 'not_checked')
      addIssue(
        issues,
        'coverage.coverageStatus',
        'mapped OSM counts do not verify coverage',
      );
    if (
      !nonempty(coverage.note) ||
      !coverage.note.toLowerCase().includes('not completeness')
    )
      addIssue(
        issues,
        'coverage.note',
        'must state counts are not completeness evidence',
      );
  }

  if (!isRecord(buildingDescriptor)) {
    addIssue(issues, 'buildings', 'must describe the local JSON payload');
  } else {
    if (buildingDescriptor.path !== 'buildings.json')
      addIssue(
        issues,
        'buildings.path',
        'must be the safe local buildings.json asset',
      );
    if (!isSafeLocalAssetPath(buildingDescriptor.path))
      addIssue(issues, 'buildings.path', 'must be a safe local relative path');
    if (
      !isPositiveInteger(buildingDescriptor.byteLength) ||
      buildingDescriptor.byteLength > MAX_BUILDINGS_BYTES
    ) {
      addIssue(
        issues,
        'buildings.byteLength',
        `must be from 1 to ${MAX_BUILDINGS_BYTES} bytes`,
      );
    }
    if (!isHash(buildingDescriptor.sha256))
      addIssue(
        issues,
        'buildings.sha256',
        'must be a 64-character SHA-256 digest',
      );
    if (
      !isPositiveInteger(buildingDescriptor.count) ||
      buildingDescriptor.count > MAX_BUILDING_FEATURES
    ) {
      addIssue(
        issues,
        'buildings.count',
        `must be from 1 to ${MAX_BUILDING_FEATURES}`,
      );
    }
  }
  if (!isRecord(qaDescriptor)) {
    addIssue(issues, 'qaReport', 'must bind the local QA JSON');
  } else {
    if (
      qaDescriptor.path !== 'qa.json' ||
      !isSafeLocalAssetPath(qaDescriptor.path)
    ) {
      addIssue(issues, 'qaReport.path', 'must be the safe local qa.json asset');
    }
    if (
      !isPositiveInteger(qaDescriptor.byteLength) ||
      qaDescriptor.byteLength > MAX_BUILDING_QA_BYTES
    ) {
      addIssue(
        issues,
        'qaReport.byteLength',
        `must be from 1 to ${MAX_BUILDING_QA_BYTES} bytes`,
      );
    }
    if (!isHash(qaDescriptor.sha256))
      addIssue(
        issues,
        'qaReport.sha256',
        'must be a 64-character SHA-256 digest',
      );
  }

  if (issues.length > 0) return { ok: false, issues };
  return {
    ok: true,
    value: input as unknown as BuildingPackageManifest,
  };
}

function isHash(value: unknown): value is string {
  return typeof value === 'string' && /^[a-f0-9]{64}$/i.test(value);
}

function parseFeature(
  input: unknown,
  path: string,
  manifest: BuildingPackageManifest,
  issues: BuildingValidationIssue[],
  coordinateCounter: { coordinates: number },
): BuildingFeature | undefined {
  if (!isRecord(input)) {
    addIssue(issues, path, 'must be a building object');
    return undefined;
  }
  const source = input.source;
  const geometryInput = input.geometry;
  const tagsInput = input.tags;
  let featureValid = true;
  const fail = (field: string, message: string): void => {
    addIssue(issues, `${path}.${field}`, message);
    featureValid = false;
  };
  if (!nonempty(input.id) || !/^osm:(way|relation):\d+$/.test(input.id)) {
    fail('id', 'must be a stable osm:way:<id> or osm:relation:<id> identity');
  }
  if (!isRecord(source)) {
    fail('source', 'must identify the OSM object');
  } else {
    if (!nonempty(source.dataset)) fail('source.dataset', 'must be non-empty');
    if (source.objectType !== 'way' && source.objectType !== 'relation')
      fail('source.objectType', 'must be way or relation');
    if (!isPositiveInteger(source.osmId))
      fail('source.osmId', 'must be a positive integer');
    if (!isPositiveInteger(source.version))
      fail('source.version', 'must be a positive integer');
    if (!nonempty(source.timestamp))
      fail('source.timestamp', 'must be non-empty');
    if (
      typeof input.id === 'string' &&
      source.objectType &&
      source.osmId !== undefined &&
      input.id !== `osm:${source.objectType}:${source.osmId}`
    ) {
      fail('id', 'must match the source object type and ID');
    }
  }
  if (!isRecord(tagsInput)) {
    fail('tags', 'must be an object containing retained string tags');
  }
  const tags: Record<string, string> = {};
  if (isRecord(tagsInput)) {
    for (const [key, value] of Object.entries(tagsInput)) {
      if (!isString(value)) fail(`tags.${key}`, 'must be a string');
      else tags[key] = value;
    }
  }
  if (
    !isRecord(geometryInput) ||
    geometryInput.type !== 'MultiPolygon' ||
    !Array.isArray(geometryInput.polygons) ||
    geometryInput.polygons.length === 0
  ) {
    fail('geometry', 'must be a non-empty MultiPolygon');
  }
  const polygons: BuildingPolygon[] = [];
  let area = 0;
  if (isRecord(geometryInput) && Array.isArray(geometryInput.polygons)) {
    geometryInput.polygons.forEach((polygonInput, polygonIndex) => {
      const polygonPath = `${path}.geometry.polygons[${polygonIndex}]`;
      if (!isRecord(polygonInput)) {
        addIssue(issues, polygonPath, 'must be a polygon object');
        featureValid = false;
        return;
      }
      const exterior = parseRing(
        polygonInput.exteriorXZ,
        `${polygonPath}.exteriorXZ`,
        true,
        issues,
        coordinateCounter,
      );
      const holesInput = polygonInput.interiorRingsXZ;
      if (!Array.isArray(holesInput)) {
        addIssue(
          issues,
          `${polygonPath}.interiorRingsXZ`,
          'must be an array of closed rings',
        );
        featureValid = false;
        return;
      }
      const holes: XzPosition[][] = [];
      for (let holeIndex = 0; holeIndex < holesInput.length; holeIndex += 1) {
        const hole = parseRing(
          holesInput[holeIndex],
          `${polygonPath}.interiorRingsXZ[${holeIndex}]`,
          false,
          issues,
          coordinateCounter,
        );
        if (hole) holes.push(hole);
        else featureValid = false;
      }
      if (!exterior) {
        featureValid = false;
        return;
      }
      const minX = -manifest.aoi.widthM / 2 - 1e-6;
      const maxX = manifest.aoi.widthM / 2 + 1e-6;
      const minZ = -manifest.aoi.heightM / 2 - 1e-6;
      const maxZ = manifest.aoi.heightM / 2 + 1e-6;
      for (const [ringIndex, ring] of [exterior, ...holes].entries()) {
        if (
          ring.some(([x, z]) => x < minX || x > maxX || z < minZ || z > maxZ)
        ) {
          addIssue(
            issues,
            ringIndex === 0
              ? `${polygonPath}.exteriorXZ`
              : `${polygonPath}.interiorRingsXZ[${ringIndex - 1}]`,
            'coordinates must remain within the local AOI bounds',
          );
          featureValid = false;
        }
      }
      for (let holeIndex = 0; holeIndex < holes.length; holeIndex += 1) {
        const hole = holes[holeIndex]!;
        if (
          !hole
            .slice(0, -1)
            .every((point) => pointInRingInterior(point, exterior)) ||
          hasForbiddenRingIntersection(hole, exterior, false)
        ) {
          addIssue(
            issues,
            `${polygonPath}.interiorRingsXZ[${holeIndex}]`,
            'hole must be wholly contained by its exterior and cannot cross or touch its boundary',
          );
          featureValid = false;
        }
        for (let otherIndex = 0; otherIndex < holeIndex; otherIndex += 1) {
          const other = holes[otherIndex]!;
          if (
            hasForbiddenRingIntersection(hole, other, false) ||
            pointInRing(hole[0]!, other) ||
            pointInRing(other[0]!, hole)
          ) {
            addIssue(
              issues,
              `${polygonPath}.interiorRingsXZ`,
              'holes cannot cross, touch, overlap, or contain one another',
            );
            featureValid = false;
            break;
          }
        }
      }
      const polygonArea =
        Math.abs(signedArea(exterior)) -
        holes.reduce((sum, ring) => sum + Math.abs(signedArea(ring)), 0);
      if (!Number.isFinite(polygonArea) || polygonArea <= 1e-8) {
        addIssue(
          issues,
          polygonPath,
          'must have positive area after subtracting holes',
        );
        featureValid = false;
      }
      area += polygonArea;
      holes.sort((left, right) =>
        canonicalRingKey(left).localeCompare(canonicalRingKey(right)),
      );
      polygons.push({ exteriorXZ: exterior, interiorRingsXZ: holes });
    });
  }
  for (
    let polygonIndex = 0;
    polygonIndex < polygons.length;
    polygonIndex += 1
  ) {
    for (let otherIndex = 0; otherIndex < polygonIndex; otherIndex += 1) {
      if (polygonsOverlap(polygons[polygonIndex]!, polygons[otherIndex]!)) {
        addIssue(
          issues,
          `${path}.geometry.polygons[${polygonIndex}]`,
          'MultiPolygon component interiors cannot overlap; isolated point contacts and islands inside holes are allowed',
        );
        featureValid = false;
        break;
      }
    }
  }
  polygons.sort((left, right) =>
    canonicalRingKey(left.exteriorXZ).localeCompare(
      canonicalRingKey(right.exteriorXZ),
    ),
  );
  if (
    !isNumber(input.footprintAreaM2) ||
    input.footprintAreaM2 <= 0 ||
    Math.abs(input.footprintAreaM2 - area) > Math.max(0.01, area * 1e-6)
  ) {
    fail(
      'footprintAreaM2',
      'must match the finite positive polygon area in square metres',
    );
  }
  if (typeof input.clippedToAoi !== 'boolean')
    fail('clippedToAoi', 'must be boolean');
  if (
    !Array.isArray(input.qualityFlags) ||
    input.qualityFlags.some((flag) => !isString(flag))
  )
    fail('qualityFlags', 'must be an array of strings');
  if (
    !Array.isArray(input.duplicateReferences) ||
    input.duplicateReferences.some((reference) => !nonempty(reference))
  )
    fail('duplicateReferences', 'must be an array of non-empty identities');
  if (!isNumber(input.heightM) || input.heightM <= 0)
    fail('heightM', 'must be a positive finite number');
  if (!isRecord(manifest.policies.height))
    fail('heightM', 'effective height policy is unavailable');
  if (isRecord(manifest.policies.height) && isRecord(input.heightProvenance)) {
    const policy = manifest.policies.height;
    const expected = resolveHeight(tags, policy);
    if (
      !sameNumber(input.heightM, expected.heightM) ||
      input.heightMethod !== expected.method ||
      input.heightConfidence !== expected.confidence
    ) {
      fail(
        'heightProvenance',
        'height method, confidence, or final height disagrees with retained source tags and policy',
      );
    }
    for (const key of Object.keys(expected) as (keyof typeof expected)[]) {
      const actual = input.heightProvenance[key];
      const expectedValue = expected[key];
      const matches =
        typeof expectedValue === 'number'
          ? sameNumber(actual, expectedValue)
          : actual === expectedValue;
      if (!matches)
        fail(
          `heightProvenance.${key}`,
          'does not match retained tags and effective policy',
        );
    }
  } else {
    fail(
      'heightProvenance',
      'must contain the recomputable source and fallback record',
    );
  }
  if (!featureValid) return undefined;
  return {
    ...(input as unknown as BuildingFeature),
    geometry: { type: 'MultiPolygon', polygons },
  };
}

function validatePayloadAndQa(
  payloadInput: unknown,
  qaInput: unknown,
  manifest: BuildingPackageManifest,
): BuildingValidationResult<LoadedBuildingPackage> {
  const issues: BuildingValidationIssue[] = [];
  if (!isRecord(payloadInput)) {
    return {
      ok: false,
      issues: [{ path: 'buildings.json', message: 'must be an object' }],
    };
  }
  if (
    payloadInput.formatVersion !== 1 ||
    typeof payloadInput.formatVersion === 'boolean'
  )
    addIssue(issues, 'buildings.json.formatVersion', 'must be integer 1');
  if (payloadInput.worldId !== manifest.worldId)
    addIssue(issues, 'buildings.json.worldId', 'does not match the manifest');
  if (payloadInput.axisConvention !== '+X east, +Y up, -Z north')
    addIssue(
      issues,
      'buildings.json.axisConvention',
      'must match the terrain axes',
    );
  if (payloadInput.units !== 'metres')
    addIssue(issues, 'buildings.json.units', 'must be metres');
  if (
    payloadInput.geometryCoordinates !==
    'local XZ metres; no absolute BNG coordinates per vertex'
  )
    addIssue(
      issues,
      'buildings.json.geometryCoordinates',
      'must use local XZ coordinates',
    );
  if (!Array.isArray(payloadInput.buildings))
    addIssue(issues, 'buildings.json.buildings', 'must be an array');
  const inputFeatures = Array.isArray(payloadInput.buildings)
    ? payloadInput.buildings
    : [];
  if (inputFeatures.length !== manifest.buildings.count)
    addIssue(
      issues,
      'buildings.json.buildings',
      'feature count does not match manifest',
    );
  if (inputFeatures.length > MAX_BUILDING_FEATURES)
    addIssue(
      issues,
      'buildings.json.buildings',
      `exceeds the ${MAX_BUILDING_FEATURES} feature safety limit`,
    );
  const seenIds = new Set<string>();
  const seenGeometry = new Set<string>();
  const coordinateCounter = { coordinates: 0 };
  const features: BuildingFeature[] = [];
  for (
    let index = 0;
    index < Math.min(inputFeatures.length, MAX_BUILDING_FEATURES);
    index += 1
  ) {
    const feature = parseFeature(
      inputFeatures[index],
      `buildings.json.buildings[${index}]`,
      manifest,
      issues,
      coordinateCounter,
    );
    if (!feature) continue;
    if (seenIds.has(feature.id))
      addIssue(
        issues,
        `buildings.json.buildings[${index}].id`,
        'duplicate building identity',
      );
    seenIds.add(feature.id);
    const signature = JSON.stringify(feature.geometry.polygons);
    if (seenGeometry.has(signature))
      addIssue(
        issues,
        `buildings.json.buildings[${index}].geometry`,
        'duplicate canonical geometry is not allowed',
      );
    seenGeometry.add(signature);
    features.push(feature);
  }

  if (!isRecord(qaInput)) {
    addIssue(issues, 'qa.json', 'must be an object');
  } else {
    if (
      qaInput.formatVersion !== 1 ||
      typeof qaInput.formatVersion === 'boolean'
    )
      addIssue(issues, 'qa.json.formatVersion', 'must be integer 1');
    if (qaInput.aoiId !== manifest.worldId)
      addIssue(issues, 'qa.json.aoiId', 'does not match the manifest');
    if (qaInput.selectionStatus !== 'selected_pending_coverage')
      addIssue(
        issues,
        'qa.json.selectionStatus',
        'must preserve pending AOI status',
      );
    if (qaInput.coverageStatus !== 'not_checked')
      addIssue(issues, 'qa.json.coverageStatus', 'must remain not_checked');
    const packageIdentity = qaInput.package;
    if (!isRecord(packageIdentity)) {
      addIssue(
        issues,
        'qa.json.package',
        'must bind the QA report to the validated building payload',
      );
    } else {
      if (packageIdentity.worldId !== manifest.worldId)
        addIssue(
          issues,
          'qa.json.package.worldId',
          'must match the validated package world ID',
        );
      if (packageIdentity.manifestPath !== 'manifest.json')
        addIssue(
          issues,
          'qa.json.package.manifestPath',
          'must identify the package-local manifest',
        );
      if (packageIdentity.buildingsPath !== manifest.buildings.path)
        addIssue(
          issues,
          'qa.json.package.buildingsPath',
          'must match manifest.buildings.path',
        );
      if (
        !isPositiveInteger(packageIdentity.buildingsByteLength) ||
        packageIdentity.buildingsByteLength !== manifest.buildings.byteLength
      )
        addIssue(
          issues,
          'qa.json.package.buildingsByteLength',
          'must match manifest.buildings.byteLength',
        );
      if (
        !isHash(packageIdentity.buildingsSha256) ||
        packageIdentity.buildingsSha256 !== manifest.buildings.sha256
      )
        addIssue(
          issues,
          'qa.json.package.buildingsSha256',
          'must match manifest.buildings.sha256',
        );
    }
  }
  const counts =
    isRecord(qaInput) && isRecord(qaInput.counts) ? qaInput.counts : undefined;
  const quality =
    isRecord(qaInput) && isRecord(qaInput.quality)
      ? qaInput.quality
      : undefined;
  const qaSummary =
    isRecord(qaInput) && isRecord(qaInput.summary)
      ? qaInput.summary
      : undefined;
  let componentCount = 0;
  let holeCount = 0;
  let footprintAreaM2 = 0;
  let minimumHeightM = Number.POSITIVE_INFINITY;
  let maximumHeightM = Number.NEGATIVE_INFINITY;
  let totalHeightM = 0;
  const heightMethodCounts: Record<BuildingHeightMethod, number> = {
    osm_height: 0,
    estimated_levels: 0,
    estimated_default: 0,
  };
  const heightClampCounts: Record<string, number> = {};
  for (const feature of features) {
    componentCount += feature.geometry.polygons.length;
    holeCount += feature.geometry.polygons.reduce(
      (sum, polygon) => sum + polygon.interiorRingsXZ.length,
      0,
    );
    footprintAreaM2 += feature.footprintAreaM2;
    minimumHeightM = Math.min(minimumHeightM, feature.heightM);
    maximumHeightM = Math.max(maximumHeightM, feature.heightM);
    totalHeightM += feature.heightM;
    heightMethodCounts[feature.heightMethod] += 1;
    if (feature.heightProvenance.clamp !== null) {
      heightClampCounts[feature.heightProvenance.clamp] =
        (heightClampCounts[feature.heightProvenance.clamp] ?? 0) + 1;
    }
  }
  if (!counts || counts.exported_buildings !== features.length)
    addIssue(
      issues,
      'qa.json.counts.exported_buildings',
      'must equal the validated feature count',
    );
  if (!counts || counts.exported_components !== componentCount)
    addIssue(
      issues,
      'qa.json.counts.exported_components',
      'must equal the validated polygon component count',
    );
  if (!counts || counts.exported_holes !== holeCount)
    addIssue(
      issues,
      'qa.json.counts.exported_holes',
      'must equal the validated interior ring count',
    );
  if (!quality || quality.taggedHeightsAreUnverified !== true)
    addIssue(
      issues,
      'qa.json.quality.taggedHeightsAreUnverified',
      'must disclose that OSM tagged heights are unverified',
    );
  const reportedMethodCounts = {
    osm_height: heightMethodCounts.osm_height,
    estimated_levels: heightMethodCounts.estimated_levels,
    estimated_default: heightMethodCounts.estimated_default,
  };
  for (const key of Object.keys(
    reportedMethodCounts,
  ) as BuildingHeightMethod[]) {
    if (reportedMethodCounts[key] === 0)
      delete (
        reportedMethodCounts as Partial<Record<BuildingHeightMethod, number>>
      )[key];
  }
  if (
    !quality ||
    !isRecord(quality.heightMethodCounts) ||
    JSON.stringify(sortRecord(quality.heightMethodCounts)) !==
      JSON.stringify(sortRecord(reportedMethodCounts))
  )
    addIssue(
      issues,
      'qa.json.quality.heightMethodCounts',
      'must match the validated feature records',
    );
  if (
    !quality ||
    !isRecord(quality.heightClampCounts) ||
    JSON.stringify(sortRecord(quality.heightClampCounts)) !==
      JSON.stringify(sortRecord(heightClampCounts))
  )
    addIssue(
      issues,
      'qa.json.quality.heightClampCounts',
      'must match the validated feature records',
    );
  if (!qaSummary)
    addIssue(
      issues,
      'qa.json.summary',
      'must contain measured feature summaries',
    );
  else {
    if (
      !sameNumber(
        qaSummary.buildingFootprintAreaM2,
        footprintAreaM2,
        Math.max(0.01, footprintAreaM2 * 1e-6),
      )
    )
      addIssue(
        issues,
        'qa.json.summary.buildingFootprintAreaM2',
        'must match validated stored footprint area',
      );
    if (!sameNumber(qaSummary.minimumHeightM, minimumHeightM))
      addIssue(
        issues,
        'qa.json.summary.minimumHeightM',
        'must match validated feature heights',
      );
    if (!sameNumber(qaSummary.maximumHeightM, maximumHeightM))
      addIssue(
        issues,
        'qa.json.summary.maximumHeightM',
        'must match validated feature heights',
      );
    const mean = features.length > 0 ? totalHeightM / features.length : 0;
    // The Python exporter stores this summary at millimetre precision.
    if (!sameNumber(qaSummary.meanHeightM, mean, 0.0005001))
      addIssue(
        issues,
        'qa.json.summary.meanHeightM',
        'must match validated feature heights',
      );
    if (
      !nonempty(qaSummary.densityInterpretation) ||
      !qaSummary.densityInterpretation
        .toLowerCase()
        .includes('not a completeness estimate')
    )
      addIssue(
        issues,
        'qa.json.summary.densityInterpretation',
        'must state mapped counts do not establish completeness',
      );
  }
  if (issues.length > 0) return { ok: false, issues };
  return {
    ok: true,
    value: {
      manifest,
      features,
      qa: qaInput as unknown as BuildingQaSummary,
      componentCount,
      holeCount,
      heightMethodCounts,
    },
  };
}

function sortRecord(value: UnknownRecord): UnknownRecord {
  return Object.fromEntries(
    Object.entries(value).sort(([a], [b]) => a.localeCompare(b)),
  );
}

export function validateBuildingPackageManifest(
  input: unknown,
  terrain: RealTerrainSceneManifest,
): BuildingValidationResult<BuildingPackageManifest> {
  return validateManifest(input, terrain);
}

export function validateBuildingPayload(
  payload: unknown,
  qa: unknown,
  manifest: BuildingPackageManifest,
): BuildingValidationResult<LoadedBuildingPackage> {
  return validatePayloadAndQa(payload, qa, manifest);
}

export function formatBuildingIssues(
  issues: BuildingValidationIssue[],
): string {
  return issues.map(({ path, message }) => `${path}: ${message}`).join('; ');
}
