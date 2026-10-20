import { expect, test } from '@playwright/test';
import { resolve } from 'node:path';

const packageNoticeScreenshot = resolve(
  'docs/milestones/screenshots/AOI-2km-real-route-1km-package-notice.png',
);

async function waitForRoute(page: import('@playwright/test').Page) {
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded', {
    timeout: 30_000,
  });
  await expect(shell).toHaveAttribute('data-renderer-ready', 'true', {
    timeout: 30_000,
  });
  await expect(page.getByTestId('world-provenance')).toHaveText(
    'REAL DATA · EA DTM 2022 composite',
  );
  await expect(page.getByTestId('world-attribution')).toContainText(
    'Environment Agency copyright',
  );
  await expect(page.getByTestId('real-package-extent-notice')).toBeVisible();
  await expect(page.getByTestId('real-package-extent-notice')).toContainText(
    'earlier 1 km browser packages',
  );
  await expect(page.getByTestId('real-package-extent-notice')).toContainText(
    '2 km candidate is pending and is not rendered',
  );
  await expect(page.getByTestId('real-package-extent-notice')).toBeInViewport({
    ratio: 1,
  });
  await expect(page.getByTestId('terrain-details')).toHaveText(
    '501 columns × 501 rows · 2 m spacing',
  );
  await expect(page.getByTestId('flight-speed')).toHaveAttribute(
    'data-meters-per-second',
    '15.00',
  );
}

test('production terrain, buildings, roads and combined local routes load with provenance', async ({
  page,
}) => {
  test.skip(
    process.env.TVW014_REAL_PRODUCTION !== 'true',
    'Run against the isolated production preview profile.',
  );
  const cases = [
    { url: '/?world=torquay-poc-001', buildings: false, roads: false },
    {
      url: '/?world=torquay-poc-001&buildings=1',
      buildings: true,
      roads: false,
    },
    { url: '/?world=torquay-poc-001&roads=1', buildings: false, roads: true },
    {
      url: '/?world=torquay-poc-001&buildings=1&roads=1',
      buildings: true,
      roads: true,
    },
  ];

  const unexpected: string[] = [];
  page.on('pageerror', (error) => unexpected.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') unexpected.push(message.text());
  });

  for (const scenario of cases) {
    await page.goto(scenario.url);
    await waitForRoute(page);
    if (scenario.buildings) {
      await expect(page.getByTestId('building-status')).toHaveAttribute(
        'data-state',
        'loaded',
        { timeout: 30_000 },
      );
      await expect(page.getByTestId('building-status')).toHaveAttribute(
        'data-building-count',
        '1000',
      );
      await expect(page.getByTestId('building-attribution')).toContainText(
        'OpenStreetMap contributors',
      );
    } else {
      await expect(page.getByTestId('building-status')).toHaveAttribute(
        'data-state',
        'off',
      );
    }
    if (scenario.roads) {
      await expect(page.getByTestId('road-status')).toHaveAttribute(
        'data-state',
        'loaded',
        { timeout: 30_000 },
      );
      await expect(page.getByTestId('road-status')).toHaveAttribute(
        'data-way-count',
        '198',
      );
      await expect(page.getByTestId('road-attribution')).toContainText(
        'OpenStreetMap contributors',
      );
    } else {
      await expect(page.getByTestId('road-status')).toHaveAttribute(
        'data-state',
        'off',
      );
    }
  }

  await page.getByTestId('start-button').click();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  await page.screenshot({ path: packageNoticeScreenshot });
  await page.keyboard.press('Escape');
  await expect
    .poll(() => page.evaluate(() => document.pointerLockElement === null))
    .toBe(true);

  await page.goto('/');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-load-state',
    'loaded',
    { timeout: 30_000 },
  );
  await expect(page.getByTestId('real-package-extent-notice')).toBeHidden();

  const hasProductionQaHook = await page.evaluate(
    () => '__torquayAlignmentQa' in window,
  );
  expect(hasProductionQaHook).toBe(false);
  expect(unexpected).toEqual([]);
});

test('production combined mode exercises walking, fly return, reset and pointer release', async ({
  page,
}) => {
  test.skip(
    process.env.TVW014_REAL_PRODUCTION !== 'true',
    'Run against the isolated production preview profile.',
  );
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  await page.goto('/?world=torquay-poc-001&buildings=1&roads=1');
  await waitForRoute(page);
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

  await page.getByRole('button', { name: 'Start exploring' }).click();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  await page.keyboard.press('f');
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'walk',
    { timeout: 20_000 },
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
  await page.keyboard.up('Shift');
  await page.keyboard.press('f');
  await expect(page.getByTestId('navigation-mode')).toHaveAttribute(
    'data-mode',
    'fly',
  );
  await page.keyboard.press('r');
  await page.keyboard.press('Escape');
  await expect
    .poll(() => page.evaluate(() => document.pointerLockElement === null))
    .toBe(true);
  expect(pageErrors).toEqual([]);
  expect(consoleErrors).toEqual([]);
});

test('production missing-road recovery returns to the functioning synthetic world', async ({
  page,
}) => {
  test.skip(
    process.env.TVW014_REAL_PRODUCTION !== 'true',
    'Run against the isolated production preview profile.',
  );
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  const expectedMissingManifestResponses: string[] = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('response', (response) => {
    if (
      response.url().endsWith('/worlds/torquay-poc-001/roads/manifest.json') &&
      response.status() === 404
    ) {
      expectedMissingManifestResponses.push(response.url());
    }
  });
  await page.route('**/worlds/torquay-poc-001/roads/manifest.json', (route) =>
    route.fulfill({ status: 404, contentType: 'application/json', body: '{}' }),
  );
  await page.goto('/?world=torquay-poc-001&roads=1');
  await waitForRoute(page);
  await expect(page.getByTestId('road-error')).toBeVisible();
  await page.getByTestId('roads-return-synthetic').click();
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-load-state',
    'loaded',
  );
  await expect(page.getByTestId('provenance-badge')).toContainText(
    'SYNTHETIC · FICTIONAL LOCAL DATA',
  );
  expect(pageErrors).toEqual([]);
  expect(expectedMissingManifestResponses).toHaveLength(1);
  expect(consoleErrors).toHaveLength(1);
  expect(consoleErrors[0]).toMatch(/responded with a status of 404/);
});
