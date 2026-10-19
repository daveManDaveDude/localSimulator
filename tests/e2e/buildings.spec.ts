import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { expect, test } from '@playwright/test';

async function readPosition(page: import('@playwright/test').Page) {
  const output = page.getByTestId('camera-position');
  return {
    x: Number(await output.getAttribute('data-x')),
    y: Number(await output.getAttribute('data-y')),
    z: Number(await output.getAttribute('data-z')),
  };
}

async function readOrientation(page: import('@playwright/test').Page) {
  const output = page.getByTestId('camera-orientation');
  return {
    bearing: Number(await output.getAttribute('data-bearing-degrees')),
    pitch: Number(await output.getAttribute('data-pitch-degrees')),
  };
}

function signedAngleDelta(target: number, current: number): number {
  return ((target - current + 540) % 360) - 180;
}

function pointInRing(
  point: { x: number; z: number },
  ring: readonly [number, number][],
): boolean {
  let inside = false;
  for (
    let current = 0, previous = ring.length - 1;
    current < ring.length;
    previous = current++
  ) {
    const [currentX, currentZ] = ring[current]!;
    const [previousX, previousZ] = ring[previous]!;
    const crosses =
      currentZ > point.z !== previousZ > point.z &&
      point.x <
        ((previousX - currentX) * (point.z - currentZ)) /
          (previousZ - currentZ) +
          currentX;
    if (crosses) inside = !inside;
  }
  return inside;
}

interface FootprintPackage {
  buildings: Array<{
    geometry: {
      polygons: Array<{
        exteriorXZ: [number, number][];
        interiorRingsXZ: [number, number][][];
      }>;
    };
  }>;
}

function isInsideBuilding(
  point: { x: number; z: number },
  packageData: FootprintPackage,
): boolean {
  return packageData.buildings.some((building) =>
    building.geometry.polygons.some(
      (polygon) =>
        pointInRing(point, polygon.exteriorXZ) &&
        !polygon.interiorRingsXZ.some((hole) => pointInRing(point, hole)),
    ),
  );
}

test('loads the opt-in OSM layer, keeps terrain navigation, and captures both views', async ({
  page,
  browserName,
}) => {
  test.setTimeout(180_000);
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

  await page.goto('/?world=torquay-poc-001&buildings=1');
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded');
  await expect(shell).toHaveAttribute('data-renderer-ready', 'true');
  await expect(shell).toHaveAttribute('data-building-state', 'loaded');
  await expect(shell).toHaveAttribute('data-building-count', '1000');
  await expect(shell).toHaveAttribute('data-building-components', '1002');
  await expect(page.getByTestId('building-status')).toContainText(
    '1,000 footprints / 1,002 components',
  );
  await expect(page.getByTestId('building-status')).toContainText(
    '0 tagged-but-unverified heights, 2 level estimates, 998 default estimates',
  );
  await expect(page.getByTestId('building-extract-vintage')).toHaveText(
    'OSM extract vintage: 2026-10-16T20:21:21Z.',
  );
  await expect(page.getByTestId('building-policy')).toBeVisible();
  await expect(page.getByTestId('building-attribution')).toContainText(
    'OpenStreetMap contributors',
  );
  await expect(
    page.getByRole('link', { name: 'ODbL 1.0 attribution and licence' }),
  ).toHaveAttribute('href', 'https://www.openstreetmap.org/copyright');

  const localOrigin = new URL(page.url()).origin;
  expect(requestedUrls).toContain(
    `${localOrigin}/worlds/torquay-poc-001/buildings/manifest.json`,
  );
  expect(requestedUrls).toContain(
    `${localOrigin}/worlds/torquay-poc-001/buildings/buildings.json`,
  );
  expect(requestedUrls).toContain(
    `${localOrigin}/worlds/torquay-poc-001/buildings/qa.json`,
  );
  expect(
    requestedUrls.every((url) => new URL(url).origin === localOrigin),
  ).toBe(true);

  const initialMeshCount = Number(
    await shell.getAttribute('data-building-mesh-count'),
  );
  expect(initialMeshCount).toBeGreaterThan(0);
  const drawCalls = Number(await shell.getAttribute('data-draw-calls'));
  const triangles = Number(await shell.getAttribute('data-triangles'));
  expect(drawCalls).toBeGreaterThan(0);
  expect(triangles).toBeGreaterThan(0);
  const visibilityButton = page.getByTestId('buildings-toggle');
  await visibilityButton.click();
  await expect(shell).toHaveAttribute('data-building-visible', 'false');
  await expect(visibilityButton).toHaveAttribute('aria-pressed', 'false');
  await expect(page.getByTestId('building-status')).toContainText(
    '0 tagged-but-unverified heights, 2 level estimates, 998 default estimates',
  );
  await expect(shell).toHaveAttribute(
    'data-building-mesh-count',
    String(initialMeshCount),
  );
  await visibilityButton.click();
  await expect(shell).toHaveAttribute('data-building-visible', 'true');
  await expect(visibilityButton).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByTestId('building-status')).toContainText(
    '0 tagged-but-unverified heights, 2 level estimates, 998 default estimates',
  );

  const screenshotDirectory = resolve(
    process.cwd(),
    'docs/milestones/screenshots',
  );
  await mkdir(screenshotDirectory, { recursive: true });
  const overheadPath = resolve(
    screenshotDirectory,
    'TVW-010-buildings-overhead.png',
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
  await page.keyboard.press('h');
  await expect(page.getByTestId('controls-help')).toBeVisible();
  await page.keyboard.press('h');
  await expect(page.getByTestId('controls-help')).toBeHidden();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  await page.keyboard.press('r');
  await page.screenshot({ path: overheadPath, animations: 'disabled' });

  const initialPosition = await readPosition(page);
  const positionAtFrontage = await readPosition(page);
  expect(positionAtFrontage.x).toBeCloseTo(0, 0);
  expect(positionAtFrontage.z).toBeCloseTo(initialPosition.z, 1);
  const footprintPackage = JSON.parse(
    await readFile(
      resolve(
        process.cwd(),
        'public/worlds/torquay-poc-001/buildings/buildings.json',
      ),
      'utf8',
    ),
  ) as FootprintPackage;
  expect(isInsideBuilding(positionAtFrontage, footprintPackage)).toBe(false);

  // Use cruise-speed descent so a slow browser frame cannot overshoot the
  // ground-eye capture after the project speed was doubled.
  await page.keyboard.down('Control');
  await page.waitForFunction(
    () => {
      const position = document.querySelector<HTMLOutputElement>(
        '[data-testid="camera-position"]',
      );
      const ground = document.querySelector<HTMLOutputElement>(
        '[data-testid="ground-height"]',
      );
      if (!position || !ground) return false;
      return (
        Number(position.dataset.y) - Number(ground.dataset.heightMeters) <= 5
      );
    },
    { polling: 20, timeout: 30_000 },
  );
  await page.keyboard.up('Control');
  const positionAtGroundEye = await readPosition(page);
  const groundAtGroundEye = Number(
    await page.getByTestId('ground-height').getAttribute('data-height-meters'),
  );
  const altitudeAboveGround = positionAtGroundEye.y - groundAtGroundEye;
  expect(altitudeAboveGround).toBeGreaterThan(0);
  expect(altitudeAboveGround).toBeLessThan(5.5);

  // Face north across the terrain from the existing spawn pose. This keeps
  // the closest footprint in the scene without turning the camera into a wall.
  // Pointer-lock mouse deltas are real browser input; orientation is read back
  // from app telemetry before applying a measured correction.
  await page.mouse.move(720, 450);
  await page.waitForTimeout(200);
  let orientation = await readOrientation(page);
  const bearingCorrection = signedAngleDelta(0, orientation.bearing);
  await page.mouse.move(720 + Math.round(bearingCorrection / 0.0825), 450, {
    steps: 8,
  });
  await page.waitForTimeout(200);
  orientation = await readOrientation(page);
  const pitchCorrection = -(-7 - orientation.pitch) / 0.0825;
  await page.mouse.move(
    Math.round(720 + bearingCorrection / 0.0825),
    450 + Math.round(pitchCorrection),
    { steps: 8 },
  );
  await page.waitForTimeout(300);
  orientation = await readOrientation(page);
  expect(Math.abs(signedAngleDelta(0, orientation.bearing))).toBeLessThan(3);
  expect(Math.abs(-7 - orientation.pitch)).toBeLessThan(3);
  const groundEyePath = resolve(
    screenshotDirectory,
    'TVW-010-buildings-ground-eye.png',
  );
  await page.addStyleTag({
    content:
      '.viewer-topline,.world-selector,.debug-hud,.building-controls,.controls-help,.corner-note,.start-card{visibility:hidden!important}',
  });
  await page.screenshot({ path: groundEyePath, animations: 'disabled' });

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

  await page.waitForTimeout(2_000);
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
    };
  });
  const evidencePath = resolve(
    process.cwd(),
    'test-results/tvw-010-browser-evidence.json',
  );
  await mkdir(dirname(evidencePath), { recursive: true });
  await writeFile(
    evidencePath,
    JSON.stringify(
      {
        ...browserEvidence,
        browserName,
        browserVersion: page.context().browser()?.version(),
        initialPosition,
        frontagePosition: positionAtFrontage,
        groundEyeOrientation: orientation,
        groundEyePosition: await readPosition(page),
        groundEyeAltitudeM:
          (await readPosition(page)).y -
          Number(
            await page
              .getByTestId('ground-height')
              .getAttribute('data-height-meters'),
          ),
        buildings: {
          features: Number(await shell.getAttribute('data-building-count')),
          components: Number(
            await shell.getAttribute('data-building-components'),
          ),
          meshCount: initialMeshCount,
        },
        renderStats: { drawCalls, triangles },
        fpsSamples,
        medianFps,
        screenshots: [overheadPath, groundEyePath],
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

test('keeps terrain usable when the building manifest is unavailable and supports retry', async ({
  page,
}) => {
  let manifestRequests = 0;
  await page.route(
    '**/worlds/torquay-poc-001/buildings/manifest.json',
    async (route) => {
      manifestRequests += 1;
      if (manifestRequests === 1) {
        await route.fulfill({ status: 404, body: 'local package is absent' });
      } else {
        await route.continue();
      }
    },
  );
  await page.goto('/?world=torquay-poc-001&buildings=1');
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded');
  await expect(shell).toHaveAttribute('data-building-state', 'error');
  await expect(page.getByTestId('building-error')).toBeVisible();
  await expect(page.getByTestId('building-error-message')).toContainText(
    'manifest request',
  );
  await expect(page.getByTestId('building-error-message')).toContainText(
    'publish-buildings',
  );
  await expect(page.getByTestId('terrain-details')).toContainText(
    '501 columns',
  );
  await page.getByTestId('buildings-terrain-only').click();
  await expect(shell).toHaveAttribute('data-building-state', 'off');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded');
  await page.getByTestId('buildings-toggle').click();
  await expect(shell).toHaveAttribute('data-building-state', 'loaded');
  expect(manifestRequests).toBeGreaterThanOrEqual(2);
});

test('rejects corrupt building payload and QA hashes without hiding terrain', async ({
  page,
}) => {
  let corruptPayload = true;
  let corruptQa = true;
  await page.route(
    '**/worlds/torquay-poc-001/buildings/buildings.json',
    async (route) => {
      if (!corruptPayload) return route.continue();
      corruptPayload = false;
      const response = await route.fetch();
      const bytes = Buffer.from(await response.body());
      bytes[0] = bytes[0]! ^ 1;
      await route.fulfill({ response, body: bytes });
    },
  );
  await page.route(
    '**/worlds/torquay-poc-001/buildings/qa.json',
    async (route) => {
      if (!corruptQa) return route.continue();
      corruptQa = false;
      const response = await route.fetch();
      const bytes = Buffer.from(await response.body());
      bytes[0] = bytes[0]! ^ 1;
      await route.fulfill({ response, body: bytes });
    },
  );

  await page.goto('/?world=torquay-poc-001&buildings=1');
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-building-state', 'error');
  await expect(page.getByTestId('building-error-message')).toContainText(
    'SHA-256 mismatch',
  );
  await expect(shell).toHaveAttribute('data-load-state', 'loaded');
  await page.getByTestId('buildings-retry').click();
  await expect(shell).toHaveAttribute('data-building-state', 'loaded');

  await page.getByTestId('buildings-toggle').click();
  await page.getByTestId('buildings-toggle').click();
  await expect(shell).toHaveAttribute('data-building-visible', 'true');
});
