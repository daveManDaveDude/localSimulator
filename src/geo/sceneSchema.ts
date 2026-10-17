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

export interface ManifestValidationIssue {
  path: string;
  message: string;
}

export type ManifestValidationResult =
  | { ok: true; manifest: SyntheticSceneManifest }
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
export function validateSceneManifest(
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
