import { expect, test } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const screenshotDir = resolve('docs/milestones/screenshots');
const overviewScreenshot = resolve(screenshotDir, 'Torquay-2km-overview.png');
const outerScreenshot = resolve(screenshotDir, 'Torquay-2km-outer-annulus.png');
const evidencePath = resolve(
  'docs/milestones/artifacts/Torquay-2km-browser-evidence.json',
);

async function expectLoaded(page: import('@playwright/test').Page) {
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded', {
    timeout: 120_000,
  });
  await expect(shell).toHaveAttribute('data-renderer-ready', 'true', {
    timeout: 120_000,
  });
  await expect(shell).toHaveAttribute('data-scene-profile', 'current_2km');
  await expect(page.getByTestId('terrain-details')).toHaveText(
    '1001 columns × 1001 rows · 2 m spacing',
  );
  await expect(page.getByTestId('real-package-extent-notice')).toContainText(
    'selection remains pending and coverage is not checked',
  );
  await expect(page.getByTestId('world-attribution')).toContainText(
    'Environment Agency copyright',
  );
}

test('current 2 km combined package loads, navigates into its outer annulus, and reports bounded routes', async ({
  page,
}) => {
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  const failedResponses: string[] = [];
  const requestedUrls: string[] = [];
  const manifests = new Map<string, Record<string, unknown>>();
  let releaseInventory: Record<string, unknown> | undefined;
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('request', (request) => requestedUrls.push(request.url()));
  page.on('response', async (response) => {
    if (response.status() >= 400) {
      failedResponses.push(`${response.status()} ${response.url()}`);
    }
    const releasePath = new URL(response.url()).pathname.match(
      /\/worlds\/torquay-poc-001-2km\/releases\/[a-f0-9]{64}\/(.+)$/,
    )?.[1];
    if (releasePath === 'inventory.json') {
      try {
        releaseInventory = await response.json();
      } catch {
        // The readiness/inventory loader reports malformed release metadata.
      }
    }
    if (releasePath?.endsWith('manifest.json')) {
      try {
        manifests.set(releasePath, await response.json());
      } catch {
        // The normal loader assertion below reports a malformed package.
      }
    }
  });

  await mkdir(screenshotDir, { recursive: true });
  await mkdir(resolve('docs/milestones/artifacts'), { recursive: true });
  const loadStartedAt = Date.now();
  await page.goto('/?world=torquay-poc-001-2km&buildings=1&roads=1');
  await expectLoaded(page);
  const buildingStatus = page.getByTestId('building-status');
  const roadStatus = page.getByTestId('road-status');
  await expect(buildingStatus).toHaveAttribute('data-state', 'loaded', {
    timeout: 120_000,
  });
  await expect
    .poll(() => roadStatus.getAttribute('data-state'), { timeout: 120_000 })
    .toMatch(/^(loaded|error)$/);
  const roadState = await roadStatus.getAttribute('data-state');
  expect(
    roadState,
    `road load details: ${await page.getByTestId('road-error').textContent()}\n` +
      `requests: ${requestedUrls.join('\n')}\nfailed responses: ${failedResponses.join('\n')}`,
  ).toBe('loaded');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-road-float32-reoriented-triangles',
    '1',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-road-float32-collapsed-triangles',
    '1',
  );
  const loadTimeMs = Date.now() - loadStartedAt;
  const buildingCount = Number(
    await buildingStatus.getAttribute('data-building-count'),
  );
  const roadCount = Number(await roadStatus.getAttribute('data-way-count'));
  expect(buildingCount).toBeGreaterThan(1000);
  expect(roadCount).toBeGreaterThan(198);
  await expect(page.getByTestId('building-attribution')).toContainText(
    'OpenStreetMap contributors',
  );
  await expect(page.getByTestId('road-attribution')).toContainText(
    'OpenStreetMap contributors',
  );

  await expect.poll(() => manifests.size).toBeGreaterThanOrEqual(3);
  await expect
    .poll(() => Array.isArray(releaseInventory?.['files']))
    .toBe(true);
  const terrainManifest = manifests.get('manifest.json');
  const buildingManifest = manifests.get('buildings/manifest.json');
  const roadManifest = manifests.get('roads/manifest.json');
  expect(terrainManifest).toBeDefined();
  expect((terrainManifest?.heightfield as { columns?: number }).columns).toBe(
    1001,
  );
  expect((terrainManifest?.heightfield as { rows?: number }).rows).toBe(1001);
  expect((terrainManifest?.extentM as { width?: number }).width).toBe(2000);
  expect(terrainManifest?.sceneProfile).toBe('current_2km');
  expect(buildingManifest?.sceneProfile).toBe('current_2km');
  expect(roadManifest?.sceneProfile).toBe('current_2km');
  expect(
    requestedUrls.some((url) =>
      url.includes('/worlds/torquay-poc-001/overview/'),
    ),
  ).toBe(false);
  const releaseIds = new Set(
    requestedUrls.flatMap((value) => {
      const releaseId = new URL(value).pathname.match(
        /\/worlds\/torquay-poc-001-2km\/releases\/([a-f0-9]{64})\//,
      )?.[1];
      return releaseId ? [releaseId] : [];
    }),
  );
  expect(releaseIds.size).toBe(1);
  const [pinnedReleaseId] = [...releaseIds];
  expect(pinnedReleaseId).toBeDefined();
  for (const layerManifest of [
    'buildings/manifest.json',
    'roads/manifest.json',
  ]) {
    expect(
      requestedUrls.some(
        (value) =>
          new URL(value).pathname ===
          `/worlds/torquay-poc-001-2km/releases/${pinnedReleaseId}/${layerManifest}`,
      ),
    ).toBe(true);
  }
  expect(
    requestedUrls.some(
      (value) =>
        new URL(value).pathname === '/worlds/torquay-poc-001-2km/ready.json',
    ),
  ).toBe(true);
  expect(
    requestedUrls.some((url) =>
      /\/torquay-poc-001-2km\/manifest\.json/.test(url),
    ),
  ).toBe(false);

  await page.getByTestId('start-button').click();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  const overviewCapture = await page.evaluate(() => {
    const canvas = document.querySelector('canvas');
    return {
      viewport: { width: window.innerWidth, height: window.innerHeight },
      devicePixelRatio: window.devicePixelRatio,
      canvas: canvas
        ? {
            cssWidth: canvas.getBoundingClientRect().width,
            cssHeight: canvas.getBoundingClientRect().height,
            bufferWidth: canvas.width,
            bufferHeight: canvas.height,
          }
        : null,
      camera: {
        x: document
          .querySelector('[data-testid="camera-position"]')
          ?.getAttribute('data-x'),
        y: document
          .querySelector('[data-testid="camera-position"]')
          ?.getAttribute('data-y'),
        z: document
          .querySelector('[data-testid="camera-position"]')
          ?.getAttribute('data-z'),
      },
      groundHeight: document
        .querySelector('[data-testid="ground-height"]')
        ?.getAttribute('data-height-meters'),
      mode: document
        .querySelector('[data-testid="navigation-mode"]')
        ?.getAttribute('data-mode'),
    };
  });
  await page.screenshot({ path: overviewScreenshot });
  await page.keyboard.press('Escape');
  await expect
    .poll(() => page.evaluate(() => document.pointerLockElement === null))
    .toBe(true);

  await page.getByTestId('overview-toggle').click();
  const overviewPanel = page.getByTestId('geographic-overview');
  await expect(overviewPanel).toHaveAttribute('data-state', 'unavailable');
  await expect(page.getByTestId('overview-status')).toContainText(
    'unavailable for the current 2 km scene',
  );
  await expect(overviewPanel).toHaveAttribute('data-map-engine', 'none');
  await page.getByTestId('overview-close').click();

  const canvasBuffer = () =>
    page.locator('canvas').evaluate((element) => {
      const canvas = element as HTMLCanvasElement;
      const rect = canvas.getBoundingClientRect();
      return {
        cssWidth: rect.width,
        cssHeight: rect.height,
        bufferWidth: canvas.width,
        bufferHeight: canvas.height,
        dpr: window.devicePixelRatio,
      };
    });
  const bufferBeforeResize = await canvasBuffer();
  await page.setViewportSize({ width: 1280, height: 800 });
  await expect
    .poll(async () => {
      const size = await canvasBuffer();
      const cappedPixelRatio = Math.min(size.dpr, 1);
      return (
        size.bufferWidth === Math.round(size.cssWidth * cappedPixelRatio) &&
        size.bufferHeight === Math.round(size.cssHeight * cappedPixelRatio)
      );
    })
    .toBe(true);
  const resizedCanvas = await canvasBuffer();
  expect(resizedCanvas.bufferWidth).not.toBe(bufferBeforeResize.bufferWidth);
  expect(resizedCanvas.bufferHeight).not.toBe(bufferBeforeResize.bufferHeight);

  const initial = {
    x: Number(await page.getByTestId('camera-position').getAttribute('data-x')),
    y: Number(await page.getByTestId('camera-position').getAttribute('data-y')),
    z: Number(await page.getByTestId('camera-position').getAttribute('data-z')),
  };
  expect(initial.z).toBeGreaterThan(350);
  await page.getByTestId('start-button').click();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  await expect(page.getByTestId('flight-speed')).toHaveAttribute(
    'data-meters-per-second',
    '15.00',
  );
  const bearingBeforeLook = Number(
    await page
      .getByTestId('camera-orientation')
      .getAttribute('data-bearing-degrees'),
  );
  await page.mouse.move(700, 480);
  await page.mouse.move(760, 480, { steps: 6 });
  await expect
    .poll(() =>
      page
        .getByTestId('camera-orientation')
        .getAttribute('data-bearing-degrees'),
    )
    .not.toBe(String(bearingBeforeLook));
  await page.keyboard.down('Shift');
  await expect(page.getByTestId('flight-speed')).toHaveAttribute(
    'data-meters-per-second',
    '41.25',
  );
  await page.keyboard.up('Shift');
  await page.keyboard.down('Space');
  await page.waitForTimeout(350);
  await page.keyboard.up('Space');
  const afterRise = Number(
    await page.getByTestId('camera-position').getAttribute('data-y'),
  );
  expect(afterRise).toBeGreaterThan(initial.y);
  await page.keyboard.down('Control');
  await page.waitForTimeout(350);
  await page.keyboard.up('Control');
  await page.keyboard.press('f');
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'walk',
  );
  await expect
    .poll(() =>
      page.getByTestId('eye-clearance').getAttribute('data-clearance-meters'),
    )
    .toMatch(/^1\.7\d{2,}$/);
  await page.keyboard.press('f');
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'fly',
  );
  await page.keyboard.press('r');
  await expect
    .poll(() => page.getByTestId('camera-position').getAttribute('data-z'))
    .toBe(initial.z.toFixed(6));
  await page.keyboard.press('f');
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'walk',
  );
  await expect
    .poll(() =>
      page.getByTestId('eye-clearance').getAttribute('data-clearance-meters'),
    )
    .toMatch(/^1\.7\d{2,}$/);
  await page.keyboard.down('Shift');
  await expect(page.getByTestId('flight-speed')).toHaveAttribute(
    'data-meters-per-second',
    '41.25',
  );
  await page.keyboard.down('s');
  await page.waitForTimeout(4850);
  await page.keyboard.up('s');
  await page.keyboard.up('Shift');
  // Move to a QA pose just off the mapped road, then look along it with nearby
  // terrain and buildings in frame. This remains outside the centerline ribbon.
  await page.keyboard.down('a');
  await page.waitForTimeout(6000);
  await page.keyboard.up('a');
  await page.mouse.move(475, 280, { steps: 8 });
  await expect
    .poll(() =>
      page
        .getByTestId('camera-orientation')
        .getAttribute('data-bearing-degrees'),
    )
    .toBe('336.5');
  await expect
    .poll(() =>
      page.getByTestId('camera-orientation').getAttribute('data-pitch-degrees'),
    )
    .toMatch(/^-(?:[5-9]|1[0-5])\.\d$/);
  const outerX = Number(
    await page.getByTestId('camera-position').getAttribute('data-x'),
  );
  const outerZ = Number(
    await page.getByTestId('camera-position').getAttribute('data-z'),
  );
  expect(outerX).toBeLessThan(-80);
  expect(outerX).toBeGreaterThan(-100);
  expect(outerZ).toBeGreaterThan(585);
  expect(outerZ).toBeLessThan(615);
  await expect
    .poll(() =>
      page.evaluate(() => {
        const y = Number(
          document
            .querySelector('[data-testid="camera-position"]')
            ?.getAttribute('data-y'),
        );
        const ground = Number(
          document
            .querySelector('[data-testid="ground-height"]')
            ?.getAttribute('data-height-meters'),
        );
        return y - ground;
      }),
    )
    .toBeGreaterThan(1.65);
  await expect
    .poll(() =>
      page.evaluate(() => {
        const y = Number(
          document
            .querySelector('[data-testid="camera-position"]')
            ?.getAttribute('data-y'),
        );
        const ground = Number(
          document
            .querySelector('[data-testid="ground-height"]')
            ?.getAttribute('data-height-meters'),
        );
        return y - ground;
      }),
    )
    .toBeLessThan(1.75);
  const outerCapture = await page.evaluate(() => {
    const canvas = document.querySelector('canvas');
    return {
      viewport: { width: window.innerWidth, height: window.innerHeight },
      devicePixelRatio: window.devicePixelRatio,
      canvas: canvas
        ? {
            cssWidth: canvas.getBoundingClientRect().width,
            cssHeight: canvas.getBoundingClientRect().height,
            bufferWidth: canvas.width,
            bufferHeight: canvas.height,
          }
        : null,
      camera: {
        x: document
          .querySelector('[data-testid="camera-position"]')
          ?.getAttribute('data-x'),
        y: document
          .querySelector('[data-testid="camera-position"]')
          ?.getAttribute('data-y'),
        z: document
          .querySelector('[data-testid="camera-position"]')
          ?.getAttribute('data-z'),
      },
      groundHeight: document
        .querySelector('[data-testid="ground-height"]')
        ?.getAttribute('data-height-meters'),
      mode: document
        .querySelector('[data-testid="navigation-mode"]')
        ?.getAttribute('data-mode'),
      orientation: {
        bearingDegrees: document
          .querySelector('[data-testid="camera-orientation"]')
          ?.getAttribute('data-bearing-degrees'),
        pitchDegrees: document
          .querySelector('[data-testid="camera-orientation"]')
          ?.getAttribute('data-pitch-degrees'),
      },
    };
  });
  await page.screenshot({ path: outerScreenshot });
  await page.keyboard.press('Escape');
  await expect
    .poll(() => page.evaluate(() => document.pointerLockElement === null))
    .toBe(true);

  const frameMetrics = await page.evaluate(async () => {
    const frameIntervals: number[] = [];
    let firstFrame: number | undefined;
    let previousFrame: number | undefined;
    const durationMs = 5_000;
    await new Promise<void>((resolveFrame) => {
      const sample = (timestamp: number): void => {
        firstFrame ??= timestamp;
        if (previousFrame !== undefined) {
          frameIntervals.push(timestamp - previousFrame);
        }
        previousFrame = timestamp;
        if (timestamp - firstFrame < durationMs) {
          requestAnimationFrame(sample);
        } else {
          resolveFrame();
        }
      };
      requestAnimationFrame(sample);
    });
    const ordered = [...frameIntervals].sort((left, right) => left - right);
    const percentile = (fraction: number): number => {
      if (ordered.length === 0) return 0;
      return ordered[Math.max(0, Math.ceil(ordered.length * fraction) - 1)]!;
    };
    const round = (value: number): number => Math.round(value * 1000) / 1000;
    const canvas = document.querySelector('canvas');
    const context = canvas?.getContext('webgl2') ?? canvas?.getContext('webgl');
    const debugInfo = context?.getExtension('WEBGL_debug_renderer_info');
    const shell = document.querySelector('.viewer-shell');
    return {
      frameCount: frameIntervals.length,
      frameTimeMs: {
        p50: round(percentile(0.5)),
        p95: round(percentile(0.95)),
        p99: round(percentile(0.99)),
        maximum: round(ordered.at(-1) ?? 0),
      },
      medianFps: round(1000 / Math.max(percentile(0.5), 0.001)),
      renderer: {
        webglVersion: context?.getParameter(context.VERSION) ?? null,
        vendor: context
          ? context.getParameter(
              debugInfo?.UNMASKED_VENDOR_WEBGL ?? context.VENDOR,
            )
          : null,
        renderer: context
          ? context.getParameter(
              debugInfo?.UNMASKED_RENDERER_WEBGL ?? context.RENDERER,
            )
          : null,
      },
      drawCalls: Number(shell?.getAttribute('data-draw-calls') ?? 0),
      triangles: Number(shell?.getAttribute('data-triangles') ?? 0),
      canvas: canvas
        ? {
            cssWidth: canvas.getBoundingClientRect().width,
            cssHeight: canvas.getBoundingClientRect().height,
            bufferWidth: canvas.width,
            bufferHeight: canvas.height,
          }
        : null,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      devicePixelRatio: window.devicePixelRatio,
      hudFps: Number(
        document
          .querySelector('[data-testid="frames-per-second"]')
          ?.getAttribute('data-fps') ?? 0,
      ),
    };
  });
  expect(frameMetrics.frameCount).toBeGreaterThan(0);
  const inventoryFiles = Array.isArray(releaseInventory?.['files'])
    ? (releaseInventory['files'] as Array<{ byteLength?: unknown }>)
    : [];
  expect(inventoryFiles.length).toBeGreaterThan(0);
  const packageByteLength = inventoryFiles.reduce((total, item) => {
    expect(Number.isSafeInteger(item.byteLength)).toBe(true);
    return total + Number(item.byteLength);
  }, 0);

  const browserEvidence = await page.evaluate(() => {
    const canvas = document.querySelector('canvas');
    const gl = canvas?.getContext('webgl2') ?? canvas?.getContext('webgl');
    const debugInfo = gl?.getExtension('WEBGL_debug_renderer_info');
    return {
      userAgent: navigator.userAgent,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      devicePixelRatio: window.devicePixelRatio,
      canvas: canvas
        ? { width: canvas.width, height: canvas.height }
        : undefined,
      renderer: debugInfo
        ? gl?.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)
        : gl?.getParameter(gl.RENDERER),
      fps: document
        .querySelector('[data-testid="frames-per-second"]')
        ?.getAttribute('data-fps'),
      camera: {
        x: document
          .querySelector('[data-testid="camera-position"]')
          ?.getAttribute('data-x'),
        y: document
          .querySelector('[data-testid="camera-position"]')
          ?.getAttribute('data-y'),
        z: document
          .querySelector('[data-testid="camera-position"]')
          ?.getAttribute('data-z'),
      },
      groundHeight: document
        .querySelector('[data-testid="ground-height"]')
        ?.getAttribute('data-height-meters'),
    };
  });
  expect(pageErrors).toEqual([]);
  expect(consoleErrors).toEqual([]);
  expect(failedResponses).toEqual([]);
  expect(requestedUrls.some((url) => /\/torquay-poc-001\//.test(url))).toBe(
    false,
  );
  await writeFile(
    evidencePath,
    JSON.stringify(
      {
        profile: 'current_2km',
        browser: browserEvidence,
        browserVersion: page.context().browser()?.version() ?? 'unknown',
        loadTimeMs,
        performance: frameMetrics,
        counts: { buildings: buildingCount, roads: roadCount },
        packageByteLength,
        releaseInventoryByteLength: inventoryFiles.reduce(
          (total, item) => total + Number(item.byteLength),
          0,
        ),
        packageAssets: {
          terrainHeightfield: terrainManifest?.heightfield,
          buildings: buildingManifest?.assets,
          roads: roadManifest?.assets,
        },
        paths: {
          overviewScreenshot: overviewScreenshot.replaceAll('\\', '/'),
          outerAnnulusScreenshot: outerScreenshot.replaceAll('\\', '/'),
        },
        screenshots: {
          overview: overviewCapture,
          outerAnnulus: outerCapture,
        },
        releaseId: pinnedReleaseId ?? null,
        outerAnnulus: {
          initialX: initial.x,
          initialZ: initial.z,
          finalX: outerX,
          finalZ: outerZ,
        },
        noHistoricalOverviewRequested: true,
        noUnexpectedPageConsoleOrHttpErrors: true,
      },
      null,
      2,
    ),
    'utf8',
  );
});

test('2 km optional layer failure preserves terrain and permits synthetic recovery', async ({
  page,
}) => {
  await page.route(
    '**/worlds/torquay-poc-001-2km/releases/*/buildings/manifest.json',
    (route) => route.fulfill({ status: 503, body: 'fixture failure' }),
  );
  await page.goto('/?world=torquay-poc-001-2km&buildings=1&roads=0');
  await expectLoaded(page);
  await expect(page.getByTestId('building-status')).toHaveAttribute(
    'data-state',
    'error',
    { timeout: 60_000 },
  );
  await expect(page.getByTestId('terrain-details')).toHaveText(
    '1001 columns × 1001 rows · 2 m spacing',
  );
  await page.getByTestId('world-select-synthetic').click();
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-world-mode',
    'synthetic',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-load-state',
    'loaded',
    { timeout: 60_000 },
  );
});

test('current 2 km route makes no runtime asset request without readiness', async ({
  page,
}) => {
  const realRequests: string[] = [];
  await page.route('**/worlds/torquay-poc-001-2km/ready.json', (route) =>
    route.fulfill({ status: 404, body: 'not published' }),
  );
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (url.pathname.includes('/worlds/torquay-poc-001-2km/')) {
      realRequests.push(url.pathname);
    }
  });
  await page.goto('/?world=torquay-poc-001-2km&buildings=1&roads=1');
  await expect(page.getByTestId('world-load-error')).toBeVisible();
  await expect(page.getByTestId('world-error-message')).toContainText(
    'publish-scene --profile current_2km',
  );
  expect(realRequests).toEqual(['/worlds/torquay-poc-001-2km/ready.json']);
});
