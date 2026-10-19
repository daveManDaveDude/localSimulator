import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';

test('share build stays synthetic and reports geographic overview unavailable without real requests', async ({
  page,
  browser,
}) => {
  test.skip(
    process.env.M8_OVERVIEW_SHARE_PRODUCTION !== 'true',
    'Run against the isolated production share preview profile.',
  );
  const errors: string[] = [];
  const realRequests: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith('/worlds/torquay-poc-001/'))
      realRequests.push(url.pathname);
    if (
      url.origin !== 'http://127.0.0.1:4204' &&
      ['http:', 'https:'].includes(url.protocol)
    )
      errors.push(`unexpected external request ${url.href}`);
  });
  await page.goto('/');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-load-state',
    'loaded',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-renderer-ready',
    'true',
  );
  await expect(page.getByTestId('world-provenance')).toContainText('SYNTHETIC');
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
  expect(realRequests).toEqual([]);
  expect(
    await page.evaluate(() =>
      performance
        .getEntriesByType('resource')
        .some((entry) => entry.name.includes('maplibre-gl-')),
    ),
  ).toBe(false);
  await mkdir(resolve('docs/milestones/screenshots'), { recursive: true });
  await page.goto('/?world=m0');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-load-state',
    'loaded',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-renderer-ready',
    'true',
  );
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
    path: resolve(
      'docs/milestones/screenshots/M8-overview-synthetic-unavailable.png',
    ),
    fullPage: true,
  });
  expect(
    await page.evaluate(() =>
      performance
        .getEntriesByType('resource')
        .some((entry) => entry.name.includes('maplibre-gl-')),
    ),
  ).toBe(false);
  expect(realRequests).toEqual([]);
  expect(errors).toEqual([]);
  const browserEvidence = await page.evaluate(() => {
    const canvas = document.querySelector<HTMLCanvasElement>('.viewer-canvas');
    const context = canvas?.getContext('webgl2') ?? canvas?.getContext('webgl');
    const extension = context?.getExtension('WEBGL_debug_renderer_info');
    return {
      viewport: { width: innerWidth, height: innerHeight },
      devicePixelRatio,
      renderer:
        context && extension
          ? context.getParameter(extension.UNMASKED_RENDERER_WEBGL)
          : 'unavailable',
      maplibreResources: performance
        .getEntriesByType('resource')
        .filter((entry) => entry.name.includes('maplibre-gl-')).length,
    };
  });
  await writeFile(
    resolve('docs/milestones/artifacts/M8-share-evidence.json'),
    `${JSON.stringify(
      {
        browser: {
          name: browser.browserType().name(),
          version: browser.version(),
        },
        ...browserEvidence,
        realPackageRequests: realRequests,
        externalRequests: [],
        syntheticWorld: 'M0 analytic synthetic demo',
        screenshot:
          'docs/milestones/screenshots/M8-overview-synthetic-unavailable.png',
      },
      null,
      2,
    )}\n`,
  );
});
