import { describe, expect, it } from 'vitest';
import {
  loadSyntheticWorld,
  loadWorld,
  type WorldFetch,
} from '../../src/app/worldLoader';
import {
  createRealManifest,
  readSyntheticFixtureBytes,
  readSyntheticFixtureManifest,
} from './fixtures';

const manifestUrl = new URL(
  'https://local.test/worlds/synthetic-heightfield/manifest.json',
);

type TestRecord = Record<string, unknown>;

function isTestRecord(value: unknown): value is TestRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function withManifestValue(path: string, value: unknown): unknown {
  const input = structuredClone(readSyntheticFixtureManifest()) as TestRecord;
  const segments = path.split('.');
  let current = input;
  for (const segment of segments.slice(0, -1)) {
    const child = current[segment];
    if (!isTestRecord(child)) throw new Error(`Missing test path ${segment}`);
    current = child;
  }
  current[segments[segments.length - 1]!] = value;
  return input;
}

function createFetcher(
  options: {
    manifest?: unknown;
    manifestBody?: string;
    manifestStatus?: number;
    heightfieldBytes?: ArrayBuffer;
    heightfieldStatus?: number;
    manifestResponse?: Response;
    heightfieldResponse?: Response;
    failOn?: 'manifest' | 'heightfield';
  } = {},
): { fetcher: WorldFetch; requests: string[] } {
  const requests: string[] = [];
  const fetcher: WorldFetch = async (url) => {
    requests.push(url.href);
    const isManifest = url.pathname.endsWith('/manifest.json');
    if (options.failOn === (isManifest ? 'manifest' : 'heightfield')) {
      throw new Error('simulated network failure');
    }
    if (isManifest) {
      if (options.manifestResponse !== undefined) {
        return options.manifestResponse;
      }
      if (options.manifestBody !== undefined) {
        return new Response(options.manifestBody, {
          status: options.manifestStatus ?? 200,
        });
      }
      return new Response(
        JSON.stringify(options.manifest ?? readSyntheticFixtureManifest()),
        {
          status: options.manifestStatus ?? 200,
        },
      );
    }
    if (options.heightfieldResponse !== undefined) {
      return options.heightfieldResponse;
    }
    return new Response(
      options.heightfieldBytes ?? readSyntheticFixtureBytes(),
      {
        status: options.heightfieldStatus ?? 200,
      },
    );
  };
  return { fetcher, requests };
}

function streamingResponse(
  chunks: Uint8Array[],
  headers: Record<string, string> = {},
): { response: Response; cancelled: () => boolean; pulls: () => number } {
  let next = 0;
  let wasCancelled = false;
  let pullCount = 0;
  const body = new ReadableStream<Uint8Array>(
    {
      pull(controller) {
        pullCount += 1;
        const chunk = chunks[next];
        if (chunk === undefined) {
          controller.close();
          return;
        }
        next += 1;
        controller.enqueue(chunk);
      },
      cancel() {
        wasCancelled = true;
      },
    },
    { highWaterMark: 0 },
  );
  return {
    response: new Response(body, { headers }),
    cancelled: () => wasCancelled,
    pulls: () => pullCount,
  };
}

async function sha256Hex(bytes: ArrayBuffer): Promise<string> {
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
}

describe('loadSyntheticWorld', () => {
  it('fetches and verifies the relative fixture, then returns decoded values', async () => {
    const { fetcher, requests } = createFetcher();
    const result = await loadSyntheticWorld(manifestUrl, fetcher);

    expect(requests).toEqual([
      manifestUrl.href,
      'https://local.test/worlds/synthetic-heightfield/heightfield.f32',
    ]);
    expect(result.manifest.id).toBe('synthetic-heightfield-3x3');
    expect([...result.heights]).toEqual([
      -2.5, 0, 1.25, 10, 11.5, 12, 20, 21, 22.75,
    ]);
  });

  it('loads an attributed real v1 manifest through local relative asset URLs', async () => {
    const bytes = new ArrayBuffer(501 * 501 * Float32Array.BYTES_PER_ELEMENT);
    const digest = await sha256Hex(bytes);
    const manifest = createRealManifest(digest);
    const realManifestUrl = new URL(
      'https://local.test/worlds/torquay-poc-001/manifest.json',
    );
    const { fetcher, requests } = createFetcher({
      manifest,
      heightfieldBytes: bytes,
    });

    const loaded = await loadWorld(realManifestUrl, fetcher);

    expect(loaded.manifest.worldType).toBe('real');
    expect(loaded.manifest.id).toBe('torquay-poc-001');
    expect(loaded.heights).toHaveLength(501 * 501);
    expect(requests).toEqual([
      realManifestUrl.href,
      'https://local.test/worlds/torquay-poc-001/heightfield.f32',
    ]);
  });

  it('keeps the typed synthetic loader from accepting a real package', async () => {
    const bytes = new ArrayBuffer(501 * 501 * Float32Array.BYTES_PER_ELEMENT);
    const manifest = createRealManifest(await sha256Hex(bytes));
    const { fetcher } = createFetcher({ manifest, heightfieldBytes: bytes });

    await expect(
      loadSyntheticWorld(manifestUrl, fetcher),
    ).rejects.toMatchObject({
      stage: 'manifest validation',
    });
  });

  it('checks real package byte length before checksum and decoding', async () => {
    const shortBytes = new ArrayBuffer(16);
    const manifest = createRealManifest(await sha256Hex(shortBytes));
    const realManifestUrl = new URL(
      'https://local.test/worlds/torquay-poc-001/manifest.json',
    );
    const { fetcher } = createFetcher({
      manifest,
      heightfieldBytes: shortBytes,
    });

    await expect(loadWorld(realManifestUrl, fetcher)).rejects.toThrow(
      'heightfield response: https://local.test/worlds/torquay-poc-001/heightfield.f32 byte length mismatch',
    );
  });

  it.each(['35', '37'])(
    'rejects and cancels a false heightfield Content-Length of %s bytes',
    async (contentLength) => {
      const streamed = streamingResponse(
        [new Uint8Array(readSyntheticFixtureBytes())],
        { 'content-length': contentLength },
      );
      const { fetcher } = createFetcher({
        heightfieldResponse: streamed.response,
      });

      await expect(loadWorld(manifestUrl, fetcher)).rejects.toThrow(
        `heightfield response: https://local.test/worlds/synthetic-heightfield/heightfield.f32 byte length mismatch: Content-Length declares ${contentLength} bytes; expected 36`,
      );
      expect(streamed.cancelled()).toBe(true);
      expect(streamed.pulls()).toBe(0);
    },
  );

  it('accepts an exact heightfield Content-Length while streaming bytes', async () => {
    const streamed = streamingResponse(
      [new Uint8Array(readSyntheticFixtureBytes())],
      { 'content-length': '36' },
    );
    const { fetcher } = createFetcher({
      heightfieldResponse: streamed.response,
    });

    const loaded = await loadSyntheticWorld(manifestUrl, fetcher);

    expect([...loaded.heights]).toHaveLength(9);
    expect(streamed.cancelled()).toBe(false);
    expect(streamed.pulls()).toBe(2);
  });

  it('cancels an oversized heightfield stream without relying on Content-Length', async () => {
    const streamed = streamingResponse([
      new Uint8Array(readSyntheticFixtureBytes()),
      new Uint8Array([0, 0, 0, 0]),
      new Uint8Array([0, 0, 0, 0]),
    ]);
    const { fetcher } = createFetcher({
      heightfieldResponse: streamed.response,
    });

    await expect(loadWorld(manifestUrl, fetcher)).rejects.toThrow(
      'heightfield response: https://local.test/worlds/synthetic-heightfield/heightfield.f32 exceeded the 36-byte response bound',
    );
    expect(streamed.cancelled()).toBe(true);
    expect(streamed.pulls()).toBeLessThan(3);
  });

  it('does not request binary data when manifest validation fails', async () => {
    const { fetcher, requests } = createFetcher({
      manifest: withManifestValue('worldType', 'real'),
    });

    await expect(
      loadSyntheticWorld(manifestUrl, fetcher),
    ).rejects.toMatchObject({ stage: 'manifest validation' });
    expect(requests).toEqual([manifestUrl.href]);
  });

  it.each(['../heightfield.f32', 'https://evil.test/data.f32'])(
    'blocks unsafe asset path %s before binary fetch',
    async (path) => {
      const { fetcher, requests } = createFetcher({
        manifest: withManifestValue('heightfield.path', path),
      });
      await expect(
        loadSyntheticWorld(manifestUrl, fetcher),
      ).rejects.toMatchObject({ stage: 'manifest validation' });
      expect(requests).toEqual([manifestUrl.href]);
    },
  );

  it('reports manifest HTTP and JSON failures with their stage', async () => {
    const httpFailure = createFetcher({ manifestStatus: 503 });
    await expect(
      loadSyntheticWorld(manifestUrl, httpFailure.fetcher),
    ).rejects.toThrow('manifest request: request for');

    const jsonFailure = createFetcher({ manifestBody: '{invalid json' });
    await expect(
      loadSyntheticWorld(manifestUrl, jsonFailure.fetcher),
    ).rejects.toThrow('manifest response: response was not valid UTF-8 JSON');
  });

  it('cancels a headerless oversized manifest stream at the metadata cap', async () => {
    const streamed = streamingResponse([
      new Uint8Array(256 * 1024 + 1),
      new Uint8Array([1]),
    ]);
    const { fetcher, requests } = createFetcher({
      manifestResponse: streamed.response,
    });

    await expect(loadWorld(manifestUrl, fetcher)).rejects.toThrow(
      'manifest response: https://local.test/worlds/synthetic-heightfield/manifest.json exceeded the 262144-byte response bound',
    );
    expect(streamed.cancelled()).toBe(true);
    expect(streamed.pulls()).toBeLessThan(3);
    expect(requests).toEqual([manifestUrl.href]);
  });

  it('rejects and cancels a manifest whose declared length exceeds the cap', async () => {
    const streamed = streamingResponse(
      [
        new TextEncoder().encode(
          JSON.stringify(readSyntheticFixtureManifest()),
        ),
      ],
      { 'content-length': String(256 * 1024 + 1) },
    );
    const { fetcher, requests } = createFetcher({
      manifestResponse: streamed.response,
    });

    await expect(loadWorld(manifestUrl, fetcher)).rejects.toThrow(
      'manifest response: https://local.test/worlds/synthetic-heightfield/manifest.json byte length mismatch: Content-Length declares 262145 bytes; expected at most 262144',
    );
    expect(streamed.cancelled()).toBe(true);
    expect(streamed.pulls()).toBe(0);
    expect(requests).toEqual([manifestUrl.href]);
  });

  it('reports binary HTTP and network failures with their stage', async () => {
    const httpFailure = createFetcher({ heightfieldStatus: 404 });
    await expect(
      loadSyntheticWorld(manifestUrl, httpFailure.fetcher),
    ).rejects.toThrow('heightfield request: request for');

    const networkFailure = createFetcher({ failOn: 'heightfield' });
    await expect(
      loadSyntheticWorld(manifestUrl, networkFailure.fetcher),
    ).rejects.toThrow('heightfield request: request failed');
  });

  it('rejects a binary checksum mismatch before decoding', async () => {
    const manifest = withManifestValue('heightfield.sha256', '0'.repeat(64));
    const { fetcher } = createFetcher({ manifest });
    await expect(loadSyntheticWorld(manifestUrl, fetcher)).rejects.toThrow(
      'heightfield checksum: SHA-256 mismatch',
    );
  });

  it('rejects a dimensionally short binary before checksum or decoding', async () => {
    const bytes = new ArrayBuffer(8);
    new DataView(bytes).setFloat32(0, 1, true);
    new DataView(bytes).setFloat32(4, 2, true);
    const manifest = withManifestValue(
      'heightfield.sha256',
      await sha256Hex(bytes),
    );
    const { fetcher } = createFetcher({ manifest, heightfieldBytes: bytes });
    await expect(loadSyntheticWorld(manifestUrl, fetcher)).rejects.toThrow(
      'heightfield response: https://local.test/worlds/synthetic-heightfield/heightfield.f32 byte length mismatch',
    );
  });

  it('reports manifest network failures contextually', async () => {
    const { fetcher } = createFetcher({ failOn: 'manifest' });
    await expect(loadSyntheticWorld(manifestUrl, fetcher)).rejects.toThrow(
      'manifest request: request failed',
    );
  });
});
