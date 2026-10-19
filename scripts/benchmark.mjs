import { createHash } from 'node:crypto';
import { spawn, execFileSync } from 'node:child_process';
import { mkdir, readFile, readdir, stat, writeFile } from 'node:fs/promises';
import net from 'node:net';
import os from 'node:os';
import { dirname, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const defaultOutputDirectory = resolve(
  projectRoot,
  'docs/milestones/artifacts',
);
const screenshotDirectory = resolve(projectRoot, 'docs/milestones/screenshots');
const viewport = { width: 1920, height: 1080 };
const deviceScaleFactor = 1;
const warmupMs = 3_000;
const runDurationMs = 10_000;
const runCount = 3;

const workloads = [
  {
    id: 'synthetic-m0',
    label: 'Synthetic M0',
    route: '/?world=m0',
    mode: 'fly',
  },
  {
    id: 'terrain-only',
    label: 'EA terrain only',
    route: '/?world=torquay-poc-001',
    mode: 'fly',
  },
  {
    id: 'terrain-buildings',
    label: 'EA terrain + OSM buildings',
    route: '/?world=torquay-poc-001&buildings=1',
    mode: 'fly',
  },
  {
    id: 'terrain-roads',
    label: 'EA terrain + OSM roads',
    route: '/?world=torquay-poc-001&roads=1',
    mode: 'fly',
  },
  {
    id: 'combined-fly',
    label: 'EA terrain + buildings + roads (fly)',
    route: '/?world=torquay-poc-001&buildings=1&roads=1',
    mode: 'fly',
  },
  {
    id: 'combined-walk',
    label: 'EA terrain + buildings + roads (walk)',
    route: '/?world=torquay-poc-001&buildings=1&roads=1',
    mode: 'walk',
  },
];

function parseArguments(argv) {
  const options = {
    outputDirectory: defaultOutputDirectory,
    screenshotsDirectory: screenshotDirectory,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === '--output-directory') {
      options.outputDirectory = resolve(argv[++index] ?? '');
    } else if (argument === '--screenshots-directory') {
      options.screenshotsDirectory = resolve(argv[++index] ?? '');
    } else if (argument !== undefined) {
      throw new Error(`Unknown benchmark argument: ${argument}`);
    }
  }
  return options;
}

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function gitValue(...args) {
  try {
    return execFileSync('git', args, {
      cwd: projectRoot,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
  } catch {
    return 'unavailable';
  }
}

async function listFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) files.push(...(await listFiles(path)));
    else if (entry.isFile()) files.push(path);
  }
  return files.sort();
}

async function directoryIdentity(directory) {
  const files = await listFiles(directory);
  const digest = createHash('sha256');
  for (const path of files) {
    const bytes = await readFile(path);
    digest.update(relative(directory, path).replaceAll(sep, '/'));
    digest.update('\0');
    digest.update(sha256(bytes));
    digest.update('\n');
  }
  return { files: files.length, sha256: digest.digest('hex') };
}

async function freeLocalPort() {
  return new Promise((resolvePort, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      if (!address || typeof address === 'string') {
        server.close();
        reject(new Error('Could not allocate a temporary local port.'));
        return;
      }
      const port = address.port;
      server.close((error) => (error ? reject(error) : resolvePort(port)));
    });
  });
}

async function startPreview(port) {
  const viteEntry = resolve(projectRoot, 'node_modules/vite/bin/vite.js');
  const child = spawn(
    process.execPath,
    [
      viteEntry,
      'preview',
      '--host',
      '127.0.0.1',
      '--port',
      String(port),
      '--strictPort',
    ],
    {
      cwd: projectRoot,
      env: process.env,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    },
  );
  let logs = '';
  child.stdout.setEncoding('utf8').on('data', (chunk) => {
    logs += chunk;
  });
  child.stderr.setEncoding('utf8').on('data', (chunk) => {
    logs += chunk;
  });
  const baseUrl = `http://127.0.0.1:${port}`;
  const deadline = Date.now() + 20_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`Vite preview exited early. Output:\n${logs}`);
    }
    try {
      const response = await fetch(baseUrl);
      if (response.ok) return { child, baseUrl, logs: () => logs };
    } catch {
      // Keep waiting while Vite starts.
    }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 200));
  }
  child.kill();
  throw new Error(`Timed out starting Vite preview. Output:\n${logs}`);
}

async function assetRecord(path, category, publicPath) {
  const bytes = await readFile(path);
  return {
    path: publicPath,
    category,
    byteLength: bytes.byteLength,
    sha256: sha256(bytes),
  };
}

async function workloadAssets(workload) {
  const assets = [];
  const distRoot = resolve(projectRoot, 'dist');
  const realRoot = resolve(distRoot, 'worlds/torquay-poc-001');
  const add = async (path, category) => {
    const relativePath = relative(distRoot, path).replaceAll(sep, '/');
    assets.push(await assetRecord(path, category, `/${relativePath}`));
  };

  if (workload.id === 'synthetic-m0') {
    return {
      assets,
      bytesByCategory: { manifest: 0, payload: 0, qa: 0 },
      totalBytes: 0,
      identity: { worldId: 'm0-analytic-synthetic', synthetic: true },
    };
  }

  if (workload.id === 'synthetic-heightfield') {
    const root = resolve(distRoot, 'worlds/synthetic-terrain-demo');
    await add(resolve(root, 'manifest.json'), 'manifest');
    await add(resolve(root, 'heightfield.f32'), 'payload');
    return summarizeAssetInventory(assets, {
      worldId: 'synthetic-terrain-demo',
      source: 'synthetic fixture',
    });
  }

  await add(resolve(realRoot, 'manifest.json'), 'manifest');
  await add(resolve(realRoot, 'heightfield.f32'), 'payload');
  const terrainManifest = JSON.parse(
    await readFile(resolve(realRoot, 'manifest.json'), 'utf8'),
  );
  const identity = {
    worldId: terrainManifest.id,
    terrainManifestSha256: sha256(
      await readFile(resolve(realRoot, 'manifest.json')),
    ),
    heightfieldSha256: terrainManifest.heightfield?.sha256,
    selectionStatus: terrainManifest.aoi?.selectionStatus,
    coverageStatus: terrainManifest.aoi?.coverageStatus,
  };
  const terrainBinary = assets.find((asset) =>
    asset.path.endsWith('/heightfield.f32'),
  );
  if (
    !terrainBinary ||
    terrainBinary.sha256 !== terrainManifest.heightfield?.sha256 ||
    terrainBinary.byteLength !== terrainManifest.heightfield?.byteLength
  ) {
    throw new Error(
      'The production terrain payload does not match its manifest identity.',
    );
  }

  if (workload.route.includes('buildings=1')) {
    const root = resolve(realRoot, 'buildings');
    await add(resolve(root, 'manifest.json'), 'manifest');
    await add(resolve(root, 'buildings.json'), 'payload');
    await add(resolve(root, 'qa.json'), 'qa');
    const manifest = JSON.parse(
      await readFile(resolve(root, 'manifest.json'), 'utf8'),
    );
    identity.buildingManifestSha256 = sha256(
      await readFile(resolve(root, 'manifest.json')),
    );
    identity.buildingsSha256 = manifest.buildings?.sha256;
    identity.buildingQaSha256 = manifest.qaReport?.sha256;
    const payload = assets.find((asset) =>
      asset.path.endsWith('/buildings/buildings.json'),
    );
    const qa = assets.find((asset) =>
      asset.path.endsWith('/buildings/qa.json'),
    );
    if (
      !payload ||
      !qa ||
      payload.sha256 !== manifest.buildings?.sha256 ||
      payload.byteLength !== manifest.buildings?.byteLength ||
      qa.sha256 !== manifest.qaReport?.sha256 ||
      qa.byteLength !== manifest.qaReport?.byteLength
    ) {
      throw new Error(
        'The production building assets do not match their manifest identity.',
      );
    }
  }

  if (workload.route.includes('roads=1')) {
    const root = resolve(realRoot, 'roads');
    await add(resolve(root, 'manifest.json'), 'manifest');
    await add(resolve(root, 'roads.json'), 'payload');
    await add(resolve(root, 'qa.json'), 'qa');
    const manifest = JSON.parse(
      await readFile(resolve(root, 'manifest.json'), 'utf8'),
    );
    identity.roadManifestSha256 = sha256(
      await readFile(resolve(root, 'manifest.json')),
    );
    identity.roadsSha256 = manifest.assets?.roads?.sha256;
    identity.roadQaSha256 = manifest.assets?.qa?.sha256;
    const payload = assets.find((asset) =>
      asset.path.endsWith('/roads/roads.json'),
    );
    const qa = assets.find((asset) => asset.path.endsWith('/roads/qa.json'));
    if (
      !payload ||
      !qa ||
      payload.sha256 !== manifest.assets?.roads?.sha256 ||
      payload.byteLength !== manifest.assets?.roads?.byteLength ||
      qa.sha256 !== manifest.assets?.qa?.sha256 ||
      qa.byteLength !== manifest.assets?.qa?.byteLength
    ) {
      throw new Error(
        'The production road assets do not match their manifest identity.',
      );
    }
  }

  return summarizeAssetInventory(assets, identity);
}

function summarizeAssetInventory(assets, identity) {
  const bytesByCategory = { manifest: 0, payload: 0, qa: 0 };
  const seen = new Set();
  let totalBytes = 0;
  for (const asset of assets) {
    const key = `${asset.path}\0${asset.sha256}`;
    if (seen.has(key)) continue;
    seen.add(key);
    bytesByCategory[asset.category] += asset.byteLength;
    totalBytes += asset.byteLength;
  }
  return { assets, bytesByCategory, totalBytes, identity };
}

async function waitForWorkload(page, workload) {
  await page.waitForFunction(
    ({ buildings, roads }) => {
      const shell = document.querySelector('.viewer-shell');
      if (
        shell?.getAttribute('data-load-state') !== 'loaded' ||
        shell?.getAttribute('data-renderer-ready') !== 'true'
      ) {
        return false;
      }
      if (
        buildings &&
        document
          .querySelector('[data-testid="building-status"]')
          ?.getAttribute('data-state') !== 'loaded'
      ) {
        return false;
      }
      if (
        roads &&
        document
          .querySelector('[data-testid="road-status"]')
          ?.getAttribute('data-state') !== 'loaded'
      ) {
        return false;
      }
      return true;
    },
    {
      buildings: workload.route.includes('buildings=1'),
      roads: workload.route.includes('roads=1'),
    },
    { timeout: 120_000 },
  );
  await page.evaluate(
    () =>
      new Promise((resolveFrame) =>
        requestAnimationFrame(() => requestAnimationFrame(resolveFrame)),
      ),
  );
}

async function loadTimeAfterLayers(page) {
  return page.evaluate(() => {
    const started = Number(window.__tvw014NavigationStart);
    return Number.isFinite(started) ? performance.now() - started : null;
  });
}

async function configureMode(page, workload) {
  if (workload.id === 'synthetic-m0') {
    // The analytic demo has no external assets but supports the same controls.
  }
  await page.getByRole('button', { name: 'Start exploring' }).click();
  await page.waitForFunction(
    () => document.pointerLockElement === document.querySelector('canvas'),
    undefined,
    { timeout: 10_000 },
  );
  if (workload.mode === 'walk') {
    await page.keyboard.press('f');
    await page.waitForFunction(
      () =>
        document
          .querySelector('[data-testid="navigation-mode"]')
          ?.getAttribute('data-mode') === 'walk',
      undefined,
      { timeout: 20_000 },
    );
  }
}

async function readBrowserMetadata(page, browser) {
  const pageMetadata = await page.evaluate(() => {
    const canvas = document.querySelector('canvas');
    const gl = canvas?.getContext('webgl2') ?? canvas?.getContext('webgl');
    const debug = gl?.getExtension('WEBGL_debug_renderer_info');
    const rendererName = debug
      ? gl?.getParameter(debug.UNMASKED_RENDERER_WEBGL)
      : gl?.getParameter(gl.RENDERER);
    const vendor = debug
      ? gl?.getParameter(debug.UNMASKED_VENDOR_WEBGL)
      : gl?.getParameter(gl.VENDOR);
    return {
      userAgent: navigator.userAgent,
      devicePixelRatio: window.devicePixelRatio,
      canvasBackingWidth: canvas?.width ?? null,
      canvasBackingHeight: canvas?.height ?? null,
      renderer: String(rendererName ?? 'unavailable'),
      vendor: String(vendor ?? 'unavailable'),
      isSoftwareRenderer: /swiftshader|software|llvmpipe/i.test(
        String(rendererName ?? ''),
      ),
    };
  });
  return {
    browser: 'Chromium',
    browserVersion: browser.version(),
    operatingSystem: `${os.platform()} ${os.release()} (${os.arch()})`,
    ...pageMetadata,
  };
}

async function readSceneMetrics(page) {
  return page.evaluate(() => {
    const shell = document.querySelector('.viewer-shell');
    const read = (name) => {
      const value = shell?.getAttribute(`data-${name}`);
      return value === null || value === undefined ? null : Number(value);
    };
    const position = document.querySelector('[data-testid="camera-position"]');
    const orientation = document.querySelector(
      '[data-testid="camera-orientation"]',
    );
    const mode = document.querySelector('[data-testid="navigation-mode"]');
    return {
      drawCalls: read('draw-calls'),
      triangles: read('triangles'),
      geometryCount: read('geometry-count'),
      textureCount: read('texture-count'),
      worldName: shell?.getAttribute('data-world-name') ?? null,
      worldSource: shell?.getAttribute('data-world-source') ?? null,
      cameraPose: {
        x: Number(position?.getAttribute('data-x')),
        y: Number(position?.getAttribute('data-y')),
        z: Number(position?.getAttribute('data-z')),
        bearingDegrees: Number(
          orientation?.getAttribute('data-bearing-degrees'),
        ),
        pitchDegrees: Number(orientation?.getAttribute('data-pitch-degrees')),
        navigationMode: mode?.getAttribute('data-mode') ?? null,
      },
    };
  });
}

async function sampleHeap(session, durationMs) {
  try {
    await session.send('Performance.enable');
    let maxBytes = null;
    const started = Date.now();
    while (Date.now() - started < durationMs) {
      const response = await session.send('Performance.getMetrics');
      const used = response.metrics.find(
        (metric) => metric.name === 'JSHeapUsedSize',
      );
      if (used) maxBytes = Math.max(maxBytes ?? 0, used.value);
      await new Promise((resolveDelay) => setTimeout(resolveDelay, 1_000));
    }
    return maxBytes === null
      ? {
          status: 'unavailable',
          reason: 'Chromium did not expose JSHeapUsedSize.',
        }
      : {
          status: 'available',
          maximumBytes: Math.round(maxBytes),
          measurement:
            'maximum sampled JSHeapUsedSize; not total process or GPU memory',
        };
  } catch (error) {
    return {
      status: 'unavailable',
      reason: error instanceof Error ? error.message : String(error),
    };
  }
}

async function measureRun(page, session) {
  const durationMs = runDurationMs;
  const framePromise = page.evaluate(async (targetDurationMs) => {
    const start = performance.now();
    let previous = null;
    const intervalsMs = [];
    const hiddenAtStart = document.hidden;
    let hiddenDuringRun = hiddenAtStart;
    const handleVisibility = () => {
      if (document.hidden) hiddenDuringRun = true;
    };
    document.addEventListener('visibilitychange', handleVisibility);
    const focusedAtStart = document.hasFocus();
    await new Promise((resolveRun) => {
      const step = (now) => {
        if (previous !== null) intervalsMs.push(now - previous);
        previous = now;
        if (now - start < targetDurationMs) requestAnimationFrame(step);
        else resolveRun();
      };
      requestAnimationFrame(step);
    });
    document.removeEventListener('visibilitychange', handleVisibility);
    return {
      intervalsMs,
      observedDurationMs: performance.now() - start,
      hiddenAtStart,
      hiddenDuringRun,
      focusedAtStart,
      focusedAtEnd: document.hasFocus(),
    };
  }, durationMs);
  const heapPromise = sampleHeap(session, durationMs);
  const [frameResult, heap] = await Promise.all([framePromise, heapPromise]);
  const intervals = frameResult.intervalsMs.filter(
    (value) => Number.isFinite(value) && value > 0,
  );
  const sorted = [...intervals].sort((a, b) => a - b);
  const percentile = (fraction) =>
    sorted.length === 0
      ? null
      : sorted[Math.max(0, Math.ceil(fraction * sorted.length) - 1)];
  const totalDurationSeconds = frameResult.observedDurationMs / 1000;
  return {
    sampleCount: intervals.length,
    observedDurationMs: Number(frameResult.observedDurationMs.toFixed(2)),
    framesPerSecond:
      totalDurationSeconds > 0
        ? Number((intervals.length / totalDurationSeconds).toFixed(3))
        : null,
    meanFrameTimeMs:
      intervals.length > 0
        ? Number(
            (
              intervals.reduce((sum, value) => sum + value, 0) /
              intervals.length
            ).toFixed(3),
          )
        : null,
    medianFrameTimeMs: percentile(0.5),
    p95FrameTimeMs: percentile(0.95),
    p99FrameTimeMs: percentile(0.99),
    maximumFrameTimeMs: sorted.length ? sorted.at(-1) : null,
    rawFrameIntervalsMs: intervals.map((value) => Number(value.toFixed(3))),
    focusVisibility: {
      hiddenAtStart: frameResult.hiddenAtStart,
      hiddenDuringRun: frameResult.hiddenDuringRun,
      focusedAtStart: frameResult.focusedAtStart,
      focusedAtEnd: frameResult.focusedAtEnd,
      validForVisibleFocusedBenchmark:
        !frameResult.hiddenAtStart &&
        !frameResult.hiddenDuringRun &&
        frameResult.focusedAtStart &&
        frameResult.focusedAtEnd,
    },
    jsHeap: heap,
  };
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  if (sorted.length === 0) return null;
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2
    ? sorted[middle]
    : (sorted[middle - 1] + sorted[middle]) / 2;
}

async function runWorkload(browser, baseUrl, workload, options) {
  const context = await browser.newContext({ viewport, deviceScaleFactor });
  const page = await context.newPage();
  const session = await context.newCDPSession(page);
  await session.send('Network.enable');
  const networkResponses = { freshContext: [], warmContextReload: [] };
  let networkPhase = 'freshContext';
  session.on('Network.responseReceived', (event) => {
    networkResponses[networkPhase].push({
      status: event.response.status,
      fromDiskCache: event.response.fromDiskCache ?? false,
      fromServiceWorker: event.response.fromServiceWorker ?? false,
      fromPrefetchCache: event.response.fromPrefetchCache ?? false,
      resourceType: event.type,
    });
  });
  await page.addInitScript(() => {
    window.__tvw014NavigationStart = performance.now();
  });
  const errors = [];
  page.on('pageerror', (error) =>
    errors.push(`${error.name}: ${error.message}`),
  );
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });

  const startedFreshAt = new Date().toISOString();
  await page.goto(new URL(workload.route, baseUrl).href, {
    waitUntil: 'domcontentloaded',
  });
  await waitForWorkload(page, workload);
  const freshLoadMs = await loadTimeAfterLayers(page);
  const freshNetworkResponses = [...networkResponses.freshContext];

  const warmStartedAt = new Date().toISOString();
  networkPhase = 'warmContextReload';
  await page.reload({ waitUntil: 'domcontentloaded' });
  await waitForWorkload(page, workload);
  const warmLoadMs = await loadTimeAfterLayers(page);
  const warmNetworkResponses = [...networkResponses.warmContextReload];
  await page.waitForTimeout(warmupMs);
  await configureMode(page, workload);
  const browserMetadata = await readBrowserMetadata(page, browser);
  const assetInventory = await workloadAssets(workload);
  const sceneMetrics = await readSceneMetrics(page);

  let screenshotPath = null;
  if (
    workload.id === 'synthetic-m0' ||
    workload.id === 'combined-fly' ||
    workload.id === 'combined-walk'
  ) {
    const fileName = {
      'synthetic-m0': 'TVW-014-synthetic-startup.png',
      'combined-fly': 'TVW-014-combined-fly.png',
      'combined-walk': 'TVW-014-combined-walk.png',
    }[workload.id];
    const absoluteScreenshotPath = resolve(
      options.screenshotsDirectory,
      fileName,
    );
    await mkdir(dirname(absoluteScreenshotPath), { recursive: true });
    await page.screenshot({ path: absoluteScreenshotPath, fullPage: true });
    screenshotPath = relative(projectRoot, absoluteScreenshotPath).replaceAll(
      sep,
      '/',
    );
  }

  const runs = [];
  for (let runIndex = 0; runIndex < runCount; runIndex += 1) {
    runs.push(await measureRun(page, session));
  }
  await session.detach();
  const allFocusedAndVisible = runs.every(
    (run) => run.focusVisibility.validForVisibleFocusedBenchmark,
  );
  const allIntervals = runs.flatMap((run) => run.rawFrameIntervalsMs);
  const sortedIntervals = [...allIntervals].sort((a, b) => a - b);
  const totalObservedDurationMs = runs.reduce(
    (total, run) => total + run.observedDurationMs,
    0,
  );
  const allPercentile = (fraction) =>
    sortedIntervals.length === 0
      ? null
      : sortedIntervals[
          Math.max(0, Math.ceil(fraction * sortedIntervals.length) - 1)
        ];
  const summary = {
    sampleCount: allIntervals.length,
    observedDurationMs: Number(totalObservedDurationMs.toFixed(2)),
    framesPerSecond:
      totalObservedDurationMs > 0
        ? Number(
            (allIntervals.length / (totalObservedDurationMs / 1000)).toFixed(3),
          )
        : null,
    meanFrameTimeMs:
      allIntervals.length > 0
        ? Number(
            (
              allIntervals.reduce((total, frame) => total + frame, 0) /
              allIntervals.length
            ).toFixed(3),
          )
        : null,
    medianFrameTimeMs: allPercentile(0.5),
    p95FrameTimeMs: allPercentile(0.95),
    p99FrameTimeMs: allPercentile(0.99),
    maximumFrameTimeMs: sortedIntervals.at(-1) ?? null,
    medianRunFps: median(runs.map((run) => run.framesPerSecond)),
    maximumSampledJsHeapBytes:
      runs
        .map((run) => run.jsHeap.maximumBytes)
        .filter(Number.isFinite)
        .reduce((maximum, bytes) => Math.max(maximum, bytes), 0) || null,
  };
  await page.keyboard.press('Escape').catch(() => undefined);
  await context.close();
  return {
    id: workload.id,
    label: workload.label,
    route: workload.route,
    requestedMode: workload.mode,
    loadTiming: {
      definition:
        'navigation start to loaded requested layers and first post-load rendered frame',
      freshContextMs: freshLoadMs,
      freshContextStartedAt: startedFreshAt,
      freshContextNetworkResponses: summarizeNetworkResponses(
        freshNetworkResponses,
      ),
      warmContextReloadMs: warmLoadMs,
      warmContextStartedAt: warmStartedAt,
      warmContextReloadNetworkResponses:
        summarizeNetworkResponses(warmNetworkResponses),
      cacheNote:
        'Cache behavior is measured from Chromium response metadata; reload is called warm-context, and actual disk/service-worker/prefetch hits are reported rather than assumed.',
    },
    browser: browserMetadata,
    viewportCssPixels: viewport,
    drawingBufferPixels: {
      width: browserMetadata.canvasBackingWidth,
      height: browserMetadata.canvasBackingHeight,
    },
    devicePixelRatio: browserMetadata.devicePixelRatio,
    scenePose: sceneMetrics.cameraPose,
    rendererMetricsAfterRenderedFrame: {
      drawCalls: sceneMetrics.drawCalls,
      renderedTriangles: sceneMetrics.triangles,
      activeGeometryObjects: sceneMetrics.geometryCount,
      activeTextureObjects: sceneMetrics.textureCount,
      note: 'Three.js renderer.info.memory geometry/texture values are object counts, not byte totals.',
    },
    assetInventory,
    warmupMs,
    timedRunDurationTargetMs: runDurationMs,
    runCount,
    runs,
    aggregate: summary,
    benchmarkValid: allFocusedAndVisible && errors.length === 0,
    invalidatingConditions: [
      ...(!allFocusedAndVisible
        ? ['page hidden or not focused during one or more timed runs']
        : []),
      ...errors.map((error) => `browser console/page error: ${error}`),
      ...(browserMetadata.isSoftwareRenderer
        ? ['software WebGL rendering detected']
        : []),
    ],
    consoleAndPageErrors: errors,
    screenshot: screenshotPath,
  };
}

function summarizeNetworkResponses(responses) {
  return {
    responseCount: responses.length,
    diskCacheHits: responses.filter((response) => response.fromDiskCache)
      .length,
    serviceWorkerHits: responses.filter(
      (response) => response.fromServiceWorker,
    ).length,
    prefetchCacheHits: responses.filter(
      (response) => response.fromPrefetchCache,
    ).length,
    status304Count: responses.filter((response) => response.status === 304)
      .length,
  };
}

function formatSummary(report) {
  const rows = report.workloads.map((workload) => {
    const summary = workload.aggregate;
    return `| ${workload.label} | ${summary.framesPerSecond?.toFixed(2) ?? 'n/a'} | ${workload.loadTiming.freshContextMs?.toFixed(0) ?? 'n/a'} | ${workload.loadTiming.warmContextReloadMs?.toFixed(0) ?? 'n/a'} | ${summary.meanFrameTimeMs?.toFixed(2) ?? 'n/a'} | ${summary.medianFrameTimeMs?.toFixed(2) ?? 'n/a'} | ${summary.p95FrameTimeMs?.toFixed(2) ?? 'n/a'} | ${summary.p99FrameTimeMs?.toFixed(2) ?? 'n/a'} | ${summary.maximumFrameTimeMs?.toFixed(2) ?? 'n/a'} | ${workload.rendererMetricsAfterRenderedFrame.drawCalls ?? 'n/a'} | ${workload.rendererMetricsAfterRenderedFrame.renderedTriangles ?? 'n/a'} | ${workload.rendererMetricsAfterRenderedFrame.activeGeometryObjects ?? 'n/a'} | ${workload.rendererMetricsAfterRenderedFrame.activeTextureObjects ?? 'n/a'} | ${summary.maximumSampledJsHeapBytes?.toLocaleString() ?? 'unavailable'} | ${workload.assetInventory.totalBytes} |`;
  });
  const invalid = report.workloads
    .filter((workload) => !workload.benchmarkValid)
    .map(
      (workload) =>
        `- **${workload.label}:** ${workload.invalidatingConditions.join('; ')}`,
    );
  return [
    '# TVW-014 local browser benchmark',
    '',
    `- Generated: ${report.generatedAtUtc}`,
    `- Commit: ${report.buildIdentity.commit}`,
    `- Build output SHA-256: ${report.buildIdentity.distSha256}`,
    `- Chromium: ${report.environment.browserVersion}`,
    `- OS: ${report.environment.operatingSystem}`,
    `- WebGL renderer: ${report.environment.renderer} (${report.environment.vendor})`,
    `- Viewport: ${viewport.width} × ${viewport.height} CSS px, DPR ${report.workloads[0]?.devicePixelRatio ?? 'n/a'}`,
    `- Method: ${warmupMs / 1000}s warm-up; ${runCount} × ${runDurationMs / 1000}s visible/focused frame-interval runs per workload. FPS is samples divided by observed elapsed duration. Load times are fresh-context navigation and warm-context reload to requested layers plus a post-load rendered frame.`,
    '',
    '| Workload | FPS | Fresh load ms | Warm reload ms | Mean frame ms | Median ms | p95 ms | p99 ms | Max ms | Draw calls | Triangles | Geometries | Textures | Max JS heap bytes | Local asset bytes |',
    '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |',
    ...rows,
    '',
    `JavaScript heap maximum: ${report.environment.jsHeapMeasurement}. The script samples Chromium ` +
      '`JSHeapUsedSize`; it does not represent total process or GPU memory. Renderer geometry/texture counters are active object counts, not bytes. Frame cadence is not GPU execution time. No performance threshold is applied.',
    '',
    ...(invalid.length
      ? ['## Invalidating conditions', '', ...invalid, '']
      : []),
    'Raw frame intervals, per-run focus/visibility state, workload poses, package identities and byte inventories are in the companion JSON file.',
    '',
  ].join('\n');
}

async function main() {
  const options = parseArguments(process.argv.slice(2));
  if (!(await stat(resolve(projectRoot, 'dist')).catch(() => null))) {
    throw new Error('Missing dist/; run npm run build before the benchmark.');
  }
  const port = await freeLocalPort();
  const preview = await startPreview(port);
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const baseContext = await browser.newContext({
      viewport,
      deviceScaleFactor,
    });
    const basePage = await baseContext.newPage();
    await basePage.goto(
      new URL('/?world=torquay-poc-001&buildings=1&roads=1', preview.baseUrl)
        .href,
      {
        waitUntil: 'domcontentloaded',
      },
    );
    await waitForWorkload(basePage, {
      route: '/?world=torquay-poc-001&buildings=1&roads=1',
    });
    const environment = await readBrowserMetadata(basePage, browser);
    await baseContext.close();

    const workloadsResult = [];
    for (const workload of workloads) {
      workloadsResult.push(
        await runWorkload(browser, preview.baseUrl, workload, options),
      );
    }
    const distIdentity = await directoryIdentity(resolve(projectRoot, 'dist'));
    const report = {
      schemaVersion: 1,
      generatedAtUtc: new Date().toISOString(),
      methodology: {
        viewportCssPixels: viewport,
        deviceScaleFactor,
        warmupMs,
        timedRunDurationTargetMs: runDurationMs,
        runCount,
        rawFrameSamplesIncluded: true,
        requestedWorkloads: workloads.map(({ id, route, mode }) => ({
          id,
          route,
          mode,
        })),
        posePolicy:
          'Route-defined deterministic spawn; no test-only camera hook or injected navigation mutation was used.',
        sampleDefinition:
          'Inter-requestAnimationFrame intervals measured with performance.now() in a visible, focused local Chromium page.',
        fpsDefinition:
          'frame interval sample count divided by observed elapsed run duration in seconds',
        noThreshold: true,
      },
      buildIdentity: {
        commit: gitValue('rev-parse', 'HEAD'),
        branch: gitValue('branch', '--show-current'),
        packageLockSha256: sha256(
          await readFile(resolve(projectRoot, 'package-lock.json')),
        ),
        distFileCount: distIdentity.files,
        distSha256: distIdentity.sha256,
        previewBaseUrl: preview.baseUrl,
      },
      environment: {
        ...environment,
        jsHeapMeasurement:
          'Chromium CDP Performance.getMetrics JSHeapUsedSize sampled approximately once per second; per-run maximum is reported when supported.',
      },
      caveats: [
        'No performance pass/fail threshold is imposed; these measurements describe this browser, machine, renderer, viewport and build only.',
        'Browser hidden-page throttling or loss of focus invalidates a run and is recorded per run.',
        'Software WebGL is flagged and must not be presented as hardware performance.',
        'Renderer.info memory values count geometry and texture objects; asset byte totals are from exact local package files and counted once per workload by path and hash.',
        'The browser benchmark does not measure GPU execution time or total process/GPU memory.',
        'The real AOI remains selected_pending_coverage / not_checked; mapped feature counts do not establish completeness.',
      ],
      workloads: workloadsResult,
    };
    const firstReal = workloadsResult.find(
      (result) => result.id === 'terrain-only',
    );
    if (firstReal) {
      report.environment = {
        ...report.environment,
        renderer: firstReal.browser.renderer,
        vendor: firstReal.browser.vendor,
        isSoftwareRenderer: firstReal.browser.isSoftwareRenderer,
      };
    }
    const heapValues = workloadsResult.flatMap((result) =>
      result.runs
        .map((run) => run.jsHeap.maximumBytes)
        .filter((value) => Number.isFinite(value)),
    );
    report.environment.jsHeapMaximumBytes =
      heapValues.length > 0 ? Math.max(...heapValues) : null;
    if (heapValues.length === 0) {
      report.environment.jsHeapMeasurement =
        'unavailable: Chromium CDP did not expose JSHeapUsedSize';
    }
    await mkdir(options.outputDirectory, { recursive: true });
    const jsonPath = resolve(options.outputDirectory, 'TVW-014-benchmark.json');
    const markdownPath = resolve(
      options.outputDirectory,
      'TVW-014-benchmark.md',
    );
    await writeFile(jsonPath, `${JSON.stringify(report, null, 2)}\n`);
    await writeFile(markdownPath, formatSummary(report));
    console.log(`Benchmark JSON: ${jsonPath}`);
    console.log(`Benchmark summary: ${markdownPath}`);
    for (const workload of report.workloads) {
      console.log(
        `${workload.id}: ${workload.aggregate.framesPerSecond?.toFixed(2) ?? 'n/a'} FPS; ` +
          `${workload.aggregate.p95FrameTimeMs?.toFixed(2) ?? 'n/a'} ms p95; ` +
          `valid=${workload.benchmarkValid}`,
      );
    }
    const invalidWorkloads = report.workloads.filter(
      (workload) => !workload.benchmarkValid,
    );
    if (invalidWorkloads.length > 0) {
      throw new Error(
        `Benchmark completed with invalid workloads: ${invalidWorkloads.map((item) => item.id).join(', ')}. See the generated report.`,
      );
    }
  } finally {
    await browser?.close();
    preview.child.kill();
  }
}

if (
  process.argv[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.stack : error);
    process.exitCode = 1;
  });
}
