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
  await page.goto('/?world=torquay-poc-001-2km&buildings=1&roads=1');
  await expectLoaded(page);
  const buildingStatus = page.getByTestId('building-status');
  const roadStatus = page.getByTestId('road-status');
  await expect(buildingStatus).toHaveAttribute('data-state', 'loaded', {
    timeout: 120_000,
  });
  await expect(roadStatus).toHaveAttribute('data-state', 'loaded', {
    timeout: 120_000,
  });
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
  await page.keyboard.press('Escape');
  await expect
    .poll(() => page.evaluate(() => document.pointerLockElement === null))
    .toBe(true);
  await page.screenshot({ path: overviewScreenshot });

  await page.getByTestId('overview-toggle').click();
  const overviewPanel = page.getByTestId('geographic-overview');
  await expect(overviewPanel).toHaveAttribute('data-state', 'unavailable');
  await expect(page.getByTestId('overview-status')).toContainText(
    'unavailable for the current 2 km scene',
  );
  await expect(overviewPanel).toHaveAttribute('data-map-engine', 'none');
  await page.getByTestId('overview-close').click();

  await page.setViewportSize({ width: 1280, height: 800 });
  const resizedCanvas = await page.locator('canvas').evaluate((element) => {
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
  expect(resizedCanvas.bufferWidth).toBe(
    Math.round(resizedCanvas.cssWidth * resizedCanvas.dpr),
  );
  expect(resizedCanvas.bufferHeight).toBe(
    Math.round(resizedCanvas.cssHeight * resizedCanvas.dpr),
  );

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
  await page.waitForTimeout(4200);
  await page.keyboard.up('s');
  await page.keyboard.up('Shift');
  const outerZ = Number(
    await page.getByTestId('camera-position').getAttribute('data-z'),
  );
  expect(outerZ).toBeGreaterThan(500);
  expect(outerZ).toBeLessThan(1000);
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
  await page.keyboard.press('Escape');
  await expect
    .poll(() => page.evaluate(() => document.pointerLockElement === null))
    .toBe(true);
  await page.screenshot({ path: outerScreenshot });

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
        counts: { buildings: buildingCount, roads: roadCount },
        packageAssets: {
          terrainHeightfield: terrainManifest?.heightfield,
          buildings: buildingManifest?.assets,
          roads: roadManifest?.assets,
        },
        paths: {
          overviewScreenshot: overviewScreenshot.replaceAll('\\', '/'),
          outerAnnulusScreenshot: outerScreenshot.replaceAll('\\', '/'),
        },
        outerAnnulus: { initialZ: initial.z, finalZ: outerZ },
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
