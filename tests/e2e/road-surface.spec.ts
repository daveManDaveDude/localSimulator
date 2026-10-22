import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { relative, resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

type TerrainManifest = {
  origin: { elevationM: number };
  extentM: { width: number; depth: number };
  heightfield: { columns: number; rows: number; spacingM: number };
};

type RoadSurfaceContext = {
  id: string;
  anchorLocalXZ: [number, number];
  tangentXZ: [number, number];
  wayIds: number[];
  buildingIds?: string[];
  stationM?: number;
};

type Pose = {
  x: number;
  y: number;
  z: number;
  bearingDegrees: number;
  pitchDegrees: number;
};

const releaseId =
  '616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a';
const releaseRoot = resolve(
  process.cwd(),
  'public/worlds/torquay-poc-001-2km/releases',
  releaseId,
);
const previewDirectory = resolve(
  process.cwd(),
  'public/worlds/torquay-road-surface-preview',
);
const evidenceDirectory = resolve(
  process.cwd(),
  'docs/milestones/artifacts/Road-surface-treatment/correction-1/run-5',
);
const screenshotDirectory = resolve(evidenceDirectory, 'screenshots');

function terrainSampler(
  manifest: TerrainManifest,
  bytes: Buffer,
): (x: number, z: number) => { localM: number; orthometricM: number } {
  const { columns, rows, spacingM } = manifest.heightfield;
  if (bytes.byteLength !== columns * rows * Float32Array.BYTES_PER_ELEMENT)
    throw new Error('Terrain binary does not match the selected grid.');
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const halfWidth = manifest.extentM.width / 2;
  const halfDepth = manifest.extentM.depth / 2;
  return (x, z) => {
    const gridX = (x + halfWidth) / spacingM;
    const gridZ = (z + halfDepth) / spacingM;
    if (gridX < 0 || gridX > columns - 1 || gridZ < 0 || gridZ > rows - 1)
      throw new Error('Camera target is outside the current terrain grid.');
    const column = Math.min(Math.floor(gridX), columns - 2);
    const row = Math.min(Math.floor(gridZ), rows - 2);
    const u = gridX - column;
    const v = gridZ - row;
    const sample = (sampleRow: number, sampleColumn: number): number =>
      view.getFloat32((sampleRow * columns + sampleColumn) * 4, true);
    const a = sample(row, column);
    const b = sample(row, column + 1);
    const c = sample(row + 1, column);
    const d = sample(row + 1, column + 1);
    const localM =
      u + v <= 1
        ? a + (b - a) * u + (c - a) * v
        : d + (c - d) * (1 - u) + (b - d) * (1 - v);
    return { localM, orthometricM: localM + manifest.origin.elevationM };
  };
}

async function readObject<T>(path: string): Promise<T> {
  return JSON.parse(await readFile(path, 'utf8')) as T;
}

async function cameraPose(page: Page): Promise<Pose> {
  return page.getByTestId('camera-position').evaluate((element) => {
    const position = element as HTMLOutputElement;
    const orientation = document.querySelector<HTMLOutputElement>(
      '[data-testid="camera-orientation"]',
    );
    if (!orientation)
      throw new Error('Camera orientation telemetry is missing.');
    return {
      x: Number(position.dataset.x),
      y: Number(position.dataset.y),
      z: Number(position.dataset.z),
      bearingDegrees: Number(orientation.dataset.bearingDegrees),
      pitchDegrees: Number(orientation.dataset.pitchDegrees),
    };
  });
}

async function setQaPose(page: Page, pose: Pose): Promise<void> {
  await page.evaluate((nextPose) => {
    const qa = window.__torquayAlignmentQa;
    if (!qa)
      throw new Error('Development-only alignment camera hook is missing.');
    qa.setPose(nextPose);
  }, pose);
  await expect
    .poll(async () => {
      const current = await cameraPose(page);
      return Math.hypot(current.x - pose.x, current.z - pose.z);
    })
    .toBeLessThan(0.02);
}

async function runtimeInfo(page: Page) {
  return page.evaluate(() => {
    const canvas = document.querySelector<HTMLCanvasElement>(
      'canvas.viewer-canvas',
    );
    if (!canvas) throw new Error('The WebGL canvas is missing.');
    const gl = canvas.getContext('webgl2') ?? canvas.getContext('webgl');
    const extension = gl?.getExtension('WEBGL_debug_renderer_info');
    return {
      renderer: gl
        ? extension
          ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL)
          : gl.getParameter(gl.RENDERER)
        : 'WebGL unavailable',
      canvas: {
        cssWidth: canvas.clientWidth,
        cssHeight: canvas.clientHeight,
        width: canvas.width,
        height: canvas.height,
      },
      userAgent: navigator.userAgent,
      viewport: {
        width: innerWidth,
        height: innerHeight,
        devicePixelRatio,
      },
    };
  });
}

const contextIds = [
  'parkfield-severe',
  'pennys-teignmouth',
  'arthington-control',
] as const;

test('captures the labelled current-release road-surface comparison and walk clearance', async ({
  page,
  browserName,
}, testInfo) => {
  await mkdir(screenshotDirectory, { recursive: true });
  const requests: string[] = [];
  const failedRequests: { url: string; failure: string | null }[] = [];
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  page.on('request', (request) => requests.push(request.url()));
  page.on('requestfailed', (request) =>
    failedRequests.push({
      url: request.url(),
      failure: request.failure()?.errorText ?? null,
    }),
  );
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => pageErrors.push(error.message));

  const ready = await readObject<{ releaseId: string }>(
    resolve(process.cwd(), 'public/worlds/torquay-poc-001-2km/ready.json'),
  );
  expect(ready.releaseId).toBe(releaseId);
  const manifest = await readObject<TerrainManifest>(
    resolve(releaseRoot, 'manifest.json'),
  );
  const qa = await readObject<{
    source: Record<string, string>;
    derivative: { sha256: string; byteLength: number };
    gridTreatment: Record<string, unknown>;
    profiles: { ways: Record<string, unknown>[] };
    browserContexts: RoadSurfaceContext[];
  }>(resolve(previewDirectory, 'qa.json'));
  const baselineBytes = await readFile(resolve(releaseRoot, 'heightfield.f32'));
  const previewBytes = await readFile(
    resolve(previewDirectory, 'heightfield.f32'),
  );
  const baselineAt = terrainSampler(manifest, baselineBytes);
  const previewAt = terrainSampler(manifest, previewBytes);
  const byId = new Map(
    qa.browserContexts.map((context) => [context.id, context]),
  );
  const mandatoryContexts = contextIds.map((id) => {
    const context = byId.get(id);
    if (!context)
      throw new Error(`Required QA camera context ${id} is missing.`);
    return context;
  });
  const parkfield = byId.get('parkfield-severe')!;
  const lymingtonContext = byId.get('user-map-context-2')!;
  const cricketfield = byId.get('cricketfield-junction')!;
  const overviewContext: RoadSurfaceContext = {
    id: 'parkfield-lymington-overview',
    anchorLocalXZ: [
      (parkfield.anchorLocalXZ[0] + lymingtonContext.anchorLocalXZ[0]) / 2,
      (parkfield.anchorLocalXZ[1] + lymingtonContext.anchorLocalXZ[1]) / 2,
    ],
    tangentXZ: lymingtonContext.tangentXZ,
    wayIds: [30480989, 1363931058],
  };
  const addedGradientContext = byId.get('maximum-added-gradient');
  if (!addedGradientContext)
    throw new Error('Required maximum added-gradient QA context is missing.');
  const newtonContext = byId.get('newton-high-fill');
  if (!newtonContext)
    throw new Error('Required Newton maximum-fill QA context is missing.');
  const harmfulGradientContexts = qa.browserContexts
    .filter((context) => context.id.startsWith('harm-gradient-region-'))
    .slice(0, 2);
  await page.goto('/');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-load-state',
    'loaded',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-road-surface-state',
    'off',
  );
  expect(
    requests.some((url) => url.includes('torquay-road-surface-preview')),
  ).toBe(false);
  await expect(page.getByTestId('building-status')).toHaveAttribute(
    'data-state',
    'loaded',
  );
  await expect(page.getByTestId('road-status')).toHaveAttribute(
    'data-state',
    'loaded',
  );
  await page.getByTestId('start-button').click();
  await expect
    .poll(() => page.evaluate(() => document.pointerLockElement?.tagName))
    .toBe('CANVAS');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-renderer-ready',
    'true',
  );

  const screenshotRecords: Record<string, unknown>[] = [];
  const capture = async (
    side: 'baseline' | 'preview',
    context: RoadSurfaceContext,
    view: { id: string; offsetM: number; clearanceM: number; pitch: number },
    sample: typeof baselineAt,
  ): Promise<void> => {
    const [targetX, targetZ] = context.anchorLocalXZ;
    const [tangentX, tangentZ] = context.tangentXZ;
    const bearingDegrees =
      ((Math.atan2(tangentX, -tangentZ) * 180) / Math.PI + 360) % 360;
    const insideTerrain = (x: number, z: number): boolean =>
      Math.abs(x) <= manifest.extentM.width / 2 &&
      Math.abs(z) <= manifest.extentM.depth / 2;
    let appliedOffsetM = view.offsetM;
    let x = targetX - tangentX * appliedOffsetM;
    let z = targetZ - tangentZ * appliedOffsetM;
    if (!insideTerrain(x, z)) {
      appliedOffsetM = -view.offsetM;
      x = targetX - tangentX * appliedOffsetM;
      z = targetZ - tangentZ * appliedOffsetM;
    }
    if (!insideTerrain(x, z)) {
      appliedOffsetM = 0;
      x = targetX;
      z = targetZ;
    }
    const ground = sample(x, z);
    const pose = {
      x,
      y: ground.localM + view.clearanceM,
      z,
      bearingDegrees,
      pitchDegrees: view.pitch,
    };
    await setQaPose(page, pose);
    await expect
      .poll(async () =>
        Number(
          await page
            .getByTestId('ground-height')
            .getAttribute('data-height-meters'),
        ),
      )
      .toBeCloseTo(ground.localM, 3);
    const actual = await cameraPose(page);
    const sampledGroundLocalM = Number(
      await page
        .getByTestId('ground-height')
        .getAttribute('data-height-meters'),
    );
    const sampledGroundOrthometricM = Number(
      await page
        .getByTestId('ground-height')
        .getAttribute('data-orthometric-meters'),
    );
    expect(sampledGroundOrthometricM).toBeCloseTo(ground.orthometricM, 3);
    expect(actual.y - sampledGroundLocalM).toBeCloseTo(view.clearanceM, 2);
    await page.waitForTimeout(120);

    const filename = `${side}-${context.id}-${view.id}.png`;
    const screenshotPath = resolve(screenshotDirectory, filename);
    await page.screenshot({ path: screenshotPath, animations: 'disabled' });
    screenshotRecords.push({
      side,
      contextId: context.id,
      sourceWayIds: context.wayIds,
      sourceBuildingIds: context.buildingIds ?? [],
      stationM: context.stationM,
      targetLocalXZMetres: context.anchorLocalXZ,
      tangentLocalXZ: context.tangentXZ,
      view: view.id,
      camera: actual,
      cameraYDatum:
        'package-local visual grid metres; orthometric telemetry is recorded separately',
      sampledGroundLocalM,
      sampledGroundOrthometricM,
      requestedCameraOffsetM: view.offsetM,
      appliedCameraOffsetM: appliedOffsetM,
      requestedClearanceAboveDisplayedTerrainM: view.clearanceM,
      measuredClearanceAboveDisplayedTerrainM: actual.y - sampledGroundLocalM,
      screenshot: relative(process.cwd(), screenshotPath).replaceAll('\\', '/'),
      screenshotSha256: createHash('sha256')
        .update(await readFile(screenshotPath))
        .digest('hex'),
    });
  };

  const primaryViews = [
    { id: 'overhead', offsetM: 0, clearanceM: 110, pitch: -82 },
    { id: 'low-oblique', offsetM: 45, clearanceM: 15, pitch: -24 },
  ] as const;
  for (const context of mandatoryContexts) {
    for (const view of primaryViews)
      await capture('baseline', context, view, baselineAt);
  }
  await capture(
    'baseline',
    overviewContext,
    { id: 'overhead', offsetM: 0, clearanceM: 220, pitch: -84 },
    baselineAt,
  );
  await capture(
    'baseline',
    cricketfield,
    { id: 'junction-oblique', offsetM: 32, clearanceM: 36, pitch: -36 },
    baselineAt,
  );
  await capture(
    'baseline',
    addedGradientContext,
    { id: 'low-oblique', offsetM: 22, clearanceM: 14, pitch: -25 },
    baselineAt,
  );
  for (const context of harmfulGradientContexts)
    await capture(
      'baseline',
      context,
      {
        id: 'harm-gradient-low-oblique',
        offsetM: 22,
        clearanceM: 14,
        pitch: -25,
      },
      baselineAt,
    );
  await capture(
    'baseline',
    newtonContext,
    { id: 'maximum-fill-overhead', offsetM: 0, clearanceM: 48, pitch: -78 },
    baselineAt,
  );
  await capture(
    'baseline',
    newtonContext,
    { id: 'maximum-fill-low-oblique', offsetM: 18, clearanceM: 16, pitch: -28 },
    baselineAt,
  );

  await page.evaluate(() => {
    window.history.pushState({}, '', '/?roadSurface=preview');
    window.dispatchEvent(new PopStateEvent('popstate'));
  });
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-road-surface-state',
    'applied',
  );
  await expect(page.getByTestId('road-surface-preview-notice')).toHaveText(
    'Road-surface preview · approximate road grading; surrounding ground adjusted.',
  );
  await expect(
    page.getByTestId('road-surface-preview-source-note'),
  ).toContainText('not EA source data or surveyed road elevations');
  await expect(page.getByTestId('building-status')).toHaveAttribute(
    'data-state',
    'loaded',
  );
  await expect(page.getByTestId('road-status')).toHaveAttribute(
    'data-state',
    'loaded',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-renderer-ready',
    'true',
  );
  // Replacing the world creates a fresh controller and releases pointer lock.
  // Reacquire it with a real input event before the preview captures.
  await page
    .locator('canvas.viewer-canvas')
    .click({ position: { x: 720, y: 480 } });
  await expect
    .poll(() => page.evaluate(() => document.pointerLockElement?.tagName))
    .toBe('CANVAS');

  for (const context of mandatoryContexts) {
    for (const view of primaryViews)
      await capture('preview', context, view, previewAt);
  }
  await capture(
    'preview',
    overviewContext,
    { id: 'overhead', offsetM: 0, clearanceM: 220, pitch: -84 },
    previewAt,
  );
  await capture(
    'preview',
    cricketfield,
    { id: 'junction-oblique', offsetM: 32, clearanceM: 36, pitch: -36 },
    previewAt,
  );
  await capture(
    'preview',
    addedGradientContext,
    { id: 'low-oblique', offsetM: 22, clearanceM: 14, pitch: -25 },
    previewAt,
  );
  for (const context of harmfulGradientContexts)
    await capture(
      'preview',
      context,
      {
        id: 'harm-gradient-low-oblique',
        offsetM: 22,
        clearanceM: 14,
        pitch: -25,
      },
      previewAt,
    );
  await capture(
    'preview',
    newtonContext,
    { id: 'maximum-fill-overhead', offsetM: 0, clearanceM: 48, pitch: -78 },
    previewAt,
  );
  await capture(
    'preview',
    newtonContext,
    { id: 'maximum-fill-low-oblique', offsetM: 18, clearanceM: 16, pitch: -28 },
    previewAt,
  );
  expect(screenshotRecords).toHaveLength(
    22 + 2 * harmfulGradientContexts.length,
  );

  await page.setViewportSize({ width: 1280, height: 800 });
  await expect
    .poll(() =>
      page
        .locator('canvas.viewer-canvas')
        .evaluate((canvas) => canvas.clientWidth),
    )
    .toBe(1280);
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.keyboard.press('r');
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'fly',
  );

  const walkChecks: Record<string, unknown>[] = [];
  for (const context of [mandatoryContexts[0]!, mandatoryContexts[1]!]) {
    const width = context.id === 'parkfield-severe' ? 6 : 7;
    const sideVector = [-context.tangentXZ[1], context.tangentXZ[0]] as const;
    const targets = [
      {
        id: 'road-centre',
        x: context.anchorLocalXZ[0],
        z: context.anchorLocalXZ[1],
      },
      {
        id: 'transition-shoulder',
        x: context.anchorLocalXZ[0] + sideVector[0] * width,
        z: context.anchorLocalXZ[1] + sideVector[1] * width,
      },
    ];
    for (const target of targets) {
      if (
        (await page
          .getByTestId('navigation-mode')
          .getAttribute('data-mode')) === 'walk'
      )
        await page.keyboard.press('f');
      const ground = previewAt(target.x, target.z);
      await setQaPose(page, {
        x: target.x,
        y: ground.localM + 1.7,
        z: target.z,
        bearingDegrees: 0,
        pitchDegrees: 0,
      });
      await page.keyboard.press('f');
      await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
        'data-mode',
        'walk',
      );
      await page.waitForTimeout(180);
      const clearance = Number(
        await page
          .getByTestId('eye-clearance')
          .getAttribute('data-clearance-meters'),
      );
      expect(clearance).toBeGreaterThanOrEqual(1.65);
      expect(clearance).toBeLessThanOrEqual(1.75);
      walkChecks.push({
        contextId: context.id,
        point: target.id,
        localXZ: [target.x, target.z],
        displayedGroundM: Number(
          await page
            .getByTestId('ground-height')
            .getAttribute('data-height-meters'),
        ),
        eyeClearanceM: clearance,
      });
      await page.keyboard.press('f');
    }
  }

  const origin = new URL(page.url()).origin;
  const externalRequests = requests.filter(
    (url) => new URL(url).origin !== origin,
  );
  expect(externalRequests).toEqual([]);
  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(failedRequests).toEqual([]);
  expect(
    requests.some((url) => url.includes('torquay-road-surface-preview')),
  ).toBe(true);
  const runtime = await runtimeInfo(page);
  const report = {
    issue: 'Road-surface treatment preview',
    route: '/?roadSurface=preview',
    releaseId,
    sceneProfile: 'current_2km',
    sourceHashes: qa.source,
    baselineHeightfieldSha256: createHash('sha256')
      .update(baselineBytes)
      .digest('hex'),
    derivativeHeightfieldSha256: qa.derivative.sha256,
    derivativeByteLength: qa.derivative.byteLength,
    derivativeLoadMilliseconds: Number(
      await page
        .locator('.viewer-shell')
        .getAttribute('data-road-surface-load-ms'),
    ),
    gradientQa: qa.gridTreatment,
    profileComparisons: qa.profiles.ways,
    browserName,
    browserVersion: page.context().browser()?.version(),
    playwrightProject: testInfo.project.name,
    runtime,
    screenshots: screenshotRecords,
    walkChecks,
    requestedUrls: [...new Set(requests)],
    externalRequests,
    failedRequests,
    consoleErrors,
    pageErrors,
    notes: [
      'Screenshots are from the loaded Chromium scenes after Start; camera positions are set by the existing development-only alignment QA camera hook.',
      'Each connected candidate region meeting the added-gradient fallback heuristic has a registered before/after low-oblique view, keyed by source way IDs and local bounds in browserContexts.',
      'Camera Y and clearance use package-local display-grid metres; orthometric ground telemetry is recorded independently.',
      'Screenshot contexts are map-derived local coordinates and source centerlines, not Google imagery pixel matches.',
      'The two highest candidate added-gradient fallback regions receive matched Chromium views; registered per-region terrain and footing sections numerically cover every fallback region.',
      'Source heightfield, road centerlines and configured widths are unchanged; terrain treatment is an ignored local visual derivative.',
      'The EA preferred OSTN15 operation grid remains unavailable; the recorded conversion operation reports 2 m accuracy.',
    ],
  };
  await writeFile(
    resolve(evidenceDirectory, 'browser-evidence.json'),
    `${JSON.stringify(report, null, 2)}\n`,
    'utf8',
  );
});

test('preview load failures keep the validated source terrain', async ({
  page,
}) => {
  const fallbackCases: { id: string; install: () => Promise<void> }[] = [];
  const requests: string[] = [];
  page.on('request', (request) => requests.push(request.url()));

  fallbackCases.push({
    id: 'missing',
    install: async () => {
      await page.route(
        '**/torquay-road-surface-preview/manifest.json',
        (route) => route.fulfill({ status: 404, body: 'missing derivative' }),
      );
    },
  });
  fallbackCases.push({
    id: 'corrupt',
    install: async () => {
      await page.route(
        '**/torquay-road-surface-preview/heightfield.f32',
        async (route) => {
          const response = await route.fetch();
          const bytes = await response.body();
          bytes[100]! ^= 1;
          await route.fulfill({ response, body: bytes });
        },
      );
    },
  });
  fallbackCases.push({
    id: 'stale',
    install: async () => {
      await page.route(
        '**/torquay-road-surface-preview/manifest.json',
        async (route) => {
          const response = await route.fetch();
          const value = (await response.json()) as {
            source: { readySha256: string };
          };
          value.source.readySha256 = '0'.repeat(64);
          await route.fulfill({ json: value });
        },
      );
    },
  });

  for (const testCase of fallbackCases) {
    await testCase.install();
    await page.goto('/?roadSurface=preview');
    await expect(page.locator('.viewer-shell')).toHaveAttribute(
      'data-load-state',
      'loaded',
    );
    await expect(page.locator('.viewer-shell')).toHaveAttribute(
      'data-road-surface-state',
      'fallback',
    );
    await expect(page.getByTestId('road-surface-preview-notice')).toHaveText(
      'Road-surface preview unavailable; showing source terrain.',
    );
    await expect(page.getByTestId('world-source-mode')).toHaveText(
      'LOCAL HEIGHTFIELD · EPSG:27700',
    );
    expect(
      requests.filter((url) => url.includes('torquay-road-surface-preview')),
    ).toContain(
      `http://127.0.0.1:4213/worlds/torquay-road-surface-preview/manifest.json`,
    );
    await page.unrouteAll({ behavior: 'wait' });
  }
});

test('synthetic and historical profiles ignore the preview parameter; cancellation cannot install stale preview state', async ({
  page,
}) => {
  const requests: string[] = [];
  page.on('request', (request) => requests.push(request.url()));
  await page.goto('/?world=synthetic&roadSurface=preview');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-load-state',
    'loaded',
  );
  expect(
    requests.some((url) => url.includes('torquay-road-surface-preview')),
  ).toBe(false);
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-road-surface-state',
    'off',
  );

  requests.length = 0;
  await page.goto('/?world=torquay-poc-001&roadSurface=preview');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-load-state',
    'loaded',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-scene-profile',
    'historical_1km',
  );
  expect(
    requests.some((url) => url.includes('torquay-road-surface-preview')),
  ).toBe(false);
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-road-surface-state',
    'off',
  );

  let releaseStalled: (() => void) | undefined;
  let requestStarted: (() => void) | undefined;
  const stalled = new Promise<void>((resolveStalled) => {
    releaseStalled = resolveStalled;
  });
  const started = new Promise<void>((resolveStarted) => {
    requestStarted = resolveStarted;
  });
  await page.route(
    '**/torquay-road-surface-preview/heightfield.f32',
    async (route) => {
      requestStarted?.();
      const response = await route.fetch();
      await stalled;
      try {
        await route.fulfill({ response });
      } catch {
        // The browser cancels the pending derivative request when the scene is replaced.
      }
    },
  );
  await page.evaluate(() => {
    window.history.pushState({}, '', '/?roadSurface=preview');
    window.dispatchEvent(new PopStateEvent('popstate'));
  });
  await started;
  await page.evaluate(() => {
    window.history.pushState({}, '', '/?world=synthetic');
    window.dispatchEvent(new PopStateEvent('popstate'));
  });
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-scene-profile',
    '',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-load-state',
    'loaded',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-road-surface-state',
    'off',
  );
  releaseStalled?.();
  await page.waitForTimeout(120);
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-road-surface-state',
    'off',
  );
});

test('the direct preview route validates its current-release derivative', async ({
  page,
}) => {
  const requests: string[] = [];
  page.on('request', (request) => requests.push(request.url()));
  await page.goto('/?roadSurface=preview');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-load-state',
    'loaded',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-road-surface-state',
    'applied',
  );
  await expect(page.getByTestId('road-surface-preview-notice')).toHaveText(
    'Road-surface preview · approximate road grading; surrounding ground adjusted.',
  );
  expect(
    requests
      .filter((url) => url.includes('torquay-road-surface-preview'))
      .map((url) => new URL(url).pathname)
      .sort(),
  ).toEqual(
    [
      '/worlds/torquay-road-surface-preview/manifest.json',
      '/worlds/torquay-road-surface-preview/heightfield.f32',
      '/worlds/torquay-road-surface-preview/qa.json',
    ].sort(),
  );
  expect(
    Number(
      await page
        .locator('.viewer-shell')
        .getAttribute('data-road-surface-load-ms'),
    ),
  ).toBeGreaterThan(0);
});

test('records descriptive preview geometry and frame pacing', async ({
  page,
  browserName,
}) => {
  await page.goto('/?roadSurface=preview');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-load-state',
    'loaded',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-road-surface-state',
    'applied',
  );
  await page.getByTestId('start-button').click();
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-renderer-ready',
    'true',
  );

  const renderObservation = await page.evaluate(async () => {
    const shell = document.querySelector<HTMLElement>('.viewer-shell');
    const canvas = document.querySelector<HTMLCanvasElement>(
      'canvas.viewer-canvas',
    );
    const fpsOutput = document.querySelector<HTMLOutputElement>(
      '[data-testid="frames-per-second"]',
    );
    if (!shell || !canvas || !fpsOutput)
      throw new Error('Preview render telemetry is missing.');

    const frameIntervalsMs = await new Promise<number[]>((resolveFrames) => {
      const intervals: number[] = [];
      let previous = 0;
      const sample = (timestamp: number) => {
        if (previous > 0) intervals.push(timestamp - previous);
        previous = timestamp;
        if (intervals.length >= 179) resolveFrames(intervals);
        else requestAnimationFrame(sample);
      };
      requestAnimationFrame(sample);
    });
    const orderedIntervals = [...frameIntervalsMs].sort((a, b) => a - b);
    const percentile = (fraction: number) =>
      orderedIntervals[
        Math.min(
          orderedIntervals.length - 1,
          Math.floor(orderedIntervals.length * fraction),
        )
      ];
    return {
      rendererCounters: {
        drawCalls: Number(shell.dataset.drawCalls),
        triangles: Number(shell.dataset.triangles),
        geometries: Number(shell.dataset.geometryCount),
        textures: Number(shell.dataset.textureCount),
      },
      rendererReportedFps: Number(fpsOutput.dataset.fps),
      frameIntervals: {
        sampleCount: frameIntervalsMs.length,
        medianMs: percentile(0.5),
        p95Ms: percentile(0.95),
        maximumMs: orderedIntervals.at(-1),
        interpretation:
          'descriptive requestAnimationFrame pacing in this headless Chromium run; not a performance benchmark or user-device FPS claim',
      },
      canvas: {
        cssWidth: canvas.clientWidth,
        cssHeight: canvas.clientHeight,
        width: canvas.width,
        height: canvas.height,
      },
      viewport: {
        width: innerWidth,
        height: innerHeight,
        devicePixelRatio,
      },
      userAgent: navigator.userAgent,
    };
  });
  await mkdir(evidenceDirectory, { recursive: true });
  await writeFile(
    resolve(evidenceDirectory, 'runtime-observation.json'),
    JSON.stringify(
      {
        issue: 'Road-surface treatment preview',
        route: '/?roadSurface=preview',
        browserName,
        sceneProfile: 'current_2km',
        runtime: await runtimeInfo(page),
        ...renderObservation,
      },
      null,
      2,
    ),
  );
});
