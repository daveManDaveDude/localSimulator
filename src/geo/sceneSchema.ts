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

export interface RealTerrainSceneManifest {
  formatVersion: 1;
  id: string;
  name: string;
  worldType: 'real';
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
  heightfield: SyntheticSceneManifest['heightfield'];
  provenance: {
    kind: 'real';
    publisher: string;
    product: string;
    licence: string;
    attribution: string;
    verticalReference: string;
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
    widthM: number;
    heightM: number;
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

  const provenanceInput = input.provenance;
  let provenance: RealTerrainSceneManifest['provenance'] | undefined;
  if (!isRecord(provenanceInput)) {
    issues.push({ path: 'provenance', message: 'must be an object' });
  } else {
    if (provenanceInput.kind !== 'real') {
      issues.push({ path: 'provenance.kind', message: 'must be real' });
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
      publisher &&
      product &&
      licence &&
      attribution &&
      verticalReference &&
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
        publisher,
        product,
        licence,
        attribution,
        verticalReference,
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
    if (widthM !== undefined && widthM !== 1000)
      issues.push({
        path: 'aoi.widthM',
        message: 'must match the reviewed 1,000 m AOI',
      });
    if (heightM !== undefined && heightM !== 1000)
      issues.push({
        path: 'aoi.heightM',
        message: 'must match the reviewed 1,000 m AOI',
      });
    if (
      boundsM &&
      widthM !== undefined &&
      !extentMatchesGrid(widthM, boundsM[2] - boundsM[0])
    ) {
      issues.push({
        path: 'aoi.boundsM',
        message: 'easting span must equal aoi.widthM',
      });
    }
    if (
      boundsM &&
      heightM !== undefined &&
      !extentMatchesGrid(heightM, boundsM[3] - boundsM[1])
    ) {
      issues.push({
        path: 'aoi.boundsM',
        message: 'northing span must equal aoi.heightM',
      });
    }
    if (boundsM && syntheticBase.ok) {
      if (
        !extentMatchesGrid(
          (boundsM[0] + boundsM[2]) / 2,
          syntheticBase.manifest.origin.eastingM,
        )
      ) {
        issues.push({
          path: 'aoi.boundsM',
          message: 'easting midpoint must match the projected world origin',
        });
      }
      if (
        !extentMatchesGrid(
          (boundsM[1] + boundsM[3]) / 2,
          syntheticBase.manifest.origin.northingM,
        )
      ) {
        issues.push({
          path: 'aoi.boundsM',
          message: 'northing midpoint must match the projected world origin',
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
      widthM === 1000 &&
      heightM === 1000 &&
      aoiInput.crs === 'EPSG:27700' &&
      aoiInput.selectionStatus === 'selected_pending_coverage' &&
      aoiInput.coverageStatus === 'not_checked'
    ) {
      aoi = {
        crs: 'EPSG:27700',
        boundsM,
        widthM,
        heightM,
        selectionStatus: 'selected_pending_coverage',
        coverageStatus: 'not_checked',
      };
    }
  }

  if (issues.length > 0 || !syntheticBase.ok || !provenance || !aoi) {
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
      sourceCrs: 'EPSG:27700',
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
