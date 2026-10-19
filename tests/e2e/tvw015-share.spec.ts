import { expect, test } from '@playwright/test';

test('share build remains synthetic and contains no real road labels or assets', async ({
  page,
}) => {
  const roadRequests: string[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/worlds/torquay-poc-001/roads/')) {
      roadRequests.push(request.url());
    }
  });
  await page.goto('/');
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-world-mode', 'synthetic');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded');
  await expect(page.getByTestId('road-controls')).toBeHidden();
  await expect(page.locator('.road-label-overlay')).toHaveCount(1);
  await expect(
    page.locator('.road-name-label:not(.road-name-measure)'),
  ).toHaveCount(20);
  await expect(
    page.locator('.road-name-label:not(.road-name-measure):visible'),
  ).toHaveCount(0);
  expect(roadRequests).toEqual([]);
  expect(
    await page
      .locator('.road-name-label:not(.road-name-measure)')
      .allTextContents(),
  ).toEqual(Array(20).fill(''));
});
