export const CURRENT_2KM_RUNTIME_FILES = [
  'buildings/buildings.json',
  'buildings/manifest.json',
  'buildings/qa.json',
  'heightfield.f32',
  'manifest.json',
  'qa.json',
  'roads/manifest.json',
  'roads/qa.json',
  'roads/roads.json',
  'scene-qa.json',
] as const;

export type Current2kmRuntimeFile = (typeof CURRENT_2KM_RUNTIME_FILES)[number];

export interface SceneReleaseFile {
  path: Current2kmRuntimeFile;
  byteLength: number;
  sha256: string;
}

export type SceneReleaseFetch = (
  input: URL,
  init?: RequestInit,
) => Promise<Response>;

export class SceneReleaseLoadError extends Error {
  constructor(
    readonly stage:
      | 'ready URL'
      | 'ready request'
      | 'ready response'
      | 'inventory request'
      | 'inventory response'
      | 'inventory validation'
      | 'asset integrity',
    message: string,
  ) {
    super(`${stage}: ${message}`);
    this.name = 'SceneReleaseLoadError';
  }
}

export interface SceneReleaseIntegrity {
  readonly releaseId: string;
  readonly releaseRootUrl: URL;
  readonly files: ReadonlyMap<Current2kmRuntimeFile, SceneReleaseFile>;
  assertAssetUrl(url: URL, label: string): void;
  verifyAsset(url: URL, bytes: ArrayBuffer, label: string): Promise<void>;
}

const READY_URL = '/worlds/torquay-poc-001-2km/ready.json';
const INVENTORY_LIMIT_BYTES = 32 * 1024;
const READY_LIMIT_BYTES = 8 * 1024;
const RELEASE_ID_PATTERN = /^[a-f0-9]{64}$/;
const browserFetch: SceneReleaseFetch = (input, init) =>
  globalThis.fetch(input, init);

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function exactKeys(value: UnknownRecord, expected: readonly string[]): boolean {
  const keys = Object.keys(value).sort();
  return (
    keys.length === expected.length &&
    keys.every((key, index) => key === [...expected].sort()[index])
  );
}

function resolveReadyUrl(input: string | URL): URL {
  try {
    const href = input instanceof URL ? input.href : input;
    const base = typeof document === 'undefined' ? undefined : document.baseURI;
    const url = base === undefined ? new URL(href) : new URL(href, base);
    if (
      (url.protocol !== 'http:' && url.protocol !== 'https:') ||
      url.pathname !== READY_URL ||
      url.username !== '' ||
      url.password !== '' ||
      url.search !== '' ||
      url.hash !== '' ||
      (typeof location !== 'undefined' && url.origin !== location.origin)
    ) {
      throw new Error(
        'only the fixed same-origin current_2km ready.json is allowed',
      );
    }
    return url;
  } catch (error) {
    throw new SceneReleaseLoadError(
      'ready URL',
      error instanceof Error ? error.message : String(error),
    );
  }
}

async function readBoundedResponse(
  fetcher: SceneReleaseFetch,
  url: URL,
  stage: 'ready request' | 'inventory request',
  limit: number,
  signal?: AbortSignal,
): Promise<Uint8Array> {
  let response: Response;
  try {
    response = await fetcher(
      url,
      signal === undefined ? undefined : { signal },
    );
  } catch (error) {
    throw new SceneReleaseLoadError(
      stage,
      `request failed for ${url.href}: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  if (!response.ok) {
    throw new SceneReleaseLoadError(
      stage,
      `request for ${url.href} returned HTTP ${response.status}`,
    );
  }
  const contentLength = response.headers.get('content-length');
  if (contentLength !== null) {
    const declared = Number(contentLength);
    if (!Number.isSafeInteger(declared) || declared < 0 || declared > limit) {
      await response.body?.cancel();
      throw new SceneReleaseLoadError(
        stage.replace('request', 'response') as
          'ready response' | 'inventory response',
        `${url.href} declares an invalid or oversized response (${contentLength} bytes; limit ${limit})`,
      );
    }
  }
  if (response.body === null) {
    const bytes = new Uint8Array(await response.arrayBuffer());
    if (bytes.byteLength > limit) {
      throw new SceneReleaseLoadError(
        stage.replace('request', 'response') as
          'ready response' | 'inventory response',
        `${url.href} exceeds the ${limit}-byte limit`,
      );
    }
    return bytes;
  }
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > limit) {
        await reader.cancel('scene release metadata exceeds size limit');
        throw new SceneReleaseLoadError(
          stage.replace('request', 'response') as
            'ready response' | 'inventory response',
          `${url.href} exceeds the ${limit}-byte limit`,
        );
      }
      chunks.push(value);
    }
  } catch (error) {
    if (error instanceof SceneReleaseLoadError) throw error;
    throw new SceneReleaseLoadError(
      stage.replace('request', 'response') as
        'ready response' | 'inventory response',
      `could not read ${url.href}: ${error instanceof Error ? error.message : String(error)}`,
    );
  } finally {
    reader.releaseLock();
  }
  const output = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    output.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return output;
}

function parseJson(
  bytes: Uint8Array,
  stage: 'ready response' | 'inventory response',
): unknown {
  try {
    return JSON.parse(
      new TextDecoder('utf-8', { fatal: true }).decode(bytes),
    ) as unknown;
  } catch (error) {
    throw new SceneReleaseLoadError(
      stage,
      `response was not valid UTF-8 JSON: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
}

function sortJson(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortJson);
  if (!isRecord(value)) return value;
  const sorted: UnknownRecord = {};
  for (const key of Object.keys(value).sort())
    sorted[key] = sortJson(value[key]);
  return sorted;
}

function canonicalJsonBytes(value: unknown): Uint8Array {
  return new TextEncoder().encode(`${JSON.stringify(sortJson(value))}\n`);
}

async function sha256Hex(bytes: Uint8Array | ArrayBuffer): Promise<string> {
  const source =
    bytes instanceof ArrayBuffer
      ? bytes
      : (bytes.buffer.slice(
          bytes.byteOffset,
          bytes.byteOffset + bytes.byteLength,
        ) as ArrayBuffer);
  const digest = await globalThis.crypto.subtle.digest('SHA-256', source);
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
}

function isSafeSha256(value: unknown): value is string {
  return typeof value === 'string' && RELEASE_ID_PATTERN.test(value);
}

function parseReady(input: unknown): {
  releaseId: string;
  inventoryByteLength: number;
  inventorySha256: string;
} {
  if (
    !isRecord(input) ||
    !exactKeys(input, [
      'formatVersion',
      'worldId',
      'sceneProfile',
      'releaseId',
      'inventoryPath',
      'inventoryByteLength',
      'inventorySha256',
    ])
  ) {
    throw new SceneReleaseLoadError(
      'ready response',
      'ready.json has an invalid object shape',
    );
  }
  const releaseId = input['releaseId'];
  const byteLength = input['inventoryByteLength'];
  const inventorySha256 = input['inventorySha256'];
  if (
    input['formatVersion'] !== 1 ||
    input['worldId'] !== 'torquay-poc-001' ||
    input['sceneProfile'] !== 'current_2km' ||
    !isSafeSha256(releaseId) ||
    input['inventoryPath'] !== `releases/${releaseId}/inventory.json` ||
    typeof byteLength !== 'number' ||
    !Number.isSafeInteger(byteLength) ||
    byteLength < 1 ||
    byteLength > INVENTORY_LIMIT_BYTES ||
    !isSafeSha256(inventorySha256)
  ) {
    throw new SceneReleaseLoadError(
      'ready response',
      'ready.json does not describe the fixed current_2km content-addressed release',
    );
  }
  return { releaseId, inventoryByteLength: byteLength, inventorySha256 };
}

function parseInventory(
  input: unknown,
  releaseId: string,
): Map<Current2kmRuntimeFile, SceneReleaseFile> {
  if (
    !isRecord(input) ||
    !exactKeys(input, [
      'formatVersion',
      'worldId',
      'sceneProfile',
      'releaseId',
      'files',
    ]) ||
    input['formatVersion'] !== 1 ||
    input['worldId'] !== 'torquay-poc-001' ||
    input['sceneProfile'] !== 'current_2km' ||
    input['releaseId'] !== releaseId ||
    !Array.isArray(input['files']) ||
    input['files'].length !== CURRENT_2KM_RUNTIME_FILES.length
  ) {
    throw new SceneReleaseLoadError(
      'inventory validation',
      'inventory.json has an invalid shape',
    );
  }
  const files = new Map<Current2kmRuntimeFile, SceneReleaseFile>();
  for (let index = 0; index < input['files'].length; index += 1) {
    const item: unknown = input['files'][index];
    if (
      !isRecord(item) ||
      !exactKeys(item, ['path', 'byteLength', 'sha256']) ||
      typeof item['path'] !== 'string' ||
      !CURRENT_2KM_RUNTIME_FILES.includes(
        item['path'] as Current2kmRuntimeFile,
      ) ||
      typeof item['byteLength'] !== 'number' ||
      !Number.isSafeInteger(item['byteLength']) ||
      item['byteLength'] < 0 ||
      !isSafeSha256(item['sha256'])
    ) {
      throw new SceneReleaseLoadError(
        'inventory validation',
        `inventory.files[${index}] is malformed or not allowlisted`,
      );
    }
    const path = item['path'] as Current2kmRuntimeFile;
    if (files.has(path)) {
      throw new SceneReleaseLoadError(
        'inventory validation',
        `duplicate inventory path '${path}'`,
      );
    }
    files.set(path, {
      path,
      byteLength: item['byteLength'],
      sha256: item['sha256'],
    });
  }
  const expectedOrder = [...CURRENT_2KM_RUNTIME_FILES];
  if (
    Array.from(files.keys()).some(
      (path, index) => path !== expectedOrder[index],
    )
  ) {
    throw new SceneReleaseLoadError(
      'inventory validation',
      'inventory file entries are not in the fixed deterministic order',
    );
  }
  return files;
}

/** Fetch readiness first and construct only the fixed local release URLs. */
export async function loadCurrent2kmRelease(
  readyLocation: string | URL,
  fetcher: SceneReleaseFetch = browserFetch,
  signal?: AbortSignal,
): Promise<SceneReleaseIntegrity> {
  const readyUrl = resolveReadyUrl(readyLocation);
  const readyBytes = await readBoundedResponse(
    fetcher,
    readyUrl,
    'ready request',
    READY_LIMIT_BYTES,
    signal,
  );
  const ready = parseReady(parseJson(readyBytes, 'ready response'));
  const inventoryUrl = new URL(
    `/worlds/torquay-poc-001-2km/releases/${ready.releaseId}/inventory.json`,
    readyUrl.origin,
  );
  const inventoryBytes = await readBoundedResponse(
    fetcher,
    inventoryUrl,
    'inventory request',
    INVENTORY_LIMIT_BYTES,
    signal,
  );
  if (
    inventoryBytes.byteLength !== ready.inventoryByteLength ||
    (await sha256Hex(inventoryBytes)) !== ready.inventorySha256
  ) {
    throw new SceneReleaseLoadError(
      'inventory validation',
      'ready.json inventory length or SHA-256 does not match the fetched inventory',
    );
  }
  const inventory = parseJson(inventoryBytes, 'inventory response');
  const files = parseInventory(inventory, ready.releaseId);
  if (!isRecord(inventory)) {
    throw new SceneReleaseLoadError(
      'inventory validation',
      'inventory.json must be an object',
    );
  }
  const body = {
    formatVersion: inventory['formatVersion'],
    worldId: inventory['worldId'],
    sceneProfile: inventory['sceneProfile'],
    files: inventory['files'],
  };
  if ((await sha256Hex(canonicalJsonBytes(body))) !== ready.releaseId) {
    throw new SceneReleaseLoadError(
      'inventory validation',
      'inventory entries do not match their content-addressed release ID',
    );
  }
  const releaseRootUrl = new URL(
    `/worlds/torquay-poc-001-2km/releases/${ready.releaseId}/`,
    readyUrl.origin,
  );
  const assertAssetUrl = (url: URL, label: string): void => {
    if (
      url.origin !== releaseRootUrl.origin ||
      !url.pathname.startsWith(releaseRootUrl.pathname) ||
      url.search !== '' ||
      url.hash !== ''
    ) {
      throw new SceneReleaseLoadError(
        'asset integrity',
        `${label} URL is outside the pinned immutable release`,
      );
    }
    const relative = url.pathname.slice(releaseRootUrl.pathname.length);
    if (
      !CURRENT_2KM_RUNTIME_FILES.includes(relative as Current2kmRuntimeFile)
    ) {
      throw new SceneReleaseLoadError(
        'asset integrity',
        `${label} path '${relative}' is not in the runtime inventory`,
      );
    }
  };
  return {
    releaseId: ready.releaseId,
    releaseRootUrl,
    files,
    assertAssetUrl,
    async verifyAsset(
      url: URL,
      bytes: ArrayBuffer,
      label: string,
    ): Promise<void> {
      assertAssetUrl(url, label);
      const relative = url.pathname.slice(releaseRootUrl.pathname.length);
      const descriptor = files.get(relative as Current2kmRuntimeFile);
      if (!descriptor || bytes.byteLength !== descriptor.byteLength) {
        throw new SceneReleaseLoadError(
          'asset integrity',
          `${label} byte length does not match the pinned inventory`,
        );
      }
      const actual = await sha256Hex(bytes);
      if (actual !== descriptor.sha256) {
        throw new SceneReleaseLoadError(
          'asset integrity',
          `${label} SHA-256 does not match the pinned inventory`,
        );
      }
    },
  };
}
