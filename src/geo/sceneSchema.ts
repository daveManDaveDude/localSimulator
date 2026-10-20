export const MAX_HEIGHTFIELD_SAMPLES = 16_000_000;
export const HEIGHTFIELD_EXTENT_RELATIVE_TOLERANCE = 1e-9;
export const AXIS_CONVENTION = '+X east, +Y up, -Z north' as const;
export const HEIGHTFIELD_VALUE_MEANING =
  'world Y in metres relative to origin elevation' as const;

export interface SyntheticSceneManifest {
  formatVersion: 1;
  id: string;
  name: string;
  worldType: 'synthetic';
  sourceCrs: 'LOCAL_SYNTHETIC';
  axisConvention: typeof AXIS_CONVENTION;
  origin: {
    eastingM: number;
    northingM: number;
    elevationM: number;
  };
  extentM: {
    width: number;
    depth: number;
  };
  heightfield: {
    path: string;
    columns: number;
    rows: number;
    spacingM: number;
    rowOrder: 'north-to-south';
    byteOrder: 'little-endian';
    encoding: 'float32';
    valueMeaning: typeof HEIGHTFIELD_VALUE_MEANING;
    sha256: string;
  };
  provenance: {
    kind: 'synthetic';
    generator: string;
    generatorVersion: string;
    note: string;
  };
  buildings?: string;
  roads?: string;
}

export interface RealTerrainSource {
  tileName: string;
  archiveFilename: string;
  archiveSizeBytes: number;
  archiveSha256: string;
  archiveDownloadUrl: string;
  downloadDate: string;
  archiveRasterMember: string;
  archiveXmlMember: string;
  rasterFilename: string;
  rasterSizeBytes: number;
  rasterSha256: string;
  rasterCrs: 'EPSG:27700';
  rasterTransform: [number, number, number, number, number, number];
  rasterBoundsM: [number, number, number, number];
  rasterWidthPixels: number;
  rasterHeightPixels: number;
  rasterResolutionM: [1, 1];
  rasterDtype: 'float32';
  rasterNodata: number;
  xmlFilename: string;
  xmlSizeBytes: number;
  xmlSha256: string;
  tileSurveyPeriod: string;
  xmlVerticalReference: string;
}

export interface RealTerrainCoordinateOperation {
  name: 'EPSG:1314 + EPSG:19916';
  authorityCodes: ['EPSG:1314', 'EPSG:19916'];
  definition: string;
  reportedAccuracyM: 2;
  selectedUsesGrids: false;
  bestAvailable: false;
  preferredMissingGridNames: string[];
  missingPreferredGridCaveat: string;
}

export interface RealTerrainAnchorWgs84 {
  postcode: string;
  crs: 'EPSG:4326';
  longitude: number;
  latitude: number;
  coordinateMeaning: string;
  quality: number;
  sourceName: string;
  sourceUrl: string;
  sourceLicense: string;
  retrievedDate: string;
}

type Wgs84Coordinate = [longitude: number, latitude: number];

export interface RealTerrainBoundaryWgs84 {
  crs: 'EPSG:4326';
  coordinateOrder: 'longitude-latitude';
  geometryType: 'Polygon';
  ring: Wgs84Coordinate[];
}

const EXPECTED_TQ1_4HN_AOI_BOUNDARY_WGS84: readonly Wgs84Coordinate[] = [
  [-3.542910651853897, 50.47326489870257],
  [-3.528823875124863, 50.473450849062345],
  [-3.5291139928135884, 50.48244068998469],
  [-3.5432034396837033, 50.48225468056402],
  [-3.542910651853897, 50.47326489870257],
];
const EXPECTED_TQ1_4HN_AOI_BOUNDARY_2KM_WGS84: readonly Wgs84Coordinate[] = [
  [-3.5498069791321853, 50.46867640263527],
  [-3.5216360951366497, 50.4690482443],
  [-3.5222136603237235, 50.48702798479993],
  [-3.5503952248835833, 50.48665590689169],
  [-3.5498069791321853, 50.46867640263527],
];
export type RealSceneProfile = 'historical_1km' | 'current_2km';

const PINNED_BNG_OPERATION_DEFINITION = [
  'proj=pipeline',
  'step proj=unitconvert xy_in=deg xy_out=rad',
  'step proj=push v_3',
  'step proj=cart ellps=WGS84',
  'step inv proj=helmert x=446.448 y=-125.157 z=542.06 rx=0.15 ry=0.247 rz=0.842 s=-20.489 convention=position_vector',
  'step inv proj=cart ellps=airy',
  'step proj=pop v_3',
  'step proj=tmerc lat_0=49 lon_0=-2 k=0.9996012717 x_0=400000 y_0=-100000 ellps=airy',
].join(' ');

function validateRealBoundaryWgs84(
  value: unknown,
  issues: ManifestValidationIssue[],
  profile: RealSceneProfile,
): RealTerrainBoundaryWgs84 | undefined {
  const expectedRing =
    profile === 'current_2km'
      ? EXPECTED_TQ1_4HN_AOI_BOUNDARY_2KM_WGS84
      : EXPECTED_TQ1_4HN_AOI_BOUNDARY_WGS84;
  const path = 'aoi.boundaryWgs84';
  if (!isRecord(value)) {
    issues.push({
      path,
      message: 'must contain the generated EPSG:4326 candidate polygon ring',
    });
    return undefined;
  }
  if (value.crs !== 'EPSG:4326') {
    issues.push({ path: `${path}.crs`, message: 'must be EPSG:4326' });
  }
  if (value.coordinateOrder !== 'longitude-latitude') {
    issues.push({
      path: `${path}.coordinateOrder`,
      message: 'must be longitude-latitude (GeoJSON coordinate order)',
    });
  }
  if (value.geometryType !== 'Polygon') {
    issues.push({
      path: `${path}.geometryType`,
      message: 'must be Polygon with one closed exterior ring',
    });
  }

  const ringValue = value.ring;
  if (!Array.isArray(ringValue) || ringValue.length !== expectedRing.length) {
    issues.push({
      path: `${path}.ring`,
      message: 'must contain the four candidate corners and a closing position',
    });
    return undefined;
  }

  const parsedRing: Wgs84Coordinate[] = [];
  let validRing = true;
  ringValue.forEach((position, index) => {
    const positionPath = `${path}.ring[${index}]`;
    if (
      !Array.isArray(position) ||
      position.length !== 2 ||
      !isFiniteNumber(position[0]) ||
      !isFiniteNumber(position[1])
    ) {
      issues.push({
        path: positionPath,
        message: 'must be a two-number [longitude, latitude] coordinate pair',
      });
      validRing = false;
      return;
    }
    const longitude = position[0];
    const latitude = position[1];
    if (longitude < -180 || longitude > 180) {
      issues.push({
        path: `${positionPath}[0]`,
        message: 'longitude must be between -180 and 180 degrees',
      });
      validRing = false;
    }
    if (latitude < -90 || latitude > 90) {
      issues.push({
        path: `${positionPath}[1]`,
        message: 'latitude must be between -90 and 90 degrees',
      });
      validRing = false;
    }
    parsedRing.push([longitude, latitude]);
  });

  if (!validRing || parsedRing.length !== expectedRing.length) {
    return undefined;
  }
  const first = parsedRing[0]!;
  const last = parsedRing.at(-1)!;
  if (first[0] !== last[0] || first[1] !== last[1]) {
    issues.push({
      path: `${path}.ring`,
      message: 'must be closed by repeating its first coordinate as its last',
    });
    validRing = false;
  }
  if (
    parsedRing.some(
      (position, index) =>
        position[0] !== expectedRing[index]![0] ||
        position[1] !== expectedRing[index]![1],
    )
  ) {
    issues.push({
      path: `${path}.ring`,
      message:
        'must match the generated TQ1 4HN polygon corresponding to the reviewed EPSG:27700 bounds',
    });
    validRing = false;
  }

  return validRing
    ? {
        crs: 'EPSG:4326',
        coordinateOrder: 'longitude-latitude',
        geometryType: 'Polygon',
        ring: parsedRing,
      }
    : undefined;
}

function validateRealAnchorWgs84(
  value: unknown,
  issues: ManifestValidationIssue[],
): RealTerrainAnchorWgs84 | undefined {
  const path = 'aoi.anchorWgs84';
  if (!isRecord(value)) {
    issues.push({
      path,
      message: 'must be an object describing the configured WGS84 anchor',
    });
    return undefined;
  }
  const postcode = addRequiredStringIssue(
    issues,
    value,
    'postcode',
    `${path}.postcode`,
  );
  const longitude = addFiniteNumberIssue(
    issues,
    value,
    'longitude',
    `${path}.longitude`,
  );
  const latitude = addFiniteNumberIssue(
    issues,
    value,
    'latitude',
    `${path}.latitude`,
  );
  const coordinateMeaning = addRequiredStringIssue(
    issues,
    value,
    'coordinateMeaning',
    `${path}.coordinateMeaning`,
  );
  const quality = addPositiveIntegerIssue(
    issues,
    value,
    'quality',
    `${path}.quality`,
  );
  const sourceName = addRequiredStringIssue(
    issues,
    value,
    'sourceName',
    `${path}.sourceName`,
  );
  const sourceUrl = addHttpsIssue(
    issues,
    value,
    'sourceUrl',
    `${path}.sourceUrl`,
  );
  const sourceLicense = addRequiredStringIssue(
    issues,
    value,
    'sourceLicense',
    `${path}.sourceLicense`,
  );
  const retrievedDate = addRequiredStringIssue(
    issues,
    value,
    'retrievedDate',
    `${path}.retrievedDate`,
  );
  if (value.crs !== 'EPSG:4326') {
    issues.push({ path: `${path}.crs`, message: 'must be EPSG:4326' });
  }
  if (longitude !== undefined && (longitude < -180 || longitude > 180)) {
    issues.push({
      path: `${path}.longitude`,
      message: 'must be between -180 and 180 degrees',
    });
  }
  if (latitude !== undefined && (latitude < -90 || latitude > 90)) {
    issues.push({
      path: `${path}.latitude`,
      message: 'must be between -90 and 90 degrees',
    });
  }
  if (postcode !== 'TQ1 4HN') {
    issues.push({
      path: `${path}.postcode`,
      message: 'must match the configured TQ1 4HN anchor',
    });
  }
  if (longitude !== -3.536013 || latitude !== 50.477853) {
    issues.push({
      path,
      message:
        'WGS84 coordinates must match the configured TQ1 4HN postcode centroid',
    });
  }
  if (
    coordinateMeaning &&
    (!coordinateMeaning.toLowerCase().includes('postcode centroid') ||
      !coordinateMeaning
        .toLowerCase()
        .includes('not a property or survey point'))
  ) {
    issues.push({
      path: `${path}.coordinateMeaning`,
      message:
        'must identify a postcode centroid, not a property or survey point',
    });
  }
  if (quality !== 1) {
    issues.push({
      path: `${path}.quality`,
      message: 'must preserve the lookup quality value 1',
    });
  }
  if (sourceName !== 'Postcodes.io') {
    issues.push({
      path: `${path}.sourceName`,
      message: 'must identify Postcodes.io',
    });
  }
  if (sourceUrl !== 'https://api.postcodes.io/postcodes/TQ1%204HN') {
    issues.push({
      path: `${path}.sourceUrl`,
      message: 'must identify the recorded TQ1 4HN lookup',
    });
  }
  if (sourceLicense && !sourceLicense.includes('OS OpenData')) {
    issues.push({
      path: `${path}.sourceLicense`,
      message: 'must preserve the OS OpenData licence note',
    });
  }
  if (retrievedDate && !/^\d{4}-\d{2}-\d{2}$/.test(retrievedDate)) {
    issues.push({
      path: `${path}.retrievedDate`,
      message: 'must use YYYY-MM-DD format',
    });
  }
  if (retrievedDate !== '2026-10-17') {
    issues.push({
      path: `${path}.retrievedDate`,
      message: 'must match the recorded anchor lookup date',
    });
  }
  if (
    postcode === 'TQ1 4HN' &&
    value.crs === 'EPSG:4326' &&
    longitude === -3.536013 &&
    latitude === 50.477853 &&
    coordinateMeaning?.toLowerCase().includes('postcode centroid') &&
    coordinateMeaning
      ?.toLowerCase()
      .includes('not a property or survey point') &&
    quality === 1 &&
    sourceName === 'Postcodes.io' &&
    sourceUrl === 'https://api.postcodes.io/postcodes/TQ1%204HN' &&
    sourceLicense?.includes('OS OpenData') &&
    retrievedDate &&
    retrievedDate === '2026-10-17' &&
    /^\d{4}-\d{2}-\d{2}$/.test(retrievedDate)
  ) {
    return {
      postcode,
      crs: 'EPSG:4326',
      longitude,
      latitude,
      coordinateMeaning,
      quality: 1,
      sourceName,
      sourceUrl,
      sourceLicense,
      retrievedDate,
    };
  }
  return undefined;
}

export interface RealTerrainSceneManifest {
  formatVersion: 1;
  id: string;
  name: string;
  worldType: 'real';
  sceneProfile: RealSceneProfile;
  sourceCrs: 'EPSG:27700';
  axisConvention: typeof AXIS_CONVENTION;
  origin: {
    eastingM: number;
    northingM: number;
    elevationM: number;
  };
  extentM: {
    width: number;
    depth: number;
  };
  heightfield: SyntheticSceneManifest['heightfield'] & { byteLength: number };
  provenance: {
    kind: 'real';
    generator: string;
    generatorVersion: string;
    publisher: string;
    product: string;
    licence: string;
    licenceUrl: string;
    attribution: string;
    verticalReference: string;
    catalogueUrl: string;
    productSurveyPeriod: string;
    xmlCopyrightConflict: string;
    coordinateOperation: RealTerrainCoordinateOperation;
    sources: RealTerrainSource[];
    selectionStatus: 'selected_pending_coverage';
    coverageStatus: 'not_checked';
    resampling: string;
    fillPolicy: string;
    qa: {
      sampling: string;
      maximumObservedResamplingErrorM: number;
      maximumObservedFloat32QuantizationErrorM: number;
    };
  };
  aoi: {
    crs: 'EPSG:27700';
    boundsM: [number, number, number, number];
    centerBngM: [number, number];
    widthM: number;
    heightM: number;
    anchorWgs84: RealTerrainAnchorWgs84;
    boundaryWgs84: RealTerrainBoundaryWgs84;
    selectionStatus: 'selected_pending_coverage';
    coverageStatus: 'not_checked';
  };
}

export type SceneManifest = SyntheticSceneManifest | RealTerrainSceneManifest;

export interface ManifestValidationIssue {
  path: string;
  message: string;
}

export type ManifestValidationResult =
  | { ok: true; manifest: SceneManifest }
  | { ok: false; issues: ManifestValidationIssue[] };

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

/**
 * Local asset paths use a conservative URL-path subset. This excludes URL
 * schemes, absolute paths, encoded separators, query/hash suffixes and dot
 * segments so assets stay beside the manifest within the public package.
 */
export function isSafeLocalAssetPath(value: unknown): value is string {
  if (typeof value !== 'string' || value.length === 0 || value.includes('%')) {
    return false;
  }

  const segments = value.split('/');
  return segments.every(
    (segment) =>
      segment.length > 0 &&
      segment !== '.' &&
      segment !== '..' &&
      /^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(segment),
  );
}

function addRequiredStringIssue(
  issues: ManifestValidationIssue[],
  record: UnknownRecord,
  key: string,
  path: string,
): string | undefined {
  const value = record[key];
  if (!isNonEmptyString(value)) {
    issues.push({ path, message: 'must be a non-empty string' });
    return undefined;
  }
  return value;
}

function addFiniteNumberIssue(
  issues: ManifestValidationIssue[],
  record: UnknownRecord,
  key: string,
  path: string,
): number | undefined {
  const value = record[key];
  if (!isFiniteNumber(value)) {
    issues.push({ path, message: 'must be a finite number' });
    return undefined;
  }
  return value;
}

function addAssetPathIssue(
  issues: ManifestValidationIssue[],
  value: unknown,
  path: string,
): string | undefined {
  if (!isSafeLocalAssetPath(value)) {
    issues.push({
      path,
      message:
        'must be a safe local relative path using letters, digits, dots, underscores, or hyphens',
    });
    return undefined;
  }
  return value;
}

function extentMatchesGrid(extent: number, sampledExtent: number): boolean {
  const tolerance =
    HEIGHTFIELD_EXTENT_RELATIVE_TOLERANCE *
    Math.max(1, Math.abs(extent), Math.abs(sampledExtent));
  return Math.abs(extent - sampledExtent) <= tolerance;
}

/** Validate the deliberately synthetic v1 manifest without schema dependencies. */
function validateSyntheticSceneManifest(
  input: unknown,
): ManifestValidationResult {
  const issues: ManifestValidationIssue[] = [];
  if (!isRecord(input)) {
    return {
      ok: false,
      issues: [{ path: '$', message: 'must be a JSON object' }],
    };
  }

  if (input.formatVersion !== 1) {
    issues.push({
      path: 'formatVersion',
      message: 'must be the supported version 1',
    });
  }

  const id = addRequiredStringIssue(issues, input, 'id', 'id');
  const name = addRequiredStringIssue(issues, input, 'name', 'name');

  if (input.worldType !== 'synthetic') {
    issues.push({
      path: 'worldType',
      message: 'only synthetic worlds are supported by this loader',
    });
  }
  if (input.sourceCrs !== 'LOCAL_SYNTHETIC') {
    issues.push({
      path: 'sourceCrs',
      message:
        'must be LOCAL_SYNTHETIC; projected and geographic CRS are unsupported',
    });
  }
  if (input.axisConvention !== AXIS_CONVENTION) {
    issues.push({
      path: 'axisConvention',
      message: `must be exactly "${AXIS_CONVENTION}"`,
    });
  }

  const originInput = input.origin;
  let origin: SyntheticSceneManifest['origin'] | undefined;
  if (!isRecord(originInput)) {
    issues.push({ path: 'origin', message: 'must be an object' });
  } else {
    const eastingM = addFiniteNumberIssue(
      issues,
      originInput,
      'eastingM',
      'origin.eastingM',
    );
    const northingM = addFiniteNumberIssue(
      issues,
      originInput,
      'northingM',
      'origin.northingM',
    );
    const elevationM = addFiniteNumberIssue(
      issues,
      originInput,
      'elevationM',
      'origin.elevationM',
    );
    if (
      eastingM !== undefined &&
      northingM !== undefined &&
      elevationM !== undefined
    ) {
      origin = { eastingM, northingM, elevationM };
    }
  }

  const extentInput = input.extentM;
  let extent: SyntheticSceneManifest['extentM'] | undefined;
  if (!isRecord(extentInput)) {
    issues.push({ path: 'extentM', message: 'must be an object' });
  } else {
    const width = addFiniteNumberIssue(
      issues,
      extentInput,
      'width',
      'extentM.width',
    );
    const depth = addFiniteNumberIssue(
      issues,
      extentInput,
      'depth',
      'extentM.depth',
    );
    if (width !== undefined && width <= 0) {
      issues.push({
        path: 'extentM.width',
        message: 'must be greater than zero',
      });
    }
    if (depth !== undefined && depth <= 0) {
      issues.push({
        path: 'extentM.depth',
        message: 'must be greater than zero',
      });
    }
    if (width !== undefined && width > 0 && depth !== undefined && depth > 0) {
      extent = { width, depth };
    }
  }

  const heightfieldInput = input.heightfield;
  let heightfield: SyntheticSceneManifest['heightfield'] | undefined;
  if (!isRecord(heightfieldInput)) {
    issues.push({ path: 'heightfield', message: 'must be an object' });
  } else {
    const path = addAssetPathIssue(
      issues,
      heightfieldInput.path,
      'heightfield.path',
    );
    const columnsValue = heightfieldInput.columns;
    const rowsValue = heightfieldInput.rows;
    const spacingM = addFiniteNumberIssue(
      issues,
      heightfieldInput,
      'spacingM',
      'heightfield.spacingM',
    );
    let columns: number | undefined;
    let rows: number | undefined;

    if (
      typeof columnsValue !== 'number' ||
      !Number.isSafeInteger(columnsValue) ||
      columnsValue < 2
    ) {
      issues.push({
        path: 'heightfield.columns',
        message: 'must be a safe integer of at least 2',
      });
    } else {
      columns = columnsValue;
    }
    if (
      typeof rowsValue !== 'number' ||
      !Number.isSafeInteger(rowsValue) ||
      rowsValue < 2
    ) {
      issues.push({
        path: 'heightfield.rows',
        message: 'must be a safe integer of at least 2',
      });
    } else {
      rows = rowsValue;
    }
    if (spacingM !== undefined && spacingM <= 0) {
      issues.push({
        path: 'heightfield.spacingM',
        message: 'must be greater than zero',
      });
    }

    if (columns !== undefined && rows !== undefined) {
      const sampleCount = columns * rows;
      if (!Number.isSafeInteger(sampleCount)) {
        issues.push({
          path: 'heightfield',
          message: 'sample count exceeds safe integer arithmetic',
        });
      } else if (sampleCount > MAX_HEIGHTFIELD_SAMPLES) {
        issues.push({
          path: 'heightfield',
          message: `sample count exceeds the ${MAX_HEIGHTFIELD_SAMPLES.toLocaleString('en-US')} sample limit`,
        });
      } else if (
        !Number.isSafeInteger(sampleCount * Float32Array.BYTES_PER_ELEMENT)
      ) {
        issues.push({
          path: 'heightfield',
          message: 'byte length exceeds safe integer arithmetic',
        });
      }
    }

    if (
      columns !== undefined &&
      rows !== undefined &&
      spacingM !== undefined &&
      spacingM > 0 &&
      extent !== undefined
    ) {
      const sampledWidth = (columns - 1) * spacingM;
      if (!Number.isFinite(sampledWidth)) {
        issues.push({
          path: 'extentM.width',
          message:
            'computed grid extent from heightfield.columns and spacingM must be finite',
        });
      } else if (!extentMatchesGrid(extent.width, sampledWidth)) {
        issues.push({
          path: 'extentM.width',
          message:
            'must equal (heightfield.columns - 1) × spacingM within 1e-9 relative tolerance',
        });
      }
      const sampledDepth = (rows - 1) * spacingM;
      if (!Number.isFinite(sampledDepth)) {
        issues.push({
          path: 'extentM.depth',
          message:
            'computed grid extent from heightfield.rows and spacingM must be finite',
        });
      } else if (!extentMatchesGrid(extent.depth, sampledDepth)) {
        issues.push({
          path: 'extentM.depth',
          message:
            'must equal (heightfield.rows - 1) × spacingM within 1e-9 relative tolerance',
        });
      }
    }

    const literals = [
      ['rowOrder', 'north-to-south'],
      ['byteOrder', 'little-endian'],
      ['encoding', 'float32'],
      ['valueMeaning', HEIGHTFIELD_VALUE_MEANING],
    ] as const;
    for (const [key, expected] of literals) {
      if (heightfieldInput[key] !== expected) {
        issues.push({
          path: `heightfield.${key}`,
          message: `must be exactly "${expected}"`,
        });
      }
    }

    const sha256Value = heightfieldInput.sha256;
    let sha256: string | undefined;
    if (
      typeof sha256Value !== 'string' ||
      !/^[a-fA-F0-9]{64}$/.test(sha256Value)
    ) {
      issues.push({
        path: 'heightfield.sha256',
        message: 'must be a 64-character hexadecimal SHA-256 digest',
      });
    } else {
      sha256 = sha256Value.toLowerCase();
    }

    if (
      path !== undefined &&
      columns !== undefined &&
      rows !== undefined &&
      spacingM !== undefined &&
      spacingM > 0 &&
      sha256 !== undefined
    ) {
      heightfield = {
        path,
        columns,
        rows,
        spacingM,
        rowOrder: 'north-to-south',
        byteOrder: 'little-endian',
        encoding: 'float32',
        valueMeaning: HEIGHTFIELD_VALUE_MEANING,
        sha256,
      };
    }
  }

  const provenanceInput = input.provenance;
  let provenance: SyntheticSceneManifest['provenance'] | undefined;
  if (!isRecord(provenanceInput)) {
    issues.push({ path: 'provenance', message: 'must be an object' });
  } else {
    if (provenanceInput.kind !== 'synthetic') {
      issues.push({
        path: 'provenance.kind',
        message: 'must be synthetic; real-data provenance is not supported yet',
      });
    }
    const generator = addRequiredStringIssue(
      issues,
      provenanceInput,
      'generator',
      'provenance.generator',
    );
    const generatorVersion = addRequiredStringIssue(
      issues,
      provenanceInput,
      'generatorVersion',
      'provenance.generatorVersion',
    );
    const note = addRequiredStringIssue(
      issues,
      provenanceInput,
      'note',
      'provenance.note',
    );
    if (
      provenanceInput.kind === 'synthetic' &&
      generator !== undefined &&
      generatorVersion !== undefined &&
      note !== undefined
    ) {
      provenance = { kind: 'synthetic', generator, generatorVersion, note };
    }
  }

  let buildings: string | undefined;
  if (input.buildings !== undefined) {
    buildings = addAssetPathIssue(issues, input.buildings, 'buildings');
  }
  let roads: string | undefined;
  if (input.roads !== undefined) {
    roads = addAssetPathIssue(issues, input.roads, 'roads');
  }

  if (issues.length > 0) {
    return { ok: false, issues };
  }

  // Required values are all established above whenever no validation issue remains.
  return {
    ok: true,
    manifest: {
      formatVersion: 1,
      id: id!,
      name: name!,
      worldType: 'synthetic',
      sourceCrs: 'LOCAL_SYNTHETIC',
      axisConvention: AXIS_CONVENTION,
      origin: origin!,
      extentM: extent!,
      heightfield: heightfield!,
      provenance: provenance!,
      ...(buildings === undefined ? {} : { buildings }),
      ...(roads === undefined ? {} : { roads }),
    },
  };
}

function addPositiveIntegerIssue(
  issues: ManifestValidationIssue[],
  record: UnknownRecord,
  key: string,
  path: string,
): number | undefined {
  const value = record[key];
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value <= 0) {
    issues.push({ path, message: 'must be a positive safe integer' });
    return undefined;
  }
  return value;
}

function isSha256(value: unknown): value is string {
  return typeof value === 'string' && /^[a-fA-F0-9]{64}$/.test(value);
}

function addDigestIssue(
  issues: ManifestValidationIssue[],
  record: UnknownRecord,
  key: string,
  path: string,
): string | undefined {
  if (!isSha256(record[key])) {
    issues.push({
      path,
      message: 'must be a 64-character hexadecimal SHA-256 digest',
    });
    return undefined;
  }
  return (record[key] as string).toLowerCase();
}

function addHttpsIssue(
  issues: ManifestValidationIssue[],
  record: UnknownRecord,
  key: string,
  path: string,
): string | undefined {
  const value = record[key];
  if (typeof value !== 'string') {
    issues.push({ path, message: 'must be a publisher HTTPS URL' });
    return undefined;
  }
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || !url.hostname)
      throw new Error('not HTTPS');
    return value;
  } catch {
    issues.push({ path, message: 'must be a publisher HTTPS URL' });
    return undefined;
  }
}

function validateRealSource(
  value: unknown,
  index: number,
  issues: ManifestValidationIssue[],
): RealTerrainSource | undefined {
  const path = `provenance.sources[${index}]`;
  if (!isRecord(value)) {
    issues.push({ path, message: 'must be an object' });
    return undefined;
  }
  const stringKeys = [
    'tileName',
    'archiveFilename',
    'downloadDate',
    'archiveRasterMember',
    'archiveXmlMember',
    'rasterFilename',
    'xmlFilename',
    'tileSurveyPeriod',
    'xmlVerticalReference',
  ] as const;
  const strings: Partial<Record<(typeof stringKeys)[number], string>> = {};
  for (const key of stringKeys) {
    const checked = addRequiredStringIssue(
      issues,
      value,
      key,
      `${path}.${key}`,
    );
    if (checked !== undefined) strings[key] = checked;
  }
  for (const key of ['archiveRasterMember', 'archiveXmlMember'] as const) {
    const member = strings[key];
    if (
      member !== undefined &&
      (member.includes('..') || member.includes('\\') || member.startsWith('/'))
    ) {
      issues.push({
        path: `${path}.${key}`,
        message: 'must identify a safe ZIP member name',
      });
    }
  }
  const archiveDownloadUrl = addHttpsIssue(
    issues,
    value,
    'archiveDownloadUrl',
    `${path}.archiveDownloadUrl`,
  );
  const archiveSha256 = addDigestIssue(
    issues,
    value,
    'archiveSha256',
    `${path}.archiveSha256`,
  );
  const rasterSha256 = addDigestIssue(
    issues,
    value,
    'rasterSha256',
    `${path}.rasterSha256`,
  );
  const xmlSha256 = addDigestIssue(
    issues,
    value,
    'xmlSha256',
    `${path}.xmlSha256`,
  );
  const archiveSizeBytes = addPositiveIntegerIssue(
    issues,
    value,
    'archiveSizeBytes',
    `${path}.archiveSizeBytes`,
  );
  const rasterSizeBytes = addPositiveIntegerIssue(
    issues,
    value,
    'rasterSizeBytes',
    `${path}.rasterSizeBytes`,
  );
  const xmlSizeBytes = addPositiveIntegerIssue(
    issues,
    value,
    'xmlSizeBytes',
    `${path}.xmlSizeBytes`,
  );
  const rasterWidthPixels = addPositiveIntegerIssue(
    issues,
    value,
    'rasterWidthPixels',
    `${path}.rasterWidthPixels`,
  );
  const rasterHeightPixels = addPositiveIntegerIssue(
    issues,
    value,
    'rasterHeightPixels',
    `${path}.rasterHeightPixels`,
  );
  if (!/^\d{4}-\d{2}-\d{2}$/.test(strings.downloadDate ?? '')) {
    issues.push({
      path: `${path}.downloadDate`,
      message: 'must use YYYY-MM-DD',
    });
  }
  if (value.rasterCrs !== 'EPSG:27700') {
    issues.push({ path: `${path}.rasterCrs`, message: 'must be EPSG:27700' });
  }
  if (value.rasterDtype !== 'float32') {
    issues.push({ path: `${path}.rasterDtype`, message: 'must be float32' });
  }
  const tuple = (
    key: 'rasterTransform' | 'rasterBoundsM' | 'rasterResolutionM',
    length: number,
  ): number[] | undefined => {
    const item = value[key];
    if (
      !Array.isArray(item) ||
      item.length !== length ||
      !item.every(isFiniteNumber)
    ) {
      issues.push({
        path: `${path}.${key}`,
        message: `must contain ${length} finite numbers`,
      });
      return undefined;
    }
    return item;
  };
  const transform = tuple('rasterTransform', 6);
  if (
    transform &&
    (transform[0] !== 1 ||
      transform[1] !== 0 ||
      transform[3] !== 0 ||
      transform[4] !== -1)
  ) {
    issues.push({
      path: `${path}.rasterTransform`,
      message: 'must use exact north-up, unrotated 1 m pixels',
    });
  }
  const rasterBoundsM = tuple('rasterBoundsM', 4);
  const resolution = tuple('rasterResolutionM', 2);
  if (resolution && (resolution[0] !== 1 || resolution[1] !== 1)) {
    issues.push({
      path: `${path}.rasterResolutionM`,
      message: 'must be exactly [1, 1]',
    });
  }
  const rasterNodata = addFiniteNumberIssue(
    issues,
    value,
    'rasterNodata',
    `${path}.rasterNodata`,
  );
  if (
    stringKeys.some((key) => strings[key] === undefined) ||
    archiveDownloadUrl === undefined ||
    archiveSha256 === undefined ||
    rasterSha256 === undefined ||
    xmlSha256 === undefined ||
    archiveSizeBytes === undefined ||
    rasterSizeBytes === undefined ||
    xmlSizeBytes === undefined ||
    rasterWidthPixels === undefined ||
    rasterHeightPixels === undefined ||
    transform === undefined ||
    rasterBoundsM === undefined ||
    resolution === undefined ||
    rasterNodata === undefined ||
    value.rasterCrs !== 'EPSG:27700' ||
    value.rasterDtype !== 'float32' ||
    transform[0] !== 1 ||
    transform[1] !== 0 ||
    transform[3] !== 0 ||
    transform[4] !== -1 ||
    resolution[0] !== 1 ||
    resolution[1] !== 1
  ) {
    return undefined;
  }
  return {
    tileName: strings.tileName!,
    archiveFilename: strings.archiveFilename!,
    archiveSizeBytes,
    archiveSha256,
    archiveDownloadUrl,
    downloadDate: strings.downloadDate!,
    archiveRasterMember: strings.archiveRasterMember!,
    archiveXmlMember: strings.archiveXmlMember!,
    rasterFilename: strings.rasterFilename!,
    rasterSizeBytes,
    rasterSha256,
    rasterCrs: 'EPSG:27700',
    rasterTransform: transform as RealTerrainSource['rasterTransform'],
    rasterBoundsM: rasterBoundsM as RealTerrainSource['rasterBoundsM'],
    rasterWidthPixels,
    rasterHeightPixels,
    rasterResolutionM: [1, 1],
    rasterDtype: 'float32',
    rasterNodata,
    xmlFilename: strings.xmlFilename!,
    xmlSizeBytes,
    xmlSha256,
    tileSurveyPeriod: strings.tileSurveyPeriod!,
    xmlVerticalReference: strings.xmlVerticalReference!,
  };
}

function validateRealCoordinateOperation(
  value: unknown,
  issues: ManifestValidationIssue[],
): RealTerrainCoordinateOperation | undefined {
  const path = 'provenance.coordinateOperation';
  if (!isRecord(value)) {
    issues.push({ path, message: 'must be an object' });
    return undefined;
  }

  const name = addRequiredStringIssue(issues, value, 'name', `${path}.name`);
  const definition = addRequiredStringIssue(
    issues,
    value,
    'definition',
    `${path}.definition`,
  );
  const reportedAccuracyM = addFiniteNumberIssue(
    issues,
    value,
    'reportedAccuracyM',
    `${path}.reportedAccuracyM`,
  );
  const expectedCodes = ['EPSG:1314', 'EPSG:19916'];
  const authorityCodes = value.authorityCodes;
  if (
    !Array.isArray(authorityCodes) ||
    authorityCodes.length !== expectedCodes.length ||
    !authorityCodes.every((code, index) => code === expectedCodes[index])
  ) {
    issues.push({
      path: `${path}.authorityCodes`,
      message: 'must identify EPSG:1314 followed by EPSG:19916',
    });
  }
  if (name !== 'EPSG:1314 + EPSG:19916') {
    issues.push({
      path: `${path}.name`,
      message: 'must identify the pinned EPSG:1314 + EPSG:19916 operation',
    });
  }
  const normalizedDefinition = definition?.trim().split(/\s+/).join(' ');
  const hasPinnedDefinition =
    normalizedDefinition === PINNED_BNG_OPERATION_DEFINITION;
  if (definition !== undefined && !hasPinnedDefinition) {
    issues.push({
      path: `${path}.definition`,
      message:
        'must match every parameter in the pinned EPSG:1314 + EPSG:19916 pipeline definition',
    });
  }
  if (reportedAccuracyM !== undefined && reportedAccuracyM !== 2) {
    issues.push({
      path: `${path}.reportedAccuracyM`,
      message: 'must match the selected operation’s reported 2 m accuracy',
    });
  }
  if (value.selectedUsesGrids !== false) {
    issues.push({
      path: `${path}.selectedUsesGrids`,
      message: 'must be false for the pinned fallback operation',
    });
  }
  if (value.bestAvailable !== false) {
    issues.push({
      path: `${path}.bestAvailable`,
      message:
        'must record that the preferred higher-accuracy operation is unavailable',
    });
  }

  const gridNamesValue = value.preferredMissingGridNames;
  let preferredMissingGridNames: string[] | undefined;
  if (
    !Array.isArray(gridNamesValue) ||
    gridNamesValue.length === 0 ||
    !gridNamesValue.every(isNonEmptyString)
  ) {
    issues.push({
      path: `${path}.preferredMissingGridNames`,
      message: 'must list the missing preferred transformation grid files',
    });
  } else {
    preferredMissingGridNames = [...gridNamesValue];
    if (
      !preferredMissingGridNames.includes('uk_os_OSTN15_NTv2_OSGBtoETRS.tif')
    ) {
      issues.push({
        path: `${path}.preferredMissingGridNames`,
        message: 'must record the unavailable OSTN15 transformation grid',
      });
    }
  }

  const missingPreferredGridCaveat = addRequiredStringIssue(
    issues,
    value,
    'missingPreferredGridCaveat',
    `${path}.missingPreferredGridCaveat`,
  );
  if (
    missingPreferredGridCaveat !== undefined &&
    (!missingPreferredGridCaveat.includes('PROJ_NETWORK=OFF') ||
      !missingPreferredGridCaveat.toLowerCase().includes('unavailable') ||
      (preferredMissingGridNames !== undefined &&
        !preferredMissingGridNames.every((grid) =>
          missingPreferredGridCaveat.includes(grid),
        )))
  ) {
    issues.push({
      path: `${path}.missingPreferredGridCaveat`,
      message:
        'must identify the unavailable grid file(s) and state that PROJ_NETWORK=OFF',
    });
  }

  if (
    name === 'EPSG:1314 + EPSG:19916' &&
    hasPinnedDefinition &&
    normalizedDefinition !== undefined &&
    reportedAccuracyM === 2 &&
    value.selectedUsesGrids === false &&
    value.bestAvailable === false &&
    preferredMissingGridNames !== undefined &&
    missingPreferredGridCaveat !== undefined
  ) {
    return {
      name,
      authorityCodes: ['EPSG:1314', 'EPSG:19916'],
      definition: normalizedDefinition,
      reportedAccuracyM: 2,
      selectedUsesGrids: false,
      bestAvailable: false,
      preferredMissingGridNames,
      missingPreferredGridCaveat,
    };
  }
  return undefined;
}

function validateRealSceneManifest(
  input: UnknownRecord,
): ManifestValidationResult {
  const syntheticBase = validateSyntheticSceneManifest({
    ...input,
    worldType: 'synthetic',
    sourceCrs: 'LOCAL_SYNTHETIC',
    provenance: {
      kind: 'synthetic',
      generator: 'real-manifest-shared-field-validation',
      generatorVersion: '1',
      note: 'Internal shared field validation only.',
    },
  });
  const issues: ManifestValidationIssue[] = syntheticBase.ok
    ? []
    : [...syntheticBase.issues];
  const profileValue = input.sceneProfile;
  let sceneProfile: RealSceneProfile = 'historical_1km';
  if (profileValue === undefined) {
    // Existing 1 km package predates explicit scene profiles.
    sceneProfile = 'historical_1km';
  } else if (
    profileValue === 'historical_1km' ||
    profileValue === 'current_2km'
  ) {
    sceneProfile = profileValue;
  } else {
    issues.push({
      path: 'sceneProfile',
      message: 'must be current_2km or historical_1km',
    });
  }
  const expectedSizeM = sceneProfile === 'current_2km' ? 2000 : 1000;
  const expectedDimension = expectedSizeM / 2 + 1;
  const expectedBounds =
    sceneProfile === 'current_2km'
      ? [
          290108.9018176432, 64353.48350844931, 292108.9018176432,
          66353.48350844931,
        ]
      : [
          290608.9018176432, 64853.48350844931, 291608.9018176432,
          65853.48350844931,
        ];
  if (input.worldType !== 'real') {
    issues.push({
      path: 'worldType',
      message: 'must be real for this manifest',
    });
  }
  if (input.sourceCrs !== 'EPSG:27700') {
    issues.push({
      path: 'sourceCrs',
      message: 'must be EPSG:27700 for local EA terrain',
    });
  }

  const heightfieldInput = input.heightfield;
  let realHeightfield: RealTerrainSceneManifest['heightfield'] | undefined;
  if (isRecord(heightfieldInput)) {
    const byteLength = addPositiveIntegerIssue(
      issues,
      heightfieldInput,
      'byteLength',
      'heightfield.byteLength',
    );
    if (syntheticBase.ok) {
      const expectedByteLength =
        syntheticBase.manifest.heightfield.columns *
        syntheticBase.manifest.heightfield.rows *
        Float32Array.BYTES_PER_ELEMENT;
      if (byteLength !== undefined && byteLength !== expectedByteLength) {
        issues.push({
          path: 'heightfield.byteLength',
          message: `must equal columns × rows × 4 (${expectedByteLength} bytes)`,
        });
      }
      if (byteLength === expectedByteLength) {
        realHeightfield = { ...syntheticBase.manifest.heightfield, byteLength };
      }
    }
  } else {
    issues.push({
      path: 'heightfield.byteLength',
      message: 'must be present in the real manifest',
    });
  }

  const provenanceInput = input.provenance;
  let provenance: RealTerrainSceneManifest['provenance'] | undefined;
  if (!isRecord(provenanceInput)) {
    issues.push({ path: 'provenance', message: 'must be an object' });
  } else {
    if (provenanceInput.kind !== 'real') {
      issues.push({ path: 'provenance.kind', message: 'must be real' });
    }
    const generator = addRequiredStringIssue(
      issues,
      provenanceInput,
      'generator',
      'provenance.generator',
    );
    const generatorVersion = addRequiredStringIssue(
      issues,
      provenanceInput,
      'generatorVersion',
      'provenance.generatorVersion',
    );
    if (
      generator !== undefined &&
      generator !== 'torquay_pipeline.terrain_export'
    ) {
      issues.push({
        path: 'provenance.generator',
        message: 'must identify the TVW-008 Python terrain exporter',
      });
    }
    if (generatorVersion !== undefined && generatorVersion !== '0.1.0') {
      issues.push({
        path: 'provenance.generatorVersion',
        message: 'must match the installed TVW-008 exporter version 0.1.0',
      });
    }
    const publisher = addRequiredStringIssue(
      issues,
      provenanceInput,
      'publisher',
      'provenance.publisher',
    );
    const product = addRequiredStringIssue(
      issues,
      provenanceInput,
      'product',
      'provenance.product',
    );
    const licence = addRequiredStringIssue(
      issues,
      provenanceInput,
      'licence',
      'provenance.licence',
    );
    const licenceUrl = addHttpsIssue(
      issues,
      provenanceInput,
      'licenceUrl',
      'provenance.licenceUrl',
    );
    const attribution = addRequiredStringIssue(
      issues,
      provenanceInput,
      'attribution',
      'provenance.attribution',
    );
    const verticalReference = addRequiredStringIssue(
      issues,
      provenanceInput,
      'verticalReference',
      'provenance.verticalReference',
    );
    const catalogueUrl = addHttpsIssue(
      issues,
      provenanceInput,
      'catalogueUrl',
      'provenance.catalogueUrl',
    );
    const productSurveyPeriod = addRequiredStringIssue(
      issues,
      provenanceInput,
      'productSurveyPeriod',
      'provenance.productSurveyPeriod',
    );
    const xmlCopyrightConflict = addRequiredStringIssue(
      issues,
      provenanceInput,
      'xmlCopyrightConflict',
      'provenance.xmlCopyrightConflict',
    );
    if (
      xmlCopyrightConflict !== undefined &&
      (!xmlCopyrightConflict.includes('useLimit') ||
        !xmlCopyrightConflict.includes('idCredit') ||
        !xmlCopyrightConflict.includes('2022') ||
        !xmlCopyrightConflict.includes('2020'))
    ) {
      issues.push({
        path: 'provenance.xmlCopyrightConflict',
        message:
          'must preserve the XML useLimit 2022 versus idCredit 2020 metadata conflict',
      });
    }
    if (
      licenceUrl !== undefined &&
      licenceUrl !==
        'https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/'
    ) {
      issues.push({
        path: 'provenance.licenceUrl',
        message: 'must link to the Open Government Licence v3.0',
      });
    }
    if (
      catalogueUrl !== undefined &&
      catalogueUrl !==
        'https://www.data.gov.uk/dataset/01b3ee39-da3f-47b6-83da-dc98e73a461f/lidar-composite-dtm-2022-1m'
    ) {
      issues.push({
        path: 'provenance.catalogueUrl',
        message: 'must link to the publisher-wide EA DTM catalogue',
      });
    }
    if (
      productSurveyPeriod !== undefined &&
      productSurveyPeriod !==
        '2000-06-06 through 2022-04-02 (publisher-wide catalogue dates)'
    ) {
      issues.push({
        path: 'provenance.productSurveyPeriod',
        message: 'must identify the publisher-wide catalogue survey period',
      });
    }
    const coordinateOperation = validateRealCoordinateOperation(
      provenanceInput.coordinateOperation,
      issues,
    );
    const resampling = addRequiredStringIssue(
      issues,
      provenanceInput,
      'resampling',
      'provenance.resampling',
    );
    const fillPolicy = addRequiredStringIssue(
      issues,
      provenanceInput,
      'fillPolicy',
      'provenance.fillPolicy',
    );
    const selectionStatus = provenanceInput.selectionStatus;
    if (selectionStatus !== 'selected_pending_coverage') {
      issues.push({
        path: 'provenance.selectionStatus',
        message: 'must remain selected_pending_coverage',
      });
    }
    const coverageStatus = provenanceInput.coverageStatus;
    if (coverageStatus !== 'not_checked') {
      issues.push({
        path: 'provenance.coverageStatus',
        message: 'must remain not_checked until M2 source checks are complete',
      });
    }
    const sourceInputs = provenanceInput.sources;
    const sources: RealTerrainSource[] = [];
    if (!Array.isArray(sourceInputs) || sourceInputs.length === 0) {
      issues.push({
        path: 'provenance.sources',
        message: 'must contain at least one verified raster source',
      });
    } else {
      sourceInputs.forEach((source, index) => {
        const parsed = validateRealSource(source, index, issues);
        if (parsed) sources.push(parsed);
      });
    }
    const qaInput = provenanceInput.qa;
    let qa: RealTerrainSceneManifest['provenance']['qa'] | undefined;
    if (!isRecord(qaInput)) {
      issues.push({ path: 'provenance.qa', message: 'must be an object' });
    } else {
      const sampling = addRequiredStringIssue(
        issues,
        qaInput,
        'sampling',
        'provenance.qa.sampling',
      );
      const maximumObservedResamplingErrorM = addFiniteNumberIssue(
        issues,
        qaInput,
        'maximumObservedResamplingErrorM',
        'provenance.qa.maximumObservedResamplingErrorM',
      );
      const maximumObservedFloat32QuantizationErrorM = addFiniteNumberIssue(
        issues,
        qaInput,
        'maximumObservedFloat32QuantizationErrorM',
        'provenance.qa.maximumObservedFloat32QuantizationErrorM',
      );
      if (
        maximumObservedResamplingErrorM !== undefined &&
        maximumObservedResamplingErrorM > 0.25
      ) {
        issues.push({
          path: 'provenance.qa.maximumObservedResamplingErrorM',
          message: 'must be at most 0.25 m',
        });
      }
      if (
        maximumObservedFloat32QuantizationErrorM !== undefined &&
        maximumObservedFloat32QuantizationErrorM > 1e-4
      ) {
        issues.push({
          path: 'provenance.qa.maximumObservedFloat32QuantizationErrorM',
          message: 'must be at most 1e-4 m',
        });
      }
      if (
        sampling &&
        maximumObservedResamplingErrorM !== undefined &&
        maximumObservedFloat32QuantizationErrorM !== undefined
      ) {
        qa = {
          sampling,
          maximumObservedResamplingErrorM,
          maximumObservedFloat32QuantizationErrorM,
        };
      }
    }
    if (
      provenanceInput.kind === 'real' &&
      generator &&
      generatorVersion &&
      publisher &&
      product &&
      licence &&
      licenceUrl &&
      attribution &&
      verticalReference &&
      catalogueUrl &&
      productSurveyPeriod &&
      xmlCopyrightConflict &&
      coordinateOperation &&
      resampling &&
      fillPolicy &&
      selectionStatus === 'selected_pending_coverage' &&
      coverageStatus === 'not_checked' &&
      Array.isArray(sourceInputs) &&
      sources.length === sourceInputs.length &&
      qa
    ) {
      provenance = {
        kind: 'real',
        generator,
        generatorVersion,
        publisher,
        product,
        licence,
        licenceUrl,
        attribution,
        verticalReference,
        catalogueUrl,
        productSurveyPeriod,
        xmlCopyrightConflict,
        coordinateOperation,
        sources,
        selectionStatus: 'selected_pending_coverage',
        coverageStatus: 'not_checked',
        resampling,
        fillPolicy,
        qa,
      };
    }
  }

  const aoiInput = input.aoi;
  let aoi: RealTerrainSceneManifest['aoi'] | undefined;
  if (!isRecord(aoiInput)) {
    issues.push({ path: 'aoi', message: 'must be an object for real terrain' });
  } else {
    if (aoiInput.crs !== 'EPSG:27700')
      issues.push({ path: 'aoi.crs', message: 'must be EPSG:27700' });
    const bounds = aoiInput.boundsM;
    let boundsM: [number, number, number, number] | undefined;
    if (
      !Array.isArray(bounds) ||
      bounds.length !== 4 ||
      !bounds.every(isFiniteNumber)
    ) {
      issues.push({
        path: 'aoi.boundsM',
        message: 'must contain four finite EPSG:27700 coordinates',
      });
    } else if (!(
      (bounds as number[])[0]! < (bounds as number[])[2]! &&
      (bounds as number[])[1]! < (bounds as number[])[3]!
    )) {
      issues.push({
        path: 'aoi.boundsM',
        message: 'must be ordered west < east and south < north',
      });
    } else {
      boundsM = bounds as [number, number, number, number];
    }
    if (boundsM) {
      if (
        boundsM.some(
          (value, index) => !extentMatchesGrid(value, expectedBounds[index]!),
        )
      ) {
        issues.push({
          path: 'aoi.boundsM',
          message: `must match the ${expectedSizeM / 1000} km TQ1 4HN ${sceneProfile} bounds`,
        });
      }
    }
    const widthM = addFiniteNumberIssue(
      issues,
      aoiInput,
      'widthM',
      'aoi.widthM',
    );
    const heightM = addFiniteNumberIssue(
      issues,
      aoiInput,
      'heightM',
      'aoi.heightM',
    );
    const extentWidthM = syntheticBase.ok
      ? syntheticBase.manifest.extentM.width
      : undefined;
    const extentDepthM = syntheticBase.ok
      ? syntheticBase.manifest.extentM.depth
      : undefined;
    if (extentWidthM !== undefined && extentWidthM !== expectedSizeM) {
      issues.push({
        path: 'extentM.width',
        message: `must match the reviewed ${expectedSizeM.toLocaleString()} m AOI`,
      });
    }
    if (extentDepthM !== undefined && extentDepthM !== expectedSizeM) {
      issues.push({
        path: 'extentM.depth',
        message: `must match the reviewed ${expectedSizeM.toLocaleString()} m AOI`,
      });
    }
    if (
      syntheticBase.ok &&
      (syntheticBase.manifest.heightfield.columns !== expectedDimension ||
        syntheticBase.manifest.heightfield.rows !== expectedDimension ||
        syntheticBase.manifest.heightfield.spacingM !== 2)
    ) {
      issues.push({
        path: 'heightfield',
        message: `real terrain must use the reviewed ${expectedDimension} × ${expectedDimension} grid at 2 m spacing for ${sceneProfile}`,
      });
    }
    if (widthM !== undefined && widthM !== expectedSizeM)
      issues.push({
        path: 'aoi.widthM',
        message: `must match the reviewed ${expectedSizeM.toLocaleString()} m AOI`,
      });
    if (heightM !== undefined && heightM !== expectedSizeM)
      issues.push({
        path: 'aoi.heightM',
        message: `must match the reviewed ${expectedSizeM.toLocaleString()} m AOI`,
      });
    let centerBngM: [number, number] | undefined;
    const centerValue = aoiInput.centerBngM;
    if (
      !Array.isArray(centerValue) ||
      centerValue.length !== 2 ||
      !centerValue.every(isFiniteNumber)
    ) {
      issues.push({
        path: 'aoi.centerBngM',
        message: 'must contain two finite EPSG:27700 coordinates',
      });
    } else {
      centerBngM = [centerValue[0] as number, centerValue[1] as number];
    }
    if (centerBngM) {
      if (!extentMatchesGrid(centerBngM[0], 291108.9018176432)) {
        issues.push({
          path: 'aoi.centerBngM',
          message: 'must match the configured TQ1 4HN BNG easting',
        });
      }
      if (!extentMatchesGrid(centerBngM[1], 65353.48350844931)) {
        issues.push({
          path: 'aoi.centerBngM',
          message: 'must match the configured TQ1 4HN BNG northing',
        });
      }
    }
    const anchorWgs84 = validateRealAnchorWgs84(aoiInput.anchorWgs84, issues);
    const boundaryWgs84 = validateRealBoundaryWgs84(
      aoiInput.boundaryWgs84,
      issues,
      sceneProfile,
    );

    let eastingSpan: number | undefined;
    let northingSpan: number | undefined;
    let midpointEasting: number | undefined;
    let midpointNorthing: number | undefined;
    if (boundsM) {
      eastingSpan = boundsM[2] - boundsM[0];
      northingSpan = boundsM[3] - boundsM[1];
      if (!Number.isFinite(eastingSpan)) {
        issues.push({
          path: 'aoi.boundsM',
          message: 'easting span must be finite',
        });
        eastingSpan = undefined;
      }
      if (!Number.isFinite(northingSpan)) {
        issues.push({
          path: 'aoi.boundsM',
          message: 'northing span must be finite',
        });
        northingSpan = undefined;
      }
      if (eastingSpan !== undefined)
        midpointEasting = boundsM[0] + eastingSpan / 2;
      if (northingSpan !== undefined)
        midpointNorthing = boundsM[1] + northingSpan / 2;
      if (midpointEasting !== undefined && !Number.isFinite(midpointEasting)) {
        issues.push({
          path: 'aoi.boundsM',
          message: 'easting midpoint must be finite',
        });
        midpointEasting = undefined;
      }
      if (
        midpointNorthing !== undefined &&
        !Number.isFinite(midpointNorthing)
      ) {
        issues.push({
          path: 'aoi.boundsM',
          message: 'northing midpoint must be finite',
        });
        midpointNorthing = undefined;
      }
    }
    if (
      eastingSpan !== undefined &&
      widthM !== undefined &&
      !extentMatchesGrid(widthM, eastingSpan)
    ) {
      issues.push({
        path: 'aoi.boundsM',
        message: 'easting span must equal aoi.widthM',
      });
    }
    if (
      northingSpan !== undefined &&
      heightM !== undefined &&
      !extentMatchesGrid(heightM, northingSpan)
    ) {
      issues.push({
        path: 'aoi.boundsM',
        message: 'northing span must equal aoi.heightM',
      });
    }
    if (
      eastingSpan !== undefined &&
      extentWidthM !== undefined &&
      !extentMatchesGrid(extentWidthM, eastingSpan)
    ) {
      issues.push({
        path: 'extentM.width',
        message: 'must equal the AOI easting span',
      });
    }
    if (
      northingSpan !== undefined &&
      extentDepthM !== undefined &&
      !extentMatchesGrid(extentDepthM, northingSpan)
    ) {
      issues.push({
        path: 'extentM.depth',
        message: 'must equal the AOI northing span',
      });
    }
    if (syntheticBase.ok) {
      const origin = syntheticBase.manifest.origin;
      if (
        midpointEasting !== undefined &&
        !extentMatchesGrid(midpointEasting, origin.eastingM)
      ) {
        issues.push({
          path: 'aoi.boundsM',
          message: 'easting midpoint must match the projected world origin',
        });
      }
      if (
        midpointNorthing !== undefined &&
        !extentMatchesGrid(midpointNorthing, origin.northingM)
      ) {
        issues.push({
          path: 'aoi.boundsM',
          message: 'northing midpoint must match the projected world origin',
        });
      }
      if (centerBngM && !extentMatchesGrid(centerBngM[0], origin.eastingM)) {
        issues.push({
          path: 'aoi.centerBngM',
          message: 'easting must match the projected world origin',
        });
      }
      if (centerBngM && !extentMatchesGrid(centerBngM[1], origin.northingM)) {
        issues.push({
          path: 'aoi.centerBngM',
          message: 'northing must match the projected world origin',
        });
      }
      if (
        centerBngM &&
        midpointEasting !== undefined &&
        !extentMatchesGrid(centerBngM[0], midpointEasting)
      ) {
        issues.push({
          path: 'aoi.centerBngM',
          message: 'easting must match the AOI bounds midpoint',
        });
      }
      if (
        centerBngM &&
        midpointNorthing !== undefined &&
        !extentMatchesGrid(centerBngM[1], midpointNorthing)
      ) {
        issues.push({
          path: 'aoi.centerBngM',
          message: 'northing must match the AOI bounds midpoint',
        });
      }
    }
    if (aoiInput.selectionStatus !== 'selected_pending_coverage') {
      issues.push({
        path: 'aoi.selectionStatus',
        message: 'must remain selected_pending_coverage',
      });
    }
    if (aoiInput.coverageStatus !== 'not_checked') {
      issues.push({
        path: 'aoi.coverageStatus',
        message: 'must remain not_checked; M2 is incomplete',
      });
    }
    if (
      boundsM &&
      eastingSpan === expectedSizeM &&
      northingSpan === expectedSizeM &&
      centerBngM &&
      anchorWgs84 &&
      boundaryWgs84 &&
      extentWidthM === expectedSizeM &&
      extentDepthM === expectedSizeM &&
      syntheticBase.ok &&
      syntheticBase.manifest.heightfield.columns === expectedDimension &&
      syntheticBase.manifest.heightfield.rows === expectedDimension &&
      syntheticBase.manifest.heightfield.spacingM === 2 &&
      widthM === expectedSizeM &&
      heightM === expectedSizeM &&
      aoiInput.crs === 'EPSG:27700' &&
      aoiInput.selectionStatus === 'selected_pending_coverage' &&
      aoiInput.coverageStatus === 'not_checked'
    ) {
      aoi = {
        crs: 'EPSG:27700',
        boundsM,
        centerBngM,
        widthM,
        heightM,
        anchorWgs84,
        boundaryWgs84,
        selectionStatus: 'selected_pending_coverage',
        coverageStatus: 'not_checked',
      };
    }
  }

  if (
    issues.length > 0 ||
    !syntheticBase.ok ||
    !realHeightfield ||
    !provenance ||
    !aoi
  ) {
    return {
      ok: false,
      issues: issues.length
        ? issues
        : [{ path: '$', message: 'real manifest validation failed' }],
    };
  }
  return {
    ok: true,
    manifest: {
      ...syntheticBase.manifest,
      worldType: 'real',
      sceneProfile,
      sourceCrs: 'EPSG:27700',
      heightfield: realHeightfield,
      provenance,
      aoi,
    },
  };
}

/** Validate a local v1 synthetic or explicitly attributed real terrain manifest. */
export function validateSceneManifest(
  input: unknown,
): ManifestValidationResult {
  if (isRecord(input) && input.worldType === 'real') {
    return validateRealSceneManifest(input);
  }
  return validateSyntheticSceneManifest(input);
}
