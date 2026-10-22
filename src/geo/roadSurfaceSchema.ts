export const ROAD_SURFACE_PREVIEW_ALGORITHM = 'road-surface-preview-3.0.0';
export const ROAD_SURFACE_GRID = {
  columns: 1001,
  rows: 1001,
  spacingM: 2,
  widthM: 2000,
  depthM: 2000,
  heightfieldByteLength: 4_008_004,
} as const;

export interface RoadSurfaceSourceIdentity {
  releaseId: string;
  readySha256: string;
  inventorySha256: string;
  terrainManifestSha256: string;
  terrainHeightfieldSha256: string;
  roadManifestSha256: string;
  roadPayloadSha256: string;
}

export interface RoadSurfaceAsset {
  path: 'heightfield.f32' | 'qa.json';
  byteLength: number;
  sha256: string;
}

export interface RoadSurfacePreviewManifest {
  formatVersion: 1;
  worldId: 'torquay-poc-001';
  sceneProfile: 'current_2km';
  packageType: 'road-surface-display-grid-derivative';
  algorithmVersion: typeof ROAD_SURFACE_PREVIEW_ALGORITHM;
  interpretation: string;
  source: RoadSurfaceSourceIdentity;
  grid: {
    columns: typeof ROAD_SURFACE_GRID.columns;
    rows: typeof ROAD_SURFACE_GRID.rows;
    spacingM: typeof ROAD_SURFACE_GRID.spacingM;
    widthM: typeof ROAD_SURFACE_GRID.widthM;
    depthM: typeof ROAD_SURFACE_GRID.depthM;
    rowOrder: 'north-to-south';
    byteOrder: 'little-endian';
    encoding: 'float32';
    valueMeaning: string;
  };
  parameters: {
    transitionDistanceFactor: number;
    ambiguityDistanceM: number;
    ambiguityHeightDifferenceM: number;
    ambiguityRetentionCore: 'larger involved half-width plus one grid spacing';
    ambiguityFadeDistance: 'larger involved configured width or two grid spacings';
    maximumChangedHeightM: number;
    fallbackAbsoluteChangeM: number;
    fallbackAddedGradientMPerM: number;
    fallbackMinimumRegionAreaM2: number;
    fallbackFadeDistanceM: number;
    targetCrossfallPercent: 0;
    roadSurfaceOffsetM: 0.05;
  };
  assets: { heightfield: RoadSurfaceAsset; qa: RoadSurfaceAsset };
}

export interface RoadSurfacePreviewQa {
  formatVersion: 1;
  algorithmVersion: typeof ROAD_SURFACE_PREVIEW_ALGORITHM;
  source: RoadSurfaceSourceIdentity;
  sourceMetadata: {
    worldId: 'torquay-poc-001';
    sceneProfile: 'current_2km';
    roadFeatureCount: number;
    rasterComparisonInputs: {
      path: string;
      byteLength: number;
      sha256: string;
    }[];
  };
  derivative: {
    path: 'heightfield.f32';
    byteLength: typeof ROAD_SURFACE_GRID.heightfieldByteLength;
    sha256: string;
    grid: RoadSurfacePreviewManifest['grid'];
  };
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function exactKeys(
  value: Record<string, unknown>,
  expected: readonly string[],
) {
  const actual = Object.keys(value).sort();
  const wanted = [...expected].sort();
  return (
    actual.length === wanted.length &&
    actual.every((key, i) => key === wanted[i])
  );
}

function sha256(value: unknown): value is string {
  return typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
}

function positiveFinite(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0;
}

function parseSource(value: unknown): RoadSurfaceSourceIdentity | null {
  if (
    !isRecord(value) ||
    !exactKeys(value, [
      'releaseId',
      'readySha256',
      'inventorySha256',
      'terrainManifestSha256',
      'terrainHeightfieldSha256',
      'roadManifestSha256',
      'roadPayloadSha256',
    ]) ||
    !Object.values(value).every(sha256)
  )
    return null;
  return value as unknown as RoadSurfaceSourceIdentity;
}

function parseSourceMetadata(
  value: unknown,
): RoadSurfacePreviewQa['sourceMetadata'] | null {
  if (
    !isRecord(value) ||
    !exactKeys(value, [
      'worldId',
      'sceneProfile',
      'roadFeatureCount',
      'rasterComparisonInputs',
    ]) ||
    value['worldId'] !== 'torquay-poc-001' ||
    value['sceneProfile'] !== 'current_2km' ||
    !Number.isSafeInteger(value['roadFeatureCount']) ||
    (value['roadFeatureCount'] as number) <= 0 ||
    !Array.isArray(value['rasterComparisonInputs']) ||
    value['rasterComparisonInputs'].length !== 2
  )
    return null;
  const rasterComparisonInputs = value['rasterComparisonInputs'].map(
    (input) => {
      if (
        !isRecord(input) ||
        !exactKeys(input, ['path', 'byteLength', 'sha256']) ||
        typeof input['path'] !== 'string' ||
        !input['path'].startsWith('data/raw/ea_dtm/') ||
        !Number.isSafeInteger(input['byteLength']) ||
        (input['byteLength'] as number) <= 0 ||
        !sha256(input['sha256'])
      )
        return null;
      return input as { path: string; byteLength: number; sha256: string };
    },
  );
  if (
    rasterComparisonInputs.some((input) => input === null) ||
    new Set(rasterComparisonInputs.map((input) => input!.path)).size !== 2
  )
    return null;
  return {
    worldId: 'torquay-poc-001',
    sceneProfile: 'current_2km',
    roadFeatureCount: value['roadFeatureCount'] as number,
    rasterComparisonInputs: rasterComparisonInputs as {
      path: string;
      byteLength: number;
      sha256: string;
    }[],
  };
}

function parseGrid(value: unknown): RoadSurfacePreviewManifest['grid'] | null {
  if (
    !isRecord(value) ||
    !exactKeys(value, [
      'columns',
      'rows',
      'spacingM',
      'widthM',
      'depthM',
      'rowOrder',
      'byteOrder',
      'encoding',
      'valueMeaning',
    ]) ||
    value['columns'] !== ROAD_SURFACE_GRID.columns ||
    value['rows'] !== ROAD_SURFACE_GRID.rows ||
    value['spacingM'] !== ROAD_SURFACE_GRID.spacingM ||
    value['widthM'] !== ROAD_SURFACE_GRID.widthM ||
    value['depthM'] !== ROAD_SURFACE_GRID.depthM ||
    value['rowOrder'] !== 'north-to-south' ||
    value['byteOrder'] !== 'little-endian' ||
    value['encoding'] !== 'float32' ||
    typeof value['valueMeaning'] !== 'string'
  )
    return null;
  return value as unknown as RoadSurfacePreviewManifest['grid'];
}

function parseAsset(
  value: unknown,
  expectedPath: RoadSurfaceAsset['path'],
): RoadSurfaceAsset | null {
  if (
    !isRecord(value) ||
    !exactKeys(value, ['path', 'byteLength', 'sha256']) ||
    value['path'] !== expectedPath ||
    !Number.isSafeInteger(value['byteLength']) ||
    (value['byteLength'] as number) <= 0 ||
    !sha256(value['sha256']) ||
    (expectedPath === 'heightfield.f32' &&
      value['byteLength'] !== ROAD_SURFACE_GRID.heightfieldByteLength) ||
    (expectedPath === 'qa.json' &&
      (value['byteLength'] as number) > 16 * 1024 * 1024)
  )
    return null;
  return value as unknown as RoadSurfaceAsset;
}

export function parseRoadSurfacePreviewManifest(
  input: unknown,
): RoadSurfacePreviewManifest {
  if (
    !isRecord(input) ||
    !exactKeys(input, [
      'formatVersion',
      'worldId',
      'sceneProfile',
      'packageType',
      'algorithmVersion',
      'interpretation',
      'source',
      'grid',
      'parameters',
      'assets',
    ])
  )
    throw new Error('preview manifest has an invalid object shape');
  const source = parseSource(input['source']);
  const grid = parseGrid(input['grid']);
  const parameters = input['parameters'];
  const assets = input['assets'];
  if (
    input['formatVersion'] !== 1 ||
    input['worldId'] !== 'torquay-poc-001' ||
    input['sceneProfile'] !== 'current_2km' ||
    input['packageType'] !== 'road-surface-display-grid-derivative' ||
    input['algorithmVersion'] !== ROAD_SURFACE_PREVIEW_ALGORITHM ||
    typeof input['interpretation'] !== 'string' ||
    !source ||
    !grid ||
    !isRecord(parameters) ||
    !exactKeys(parameters, [
      'transitionDistanceFactor',
      'ambiguityDistanceM',
      'ambiguityHeightDifferenceM',
      'ambiguityRetentionCore',
      'ambiguityFadeDistance',
      'maximumChangedHeightM',
      'fallbackAbsoluteChangeM',
      'fallbackAddedGradientMPerM',
      'fallbackMinimumRegionAreaM2',
      'fallbackFadeDistanceM',
      'targetCrossfallPercent',
      'roadSurfaceOffsetM',
    ]) ||
    parameters['transitionDistanceFactor'] !== 1 ||
    !positiveFinite(parameters['ambiguityDistanceM']) ||
    !positiveFinite(parameters['ambiguityHeightDifferenceM']) ||
    parameters['ambiguityRetentionCore'] !==
      'larger involved half-width plus one grid spacing' ||
    parameters['ambiguityFadeDistance'] !==
      'larger involved configured width or two grid spacings' ||
    !positiveFinite(parameters['maximumChangedHeightM']) ||
    !positiveFinite(parameters['fallbackAbsoluteChangeM']) ||
    !positiveFinite(parameters['fallbackAddedGradientMPerM']) ||
    !positiveFinite(parameters['fallbackMinimumRegionAreaM2']) ||
    !positiveFinite(parameters['fallbackFadeDistanceM']) ||
    parameters['targetCrossfallPercent'] !== 0 ||
    parameters['roadSurfaceOffsetM'] !== 0.05 ||
    !isRecord(assets) ||
    !exactKeys(assets, ['heightfield', 'qa'])
  )
    throw new Error(
      'preview manifest does not describe the supported current_2km derivative',
    );
  const heightfield = parseAsset(assets['heightfield'], 'heightfield.f32');
  const qa = parseAsset(assets['qa'], 'qa.json');
  if (!heightfield || !qa)
    throw new Error('preview manifest has an invalid asset descriptor');
  return input as unknown as RoadSurfacePreviewManifest;
}

export function parseRoadSurfacePreviewQa(
  input: unknown,
): RoadSurfacePreviewQa {
  if (
    !isRecord(input) ||
    !isRecord(input['derivative']) ||
    input['formatVersion'] !== 1 ||
    input['algorithmVersion'] !== ROAD_SURFACE_PREVIEW_ALGORITHM
  )
    throw new Error('preview QA report has an invalid header');
  const source = parseSource(input['source']);
  const sourceMetadata = parseSourceMetadata(input['sourceMetadata']);
  const derivative = input['derivative'];
  const grid = parseGrid(derivative['grid']);
  if (
    !source ||
    !sourceMetadata ||
    !exactKeys(derivative, ['path', 'byteLength', 'sha256', 'grid']) ||
    derivative['path'] !== 'heightfield.f32' ||
    derivative['byteLength'] !== ROAD_SURFACE_GRID.heightfieldByteLength ||
    !sha256(derivative['sha256']) ||
    !grid
  )
    throw new Error(
      'preview QA report does not match its supported heightfield',
    );
  return {
    formatVersion: 1,
    algorithmVersion: ROAD_SURFACE_PREVIEW_ALGORITHM,
    source,
    sourceMetadata,
    derivative: derivative as unknown as RoadSurfacePreviewQa['derivative'],
  };
}
