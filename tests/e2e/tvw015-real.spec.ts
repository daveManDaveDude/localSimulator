import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';

interface FrameSample {
  frameIntervalsMs: number[];
  documentFocused: boolean;
  documentVisible: boolean;
  focusedFrameCount: number;
  visibleFrameCount: number;
}

async function sampleAnimationFrames(
  page: import('@playwright/test').Page,
  durationMs: number,
): Promise<FrameSample> {
  return page.evaluate(
    (duration) =>
      new Promise<FrameSample>((resolveSample) => {
        const started = performance.now();
        let previous: number | null = null;
        const frameIntervalsMs: number[] = [];
        let focusedFrameCount = 0;
        let visibleFrameCount = 0;
        const collect = (now: number): void => {
          if (previous !== null) frameIntervalsMs.push(now - previous);
          previous = now;
          if (document.hasFocus()) focusedFrameCount += 1;
          if (document.visibilityState === 'visible') visibleFrameCount += 1;
          if (now - started >= duration) {
            resolveSample({
              frameIntervalsMs,
              documentFocused: document.hasFocus(),
              documentVisible: document.visibilityState === 'visible',
              focusedFrameCount,
              visibleFrameCount,
            });
            return;
          }
          requestAnimationFrame(collect);
        };
        requestAnimationFrame(collect);
      }),
    durationMs,
  );
}

function median(values: number[]): number {
  const sorted = [...values].sort((first, second) => first - second);
  return sorted[Math.floor(sorted.length / 2)] ?? 0;
}

test('production local roads support optional projected street names and clean lifecycle', async ({
  page,
  browserName,
}, testInfo) => {
  test.setTimeout(120_000);
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  const externalRequests: string[] = [];
  const localOrigin = new URL(
    testInfo.project.use.baseURL ?? 'http://127.0.0.1:4195',
  ).origin;
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('request', (request) => {
    if (new URL(request.url()).origin !== localOrigin) {
      externalRequests.push(request.url());
    }
  });

  await page.goto('/?world=torquay-poc-001&roads=1');
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded');
  await expect(shell).toHaveAttribute('data-renderer-ready', 'true');
  await expect(shell).toHaveAttribute('data-road-state', 'loaded', {
    timeout: 30_000,
  });
  await expect(page.getByTestId('road-attribution')).toContainText(
    'OpenStreetMap contributors',
  );
  await expect(page.getByTestId('road-attribution')).toContainText(
    'Geofabrik GmbH',
  );

  const streetNames = page.getByTestId('street-names-toggle');
  await expect(streetNames).toBeEnabled();
  await expect(streetNames).toHaveAttribute('aria-pressed', 'false');
  await expect(
    page.locator('.road-name-label:not(.road-name-measure)'),
  ).toHaveCount(20);
  await expect(
    page.locator('.road-name-label:not(.road-name-measure):visible'),
  ).toHaveCount(0);

  const roadsResponse = await page.request.get(
    '/worlds/torquay-poc-001/roads/roads.json',
  );
  expect(roadsResponse.ok()).toBe(true);
  const roadsPayload = (await roadsResponse.json()) as {
    features: Array<{ sourceTags: Record<string, string> }>;
  };
  const sourceNames = new Set(
    roadsPayload.features
      .map((feature) => feature.sourceTags.name?.trim())
      .filter((name): name is string => Boolean(name)),
  );

  // Enable annotations before lock; the transparent overlay must not prevent
  // the actual canvas gesture that requests pointer lock.
  await streetNames.click();
  await expect(streetNames).toHaveAttribute('aria-pressed', 'true');
  const startButton = page.getByTestId('start-button');
  const startButtonBounds = await startButton.boundingBox();
  expect(startButtonBounds).not.toBeNull();
  const startX =
    (startButtonBounds?.x ?? 0) + (startButtonBounds?.width ?? 0) / 2;
  const startY =
    (startButtonBounds?.y ?? 0) + (startButtonBounds?.height ?? 0) / 2;
  await page.mouse.move(startX, startY);
  await startButton.click();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  await page.keyboard.press('h');
  await expect(page.getByTestId('controls-help')).toBeHidden();

  await expect(streetNames).toHaveAttribute('aria-pressed', 'true');
  await expect
    .poll(() =>
      page.locator('.road-name-label:not(.road-name-measure):visible').count(),
    )
    .toBeGreaterThanOrEqual(3);
  const firstVisibleLabels = await page
    .locator('.road-name-label:not(.road-name-measure):visible')
    .allTextContents();
  expect(firstVisibleLabels.length).toBeLessThanOrEqual(20);
  expect(new Set(firstVisibleLabels).size).toBe(firstVisibleLabels.length);
  for (const name of firstVisibleLabels)
    expect(sourceNames.has(name)).toBe(true);

  const beforeTurn = await page
    .locator('.road-name-label:not(.road-name-measure):visible')
    .evaluateAll((nodes) =>
      nodes.map((node) => {
        const bounds = node.getBoundingClientRect();
        return {
          key: (node as HTMLElement).dataset.roadLabelKey,
          x: bounds.x,
          y: bounds.y,
        };
      }),
    );
  expect(beforeTurn.length).toBeGreaterThanOrEqual(3);
  const beforeBearing = Number(
    await page
      .getByTestId('camera-orientation')
      .getAttribute('data-bearing-degrees'),
  );
  await page.mouse.move(startX + 8, startY + 4, { steps: 4 });
  await expect
    .poll(() =>
      page
        .getByTestId('camera-orientation')
        .getAttribute('data-bearing-degrees')
        .then((value) => Math.abs(Number(value) - beforeBearing)),
    )
    .toBeGreaterThan(0.3);
  await expect
    .poll(() =>
      page.evaluate((priorPositions) => {
        const visible = Array.from(
          document.querySelectorAll<HTMLElement>(
            '.road-name-label:not(.road-name-measure)',
          ),
        ).filter((item) => !item.hidden);
        let maximumDisplacement = 0;
        for (const prior of priorPositions) {
          const label = visible.find(
            (item) => item.dataset.roadLabelKey === prior.key,
          );
          if (!label) continue;
          const bounds = label.getBoundingClientRect();
          maximumDisplacement = Math.max(
            maximumDisplacement,
            Math.hypot(bounds.x - prior.x, bounds.y - prior.y),
          );
        }
        return maximumDisplacement;
      }, beforeTurn),
    )
    .toBeGreaterThan(3);

  const outputDirectory = resolve(process.cwd(), 'docs/milestones/screenshots');
  await mkdir(outputDirectory, { recursive: true });
  await page.screenshot({
    path: resolve(outputDirectory, 'TVW-015-street-labels-overview.png'),
    animations: 'disabled',
  });

  await page.setViewportSize({ width: 1280, height: 800 });
  await expect
    .poll(() =>
      page.locator('.road-name-label:not(.road-name-measure):visible').count(),
    )
    .toBeGreaterThanOrEqual(3);
  const resizedLabelBoxes = await page
    .locator('.road-name-label:not(.road-name-measure):visible')
    .evaluateAll((nodes) =>
      nodes.map((node) => {
        const bounds = node.getBoundingClientRect();
        return {
          left: bounds.left,
          right: bounds.right,
          top: bounds.top,
          bottom: bounds.bottom,
        };
      }),
    );
  for (const bounds of resizedLabelBoxes) {
    expect(bounds.left).toBeGreaterThanOrEqual(0);
    expect(bounds.right).toBeLessThanOrEqual(1280);
    expect(bounds.top).toBeGreaterThanOrEqual(0);
    expect(bounds.bottom).toBeLessThanOrEqual(800);
  }

  // Compare labels off/on at one unchanged camera pose and viewport.
  await page.keyboard.press('Escape');
  await expect
    .poll(() => page.evaluate(() => document.pointerLockElement === null))
    .toBe(true);
  await streetNames.click();
  await expect(streetNames).toHaveAttribute('aria-pressed', 'false');
  await page.waitForTimeout(2_000);
  const labelsOff = await sampleAnimationFrames(page, 3_000);
  await streetNames.click();
  await expect(streetNames).toHaveAttribute('aria-pressed', 'true');
  await page.waitForTimeout(2_000);
  const labelsOn = await sampleAnimationFrames(page, 3_000);
  const visibleLabelsDuringMeasurement = await page
    .locator('.road-name-label:not(.road-name-measure):visible')
    .count();
  const browserEvidence = await page.evaluate(() => {
    const canvas = document.querySelector<HTMLCanvasElement>(
      'canvas.viewer-canvas',
    );
    if (!canvas) throw new Error('The viewer canvas is missing.');
    const context = canvas.getContext('webgl2') ?? canvas.getContext('webgl');
    const extension = context?.getExtension('WEBGL_debug_renderer_info');
    const position = document.querySelector<HTMLOutputElement>(
      '[data-testid="camera-position"]',
    );
    const orientation = document.querySelector<HTMLOutputElement>(
      '[data-testid="camera-orientation"]',
    );
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
      cameraPosition: position?.textContent,
      cameraBearing: orientation?.dataset.bearingDegrees,
      cameraPitch: orientation?.dataset.pitchDegrees,
      drawCalls: document
        .querySelector('.viewer-shell')
        ?.getAttribute('data-draw-calls'),
      triangles: document
        .querySelector('.viewer-shell')
        ?.getAttribute('data-triangles'),
    };
  });

  await page.setViewportSize({ width: 1920, height: 1200 });
  const walkStartButton = page.getByTestId('start-button');
  const walkStartBounds = await walkStartButton.boundingBox();
  expect(walkStartBounds).not.toBeNull();
  const walkStartX =
    (walkStartBounds?.x ?? 0) + (walkStartBounds?.width ?? 0) / 2;
  const walkStartY =
    (walkStartBounds?.y ?? 0) + (walkStartBounds?.height ?? 0) / 2;
  await page.mouse.move(walkStartX, walkStartY);
  await walkStartButton.click();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);
  await page.keyboard.press('h');
  await expect(page.getByTestId('controls-help')).toBeHidden();
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
    .toMatch(/^1\.7\d+/);
  // The default camera pitch is aimed down across the terrain. At walking
  // height that puts distant road-name anchors below the viewport, so look
  // toward the horizon while remaining at the same real spawn position.
  await page.mouse.move(walkStartX + 12, walkStartY - 270, { steps: 8 });
  await expect
    .poll(() =>
      page
        .getByTestId('camera-orientation')
        .getAttribute('data-pitch-degrees')
        .then((value) => Math.abs(Number(value))),
    )
    .toBeLessThan(8);
  await expect
    .poll(() =>
      page.locator('.road-name-label:not(.road-name-measure):visible').count(),
    )
    .toBeGreaterThanOrEqual(3);
  await page.screenshot({
    path: resolve(outputDirectory, 'TVW-015-street-labels-walk.png'),
    animations: 'disabled',
  });
  const walkStart = await page
    .getByTestId('camera-position')
    .evaluate((element) => {
      const output = element as HTMLOutputElement;
      return [
        Number(output.dataset.x),
        Number(output.dataset.y),
        Number(output.dataset.z),
      ];
    });
  await page.keyboard.down('w');
  await page.waitForTimeout(300);
  await page.keyboard.up('w');
  const walkMoved = await page
    .getByTestId('camera-position')
    .evaluate((element) => {
      const output = element as HTMLOutputElement;
      return [
        Number(output.dataset.x),
        Number(output.dataset.y),
        Number(output.dataset.z),
      ];
    });
  expect(
    Math.hypot(
      walkMoved[0]! - walkStart[0]!,
      walkMoved[1]! - walkStart[1]!,
      walkMoved[2]! - walkStart[2]!,
    ),
  ).toBeGreaterThan(0.1);
  await page.keyboard.down('Shift');
  await expect(page.getByTestId('flight-speed')).toHaveAttribute(
    'data-meters-per-second',
    '41.25',
  );
  await page.keyboard.up('Shift');
  await page.keyboard.press('r');
  await expect
    .poll(() =>
      page.getByTestId('eye-clearance').getAttribute('data-clearance-meters'),
    )
    .toMatch(/^1\.7\d+/);

  await page.keyboard.press('Escape');
  await expect
    .poll(() => page.evaluate(() => document.pointerLockElement === null))
    .toBe(true);
  const roadsToggle = page.getByTestId('roads-toggle');
  await roadsToggle.click();
  await expect(streetNames).toBeDisabled();
  await expect(streetNames).toHaveAttribute('aria-pressed', 'false');
  await expect(
    page.locator('.road-name-label:not(.road-name-measure):visible'),
  ).toHaveCount(0);
  await roadsToggle.click();
  await expect(streetNames).toBeEnabled();
  await expect(streetNames).toHaveAttribute('aria-pressed', 'false');
  await streetNames.click();
  await streetNames.click();
  await streetNames.click();
  await expect(streetNames).toHaveAttribute('aria-pressed', 'true');
  await expect(
    page.locator('.road-name-label:not(.road-name-measure)'),
  ).toHaveCount(20);
  const repeatedToggleLabels = await page
    .locator('.road-name-label:not(.road-name-measure):visible')
    .allTextContents();
  await expect(page.getByTestId('street-label-status')).toHaveAttribute(
    'data-visible-count',
    String(repeatedToggleLabels.length),
  );
  expect(new Set(repeatedToggleLabels).size).toBe(repeatedToggleLabels.length);
  for (const name of repeatedToggleLabels)
    expect(sourceNames.has(name)).toBe(true);

  await page.keyboard.press('Escape');
  await expect
    .poll(() => page.evaluate(() => document.pointerLockElement === null))
    .toBe(true);
  await page.getByTestId('world-select-synthetic').click();
  await expect(shell).toHaveAttribute('data-world-mode', 'synthetic');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded');
  await expect(page.getByTestId('road-controls')).toBeHidden();
  await expect(
    page.locator('.road-name-label:not(.road-name-measure):visible'),
  ).toHaveCount(0);
  expect(
    await page
      .locator('.road-name-label:not(.road-name-measure)')
      .allTextContents(),
  ).toEqual(Array(20).fill(''));

  const frameEvidence = (sample: FrameSample) => {
    const medianFrameIntervalMs = median(sample.frameIntervalsMs);
    return {
      frameIntervalsMs: sample.frameIntervalsMs,
      medianFrameIntervalMs,
      medianFps: medianFrameIntervalMs > 0 ? 1000 / medianFrameIntervalMs : 0,
      documentFocused: sample.documentFocused,
      documentVisible: sample.documentVisible,
      focusedFrameCount: sample.focusedFrameCount,
      visibleFrameCount: sample.visibleFrameCount,
      measuredFrameCount: sample.frameIntervalsMs.length,
    };
  };
  await writeFile(
    resolve(
      process.cwd(),
      'docs/milestones/artifacts/TVW-015-label-overhead.json',
    ),
    JSON.stringify(
      {
        formatVersion: 1,
        capturedAt: new Date().toISOString(),
        route: '/?world=torquay-poc-001&roads=1',
        browserName,
        browserVersion: page.context().browser()?.version(),
        ...browserEvidence,
        measurement: {
          warmupPerConditionMs: 2_000,
          samplingPerConditionMs: 3_000,
          cameraPoseUnchanged: true,
          viewportUnchanged: true,
          labelsOff: frameEvidence(labelsOff),
          labelsOn: frameEvidence(labelsOn),
          visibleLabelNodesOff: 0,
          visibleLabelNodesOn: visibleLabelsDuringMeasurement,
        },
        screenshots: [
          'docs/milestones/screenshots/TVW-015-street-labels-overview.png',
          'docs/milestones/screenshots/TVW-015-street-labels-walk.png',
        ],
      },
      null,
      2,
    ),
  );

  expect(pageErrors).toEqual([]);
  expect(consoleErrors).toEqual([]);
  expect(externalRequests).toEqual([]);
});
