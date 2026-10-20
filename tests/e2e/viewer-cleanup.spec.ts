import { expect, test, type Page } from '@playwright/test';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const real = process.env.VIEWER_CLEANUP_PROFILE === 'real';
const evidenceDir = resolve('docs/milestones/artifacts/Viewer-cleanup');
const screenshotDir = resolve('docs/milestones/screenshots/Viewer-cleanup');
const readyPath = '/worlds/torquay-poc-001-2km/ready.json';
const visibleLabelSelector =
  '.road-name-label:not(.road-name-measure):not([hidden])';

async function expectedCurrentRoadNames() {
  const root = resolve('public/worlds/torquay-poc-001-2km');
  const pointer = JSON.parse(
    await readFile(resolve(root, 'ready.json'), 'utf8'),
  ) as { releaseId: string };
  expect(pointer.releaseId).toMatch(/^[a-f0-9]{64}$/);
  const roads = JSON.parse(
    await readFile(
      resolve(root, 'releases', pointer.releaseId, 'roads/roads.json'),
      'utf8',
    ),
  ) as {
    features: Array<{
      source: { osmId: number };
      sourceTags: { name?: string };
      centerlinePartsXZ: unknown[];
    }>;
  };
  const names = new Map<string, string>();
  for (const feature of roads.features) {
    const name = feature.sourceTags.name?.trim();
    if (name)
      feature.centerlinePartsXZ.forEach((_, index) =>
        names.set(`${feature.source.osmId}:${index}`, name),
      );
  }
  return { releaseId: pointer.releaseId, names };
}

async function observeLabels(page: Page) {
  return page.locator(visibleLabelSelector).evaluateAll((elements) =>
    elements.map((element) => ({
      name: element.textContent ?? '',
      key: element.getAttribute('data-road-label-key') ?? '',
      distanceM: Number(element.getAttribute('data-distance-meters')),
    })),
  );
}

async function assertDefaultLabels(page: Page, expected: Map<string, string>) {
  await expect
    .poll(() => page.locator(visibleLabelSelector).count())
    .toBeGreaterThan(0);
  const labels = await observeLabels(page);
  expect(labels.length).toBeLessThanOrEqual(20);
  expect(new Set(labels.map((label) => label.name)).size).toBe(labels.length);
  for (const label of labels) {
    expect(label.name).toBe(expected.get(label.key));
    expect(label.distanceM).toBeGreaterThanOrEqual(0);
    expect(label.distanceM).toBeLessThanOrEqual(500);
  }
  await expect
    .poll(() =>
      page.evaluate((selector) => {
        const rects = [...document.querySelectorAll(selector)].map((element) =>
          element.getBoundingClientRect(),
        );
        const panel = document
          .querySelector('.product-controls')!
          .getBoundingClientRect();
        const overlaps = (a: DOMRect, b: DOMRect) =>
          a.left < b.right &&
          a.right > b.left &&
          a.top < b.bottom &&
          a.bottom > b.top;
        return rects.some(
          (rect, index) =>
            overlaps(rect, panel) ||
            rects.slice(index + 1).some((other) => overlaps(rect, other)),
        );
      }, visibleLabelSelector),
    )
    .toBe(false);
  await expect(page.locator('.road-label-overlay')).toHaveCSS(
    'pointer-events',
    'none',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-road-qa-marker-count',
    '0',
  );
  return labels;
}

async function ready(page: Page, mode: 'real' | 'synthetic' | 'm0') {
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-renderer-ready', 'true', {
    timeout: 120_000,
  });
  await expect(shell).toHaveAttribute('data-world-mode', mode);
  await expect(shell).toHaveAttribute('data-grid-visible', 'false');
  if (mode !== 'real')
    await expect(page.locator(visibleLabelSelector)).toHaveCount(0);
  await expect(page.getByTestId('debug-hud')).toBeHidden();
  for (const id of [
    'world-select-real',
    'world-select-synthetic',
    'world-select-historical-1km',
    'grid-toggle',
    'wireframe-toggle',
    'roads-wireframe-toggle',
    'road-landmark-select',
    'buildings-toggle',
    'roads-toggle',
    'street-names-toggle',
    'overview-toggle',
  ]) {
    await expect(page.getByTestId(id)).toBeHidden();
  }
  await expect(
    page.getByRole('navigation', { name: 'Choose a local world' }),
  ).toHaveCount(0);
  await expect(
    page.getByRole('button', {
      name: /wireframe|grid|Load OSM|Hide OSM|Open overview|Street names/i,
    }),
  ).toHaveCount(0);
}

async function screenshot(page: Page, name: string) {
  await mkdir(screenshotDir, { recursive: true });
  await page.screenshot({ path: resolve(screenshotDir, `${name}.png`) });
}

async function position(page: Page) {
  return page.getByTestId('camera-position').evaluate((element) => ({
    x: Number(element.getAttribute('data-x')),
    y: Number(element.getAttribute('data-y')),
    z: Number(element.getAttribute('data-z')),
  }));
}

async function lock(page: Page) {
  await page.getByTestId('start-button').click();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);
}

async function move(page: Page, key: string, milliseconds = 700) {
  await page.keyboard.down(key);
  await page.waitForTimeout(milliseconds);
  await page.keyboard.up(key);
}

async function moveUntil(
  page: Page,
  key: string,
  reached: () => Promise<boolean>,
) {
  await page.keyboard.down(key);
  try {
    // Software rendering can advance movement slowly. Observe the camera
    // instead of assuming a fixed number of frames within a wall-clock delay.
    await expect.poll(reached, { timeout: 45_000 }).toBe(true);
  } finally {
    await page.keyboard.up(key);
  }
}

test('default real map loads all layers, retains navigation, and exposes compact honest sources', async ({
  page,
  browser,
}) => {
  test.skip(!real, 'Requires the locally published current package.');
  const requests: string[] = [];
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  const failedResponses: string[] = [];
  page.on('request', (request) => requests.push(request.url()));
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('response', (response) => {
    if (response.status() >= 400)
      failedResponses.push(`${response.status()} ${response.url()}`);
  });
  const started = Date.now();
  const sourceNames = await expectedCurrentRoadNames();
  await page.goto('/');
  await ready(page, 'real');
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-scene-profile', 'current_2km');
  await expect(shell).toHaveAttribute('data-building-state', 'loaded', {
    timeout: 120_000,
  });
  await expect(shell).toHaveAttribute('data-road-state', 'loaded', {
    timeout: 120_000,
  });
  await expect(shell).toHaveAttribute('data-building-count', '3613');
  await expect(shell).toHaveAttribute('data-road-way-count', '1044');
  await assertDefaultLabels(page, sourceNames.names);
  await expect(page.getByTestId('real-package-extent-notice')).toHaveText(
    '2 km candidate · AOI pending; feature coverage not checked.',
  );
  await expect(page.getByTestId('map-credit')).toContainText(
    'OpenStreetMap contributors',
  );
  await expect(page.getByTestId('terrain-details')).toHaveText(
    '1001 columns × 1001 rows · 2 m spacing',
  );
  const sources = page.getByTestId('sources');
  await sources.locator('summary').click();
  await expect(page.getByTestId('world-attribution')).toContainText(
    'Environment Agency copyright',
  );
  await expect(sources).toContainText('16 October 2026');
  await expect(sources).toContainText('no numeric offset was measured');
  await expect(
    sources.getByRole('link', { name: 'ODbL 1.0 attribution and licence' }),
  ).toHaveAttribute('href', 'https://www.openstreetmap.org/copyright');
  await sources
    .getByRole('link', { name: 'EA time-stamped products' })
    .scrollIntoViewIfNeeded();
  await expect(
    sources.getByRole('link', { name: 'EA time-stamped products' }),
  ).toBeInViewport();
  await assertDefaultLabels(page, sourceNames.names);
  await screenshot(page, 'sources');
  await sources.locator('summary').click();
  await screenshot(page, 'default-map');
  const start = await position(page);
  await lock(page);
  await page.keyboard.press('h');
  await expect(page.getByTestId('controls-help')).toBeHidden();
  await page.keyboard.press('g');
  await expect(shell).toHaveAttribute('data-grid-visible', 'false');
  const labelsAtStart = await assertDefaultLabels(page, sourceNames.names);
  await screenshot(page, 'labels-active-no-marker');
  await screenshot(page, 'active-overview');
  const bearing = await page
    .getByTestId('camera-orientation')
    .getAttribute('data-bearing-degrees');
  await page.mouse.move(720, 480);
  await page.mouse.move(765, 480, { steps: 6 });
  await expect
    .poll(() =>
      page
        .getByTestId('camera-orientation')
        .getAttribute('data-bearing-degrees'),
    )
    .not.toBe(bearing);
  await moveUntil(
    page,
    'w',
    async () => Math.abs((await position(page)).z - start.z) > 1,
  );
  expect(Math.abs((await position(page)).z - start.z)).toBeGreaterThan(1);
  const beforeStrafe = await position(page);
  await moveUntil(
    page,
    'a',
    async () => Math.abs((await position(page)).x - beforeStrafe.x) > 1,
  );
  expect(Math.abs((await position(page)).x - beforeStrafe.x)).toBeGreaterThan(
    1,
  );
  const beforeRise = await position(page);
  await moveUntil(
    page,
    'Space',
    async () => (await position(page)).y > beforeRise.y + 1,
  );
  expect((await position(page)).y).toBeGreaterThan(beforeRise.y);
  await move(page, 'Control');
  await page.keyboard.down('Shift');
  await expect(page.getByTestId('flight-speed')).toHaveAttribute(
    'data-meters-per-second',
    '41.25',
  );
  await page.keyboard.up('Shift');
  await expect(page.getByTestId('flight-speed')).toHaveAttribute(
    'data-meters-per-second',
    '15.00',
  );
  await page.keyboard.press('r');
  await expect.poll(async () => (await position(page)).z).toBe(start.z);
  await page.keyboard.press('f');
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'walk',
  );
  await expect
    .poll(async () =>
      Number(
        await page
          .getByTestId('eye-clearance')
          .getAttribute('data-clearance-meters'),
      ),
    )
    .toBeCloseTo(1.7, 2);
  await page.keyboard.down('Shift');
  await moveUntil(page, 's', async () => (await position(page)).z > 550);
  await page.keyboard.up('Shift');
  const outer = await position(page);
  expect(outer.z).toBeGreaterThan(500);
  // Lift the view from spawn's downward overview pitch for a useful walk shot.
  // These are real pointer-lock mouse events, not a mutable camera hook.
  await page.mouse.move(765, 325, { steps: 8 });
  await expect
    .poll(async () =>
      Number(
        await page
          .getByTestId('camera-orientation')
          .getAttribute('data-pitch-degrees'),
      ),
    )
    .toBeGreaterThan(-15);
  await expect
    .poll(async () =>
      Number(
        await page
          .getByTestId('camera-orientation')
          .getAttribute('data-pitch-degrees'),
      ),
    )
    .toBeLessThan(-3);
  await screenshot(page, 'outer-annulus');
  await page.keyboard.press('Escape');
  await expect
    .poll(() => page.evaluate(() => document.pointerLockElement === null))
    .toBe(true);
  await page.getByTestId('reset-button').click();
  await expect.poll(async () => (await position(page)).z).toBe(start.z);
  await page.getByTestId('navigation-mode-toggle').click();
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'fly',
  );
  await page.getByTestId('help-toggle').click();
  await expect(page.getByTestId('controls-help')).toBeVisible();
  await page.setViewportSize({ width: 1280, height: 800 });
  await expect
    .poll(() =>
      page
        .locator('canvas.viewer-canvas')
        .evaluate((canvas: HTMLCanvasElement) => canvas.width),
    )
    .toBe(1280);
  const releases = requests
    .filter((url) => url.includes('/releases/'))
    .map((url) => url.split('/releases/')[1]?.split('/')[0]);
  expect(new Set(releases).size).toBe(1);
  expect(requests.some((url) => url.includes('/worlds/torquay-poc-001/'))).toBe(
    false,
  );
  expect(requests.some((url) => url.includes('/overview/'))).toBe(false);
  expect(pageErrors).toEqual([]);
  expect(consoleErrors).toEqual([]);
  expect(failedResponses).toEqual([]);
  await mkdir(evidenceDir, { recursive: true });
  await writeFile(
    resolve(evidenceDir, 'real-browser.json'),
    JSON.stringify(
      {
        browser: browser.version(),
        viewport: page.viewportSize(),
        devicePixelRatio: await page.evaluate(() => devicePixelRatio),
        durationMs: Date.now() - started,
        start,
        outer,
        releaseIds: [...new Set(releases)],
        pageErrors,
        consoleErrors,
        failedResponses,
        labelsAtStart,
        labelSourceRelease: sourceNames.releaseId,
        sourceNamedPartCount: sourceNames.names.size,
        roadQaMarkerCount: await shell.getAttribute(
          'data-road-qa-marker-count',
        ),
        renderer: await page
          .locator('canvas.viewer-canvas')
          .evaluate((canvas: HTMLCanvasElement) => {
            const gl = canvas.getContext('webgl2');
            const extension = gl?.getExtension('WEBGL_debug_renderer_info');
            return gl && extension
              ? String(gl.getParameter(extension.UNMASKED_RENDERER_WEBGL))
              : 'unavailable';
          }),
        observations:
          'Default current 2km loaded all layers; real pointer lock/look/movement/boost/walk/reset/help/resize passed. Helpers stayed hidden after G. Source panel and outer-annulus screenshots captured.',
      },
      null,
      2,
    ),
  );
});

test('current bookmark ignores layer flags and failed layers remain recoverable', async ({
  page,
}) => {
  test.skip(!real, 'Requires the locally published current package.');
  await page.route('**/releases/*/roads/roads.json', (route) =>
    route.fulfill({ status: 503, body: 'deliberate test failure' }),
  );
  await page.route('**/releases/*/buildings/buildings.json', (route) =>
    route.fulfill({ status: 503, body: 'deliberate test failure' }),
  );
  await page.goto('/?world=torquay-poc-001-2km&buildings=0&roads=0');
  await ready(page, 'real');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-building-state',
    'error',
    { timeout: 120_000 },
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-road-state',
    'error',
    { timeout: 120_000 },
  );
  await expect(page.getByTestId('road-error')).toBeVisible();
  await expect(page.getByTestId('building-error')).toBeVisible();
  await page.unroute('**/releases/*/buildings/buildings.json');
  await page.getByTestId('buildings-retry').click();
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-building-state',
    'loaded',
  );
  await expect(page.getByTestId('roads-retry')).toBeVisible();
  await screenshot(page, 'road-recovery');
  await page.unroute('**/releases/*/roads/roads.json');
  await page.getByTestId('roads-retry').click();
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-road-state',
    'loaded',
    { timeout: 120_000 },
  );
  await expect(page.getByTestId('road-error')).toBeHidden();
});

test('invalid readiness makes no GIS requests and gives truthful automatic synthetic fallback', async ({
  page,
}) => {
  const requests: string[] = [];
  page.on('request', (request) => requests.push(request.url()));
  await page.route(`**${readyPath}`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
  );
  await page.goto('/');
  await ready(page, 'synthetic');
  await expect(page.getByTestId('fallback-notice')).toContainText(
    'showing fictional demo terrain',
  );
  await expect(page.getByTestId('fallback-notice')).toHaveAttribute(
    'data-failure-detail',
    /ready/,
  );
  await expect(page.getByTestId('retry-torquay')).toBeVisible();
  await expect(page.getByTestId('provenance-badge')).toContainText('SYNTHETIC');
  await expect(page.getByTestId('map-credit')).toBeHidden();
  expect(
    requests
      .filter((url) => url.includes('/worlds/torquay'))
      .map((url) => new URL(url).pathname),
  ).toEqual([readyPath]);
  expect(new URL(page.url()).search).toBe('');
  await screenshot(page, `${real ? 'real' : 'share'}-invalid-fallback`);
  await page.getByTestId('retry-torquay').click();
  await ready(page, 'synthetic');
  expect(requests.filter((url) => url.endsWith(readyPath))).toHaveLength(2);
  if (real) {
    await page.unroute(`**${readyPath}`);
    await page.getByTestId('retry-torquay').click();
    await ready(page, 'real');
    await expect(page.locator('.viewer-shell')).toHaveAttribute(
      'data-building-state',
      'loaded',
      { timeout: 120_000 },
    );
    await expect(page.locator('.viewer-shell')).toHaveAttribute(
      'data-road-state',
      'loaded',
      { timeout: 120_000 },
    );
    await expect(page.getByTestId('fallback-notice')).toBeHidden();
    await expect(page.getByTestId('retry-torquay')).toBeHidden();
  }
});

test('share default needs no real package and synthetic controls remain usable', async ({
  page,
  browser,
}) => {
  test.skip(real, 'Exercises a build excluding all real GIS packages.');
  const requests: string[] = [];
  const errors: string[] = [];
  const unexpectedConsoleErrors: string[] = [];
  const unexpectedResponses: string[] = [];
  page.on('request', (request) => requests.push(request.url()));
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (
      message.type() === 'error' &&
      !message.location().url.endsWith(readyPath)
    )
      unexpectedConsoleErrors.push(message.text());
  });
  page.on('response', (response) => {
    if (
      response.status() >= 400 &&
      !new URL(response.url()).pathname.endsWith(readyPath)
    )
      unexpectedResponses.push(`${response.status()} ${response.url()}`);
  });
  await page.goto('/');
  await ready(page, 'synthetic');
  await expect(page.getByTestId('fallback-notice')).toBeVisible();
  await expect(page.getByTestId('retry-torquay')).toBeVisible();
  await screenshot(page, 'share-default-fallback');
  const start = await position(page);
  await lock(page);
  await move(page, 'w');
  expect((await position(page)).z).toBeLessThan(start.z);
  await page.keyboard.press('Escape');
  await page.getByTestId('reset-button').click();
  await expect.poll(async () => (await position(page)).z).toBe(start.z);
  await page.getByTestId('navigation-mode-toggle').click();
  await lock(page);
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'walk',
  );
  await expect
    .poll(async () =>
      Number(
        await page
          .getByTestId('eye-clearance')
          .getAttribute('data-clearance-meters'),
      ),
    )
    .toBeCloseTo(1.7, 2);
  expect(
    requests
      .filter((url) => url.includes('/worlds/torquay'))
      .map((url) => new URL(url).pathname),
  ).toEqual([readyPath]);
  expect(errors).toEqual([]);
  expect(unexpectedConsoleErrors).toEqual([]);
  expect(unexpectedResponses).toEqual([]);
  await mkdir(evidenceDir, { recursive: true });
  await writeFile(
    resolve(evidenceDir, 'share-browser.json'),
    JSON.stringify(
      {
        browser: browser.version(),
        viewport: page.viewportSize(),
        requests: requests.filter((url) => url.includes('/worlds/')),
        pageErrors: errors,
        unexpectedConsoleErrors,
        unexpectedResponses,
        visibleRoadNameLabelCount: await page
          .locator(visibleLabelSelector)
          .count(),
        observation:
          'Share build auto-fell back after readiness; no GIS runtime assets requested. Synthetic movement/reset/walk passed.',
      },
      null,
      2,
    ),
  );
});

test('internal synthetic and M0 fixtures request no geographic assets', async ({
  page,
}) => {
  const requests: string[] = [];
  page.on('request', (request) => requests.push(request.url()));
  await page.goto('/?world=synthetic');
  await ready(page, 'synthetic');
  await lock(page);
  await page.keyboard.press('g');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-grid-visible',
    'false',
  );
  await page.keyboard.press('Escape');
  await page.goto('/?world=m0');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-renderer-ready',
    'true',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-world-mode',
    'm0',
  );
  await expect(page.getByTestId('debug-hud')).toBeHidden();
  await lock(page);
  const start = await position(page);
  await move(page, 'w');
  expect((await position(page)).z).toBeLessThan(start.z);
  await page.keyboard.press('Escape');
  expect(requests.some((url) => url.includes('/worlds/torquay'))).toBe(false);
});

test('historical internal route retains the original 1km profile', async ({
  page,
}) => {
  test.skip(
    !real,
    'Historical packages intentionally excluded from share builds.',
  );
  const requests: string[] = [];
  page.on('request', (request) => requests.push(request.url()));
  await page.goto('/?world=torquay-poc-001&buildings=1&roads=1');
  await ready(page, 'real');
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-scene-profile', 'historical_1km');
  await expect(shell).toHaveAttribute('data-building-state', 'loaded');
  await expect(shell).toHaveAttribute('data-road-state', 'loaded');
  await expect(shell).toHaveAttribute('data-building-count', '1000');
  await expect(shell).toHaveAttribute('data-road-way-count', '198');
  await expect(page.getByTestId('terrain-details')).toHaveText(
    '501 columns × 501 rows · 2 m spacing',
  );
  await expect(page.getByTestId('real-package-extent-notice')).toContainText(
    'Historical 1 km',
  );
  expect(requests.some((url) => url.includes('torquay-poc-001-2km'))).toBe(
    false,
  );
});
