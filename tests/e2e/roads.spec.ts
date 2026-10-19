import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';

test('loads actual local OSM road ribbons on terrain, toggles layers and captures views', async ({
  page,
  browserName,
}) => {
  test.setTimeout(180_000);
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const failedRequests: string[] = [];
  const requestedUrls: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) =>
    pageErrors.push(`${error.name}: ${error.message}`),
  );
  page.on('requestfailed', (request) =>
    failedRequests.push(`${request.method()} ${request.url()}`),
  );
  page.on('request', (request) => requestedUrls.push(request.url()));

  await page.goto('/?world=torquay-poc-001&buildings=1&roads=1');
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded');
  await expect(shell).toHaveAttribute('data-renderer-ready', 'true');
  await expect(shell).toHaveAttribute('data-road-state', 'loaded', {
    timeout: 30_000,
  });
  await expect(shell).toHaveAttribute('data-building-state', 'loaded');
  await expect(page.getByTestId('road-status')).toContainText(
    '198 mapped ways',
  );
  await expect(page.getByTestId('road-status')).toContainText(
    '198 clipped line parts',
  );
  await expect(page.getByTestId('road-extract-vintage')).toHaveText(
    'OSM extract vintage: 2026-10-16T20:21:21Z (replication sequence 4932).',
  );
  await expect(page.getByTestId('road-width-policy')).toContainText(
    'visual estimates',
  );
  await expect(page.getByTestId('road-attribution')).toContainText(
    'OpenStreetMap contributors',
  );
  await expect(page.getByTestId('road-attribution')).toContainText(
    'Geofabrik GmbH',
  );
  await expect(
    page.getByRole('link', { name: 'ODbL attribution and licence' }),
  ).toHaveAttribute('href', 'https://www.openstreetmap.org/copyright');
  expect(requestedUrls).toContain(
    'http://127.0.0.1:4173/worlds/torquay-poc-001/roads/manifest.json',
  );
  expect(requestedUrls).toContain(
    'http://127.0.0.1:4173/worlds/torquay-poc-001/roads/roads.json',
  );
  expect(requestedUrls).toContain(
    'http://127.0.0.1:4173/worlds/torquay-poc-001/roads/qa.json',
  );
  expect(requestedUrls).not.toContain(
    'http://127.0.0.1:4173/worlds/torquay-poc-001/roads/',
  );
  expect(
    requestedUrls.every(
      (url) => new URL(url).origin === 'http://127.0.0.1:4173',
    ),
  ).toBe(true);

  const status = page.getByTestId('road-status');
  const requestsBeforeToggle = requestedUrls.filter((url) =>
    url.includes('/roads/'),
  ).length;
  const roadsToggle = page.getByTestId('roads-toggle');
  await roadsToggle.click();
  await expect(shell).toHaveAttribute('data-road-visible', 'false');
  await expect(roadsToggle).toHaveAttribute('aria-pressed', 'false');
  await expect(status).toContainText('198 mapped ways');
  await expect(status).toContainText('171 streets / 0 cycleways / 27 paths');
  await roadsToggle.click();
  await expect(shell).toHaveAttribute('data-road-visible', 'true');
  await expect(status).toContainText('198 mapped ways');
  expect(requestedUrls.filter((url) => url.includes('/roads/')).length).toBe(
    requestsBeforeToggle,
  );

  const wireframe = page.getByTestId('roads-wireframe-toggle');
  await wireframe.click();
  await expect(wireframe).toHaveAttribute('aria-pressed', 'true');
  await wireframe.click();
  await expect(wireframe).toHaveAttribute('aria-pressed', 'false');

  const landmark = page.getByTestId('road-landmark-select');
  await expect(landmark.locator('option')).toHaveCount(3);
  await landmark.selectOption('sw-mount-stuart');
  await expect(status).toHaveAttribute(
    'data-selected-context',
    'sw-mount-stuart',
  );
  await expect(status).toContainText('placement cue, not a road junction');

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

  const fpsSamples: number[] = [];
  for (let sample = 0; sample < 12; sample += 1) {
    const fps = Number(
      await page.getByTestId('frames-per-second').getAttribute('data-fps'),
    );
    if (Number.isFinite(fps) && fps > 0) fpsSamples.push(fps);
    await page.waitForTimeout(250);
  }
  const sortedFpsSamples = [...fpsSamples].sort(
    (first, second) => first - second,
  );
  expect(sortedFpsSamples.length).toBeGreaterThanOrEqual(8);
  const medianFps = sortedFpsSamples[Math.floor(sortedFpsSamples.length / 2)]!;

  const outputDirectory = resolve(process.cwd(), 'docs/milestones/screenshots');
  await mkdir(outputDirectory, { recursive: true });
  const overviewPath = resolve(outputDirectory, 'TVW-011-roads-overview.png');
  await page.screenshot({ path: overviewPath, animations: 'disabled' });

  await page.keyboard.down('Control');
  await page.waitForFunction(
    () => {
      const position = document.querySelector<HTMLOutputElement>(
        '[data-testid="camera-position"]',
      );
      const ground = document.querySelector<HTMLOutputElement>(
        '[data-testid="ground-height"]',
      );
      return Boolean(
        position &&
        ground &&
        Number(position.dataset.y) - Number(ground.dataset.heightMeters) < 3.2,
      );
    },
    { polling: 25, timeout: 30_000 },
  );
  await page.keyboard.up('Control');

  await page.mouse.move(720, 450);
  await page.mouse.move(2050, 210, { steps: 8 });
  await expect
    .poll(() =>
      page
        .getByTestId('camera-orientation')
        .getAttribute('data-pitch-degrees')
        .then(Number),
    )
    .toBeGreaterThan(-2);

  const position = await page
    .getByTestId('camera-position')
    .evaluate((element) => ({
      x: Number((element as HTMLOutputElement).dataset.x),
      y: Number((element as HTMLOutputElement).dataset.y),
      z: Number((element as HTMLOutputElement).dataset.z),
    }));
  const groundHeight = Number(
    await page.getByTestId('ground-height').getAttribute('data-height-meters'),
  );
  const groundEyeAltitudeM = position.y - groundHeight;
  expect(groundEyeAltitudeM).toBeGreaterThan(1);
  expect(groundEyeAltitudeM).toBeLessThan(2.5);
  const groundEyePitchDegrees = Number(
    await page
      .getByTestId('camera-orientation')
      .getAttribute('data-pitch-degrees'),
  );
  const groundEyeBearingDegrees = Number(
    await page
      .getByTestId('camera-orientation')
      .getAttribute('data-bearing-degrees'),
  );
  expect(groundEyePitchDegrees).toBeGreaterThan(-2);
  expect(groundEyePitchDegrees).toBeLessThan(4);
  expect(groundEyeBearingDegrees).toBeGreaterThan(135);
  expect(groundEyeBearingDegrees).toBeLessThan(175);
  const groundPath = resolve(outputDirectory, 'TVW-011-roads-ground.png');
  await page.addStyleTag({
    content:
      '.viewer-topline,.world-selector,.debug-hud,.building-controls,.road-controls,.controls-help,.corner-note,.start-card{visibility:hidden!important}',
  });
  await page.screenshot({ path: groundPath, animations: 'disabled' });
  await page.keyboard.press('Escape');
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement !== document.querySelector('canvas'),
      ),
    )
    .toBe(true);

  const browserEvidence = await page.evaluate(() => {
    const canvas = document.querySelector<HTMLCanvasElement>(
      'canvas.viewer-canvas',
    );
    if (!canvas) throw new Error('The renderer canvas is missing.');
    const context = canvas.getContext('webgl2') ?? canvas.getContext('webgl');
    const extension = context?.getExtension('WEBGL_debug_renderer_info');
    return {
      userAgent: navigator.userAgent,
      renderer: context
        ? extension
          ? context.getParameter(extension.UNMASKED_RENDERER_WEBGL)
          : context.getParameter(context.RENDERER)
        : 'WebGL unavailable',
      viewport: { width: innerWidth, height: innerHeight },
      devicePixelRatio,
      canvas: {
        cssWidth: canvas.clientWidth,
        cssHeight: canvas.clientHeight,
        width: canvas.width,
        height: canvas.height,
      },
      drawCalls: document
        .querySelector('.viewer-shell')
        ?.getAttribute('data-draw-calls'),
      triangles: document
        .querySelector('.viewer-shell')
        ?.getAttribute('data-triangles'),
    };
  });
  await mkdir(resolve(process.cwd(), 'test-results'), { recursive: true });
  await writeFile(
    resolve(process.cwd(), 'test-results/tvw-011-road-browser-evidence.json'),
    JSON.stringify(
      {
        ...browserEvidence,
        browserName,
        browserVersion: page.context().browser()?.version(),
        world: 'torquay-poc-001 with buildings=1 and roads=1',
        roadCounts: {
          ways: 198,
          clippedParts: 198,
          triangles: Number(await status.getAttribute('data-triangle-count')),
        },
        groundEyePosition: position,
        groundHeightM: groundHeight,
        groundEyeAltitudeM,
        groundEyePitchDegrees,
        groundEyeBearingDegrees,
        medianFpsOverThreeSeconds: medianFps,
        sampledFps: fpsSamples,
        screenshots: [overviewPath, groundPath],
      },
      null,
      2,
    ),
  );

  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(failedRequests).toEqual([]);
});

test('does not request OSM roads on the synthetic default route', async ({
  page,
}) => {
  const roadRequests: string[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/worlds/torquay-poc-001/roads/'))
      roadRequests.push(request.url());
  });
  await page.goto('/');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-load-state',
    'loaded',
  );
  await expect(page.getByTestId('road-controls')).toBeHidden();
  expect(roadRequests).toEqual([]);
});

test('reports a corrupt road payload, retries, and can continue with terrain only', async ({
  page,
}) => {
  let corruptOnce = true;
  await page.route(
    '**/worlds/torquay-poc-001/roads/roads.json',
    async (route) => {
      if (!corruptOnce) return route.continue();
      corruptOnce = false;
      const response = await route.fetch();
      const bytes = Buffer.from(await response.body());
      bytes[0] = bytes[0]! ^ 1;
      await route.fulfill({ response, body: bytes });
    },
  );
  await page.goto('/?world=torquay-poc-001&roads=1');
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded');
  await expect(shell).toHaveAttribute('data-road-state', 'error');
  await expect(page.getByTestId('road-error')).toContainText(
    'SHA-256 mismatch',
  );
  await expect(page.getByTestId('road-recovery')).toBeVisible();
  await page.getByTestId('roads-retry').click();
  await expect(shell).toHaveAttribute('data-road-state', 'loaded');
  await page.getByTestId('roads-terrain-only').click();
  await expect(shell).toHaveAttribute('data-road-state', 'off');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded');
});

test('shows actionable recovery when the roads manifest is missing', async ({
  page,
}) => {
  await page.route('**/worlds/torquay-poc-001/roads/manifest.json', (route) =>
    route.fulfill({ status: 404, body: 'local road package is absent' }),
  );
  await page.goto('/?world=torquay-poc-001&roads=1');
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-road-state', 'error');
  await expect(page.getByTestId('road-error')).toContainText('publish-roads');
  await page.getByTestId('roads-terrain-only').click();
  await expect(shell).toHaveAttribute('data-road-state', 'off');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded');
});
