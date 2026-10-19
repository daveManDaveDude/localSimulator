import { expect, test } from '@playwright/test';

async function cameraPosition(page: import('@playwright/test').Page) {
  const output = page.getByTestId('camera-position');
  return output.evaluate((element) => ({
    x: Number(element.getAttribute('data-x')),
    y: Number(element.getAttribute('data-y')),
    z: Number(element.getAttribute('data-z')),
  }));
}

test('share production build starts synthetic and supports flight controls', async ({
  page,
}, testInfo) => {
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });

  await page.goto('/');
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded');
  await expect(shell).toHaveAttribute('data-renderer-ready', 'true');
  await expect(page.getByTestId('provenance-badge')).toContainText(
    'SYNTHETIC · FICTIONAL LOCAL DATA',
  );
  await expect(page.getByTestId('world-type')).toContainText('SYNTHETIC');
  await expect(page.getByTestId('world-attribution')).toContainText(
    'Fictional',
  );
  await expect(page.locator('canvas.viewer-canvas')).toBeVisible();
  const canvasBefore = await page
    .locator('canvas.viewer-canvas')
    .evaluate((element) => {
      const canvas = element as HTMLCanvasElement;
      return {
        width: canvas.width,
        height: canvas.height,
        rect: canvas.getBoundingClientRect().toJSON(),
      };
    });
  expect(canvasBefore.width).toBeGreaterThan(0);
  expect(canvasBefore.height).toBeGreaterThan(0);
  await page.screenshot({
    path: testInfo.outputPath('share-synthetic-startup.png'),
    fullPage: true,
  });

  await page.getByRole('button', { name: 'Start exploring' }).click();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  const spawn = await cameraPosition(page);
  await page.keyboard.down('w');
  await page.waitForTimeout(350);
  await page.keyboard.up('w');
  await expect
    .poll(async () => {
      const next = await cameraPosition(page);
      return Math.hypot(next.x - spawn.x, next.y - spawn.y, next.z - spawn.z);
    })
    .toBeGreaterThan(0.25);

  await page.keyboard.down('Shift');
  await expect(page.getByTestId('flight-speed')).toHaveAttribute(
    'data-meters-per-second',
    '41.25',
  );
  await expect(page.getByTestId('flight-speed')).toHaveAttribute(
    'data-boosting',
    'true',
  );
  await page.keyboard.up('Shift');
  await page.keyboard.press('r');
  await expect
    .poll(async () => {
      const reset = await cameraPosition(page);
      return Math.hypot(
        reset.x - spawn.x,
        reset.y - spawn.y,
        reset.z - spawn.z,
      );
    })
    .toBeLessThan(0.05);

  await page.keyboard.press('Escape');
  await expect
    .poll(() => page.evaluate(() => document.pointerLockElement === null))
    .toBe(true);
  const released = await cameraPosition(page);
  await page.keyboard.down('w');
  await page.waitForTimeout(300);
  await page.keyboard.up('w');
  const afterRelease = await cameraPosition(page);
  expect(
    Math.hypot(
      afterRelease.x - released.x,
      afterRelease.y - released.y,
      afterRelease.z - released.z,
    ),
  ).toBeLessThan(0.05);

  await page.setViewportSize({ width: 1280, height: 760 });
  await expect
    .poll(() =>
      page.locator('canvas.viewer-canvas').evaluate((element) => {
        const canvas = element as HTMLCanvasElement;
        const rect = canvas.getBoundingClientRect();
        return canvas.width >= rect.width && canvas.height >= rect.height;
      }),
    )
    .toBe(true);
  expect(pageErrors).toEqual([]);
  expect(consoleErrors).toEqual([]);
});

test('share build gives a recoverable message when local EA assets are absent', async ({
  page,
}) => {
  test.skip(
    process.env.TVW014_SHARE_PRODUCTION !== 'true',
    'This negative package test runs against the clean share production build.',
  );
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  const manifestRequests: string[] = [];
  const manifestResponses: Array<{ status: number; contentType: string }> = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('request', (request) => {
    if (request.url().endsWith('/worlds/torquay-poc-001/manifest.json')) {
      manifestRequests.push(request.url());
    }
  });
  page.on('response', (response) => {
    if (response.url().endsWith('/worlds/torquay-poc-001/manifest.json')) {
      manifestResponses.push({
        status: response.status(),
        contentType: response.headers()['content-type'] ?? '',
      });
    }
  });

  await page.goto('/');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-renderer-ready',
    'true',
  );
  await page.getByTestId('world-select-real').click();
  await expect(page.getByTestId('world-load-error')).toBeVisible();
  await expect(page.getByTestId('world-error-message')).toContainText(
    'Synthetic terrain remains available',
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
  await expect(page.getByTestId('provenance-badge')).toContainText(
    'SYNTHETIC · FICTIONAL LOCAL DATA',
  );
  expect(pageErrors).toEqual([]);
  expect(consoleErrors).toEqual([]);
  expect(manifestRequests).toHaveLength(1);
  expect(manifestResponses).toHaveLength(1);
  const manifestResponse = manifestResponses.at(0);
  if (manifestResponse === undefined) {
    throw new Error(
      'The attempted missing manifest request produced no response.',
    );
  }
  expect(
    manifestResponse.status >= 400 ||
      !manifestResponse.contentType.includes('application/json'),
  ).toBe(true);
});
