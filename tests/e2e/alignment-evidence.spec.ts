import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

type CameraPose = {
  x: number;
  y: number;
  z: number;
  bearing: number;
  pitch: number;
};

const contexts = [
  {
    id: 'ne-second-main',
    x: 191.131,
    z: -237.389,
    bearing: 48,
    cameraOffsetM: 60,
  },
  {
    id: 'nw-audley-pencorse',
    x: -380.008,
    z: -336.826,
    bearing: 125,
    cameraOffsetM: 40,
  },
  {
    id: 'sw-teignmouth-snowberry',
    x: -297.29,
    z: 239.72,
    bearing: 45,
    cameraOffsetM: 45,
  },
] as const;

async function cameraPose(page: Page): Promise<CameraPose> {
  return page.getByTestId('camera-position').evaluate((position) => {
    const orientation = document.querySelector<HTMLOutputElement>(
      '[data-testid="camera-orientation"]',
    );
    if (!orientation)
      throw new Error('Camera orientation telemetry is missing.');
    const element = position as HTMLOutputElement;
    return {
      x: Number(element.dataset.x),
      y: Number(element.dataset.y),
      z: Number(element.dataset.z),
      bearing: Number(orientation.dataset.bearingDegrees),
      pitch: Number(orientation.dataset.pitchDegrees),
    };
  });
}

test('TVW-012 captures actual 3D scenes at the three registered comparison spots', async ({
  page,
  browserName,
}) => {
  test.setTimeout(120_000);
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const failedRequests: string[] = [];
  const requestedUrls: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) =>
    pageErrors.push(`${error.name}: ${error.message}`),
  );
  page.on('requestfailed', (request) => failedRequests.push(request.url()));
  page.on('request', (request) => requestedUrls.push(request.url()));

  await page.goto('/?world=torquay-poc-001&buildings=1&roads=1');
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded');
  await expect(shell).toHaveAttribute('data-renderer-ready', 'true');
  await expect(shell).toHaveAttribute('data-road-state', 'loaded', {
    timeout: 30_000,
  });
  await expect(shell).toHaveAttribute('data-building-state', 'loaded');
  await expect(page.getByTestId('road-status')).toContainText(
    '198 mapped ways',
  );
  await expect(page.getByTestId('building-status')).toContainText(
    '1,000 footprints',
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
  const outputDirectory = resolve(process.cwd(), 'docs/milestones/screenshots');
  await mkdir(outputDirectory, { recursive: true });
  const evidence: Record<string, unknown>[] = [];

  for (const context of contexts) {
    const bearingRadians = (context.bearing * Math.PI) / 180;
    const cameraX =
      context.x - Math.sin(bearingRadians) * context.cameraOffsetM;
    const cameraZ =
      context.z + Math.cos(bearingRadians) * context.cameraOffsetM;
    await page.evaluate(
      ({ x, z, bearing }) => {
        const qa = window.__torquayAlignmentQa;
        if (!qa)
          throw new Error('Development-only alignment camera hook is missing.');
        qa.setPose({
          x,
          y: 200,
          z,
          bearingDegrees: bearing,
          pitchDegrees: -35,
        });
      },
      { x: cameraX, z: cameraZ, bearing: context.bearing },
    );
    await expect
      .poll(
        async () => {
          const pose = await cameraPose(page);
          return Math.hypot(pose.x - cameraX, pose.z - cameraZ);
        },
        { timeout: 5_000 },
      )
      .toBeLessThan(0.02);
    const groundHeight = Number(
      await page
        .getByTestId('ground-height')
        .getAttribute('data-height-meters'),
    );
    expect(Number.isFinite(groundHeight)).toBe(true);
    await page.evaluate(
      ({ x, z, bearing, eyeHeight }) => {
        const qa = window.__torquayAlignmentQa;
        if (!qa)
          throw new Error('Development-only alignment camera hook is missing.');
        qa.setPose({
          x,
          y: groundHeight() + eyeHeight,
          z,
          bearingDegrees: bearing,
          pitchDegrees: -35,
        });

        function groundHeight(): number {
          const output = document.querySelector<HTMLOutputElement>(
            '[data-testid="ground-height"]',
          );
          const value = Number(output?.dataset.heightMeters);
          if (!Number.isFinite(value)) {
            throw new Error(
              'Ground height telemetry is unavailable at the selected spot.',
            );
          }
          return value;
        }
      },
      { x: cameraX, z: cameraZ, bearing: context.bearing, eyeHeight: 35 },
    );
    await expect
      .poll(
        async () => {
          const pose = await cameraPose(page);
          return pose.y - groundHeight;
        },
        { timeout: 5_000 },
      )
      .toBeGreaterThan(34.8);
    await expect
      .poll(async () => (await cameraPose(page)).y - groundHeight, {
        timeout: 5_000,
      })
      .toBeLessThan(35.2);
    const pose = await cameraPose(page);
    expect(Math.hypot(cameraX - pose.x, cameraZ - pose.z)).toBeLessThan(0.02);

    const filename = `TVW-012-${context.id}-scene.png`;
    const screenshotPath = resolve(outputDirectory, filename);
    await page.addStyleTag({
      content:
        '.viewer-topline,.world-selector,.debug-hud,.building-controls,.road-controls,.controls-help,.corner-note,.start-card{visibility:hidden!important}',
    });
    await page.screenshot({ path: screenshotPath, animations: 'disabled' });
    await page.evaluate(() => {
      document.querySelector('style:last-of-type')?.remove();
    });

    const runtime = await page.evaluate(() => {
      const canvas = document.querySelector<HTMLCanvasElement>(
        'canvas.viewer-canvas',
      );
      if (!canvas) throw new Error('The WebGL canvas is missing.');
      const gl = canvas.getContext('webgl2') ?? canvas.getContext('webgl');
      const extension = gl?.getExtension('WEBGL_debug_renderer_info');
      return {
        renderer: gl
          ? extension
            ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL)
            : gl.getParameter(gl.RENDERER)
          : 'WebGL unavailable',
        canvas: {
          cssWidth: canvas.clientWidth,
          cssHeight: canvas.clientHeight,
          width: canvas.width,
          height: canvas.height,
        },
      };
    });
    evidence.push({
      screenshotPath,
      camera: pose,
      sampledGroundHeightM: groundHeight,
      eyeHeightAboveTerrainM: pose.y - groundHeight,
      targetLocalXZMetres: [context.x, context.z],
      cameraOffsetM: context.cameraOffsetM,
      poseMethod:
        'development-only QA camera pose setter; no camera travel is implied',
      expectedContextId: context.id,
      runtime,
      browserName,
      browserVersion: page.context().browser()?.version(),
      viewport: await page.evaluate(() => ({
        width: innerWidth,
        height: innerHeight,
        devicePixelRatio,
      })),
    });
  }

  const localOrigin = new URL(page.url()).origin;
  expect(
    requestedUrls.every((url) => new URL(url).origin === localOrigin),
  ).toBe(true);
  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(failedRequests).toEqual([]);

  await page.keyboard.press('Escape');
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement !== document.querySelector('canvas'),
      ),
    )
    .toBe(true);

  const evidencePath = resolve(
    process.cwd(),
    'docs/milestones/artifacts/TVW-012-browser-evidence.json',
  );
  await mkdir(resolve(process.cwd(), 'docs/milestones/artifacts'), {
    recursive: true,
  });
  await writeFile(
    evidencePath,
    JSON.stringify(
      { evidence, consoleErrors, pageErrors, failedRequests },
      null,
      2,
    ),
    'utf8',
  );
});
