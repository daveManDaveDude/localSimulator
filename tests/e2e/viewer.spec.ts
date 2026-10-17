import { mkdir, writeFile } from 'node:fs/promises';
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

  await page.goto('/');
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
