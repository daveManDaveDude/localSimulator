import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

interface Position {
  x: number;
  y: number;
  z: number;
}

interface Orientation {
  bearing: number;
  pitch: number;
}

async function readPosition(page: Page): Promise<Position> {
  return page.getByTestId('camera-position').evaluate((output) => ({
    x: Number(output.getAttribute('data-x')),
    y: Number(output.getAttribute('data-y')),
    z: Number(output.getAttribute('data-z')),
  }));
}

async function readOrientation(page: Page): Promise<Orientation> {
  return page.getByTestId('camera-orientation').evaluate((output) => ({
    bearing: Number(output.getAttribute('data-bearing-degrees')),
    pitch: Number(output.getAttribute('data-pitch-degrees')),
  }));
}

async function readSpeed(page: Page): Promise<number> {
  const speed = await page
    .getByTestId('flight-speed')
    .getAttribute('data-meters-per-second');
  return Number(speed);
}

function distance(from: Position, to: Position): number {
  return Math.hypot(to.x - from.x, to.y - from.y, to.z - from.z);
}

function sampleFixtureHeight(bytes: Buffer, x: number, z: number): number {
  const columns = 25;
  const rows = 19;
  const spacing = 2;
  const gridX = (x + 24) / spacing;
  const gridZ = (z + 18) / spacing;
  const column = Math.min(Math.floor(gridX), columns - 2);
  const row = Math.min(Math.floor(gridZ), rows - 2);
  const u = gridX - column;
  const v = gridZ - row;
  const valueAt = (sampleRow: number, sampleColumn: number): number =>
    bytes.readFloatLE((sampleRow * columns + sampleColumn) * 4);
  const a = valueAt(row, column);
  const b = valueAt(row, column + 1);
  const c = valueAt(row + 1, column);
  const d = valueAt(row + 1, column + 1);
  return u + v <= 1
    ? a + (b - a) * u + (c - a) * v
    : d + (c - d) * (1 - u) + (b - d) * (1 - v);
}

function sampleTerrainHeight(
  bytes: Buffer,
  columns: number,
  rows: number,
  spacing: number,
  width: number,
  depth: number,
  x: number,
  z: number,
): number | null {
  if (x < -width / 2 || x > width / 2 || z < -depth / 2 || z > depth / 2) {
    return null;
  }
  const gridX = (x + width / 2) / spacing;
  const gridZ = (z + depth / 2) / spacing;
  const column = Math.min(Math.floor(gridX), columns - 2);
  const row = Math.min(Math.floor(gridZ), rows - 2);
  const u = gridX - column;
  const v = gridZ - row;
  const valueAt = (sampleRow: number, sampleColumn: number): number =>
    bytes.readFloatLE((sampleRow * columns + sampleColumn) * 4);
  const a = valueAt(row, column);
  const b = valueAt(row, column + 1);
  const c = valueAt(row + 1, column);
  const d = valueAt(row + 1, column + 1);
  return u + v <= 1
    ? a + (b - a) * u + (c - a) * v
    : d + (c - d) * (1 - u) + (b - d) * (1 - v);
}

async function holdKey(
  page: Page,
  key: string,
  milliseconds = 220,
): Promise<void> {
  await page.keyboard.down(key);
  await page.waitForTimeout(milliseconds);
  await page.keyboard.up(key);
}

test('shows live synthetic flight state and supports browser navigation', async ({
  page,
}) => {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const failedRequests: string[] = [];
  const badResponses: string[] = [];

  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) =>
    pageErrors.push(`${error.name}: ${error.message}`),
  );
  page.on('requestfailed', (request) =>
    failedRequests.push(`${request.method()} ${request.url()}`),
  );
  page.on('response', (response) => {
    if (response.status() >= 400) {
      badResponses.push(`${response.status()} ${response.url()}`);
    }
  });

  await page.goto('/?world=m0');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-renderer-ready',
    'true',
  );
  await expect(page.locator('canvas.viewer-canvas')).toBeVisible();
  await expect(page.getByTestId('debug-hud')).toBeVisible();
  await expect(page.getByTestId('world-type')).toContainText('SYNTHETIC');
  await expect(page.getByTestId('flight-state')).toHaveAttribute(
    'data-locked',
    'false',
  );

  const spawn = await readPosition(page);
  const spawnOrientation = await readOrientation(page);
  expect(Object.values(spawn).every(Number.isFinite)).toBe(true);
  expect(Number.isFinite(spawnOrientation.bearing)).toBe(true);
  expect(Number.isFinite(spawnOrientation.pitch)).toBe(true);

  await page.getByRole('button', { name: 'Start exploring' }).click();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  await expect(page.getByTestId('flight-state')).toHaveAttribute(
    'data-locked',
    'true',
  );
  await expect(page.getByTestId('flight-speed')).toHaveAttribute(
    'data-meters-per-second',
    '15.00',
  );
  await expect(page.getByTestId('controls-help')).toBeVisible();
  await expect(page.getByTestId('frames-per-second')).toHaveAttribute(
    'data-fps',
    /^(?!0(?:\.0)?$)\d+(?:\.\d+)?$/,
  );

  const helpToggle = page.getByTestId('help-toggle');
  await expect(helpToggle).toHaveAttribute('aria-controls', 'controls-help');
  await expect(page.locator('[id="controls-help"]')).toHaveCount(1);
  await expect(helpToggle).toHaveAttribute('aria-expanded', 'true');
  await helpToggle.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByTestId('controls-help')).toBeHidden();
  await expect(helpToggle).toHaveAttribute('aria-expanded', 'false');
  await page.keyboard.press('Enter');
  await expect(page.getByTestId('controls-help')).toBeVisible();
  await expect(helpToggle).toHaveAttribute('aria-expanded', 'true');

  const afterForward = await readPosition(page);
  await holdKey(page, 'w');
  await expect
    .poll(async () => distance(afterForward, await readPosition(page)))
    .toBeGreaterThan(0.25);
  const movedForward = await readPosition(page);
  expect(movedForward.z).toBeLessThan(afterForward.z - 0.2);
  expect(movedForward.y).toBeLessThan(afterForward.y - 0.1);

  const beforeLeft = await readPosition(page);
  await holdKey(page, 'a');
  await expect
    .poll(async () => (await readPosition(page)).x)
    .toBeLessThan(beforeLeft.x - 0.2);
  const afterLeft = await readPosition(page);

  await holdKey(page, 'd');
  await expect
    .poll(async () => (await readPosition(page)).x)
    .toBeGreaterThan(afterLeft.x + 0.2);
  const afterRight = await readPosition(page);

  const beforeRise = await readPosition(page);
  await holdKey(page, 'Space');
  await expect
    .poll(async () => (await readPosition(page)).y)
    .toBeGreaterThan(beforeRise.y + 0.2);
  const afterRise = await readPosition(page);

  await holdKey(page, 'Control');
  await expect
    .poll(async () => (await readPosition(page)).y)
    .toBeLessThan(afterRise.y - 0.2);

  const beforeBoost = await readPosition(page);
  const baseSpeed = await readSpeed(page);
  await page.keyboard.down('Shift');
  await expect(page.getByTestId('flight-speed')).toHaveAttribute(
    'data-boosting',
    'true',
  );
  const boostedSpeed = await readSpeed(page);
  expect(boostedSpeed).toBeCloseTo(41.25, 2);
  expect(boostedSpeed).toBeGreaterThan(baseSpeed * 2);
  await page.keyboard.down('w');
  await page.waitForTimeout(220);
  await page.keyboard.up('w');
  await page.keyboard.up('Shift');
  await expect
    .poll(async () => distance(beforeBoost, await readPosition(page)))
    .toBeGreaterThan(1.5);
  const afterBoost = await readPosition(page);

  const beforeLook = await readOrientation(page);
  await page.mouse.move(560, 420);
  await page.mouse.move(700, 500, { steps: 8 });
  await expect
    .poll(async () => (await readOrientation(page)).bearing)
    .not.toBeCloseTo(beforeLook.bearing, 0);
  await expect
    .poll(async () => (await readOrientation(page)).pitch)
    .not.toBeCloseTo(beforeLook.pitch, 0);
  const afterLook = await readOrientation(page);

  const resetButton = page.getByTestId('reset-button');
  await resetButton.focus();
  await page.keyboard.press('Enter');
  await expect
    .poll(async () => distance(spawn, await readPosition(page)))
    .toBeLessThan(0.03);
  await holdKey(page, 'w', 120);
  await page.keyboard.press('r');
  await expect
    .poll(async () => distance(spawn, await readPosition(page)))
    .toBeLessThan(0.03);
  await expect
    .poll(async () =>
      Math.abs(
        (await readOrientation(page)).bearing - spawnOrientation.bearing,
      ),
    )
    .toBeLessThan(0.2);
  await expect
    .poll(async () =>
      Math.abs((await readOrientation(page)).pitch - spawnOrientation.pitch),
    )
    .toBeLessThan(0.2);
  await expect(page.getByTestId('flight-status-message')).toContainText(
    'reset',
  );
  await resetButton.evaluate((button) => button.blur());

  const screenshotBrowserEvidence = await page.evaluate(() => {
    const canvas = document.querySelector<HTMLCanvasElement>(
      'canvas.viewer-canvas',
    );
    if (!canvas) throw new Error('The renderer canvas is missing.');
    return {
      userAgent: navigator.userAgent,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      devicePixelRatio: window.devicePixelRatio,
      canvas: {
        cssWidth: canvas.clientWidth,
        cssHeight: canvas.clientHeight,
        width: canvas.width,
        height: canvas.height,
      },
    };
  });

  const screenshotPath = resolve(
    process.cwd(),
    'docs/milestones/screenshots/M0-synthetic.png',
  );
  await mkdir(dirname(screenshotPath), { recursive: true });
  await page.screenshot({ path: screenshotPath, animations: 'disabled' });

  await page.setViewportSize({ width: 960, height: 600 });
  const canvas = page.locator('canvas.viewer-canvas');
  await expect
    .poll(() =>
      canvas.evaluate((element) => ({
        cssWidth: element.clientWidth,
        cssHeight: element.clientHeight,
      })),
    )
    .toEqual({ cssWidth: 960, cssHeight: 600 });
  await expect
    .poll(() =>
      canvas.evaluate((element) => {
        const canvasElement = element as HTMLCanvasElement;
        const pixelRatio = Math.min(window.devicePixelRatio, 2);
        return (
          canvasElement.width ===
            Math.round(canvasElement.clientWidth * pixelRatio) &&
          canvasElement.height ===
            Math.round(canvasElement.clientHeight * pixelRatio)
        );
      }),
    )
    .toBe(true);
  const canvasMetrics = await canvas.evaluate((element) => {
    const canvasElement = element as HTMLCanvasElement;
    return {
      cssWidth: canvasElement.clientWidth,
      cssHeight: canvasElement.clientHeight,
      width: canvasElement.width,
      height: canvasElement.height,
      devicePixelRatio: window.devicePixelRatio,
    };
  });
  expect(canvasMetrics.width).toBe(
    Math.round(
      canvasMetrics.cssWidth * Math.min(canvasMetrics.devicePixelRatio, 2),
    ),
  );
  expect(canvasMetrics.height).toBe(
    Math.round(
      canvasMetrics.cssHeight * Math.min(canvasMetrics.devicePixelRatio, 2),
    ),
  );

  await page.keyboard.down('w');
  await page.waitForTimeout(150);
  await page.keyboard.press('Escape');
  const escapeReleased = await page
    .waitForFunction(
      () => document.pointerLockElement !== document.querySelector('canvas'),
      null,
      { timeout: 1_500 },
    )
    .then(() => true)
    .catch(() => false);
  expect(escapeReleased).toBe(true);
  await expect(page.getByTestId('flight-state')).toHaveAttribute(
    'data-locked',
    'false',
  );
  const atRelease = await readPosition(page);
  await page.waitForTimeout(250);
  expect(distance(atRelease, await readPosition(page))).toBeLessThan(0.03);
  await page.keyboard.up('w');
  await expect(
    page.getByRole('button', { name: 'Resume flying' }),
  ).toBeVisible();

  const browserEvidence = await page.evaluate(() => ({
    userAgent: navigator.userAgent,
    viewport: { width: window.innerWidth, height: window.innerHeight },
    devicePixelRatio: window.devicePixelRatio,
  }));
  test.info().annotations.push({
    type: 'browser-evidence',
    description: JSON.stringify({
      ...browserEvidence,
      screenshot: screenshotBrowserEvidence,
      canvas: canvasMetrics,
      spawn,
      movedForward,
      afterLeft,
      afterRight,
      afterRise,
      afterBoost,
      beforeLook,
      afterLook,
      escapeReleased,
      screenshotPath,
    }),
  });

  const evidencePath = resolve(
    process.cwd(),
    'test-results/browser-evidence.json',
  );
  await mkdir(dirname(evidencePath), { recursive: true });
  await writeFile(
    evidencePath,
    JSON.stringify(
      {
        screenshotPath,
        screenshotBrowserEvidence,
        resizedCanvas: canvasMetrics,
        spawn,
        movedForward,
        afterLeft,
        afterRight,
        afterRise,
        afterBoost,
        beforeLook,
        afterLook,
        escapeReleased,
      },
      null,
      2,
    ),
  );

  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(failedRequests).toEqual([]);
  expect(badResponses).toEqual([]);
});

test('loads and navigates the local synthetic heightfield terrain', async ({
  page,
}) => {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const failedRequests: string[] = [];
  const badResponses: string[] = [];
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
  page.on('response', (response) => {
    if (response.status() >= 400) {
      badResponses.push(`${response.status()} ${response.url()}`);
    }
  });

  await page.goto('/');
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded');
  await expect(shell).toHaveAttribute('data-renderer-ready', 'true');
  await expect(shell).toHaveAttribute('data-world-source', 'heightfield');
  await expect(shell).toHaveAttribute(
    'data-world-name',
    'SYNTHETIC · Synthetic Hill and Ridge Demo',
  );
  await expect(page.getByTestId('world-type')).toContainText(
    'Synthetic Hill and Ridge Demo',
  );
  await expect(page.getByTestId('world-source-mode')).toContainText(
    'LOCAL HEIGHTFIELD · SYNTHETIC',
  );
  await expect(page.getByTestId('terrain-details')).toHaveAttribute(
    'data-columns',
    '25',
  );
  await expect(page.getByTestId('terrain-details')).toHaveAttribute(
    'data-rows',
    '19',
  );
  await expect(page.getByTestId('ground-height')).toHaveAttribute(
    'data-outside',
    'false',
  );
  await expect(page.getByTestId('ground-height')).toHaveAttribute(
    'data-height-meters',
    /^-?\d+\.\d{4}$/,
  );
  expect(requestedUrls).toContain(
    'http://127.0.0.1:4173/worlds/synthetic-terrain-demo/manifest.json',
  );
  expect(requestedUrls).toContain(
    'http://127.0.0.1:4173/worlds/synthetic-terrain-demo/heightfield.f32',
  );
  await expect(page.locator('canvas.viewer-canvas')).toBeVisible();

  const gridToggle = page.getByTestId('grid-toggle');
  await expect(shell).toHaveAttribute('data-grid-visible', 'true');
  await gridToggle.click();
  await expect(shell).toHaveAttribute('data-grid-visible', 'false');
  await expect(gridToggle).toHaveAttribute('aria-pressed', 'false');
  await page.keyboard.press('g');
  await expect(shell).toHaveAttribute('data-grid-visible', 'true');
  await expect(gridToggle).toHaveAttribute('aria-pressed', 'true');

  const wireframeToggle = page.getByTestId('wireframe-toggle');
  await wireframeToggle.click();
  await expect(shell).toHaveAttribute('data-wireframe-visible', 'true');
  await expect(wireframeToggle).toHaveAttribute('aria-pressed', 'true');
  await wireframeToggle.click();
  await expect(shell).toHaveAttribute('data-wireframe-visible', 'false');

  await page.getByRole('button', { name: 'Start exploring' }).click();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  const spawn = await readPosition(page);
  const spawnOrientation = await readOrientation(page);
  const spawnGroundHeight = Number(
    await page.getByTestId('ground-height').getAttribute('data-height-meters'),
  );
  const fixtureBytes = await readFile(
    resolve(
      process.cwd(),
      'public/worlds/synthetic-terrain-demo/heightfield.f32',
    ),
  );
  expect(spawnGroundHeight).toBeCloseTo(
    sampleFixtureHeight(fixtureBytes, spawn.x, spawn.z),
    3,
  );

  const evidence = await page.evaluate(() => {
    const canvas = document.querySelector<HTMLCanvasElement>(
      'canvas.viewer-canvas',
    );
    if (!canvas) throw new Error('The terrain renderer canvas is missing.');
    return {
      userAgent: navigator.userAgent,
      viewport: { width: innerWidth, height: innerHeight },
      devicePixelRatio,
      canvas: {
        cssWidth: canvas.clientWidth,
        cssHeight: canvas.clientHeight,
        width: canvas.width,
        height: canvas.height,
      },
    };
  });
  const screenshotPath = resolve(
    process.cwd(),
    'docs/milestones/screenshots/M1-synthetic-heightfield.png',
  );
  await mkdir(dirname(screenshotPath), { recursive: true });
  await page.screenshot({ path: screenshotPath, animations: 'disabled' });

  await holdKey(page, 'w', 450);
  await expect
    .poll(async () => (await readPosition(page)).z)
    .toBeLessThan(spawn.z - 0.5);
  const moved = await readPosition(page);
  const movedGroundHeight = Number(
    await page.getByTestId('ground-height').getAttribute('data-height-meters'),
  );
  expect(Math.abs(movedGroundHeight - spawnGroundHeight)).toBeGreaterThan(
    0.0001,
  );
  expect(movedGroundHeight).toBeCloseTo(
    sampleFixtureHeight(fixtureBytes, moved.x, moved.z),
    3,
  );

  const beforeLook = await readOrientation(page);
  await page.mouse.move(560, 420);
  await page.mouse.move(700, 480, { steps: 8 });
  await expect
    .poll(async () => (await readOrientation(page)).bearing)
    .not.toBeCloseTo(beforeLook.bearing, 0);
  await expect
    .poll(async () => (await readOrientation(page)).pitch)
    .not.toBeCloseTo(beforeLook.pitch, 0);
  const afterLook = await readOrientation(page);

  await page.keyboard.press('Escape');
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement !== document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  await page.getByTestId('reset-button').click();
  await expect
    .poll(async () => distance(spawn, await readPosition(page)))
    .toBeLessThan(0.03);
  await expect
    .poll(async () =>
      Math.abs(
        (await readOrientation(page)).bearing - spawnOrientation.bearing,
      ),
    )
    .toBeLessThan(0.2);
  await expect
    .poll(async () =>
      Math.abs((await readOrientation(page)).pitch - spawnOrientation.pitch),
    )
    .toBeLessThan(0.2);

  await writeFile(
    resolve(process.cwd(), 'test-results/m1-browser-evidence.json'),
    JSON.stringify(
      {
        screenshotPath,
        ...evidence,
        spawn,
        moved,
        spawnGroundHeight,
        movedGroundHeight,
        beforeLook,
        afterLook,
      },
      null,
      2,
    ),
  );
  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(failedRequests).toEqual([]);
  expect(badResponses).toEqual([]);
});

test('shows missing and corrupt asset errors, retries, and returns to M0', async ({
  page,
}) => {
  let heightfieldRequests = 0;
  await page.route(
    '**/worlds/synthetic-terrain-demo/heightfield.f32',
    async (route) => {
      heightfieldRequests += 1;
      if (heightfieldRequests === 1) {
        await route.fulfill({ status: 404, body: 'synthetic missing asset' });
      } else if (heightfieldRequests === 3) {
        await route.fulfill({
          status: 200,
          contentType: 'application/octet-stream',
          body: Buffer.alloc(1900),
        });
      } else {
        await route.continue();
      }
    },
  );
  await page.goto('/');
  await expect(page.getByTestId('world-load-error')).toBeVisible();
  await expect(page.getByTestId('world-error-message')).toContainText(
    'heightfield request',
  );
  await expect(page.getByTestId('world-error-message')).toContainText(
    'HTTP 404',
  );
  await expect(page.getByTestId('return-m0')).toHaveAttribute(
    'href',
    '?world=m0',
  );

  await page.getByTestId('retry-world').click();
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-renderer-ready',
    'true',
  );
  await expect(page.getByTestId('world-load-error')).toBeHidden();
  await page.goto('/');
  await expect(page.getByTestId('world-load-error')).toBeVisible();
  await expect(page.getByTestId('world-error-message')).toContainText(
    'heightfield checksum',
  );
  await page.getByTestId('return-m0').click();
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-world-source',
    'analytic',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-renderer-ready',
    'true',
  );
});

test('loads and navigates the local EA terrain package', async ({ page }) => {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const failedRequests: string[] = [];
  const badResponses: string[] = [];
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
  page.on('response', (response) => {
    if (response.status() >= 400) {
      badResponses.push(`${response.status()} ${response.url()}`);
    }
  });

  await page.goto('/?world=torquay-poc-001');
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded');
  await expect(shell).toHaveAttribute('data-renderer-ready', 'true');
  await expect(shell).toHaveAttribute('data-world-source', 'heightfield');
  await expect(shell).toHaveAttribute(
    'data-world-name',
    'REAL EA DTM · TQ1 4HN candidate area of interest',
  );
  await expect(page.getByTestId('world-type')).toContainText('REAL EA DTM');
  await expect(page.getByTestId('world-source-mode')).toContainText(
    'EPSG:27700',
  );
  await expect(page.getByTestId('world-provenance')).toContainText(
    'REAL DATA · EA DTM 2022 composite',
  );
  await expect(page.getByTestId('provenance-badge')).toContainText(
    'REAL DATA · EA DTM 2022 composite',
  );
  await expect(page.getByTestId('vertical-reference')).toContainText('Newlyn');
  await expect(page.getByTestId('world-attribution')).toContainText(
    'Environment Agency copyright',
  );
  await expect(
    page.getByRole('link', { name: 'Publisher catalogue' }),
  ).toHaveAttribute(
    'href',
    'https://www.data.gov.uk/dataset/01b3ee39-da3f-47b6-83da-dc98e73a461f/lidar-composite-dtm-2022-1m',
  );
  await expect(
    page.getByRole('link', { name: 'Open Government Licence v3.0' }),
  ).toHaveAttribute(
    'href',
    'https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/',
  );
  await expect(page.getByTestId('terrain-details')).toHaveAttribute(
    'data-columns',
    '501',
  );
  await expect(page.getByTestId('terrain-details')).toHaveAttribute(
    'data-rows',
    '501',
  );
  await expect(page.getByTestId('ground-height')).toHaveAttribute(
    'data-orthometric-meters',
    /^-?\d+\.\d{4}$/,
  );
  expect(requestedUrls).toContain(
    'http://127.0.0.1:4173/worlds/torquay-poc-001/manifest.json',
  );
  expect(requestedUrls).toContain(
    'http://127.0.0.1:4173/worlds/torquay-poc-001/heightfield.f32',
  );

  const realHeightfield = await readFile(
    resolve(process.cwd(), 'public/worlds/torquay-poc-001/heightfield.f32'),
  );
  const resetPosition = await readPosition(page);
  const resetOrientation = await readOrientation(page);
  const initialLocalGround = Number(
    await page.getByTestId('ground-height').getAttribute('data-height-meters'),
  );
  const initialGroundAtCamera = sampleTerrainHeight(
    realHeightfield,
    501,
    501,
    2,
    1000,
    1000,
    resetPosition.x,
    resetPosition.z,
  );
  expect(initialGroundAtCamera).not.toBeNull();
  expect(initialLocalGround).toBeCloseTo(initialGroundAtCamera!, 3);

  await page.getByTestId('grid-toggle').click();
  await expect(shell).toHaveAttribute('data-grid-visible', 'false');
  await page.getByTestId('grid-toggle').click();
  await expect(shell).toHaveAttribute('data-grid-visible', 'true');
  await page.getByTestId('wireframe-toggle').click();
  await expect(shell).toHaveAttribute('data-wireframe-visible', 'true');
  await page.getByTestId('wireframe-toggle').click();

  await page.getByRole('button', { name: 'Start exploring' }).click();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  const screenshotPath = resolve(
    process.cwd(),
    'docs/milestones/screenshots/TVW-008-real-terrain.png',
  );
  await mkdir(dirname(screenshotPath), { recursive: true });
  await page.screenshot({ path: screenshotPath, animations: 'disabled' });

  const beforeMove = await readPosition(page);
  await holdKey(page, 'w', 350);
  const afterMove = await readPosition(page);
  expect(afterMove.z).toBeLessThan(beforeMove.z - 0.5);
  expect(distance(beforeMove, afterMove)).toBeGreaterThan(0.5);
  const groundAfterMove = Number(
    await page.getByTestId('ground-height').getAttribute('data-height-meters'),
  );
  const expectedGroundAfterMove = sampleTerrainHeight(
    realHeightfield,
    501,
    501,
    2,
    1000,
    1000,
    afterMove.x,
    afterMove.z,
  );
  expect(expectedGroundAfterMove).not.toBeNull();
  expect(groundAfterMove).toBeCloseTo(expectedGroundAfterMove!, 3);
  await page.keyboard.down('Shift');
  await expect(page.getByTestId('flight-speed')).toHaveAttribute(
    'data-boosting',
    'true',
  );
  const speed = await readSpeed(page);
  await page.keyboard.up('Shift');
  expect(speed).toBeCloseTo(41.25, 2);

  const beforeLook = await readOrientation(page);
  await page.mouse.move(600, 420);
  await page.mouse.move(710, 480, { steps: 8 });
  await expect
    .poll(async () => (await readOrientation(page)).bearing)
    .not.toBeCloseTo(beforeLook.bearing, 0);
  await expect
    .poll(async () => (await readOrientation(page)).pitch)
    .not.toBeCloseTo(beforeLook.pitch, 0);

  await page.keyboard.press('r');
  await expect
    .poll(async () => distance(resetPosition, await readPosition(page)))
    .toBeLessThan(0.03);
  await expect
    .poll(async () =>
      Math.abs(
        (await readOrientation(page)).bearing - resetOrientation.bearing,
      ),
    )
    .toBeLessThan(0.2);
  await expect
    .poll(async () =>
      Math.abs((await readOrientation(page)).pitch - resetOrientation.pitch),
    )
    .toBeLessThan(0.2);

  await page.keyboard.down('w');
  await page.waitForTimeout(150);
  await page.keyboard.press('Escape');
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement !== document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  await expect(page.getByTestId('flight-state')).toHaveAttribute(
    'data-locked',
    'false',
  );
  const positionAtUnlock = await readPosition(page);
  await page.waitForTimeout(250);
  expect(distance(positionAtUnlock, await readPosition(page))).toBeLessThan(
    0.03,
  );
  await page.keyboard.up('w');

  await page.waitForTimeout(2_500);
  const fpsSamples: number[] = [];
  for (let sample = 0; sample < 7; sample += 1) {
    const value = Number(
      await page.getByTestId('frames-per-second').getAttribute('data-fps'),
    );
    if (Number.isFinite(value) && value > 0) fpsSamples.push(value);
    await page.waitForTimeout(250);
  }
  expect(fpsSamples.length).toBeGreaterThanOrEqual(3);
  const sortedFps = [...fpsSamples].sort((left, right) => left - right);
  const medianFps = sortedFps[Math.floor(sortedFps.length / 2)]!;
  const browserEvidence = await page.evaluate(() => {
    const canvas = document.querySelector<HTMLCanvasElement>(
      'canvas.viewer-canvas',
    );
    if (!canvas) throw new Error('The renderer canvas is missing.');
    const context = canvas.getContext('webgl2') ?? canvas.getContext('webgl');
    const rendererExtension = context?.getExtension(
      'WEBGL_debug_renderer_info',
    );
    return {
      userAgent: navigator.userAgent,
      webglRenderer: context
        ? rendererExtension
          ? context.getParameter(rendererExtension.UNMASKED_RENDERER_WEBGL)
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
    };
  });
  expect(browserEvidence.canvas.width).toBe(1440);
  expect(browserEvidence.canvas.height).toBe(900);
  await mkdir(resolve(process.cwd(), 'test-results'), { recursive: true });
  await writeFile(
    resolve(process.cwd(), 'test-results/tvw-008-browser-evidence.json'),
    JSON.stringify(
      {
        ...browserEvidence,
        browserVersion: page.context().browser()?.version(),
        initialPosition: resetPosition,
        afterMove,
        initialLocalGround,
        groundAfterMove,
        fpsSamples,
        medianFps,
        screenshotPath,
      },
      null,
      2,
    ),
  );

  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(failedRequests).toEqual([]);
  expect(badResponses).toEqual([]);
});

test('explains an unavailable local EA package and recovers to synthetic terrain', async ({
  page,
}) => {
  await page.route('**/worlds/torquay-poc-001/manifest.json', (route) =>
    route.fulfill({ status: 404, body: 'package not generated' }),
  );
  await page.goto('/');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-load-state',
    'loaded',
  );
  await page.getByTestId('world-select-real').click();
  await expect(page.getByTestId('world-load-error')).toBeVisible();
  await expect(page.getByTestId('world-error-message')).toContainText(
    'HTTP 404',
  );
  await expect(page.getByTestId('world-error-message')).toContainText(
    'build-terrain',
  );
  await page.getByTestId('recover-synthetic').click();
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-load-state',
    'loaded',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-renderer-ready',
    'true',
  );
  await expect(page.getByTestId('world-provenance')).toContainText('SYNTHETIC');
});

test('rejects a corrupted real heightfield, retries, and recovers to synthetic terrain', async ({
  page,
}) => {
  let heightfieldRequests = 0;
  await page.route(
    '**/worlds/torquay-poc-001/heightfield.f32',
    async (route) => {
      heightfieldRequests += 1;
      if (heightfieldRequests === 1) {
        const response = await route.fetch();
        const corrupted = Buffer.from(await response.body());
        corrupted[0] = corrupted[0]! ^ 0x01;
        await route.fulfill({ response, body: corrupted });
      } else {
        await route.continue();
      }
    },
  );

  await page.goto('/?world=torquay-poc-001');
  await expect(page.getByTestId('world-load-error')).toBeVisible();
  await expect(page.getByTestId('world-error-message')).toContainText(
    'heightfield checksum',
  );
  expect(heightfieldRequests).toBe(1);

  await page.getByTestId('retry-world').click();
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-load-state',
    'loaded',
  );
  await expect(page.getByTestId('world-load-error')).toBeHidden();
  expect(heightfieldRequests).toBeGreaterThanOrEqual(2);

  await page.getByTestId('world-select-synthetic').click();
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-world-source',
    'heightfield',
  );
  await expect(page.getByTestId('world-provenance')).toContainText('SYNTHETIC');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-renderer-ready',
    'true',
  );
});
