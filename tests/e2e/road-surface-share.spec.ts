import { expect, test } from '@playwright/test';

test('current release route stays source-draped without requesting a preview derivative', async ({
  page,
}) => {
  const requests: string[] = [];
  page.on('request', (request) => requests.push(request.url()));
  await page.goto('/?world=torquay-poc-001-2km');
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-load-state',
    'loaded',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-world-mode',
    'real',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-scene-profile',
    'current_2km',
  );
  await expect(page.locator('.viewer-shell')).toHaveAttribute(
    'data-road-surface-state',
    'off',
  );
  await expect(page.getByTestId('road-surface-preview-notice')).toBeHidden();
  expect(
    requests.some((url) =>
      url.includes('/worlds/torquay-poc-001-2km/ready.json'),
    ),
  ).toBe(true);
  expect(
    requests.some((url) => url.includes('torquay-road-surface-preview')),
  ).toBe(false);
});
