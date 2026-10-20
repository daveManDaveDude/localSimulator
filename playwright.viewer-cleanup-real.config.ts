import { defineConfig, devices } from '@playwright/test';

process.env.VIEWER_CLEANUP_PROFILE = 'real';
const port = 4210;
const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: 'viewer-cleanup.spec.ts',
  outputDir: 'test-results/viewer-cleanup-real',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: Boolean(process.env.CI),
  reporter: 'list',
  timeout: 240_000,
  expect: { timeout: 45_000 },
  use: { baseURL, trace: 'retain-on-failure' },
  projects: [
    {
      name: 'cleanup-real-production',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 960 },
        deviceScaleFactor: 1.5,
      },
    },
  ],
  webServer: {
    command: `npm run preview -- --host 127.0.0.1 --port ${port} --strictPort`,
    url: baseURL,
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
