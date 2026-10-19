import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
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

interface FootprintPolygon {
  exteriorXZ: [number, number][];
  interiorRingsXZ: [number, number][][];
}

interface BuildingPackage {
  buildings: Array<{
    geometry: { polygons: FootprintPolygon[] };
  }>;
}

async function position(page: Page): Promise<Position> {
  return page.getByTestId('camera-position').evaluate((node) => ({
    x: Number(node.getAttribute('data-x')),
    y: Number(node.getAttribute('data-y')),
    z: Number(node.getAttribute('data-z')),
  }));
}

async function orientation(page: Page): Promise<Orientation> {
  return page.getByTestId('camera-orientation').evaluate((node) => ({
    bearing: Number(node.getAttribute('data-bearing-degrees')),
    pitch: Number(node.getAttribute('data-pitch-degrees')),
  }));
}

async function holdKey(
  page: Page,
  key: string,
  durationMs = 250,
): Promise<void> {
  await page.keyboard.down(key);
  await page.waitForTimeout(durationMs);
  await page.keyboard.up(key);
}

function planarDistance(from: Position, to: Position): number {
  return Math.hypot(to.x - from.x, to.z - from.z);
}

function signedAngleDelta(target: number, current: number): number {
  return ((target - current + 540) % 360) - 180;
}

function pointInRing(
  point: Position,
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

function insideBuilding(
  point: Position,
  packageData: BuildingPackage,
): boolean {
  return packageData.buildings.some((building) =>
    building.geometry.polygons.some(
      (polygon) =>
        pointInRing(point, polygon.exteriorXZ) &&
        !polygon.interiorRingsXZ.some((hole) => pointInRing(point, hole)),
    ),
  );
}

function sampleHeightfield(
  bytes: Buffer,
  columns: number,
  rows: number,
  spacingM: number,
  widthM: number,
  depthM: number,
  x: number,
  z: number,
): number | null {
  if (x < -widthM / 2 || x > widthM / 2 || z < -depthM / 2 || z > depthM / 2) {
    return null;
  }
  const gridX = (x + widthM / 2) / spacingM;
  const gridZ = (z + depthM / 2) / spacingM;
  const column = Math.min(Math.floor(gridX), columns - 2);
  const row = Math.min(Math.floor(gridZ), rows - 2);
  const u = gridX - column;
  const v = gridZ - row;
  const at = (sampleRow: number, sampleColumn: number): number =>
    bytes.readFloatLE((sampleRow * columns + sampleColumn) * 4);
  const a = at(row, column);
  const b = at(row, column + 1);
  const c = at(row + 1, column);
  const d = at(row + 1, column + 1);
  return u + v <= 1
    ? a + (b - a) * u + (c - a) * v
    : d + (c - d) * (1 - u) + (b - d) * (1 - v);
}

async function clearance(page: Page): Promise<number> {
  return Number(
    await page
      .getByTestId('eye-clearance')
      .getAttribute('data-clearance-meters'),
  );
}

async function captureBrowserInfo(
  page: Page,
): Promise<Record<string, unknown>> {
  return page.evaluate(() => {
    const canvas = document.querySelector<HTMLCanvasElement>(
      'canvas.viewer-canvas',
    );
    if (!canvas) throw new Error('The viewer canvas is missing.');
    const context = canvas.getContext('webgl2') ?? canvas.getContext('webgl');
    const debug = context?.getExtension('WEBGL_debug_renderer_info');
    const mode = document.querySelector<HTMLElement>(
      '[data-testid="navigation-mode"]',
    );
    const speed = document.querySelector<HTMLOutputElement>(
      '[data-testid="flight-speed"]',
    );
    const height = document.querySelector<HTMLOutputElement>(
      '[data-testid="ground-height"]',
    );
    const eye = document.querySelector<HTMLOutputElement>(
      '[data-testid="eye-clearance"]',
    );
    const camera = document.querySelector<HTMLOutputElement>(
      '[data-testid="camera-position"]',
    );
    const orientation = document.querySelector<HTMLOutputElement>(
      '[data-testid="camera-orientation"]',
    );
    const fps = document.querySelector<HTMLOutputElement>(
      '[data-testid="frames-per-second"]',
    );
    return {
      userAgent: navigator.userAgent,
      viewport: { width: innerWidth, height: innerHeight },
      devicePixelRatio,
      renderer: context
        ? debug
          ? context.getParameter(debug.UNMASKED_RENDERER_WEBGL)
          : context.getParameter(context.RENDERER)
        : 'WebGL unavailable',
      canvas: {
        cssWidth: canvas.clientWidth,
        cssHeight: canvas.clientHeight,
        width: canvas.width,
        height: canvas.height,
      },
      worldMode: document
        .querySelector('.viewer-shell')
        ?.getAttribute('data-world-mode'),
      navigationMode: mode?.dataset.mode,
      speedMetersPerSecond: speed?.dataset.metersPerSecond,
      groundHeightM: height?.dataset.heightMeters,
      eyeClearanceM: eye?.dataset.clearanceMeters,
      cameraPositionM: {
        x: camera?.dataset.x,
        y: camera?.dataset.y,
        z: camera?.dataset.z,
      },
      cameraOrientationDegrees: {
        bearing: orientation?.dataset.bearingDegrees,
        pitch: orientation?.dataset.pitchDegrees,
      },
      framesPerSecond: fps?.dataset.fps,
    };
  });
}

async function saveEvidence(
  page: Page,
  screenshotName: string,
  evidenceName: string,
): Promise<void> {
  const screenshotPath = resolve(
    process.cwd(),
    'docs/milestones/screenshots',
    screenshotName,
  );
  const browser = await captureBrowserInfo(page);
  const metadata = {
    browserVersion: page.context().browser()?.version(),
    screenshotPath,
    ...browser,
  };
  await mkdir(resolve(process.cwd(), 'docs/milestones/screenshots'), {
    recursive: true,
  });
  await page.screenshot({ path: screenshotPath, animations: 'disabled' });
  await mkdir(resolve(process.cwd(), 'test-results'), { recursive: true });
  await writeFile(
    resolve(process.cwd(), 'test-results', evidenceName),
    JSON.stringify(metadata, null, 2),
  );
}

test('walk mode follows the synthetic heightfield and preserves flight semantics', async ({
  page,
}) => {
  await page.goto('/');
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded');
  await expect(shell).toHaveAttribute('data-renderer-ready', 'true');
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'fly',
  );

  await page.getByRole('button', { name: 'Start exploring' }).click();
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
  await page.evaluate(() =>
    window.dispatchEvent(
      new KeyboardEvent('keydown', {
        code: 'KeyF',
        repeat: true,
        bubbles: true,
      }),
    ),
  );
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'fly',
  );

  const spawn = await position(page);
  const spawnView = await orientation(page);
  await page.keyboard.down('Shift');
  await expect(page.getByTestId('flight-speed')).toHaveAttribute(
    'data-meters-per-second',
    '41.25',
  );
  await page.keyboard.up('Shift');

  await page.keyboard.press('f');
  await expect
    .poll(() => page.getByTestId('navigation-mode').getAttribute('data-mode'))
    .toMatch(/^(entering-walk|walk)$/);
  await expect
    .poll(() => page.getByTestId('navigation-mode').getAttribute('data-mode'), {
      timeout: 15_000,
    })
    .toBe('walk');
  const acquired = await position(page);
  const acquiredView = await orientation(page);
  expect(planarDistance(spawn, acquired)).toBeLessThan(0.03);
  expect(Math.abs(acquiredView.bearing - spawnView.bearing)).toBeLessThan(0.2);
  expect(Math.abs(acquiredView.pitch - spawnView.pitch)).toBeLessThan(0.2);
  expect(await clearance(page)).toBeCloseTo(1.7, 1);

  await holdKey(page, 'w', 320);
  const walked = await position(page);
  expect(planarDistance(acquired, walked)).toBeGreaterThan(1.5);
  await expect(page.getByTestId('flight-speed')).toHaveAttribute(
    'data-meters-per-second',
    '15.00',
  );
  expect(await clearance(page)).toBeCloseTo(1.7, 1);

  const beforeVerticalKeys = await position(page);
  await holdKey(page, 'Space', 180);
  await holdKey(page, 'Control', 180);
  const afterVerticalKeys = await position(page);
  expect(planarDistance(beforeVerticalKeys, afterVerticalKeys)).toBeLessThan(
    0.08,
  );
  expect(await clearance(page)).toBeCloseTo(1.7, 1);

  await page.keyboard.down('Shift');
  await expect(page.getByTestId('flight-speed')).toHaveAttribute(
    'data-meters-per-second',
    '41.25',
  );
  const beforeBoostWalk = await position(page);
  await page.keyboard.down('w');
  await page.waitForTimeout(220);
  await page.keyboard.up('w');
  await page.keyboard.up('Shift');
  const afterBoostWalk = await position(page);
  expect(planarDistance(beforeBoostWalk, afterBoostWalk)).toBeGreaterThan(2);
  expect(await clearance(page)).toBeCloseTo(1.7, 1);

  await page.keyboard.press('r');
  await expect
    .poll(async () => {
      const current = await position(page);
      return Math.hypot(current.x - spawn.x, current.z - spawn.z);
    })
    .toBeLessThan(0.03);
  expect(await clearance(page)).toBeCloseTo(1.7, 1);
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'walk',
  );
  const resetWalk = await position(page);

  await page.keyboard.press('f');
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'fly',
  );
  const flyPosition = await position(page);
  const flyView = await orientation(page);
  expect(
    Math.hypot(
      flyPosition.x - resetWalk.x,
      flyPosition.y - resetWalk.y,
      flyPosition.z - resetWalk.z,
    ),
  ).toBeLessThan(0.03);
  expect(Math.abs(flyView.bearing - spawnView.bearing)).toBeLessThan(0.2);
  expect(Math.abs(flyView.pitch - spawnView.pitch)).toBeLessThan(0.2);

  // Stay well above the terrain long enough that acquisition remains active
  // during the cancellation assertion below.
  await holdKey(page, 'Space', 1_000);
  await page.keyboard.press('f');
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'entering-walk',
  );
  await expect(page.getByTestId('walk-acquisition')).toBeVisible();
  await page.waitForTimeout(180);
  const beforeCancel = await position(page);
  await page.keyboard.press('f');
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'fly',
  );
  await expect(page.getByTestId('flight-status-message')).toContainText(
    'cancelled',
  );
  const afterCancel = await position(page);
  expect(planarDistance(beforeCancel, afterCancel)).toBeLessThan(0.03);
  await page.waitForTimeout(180);
  expect(Math.abs((await position(page)).y - afterCancel.y)).toBeLessThan(0.05);

  await page.keyboard.press('Escape');
  await expect(page.getByTestId('flight-state')).toHaveAttribute(
    'data-locked',
    'false',
  );
  await page.getByTestId('navigation-mode-toggle').click();
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'entering-walk',
  );
  await expect(page.getByTestId('walk-acquisition')).toBeVisible();
  // Acquisition pauses while unlocked; relock before waiting for the target.
  await page.getByRole('button', { name: 'Resume walking' }).click();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'walk',
  );
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('flight-state')).toHaveAttribute(
    'data-locked',
    'false',
  );
  await page.getByTestId('navigation-mode-toggle').click();
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'fly',
  );

  await page.getByRole('button', { name: 'Resume flying' }).click();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  await holdKey(page, 'Control', 900);
  const belowTerrain = await position(page);
  await page.keyboard.press('f');
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'fly',
  );
  await expect(page.getByTestId('flight-status-message')).toContainText(
    'below the sampled terrain',
  );
  expect(planarDistance(belowTerrain, await position(page))).toBeLessThan(0.03);
  await page.keyboard.press('Escape');
});

test('walk navigation works on the combined local EA terrain, buildings and roads route', async ({
  page,
}) => {
  test.setTimeout(90_000);
  const errors: string[] = [];
  page.on('pageerror', (error) =>
    errors.push(`${error.name}: ${error.message}`),
  );
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });

  await page.goto('/?world=torquay-poc-001&buildings=1&roads=1');
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded');
  await expect(shell).toHaveAttribute('data-renderer-ready', 'true');
  await expect(page.getByTestId('building-status')).toHaveAttribute(
    'data-state',
    'loaded',
    { timeout: 30_000 },
  );
  await expect(page.getByTestId('road-status')).toHaveAttribute(
    'data-state',
    'loaded',
    { timeout: 30_000 },
  );
  const terrainBytes = await readFile(
    resolve(process.cwd(), 'public/worlds/torquay-poc-001/heightfield.f32'),
  );

  await page.getByRole('button', { name: 'Start exploring' }).click();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  const flyBeforeWalk = await position(page);
  const flyView = await orientation(page);
  await page.keyboard.press('f');
  await expect
    .poll(() => page.getByTestId('navigation-mode').getAttribute('data-mode'), {
      timeout: 5_000,
    })
    .toBe('entering-walk');
  await expect(page.getByTestId('walk-acquisition')).toBeVisible();
  await expect(page.getByTestId('walk-acquisition')).toHaveAttribute(
    'data-remaining-meters',
    /^-?\d+\.\d{4}$/,
  );
  await expect
    .poll(() => page.getByTestId('navigation-mode').getAttribute('data-mode'), {
      timeout: 15_000,
    })
    .toBe('walk');
  const walkStart = await position(page);
  expect(planarDistance(flyBeforeWalk, walkStart)).toBeLessThan(0.03);
  expect(await clearance(page)).toBeCloseTo(1.7, 1);
  await expect(page.getByTestId('world-attribution')).toContainText(
    'Environment Agency copyright',
  );
  await expect(page.getByTestId('building-attribution')).toContainText(
    'OpenStreetMap contributors',
  );
  await expect(page.getByTestId('road-attribution')).toContainText(
    'OpenStreetMap contributors',
  );

  // Use the existing development-only QA camera hook for a deterministic,
  // separately reviewed footprint-free street-level screenshot pose. The
  // pose is local scene evidence, not a source coordinate; actual walk
  // movement is exercised below.
  const buildingPackage = JSON.parse(
    await readFile(
      resolve(
        process.cwd(),
        'public/worlds/torquay-poc-001/buildings/buildings.json',
      ),
      'utf8',
    ),
  ) as BuildingPackage;
  const targetGroundHeight = sampleHeightfield(
    terrainBytes,
    501,
    501,
    2,
    1000,
    1000,
    0,
    360,
  );
  if (targetGroundHeight === null) {
    throw new Error('The street-level QA pose must lie within the terrain.');
  }
  const currentView = await orientation(page);
  await page.evaluate(
    (pose) => {
      const qa = (
        window as unknown as {
          __torquayAlignmentQa?: {
            setPose: (next: {
              x: number;
              y: number;
              z: number;
              bearingDegrees: number;
              pitchDegrees: number;
            }) => void;
          };
        }
      ).__torquayAlignmentQa;
      if (!qa)
        throw new Error('The development-only QA camera hook is missing.');
      qa.setPose(pose);
    },
    {
      x: 0,
      y: targetGroundHeight + 1.7,
      z: 360,
      bearingDegrees: currentView.bearing,
      pitchDegrees: currentView.pitch,
    },
  );
  const groundEyePose = await position(page);
  expect(Math.abs(groundEyePose.x)).toBeLessThan(0.02);
  expect(Math.abs(groundEyePose.z - 360)).toBeLessThan(0.02);
  expect(insideBuilding(groundEyePose, buildingPackage)).toBe(false);
  expect(await clearance(page)).toBeCloseTo(1.7, 1);

  await page.keyboard.press('h');
  await expect(page.getByTestId('controls-help')).toBeHidden();
  // Raise the view from the default downward spawn angle so the walk capture
  // shows the road/building corridor at eye height.
  let mouseX = 720;
  let mouseY = 450;
  await page.mouse.move(mouseX, mouseY);
  await page.waitForTimeout(120);
  const initialWalkView = await orientation(page);
  const targetWalkBearing = -105;
  mouseX += Math.round(
    signedAngleDelta(targetWalkBearing, initialWalkView.bearing) / 0.0825,
  );
  await page.mouse.move(mouseX, mouseY, { steps: 12 });
  await page.waitForTimeout(120);
  const adjustedWalkBearing = await orientation(page);
  const targetWalkPitch = -14;
  const walkPitchCorrection =
    -(targetWalkPitch - adjustedWalkBearing.pitch) / 0.0825;
  mouseY += Math.round(walkPitchCorrection);
  await page.mouse.move(mouseX, mouseY, { steps: 8 });
  await page.waitForTimeout(120);
  const adjustedWalkView = await orientation(page);
  const remainingPitchCorrection =
    -(targetWalkPitch - adjustedWalkView.pitch) / 0.0825;
  if (Math.abs(remainingPitchCorrection) > 1) {
    mouseY += Math.round(remainingPitchCorrection);
    await page.mouse.move(mouseX, mouseY, { steps: 8 });
    await page.waitForTimeout(120);
  }
  await expect
    .poll(async () =>
      Math.abs(
        signedAngleDelta(targetWalkBearing, (await orientation(page)).bearing),
      ),
    )
    .toBeLessThan(3);
  await expect
    .poll(async () => (await orientation(page)).pitch)
    .toBeGreaterThan(-16);
  await expect
    .poll(async () => (await orientation(page)).pitch)
    .toBeLessThan(-12);
  await saveEvidence(
    page,
    'TVW-013-walking-combined.png',
    'tvw-013-walk-evidence.json',
  );

  const beforeWalk = await position(page);
  const groundBeforeWalk = Number(
    await page.getByTestId('ground-height').getAttribute('data-height-meters'),
  );
  await holdKey(page, 'w', 350);
  const afterWalk = await position(page);
  expect(planarDistance(beforeWalk, afterWalk)).toBeGreaterThan(2);
  expect(await clearance(page)).toBeCloseTo(1.7, 1);
  const ground = Number(
    await page.getByTestId('ground-height').getAttribute('data-height-meters'),
  );
  expect(Number.isFinite(ground)).toBe(true);
  expect(ground).toBeCloseTo(
    sampleHeightfield(
      terrainBytes,
      501,
      501,
      2,
      1000,
      1000,
      afterWalk.x,
      afterWalk.z,
    )!,
    3,
  );
  expect(Math.abs(ground - groundBeforeWalk)).toBeGreaterThan(0.001);

  await holdKey(page, 's', 350);
  const afterReverse = await position(page);
  const groundAfterReverse = Number(
    await page.getByTestId('ground-height').getAttribute('data-height-meters'),
  );
  expect(planarDistance(afterWalk, afterReverse)).toBeGreaterThan(2);
  expect(await clearance(page)).toBeCloseTo(1.7, 1);
  expect(groundAfterReverse).toBeCloseTo(
    sampleHeightfield(
      terrainBytes,
      501,
      501,
      2,
      1000,
      1000,
      afterReverse.x,
      afterReverse.z,
    )!,
    3,
  );

  const beforeFly = await position(page);
  const beforeFlyView = await orientation(page);
  await page.keyboard.press('f');
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'fly',
  );
  const afterFly = await position(page);
  const afterFlyView = await orientation(page);
  expect(
    Math.hypot(
      afterFly.x - beforeFly.x,
      afterFly.y - beforeFly.y,
      afterFly.z - beforeFly.z,
    ),
  ).toBeLessThan(0.03);
  expect(Math.abs(afterFlyView.bearing - beforeFlyView.bearing)).toBeLessThan(
    0.2,
  );
  expect(Math.abs(afterFlyView.pitch - beforeFlyView.pitch)).toBeLessThan(0.2);
  await page.keyboard.press('r');
  await expect
    .poll(async () => (await position(page)).y)
    .toBeGreaterThan(afterFly.y + 10);
  await saveEvidence(
    page,
    'TVW-013-flying-combined.png',
    'tvw-013-fly-evidence.json',
  );

  await page.keyboard.down('w');
  await page.waitForTimeout(180);
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('flight-state')).toHaveAttribute(
    'data-locked',
    'false',
  );
  const released = await position(page);
  await page.waitForTimeout(250);
  const afterUnlock = await position(page);
  expect(planarDistance(released, afterUnlock)).toBeLessThan(0.03);
  await page.keyboard.up('w');
  expect(errors).toEqual([]);
  await writeFile(
    resolve(process.cwd(), 'test-results/tvw-013-combined-browser.json'),
    JSON.stringify(
      {
        browserVersion: page.context().browser()?.version(),
        originalView: flyView,
        walkStart,
        afterWalk,
        beforeFly,
        afterFly,
        ground,
        clearanceM: await clearance(page),
      },
      null,
      2,
    ),
  );
});
