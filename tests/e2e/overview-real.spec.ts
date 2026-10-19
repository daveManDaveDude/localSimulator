import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';

const manifestPath = '/worlds/torquay-poc-001/overview/manifest.json';
const featuresPath = '/worlds/torquay-poc-001/overview/features.geojson';
const screenshotDirectory = resolve('docs/milestones/screenshots');
const evidencePath = resolve(
  'docs/milestones/artifacts/M8-browser-evidence.json',
);

async function waitForWorld(
  page: import('@playwright/test').Page,
): Promise<void> {
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-load-state',
    'loaded',
    { timeout: 45_000 },
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-renderer-ready',
    'true',
    { timeout: 45_000 },
  );
}

test('real overview is lazy, fixed, identity-aware, local-only and disposable', async ({
  page,
  browser,
}, testInfo) => {
  test.skip(
    process.env.M8_OVERVIEW_REAL_PRODUCTION !== 'true',
    'Run against the isolated production preview profile.',
  );
  test.setTimeout(180_000);
  const errors: string[] = [];
  const externalRequests: string[] = [];
  const overviewRequests: string[] = [];
  const maplibreRequests: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (url.protocol === 'http:' || url.protocol === 'https:') {
      if (url.origin !== testInfo.project.use.baseURL)
        externalRequests.push(url.href);
      if (url.pathname.startsWith('/worlds/torquay-poc-001/overview/'))
        overviewRequests.push(url.pathname);
      if (url.pathname.includes('maplibre-gl-'))
        maplibreRequests.push(url.pathname);
    }
  });

  await page.goto('/?world=torquay-poc-001&buildings=1&roads=1');
  await waitForWorld(page);
  await expect(page.getByTestId('building-status')).toHaveAttribute(
    'data-state',
    'loaded',
  );
  await expect(page.getByTestId('road-status')).toHaveAttribute(
    'data-state',
    'loaded',
  );
  await expect(page.getByTestId('overview-toggle')).toHaveAttribute(
    'aria-expanded',
    'false',
  );
  expect(
    await page.evaluate(() =>
      performance
        .getEntriesByType('resource')
        .some((entry) => entry.name.includes('maplibre-gl-')),
    ),
  ).toBe(false);

  const packageResponse = await page.request.get(manifestPath);
  expect(packageResponse.ok()).toBe(true);
  const packageManifest = (await packageResponse.json()) as {
    features: { sha256: string; byteLength: number };
    counts: {
      featuresByRole: {
        aoi: number;
        roads: number;
        buildings: number;
        total: number;
      };
    };
    terrainIdentity: { manifestSha256: string };
  };

  const openStarted = Date.now();
  await page.getByTestId('overview-toggle').click();
  const panel = page.getByTestId('geographic-overview');
  await expect(panel).toBeVisible();
  await expect(page.getByTestId('overview-status')).toContainText(
    'Local package overview ready',
    { timeout: 45_000 },
  );
  await expect(page.locator('.overview-map .maplibregl-canvas')).toBeVisible();
  await expect(page.getByTestId('overview-layer-status')).toContainText(
    'Roads visible',
  );
  await expect(page.getByTestId('overview-layer-status')).toContainText(
    'Buildings visible',
  );
  await expect(page.getByTestId('overview-osm-attribution')).toBeVisible();
  await expect(panel).toContainText('FIXED · NORTH UP');
  await expect(panel).toContainText('no live camera position');
  await expect(panel).toContainText('coverage is not checked');
  await expect(panel.locator('.maplibregl-ctrl-scale')).toBeVisible();
  expect(await page.locator('.overview-map .maplibregl-canvas').count()).toBe(
    1,
  );

  const mapCanvasBefore = await page
    .locator('.overview-map .maplibregl-canvas')
    .evaluate((canvas) => ({
      width: (canvas as HTMLCanvasElement).width,
      height: (canvas as HTMLCanvasElement).height,
    }));
  await page.getByTestId('roads-toggle').click();
  await expect(page.getByTestId('overview-layer-status')).toContainText(
    'Roads hidden',
  );
  await expect(page.getByTestId('overview-osm-attribution')).toBeVisible();
  await page.getByTestId('buildings-toggle').click();
  await expect(page.getByTestId('overview-layer-status')).toContainText(
    'Buildings hidden',
  );
  await expect(page.getByTestId('overview-osm-attribution')).toBeHidden();
  await page.getByTestId('roads-toggle').click();
  await expect(page.getByTestId('overview-layer-status')).toContainText(
    'Roads visible',
  );
  await page.getByTestId('buildings-toggle').click();
  await expect(page.getByTestId('overview-layer-status')).toContainText(
    'Buildings visible',
  );

  await page.setViewportSize({ width: 640, height: 800 });
  await page.waitForTimeout(250);
  const mapCanvasAfter = await page
    .locator('.overview-map .maplibregl-canvas')
    .evaluate((canvas) => ({
      width: (canvas as HTMLCanvasElement).width,
      height: (canvas as HTMLCanvasElement).height,
    }));
  expect(mapCanvasAfter.width).not.toBe(mapCanvasBefore.width);
  expect(mapCanvasAfter.height).not.toBe(mapCanvasBefore.height);
  await page.setViewportSize({ width: 1440, height: 960 });
  await expect
    .poll(async () =>
      page
        .locator('.overview-map .maplibregl-canvas')
        .evaluate((canvas) => (canvas as HTMLCanvasElement).width),
    )
    .toBe(mapCanvasBefore.width);

  await mkdir(screenshotDirectory, { recursive: true });
  await page.getByTestId('overview-close').click();
  await expect(panel).toBeHidden();
  expect(await page.locator('.overview-map .maplibregl-canvas').count()).toBe(
    0,
  );
  await page.getByTestId('overview-toggle').click();
  await expect(page.getByTestId('overview-status')).toContainText(
    'Local package overview ready',
  );
  expect(await page.locator('.overview-map .maplibregl-canvas').count()).toBe(
    1,
  );
  await page.getByTestId('start-button').click();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  await page.keyboard.press('h');
  await expect(page.getByTestId('controls-help')).toBeHidden();
  await page.screenshot({
    path: resolve(screenshotDirectory, 'M8-overview-real.png'),
    fullPage: true,
  });

  const browserEvidence = await page.evaluate(() => {
    const canvas = document.querySelector<HTMLCanvasElement>('.viewer-canvas');
    const context = canvas?.getContext('webgl2') ?? canvas?.getContext('webgl');
    const extension = context?.getExtension('WEBGL_debug_renderer_info');
    const mapCanvas = document.querySelector<HTMLCanvasElement>(
      '.overview-map .maplibregl-canvas',
    );
    const mapRect = mapCanvas?.getBoundingClientRect();
    const mapContext =
      mapCanvas?.getContext('webgl2') ?? mapCanvas?.getContext('webgl');
    const mapExtension = mapContext?.getExtension('WEBGL_debug_renderer_info');
    const resources = performance
      .getEntriesByType('resource')
      .filter((entry) => entry.name.includes('maplibre-gl-'))
      .map((entry) => ({
        name: entry.name.split('/').at(-1),
        transferSize: (entry as PerformanceResourceTiming).transferSize,
        decodedBodySize: (entry as PerformanceResourceTiming).decodedBodySize,
      }));
    return {
      viewport: { width: innerWidth, height: innerHeight },
      devicePixelRatio,
      mainRenderer:
        context && extension
          ? context.getParameter(extension.UNMASKED_RENDERER_WEBGL)
          : 'unavailable',
      mapRenderer:
        mapContext && mapExtension
          ? mapContext.getParameter(mapExtension.UNMASKED_RENDERER_WEBGL)
          : 'unavailable',
      mapCanvas: mapCanvas
        ? { width: mapCanvas.width, height: mapCanvas.height }
        : null,
      mapCssRect: mapRect
        ? { width: mapRect.width, height: mapRect.height }
        : null,
      maplibreResources: resources,
      activationNote: 'Measured from click to ready state in the test process.',
    };
  });
  const evidence = {
    browser: { name: browser.browserType().name(), version: browser.version() },
    ...browserEvidence,
    overviewActivationMs: Date.now() - openStarted,
    overviewPackage: {
      manifestSha256: await page.evaluate(async () => {
        const response = await fetch(
          '/worlds/torquay-poc-001/overview/manifest.json',
        );
        const bytes = await response.arrayBuffer();
        const hash = await crypto.subtle.digest('SHA-256', bytes);
        return Array.from(new Uint8Array(hash), (value) =>
          value.toString(16).padStart(2, '0'),
        ).join('');
      }),
      featuresSha256: packageManifest.features.sha256,
      featuresByteLength: packageManifest.features.byteLength,
      featureCounts: packageManifest.counts.featuresByRole,
      terrainManifestSha256: packageManifest.terrainIdentity.manifestSha256,
    },
    requests: overviewRequests,
    externalRequests,
    errors,
    screenshot: 'docs/milestones/screenshots/M8-overview-real.png',
    syntheticScreenshot:
      'docs/milestones/screenshots/M8-overview-synthetic-unavailable.png',
    qualification:
      'The geographic overview is a fixed 2D local GeoJSON view. It does not contain a live camera marker, terrain raster, or independent completeness/alignment result.',
  };
  await writeFile(evidencePath, `${JSON.stringify(evidence, null, 2)}\n`);
  expect(overviewRequests).toContain(manifestPath);
  expect(overviewRequests).toContain(featuresPath);
  expect(externalRequests).toEqual([]);
  expect(errors).toEqual([]);

  const overviewRequestsBeforeSyntheticNavigation = overviewRequests.length;
  const maplibreRequestsBeforeSyntheticNavigation = maplibreRequests.length;
  await page.goto('/?world=m0');
  await waitForWorld(page);
  await page.getByTestId('overview-toggle').click();
  await expect(page.getByTestId('overview-status')).toContainText(
    'unavailable for synthetic worlds',
  );
  await expect(page.getByTestId('overview-disclaimer')).toContainText(
    'Synthetic scenes have no assigned real-world coordinates',
  );
  await expect(page.getByTestId('geographic-overview')).toHaveAttribute(
    'data-map-engine',
    'none',
  );
  await expect(page.getByTestId('overview-map-wrap')).toBeHidden();
  await expect(page.getByTestId('overview-layer-status')).toBeHidden();
  await expect(page.locator('.overview-ea-context')).toBeHidden();
  await expect(page.locator('.overview-maplibre-attribution')).toBeHidden();
  await expect(page.locator('.overview-legend')).toBeHidden();
  await expect(page.locator('.overview-north')).toBeHidden();
  await expect(page.locator('.overview-map .maplibregl-canvas')).toHaveCount(0);
  await page.getByTestId('start-button').click();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  await page.keyboard.press('h');
  await expect(page.getByTestId('controls-help')).toBeHidden();
  await page.screenshot({
    path: resolve(screenshotDirectory, 'M8-overview-synthetic-unavailable.png'),
    fullPage: true,
  });
  expect(overviewRequests).toHaveLength(
    overviewRequestsBeforeSyntheticNavigation,
  );
  expect(maplibreRequests).toHaveLength(
    maplibreRequestsBeforeSyntheticNavigation,
  );
  expect(errors).toEqual([]);
});

test('missing overview shows retry while keeping the real terrain and synthetic recovery available', async ({
  page,
}) => {
  test.skip(
    process.env.M8_OVERVIEW_REAL_PRODUCTION !== 'true',
    'Run against the isolated production preview profile.',
  );
  await page.route(`**${manifestPath}`, (route) =>
    route.fulfill({
      status: 404,
      body: 'overview package intentionally unavailable',
    }),
  );
  await page.goto('/?world=torquay-poc-001');
  await waitForWorld(page);
  await page.getByTestId('overview-toggle').click();
  await expect(page.getByTestId('overview-status')).toContainText(
    'Local overview package is missing',
  );
  await expect(page.getByTestId('overview-retry')).toBeVisible();
  await expect(page.locator('.viewer-canvas')).toBeVisible();
  await page.getByTestId('overview-close').click();
  await expect(page.getByTestId('overview-toggle')).toBeEnabled();
  await page.goto('/?world=m0');
  await waitForWorld(page);
  await page.getByTestId('overview-toggle').click();
  await expect(page.getByTestId('overview-status')).toContainText(
    'unavailable for synthetic worlds',
  );
  await expect(page.locator('.overview-map .maplibregl-canvas')).toHaveCount(0);
});

test('corrupt GeoJSON is rejected and the user can retry the verified overview', async ({
  page,
}) => {
  test.skip(
    process.env.M8_OVERVIEW_REAL_PRODUCTION !== 'true',
    'Run against the isolated production preview profile.',
  );
  await page.route(`**${featuresPath}`, async (route) => {
    const response = await route.fetch();
    const bytes = new Uint8Array(await response.body());
    bytes[bytes.length - 3] = bytes[bytes.length - 3]! ^ 1;
    await route.fulfill({ response, body: Buffer.from(bytes) });
  });
  await page.goto('/?world=torquay-poc-001');
  await waitForWorld(page);
  await page.getByTestId('overview-toggle').click();
  await expect(page.getByTestId('overview-status')).toContainText(
    'failed validation',
  );
  await expect(page.getByTestId('overview-retry')).toBeVisible();
  await page.unroute(`**${featuresPath}`);
  await page.getByTestId('overview-retry').click();
  await expect(page.getByTestId('overview-status')).toContainText(
    'Local package overview ready',
  );
  await expect(page.locator('.overview-map .maplibregl-canvas')).toHaveCount(1);
});
