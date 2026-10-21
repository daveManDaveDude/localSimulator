import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
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

type RoadFeature = {
  source: { osmId: number };
  sourceTags: { name?: string };
  centerlinePartsXZ: number[][][];
};

type CurrentTerrainManifest = {
  id: string;
  sceneProfile: string;
  origin: { eastingM: number; northingM: number; elevationM: number };
  extentM: { width: number; depth: number };
  heightfield: {
    path: string;
    columns: number;
    rows: number;
    spacingM: number;
    sha256: string;
  };
};

type ClosestRoadPoint = {
  x: number;
  z: number;
  tangentX: number;
  tangentZ: number;
  distanceM: number;
  wayId: number;
  name: string;
};

type VisibleRoadLabel = {
  name: string;
  key: string;
  wayId: number | null;
  distanceM: number | null;
};

const roadAlignmentReleaseId =
  '616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a';

const roadAlignmentContexts = [
  {
    id: 'pennys-teignmouth-steep',
    anchorXZ: [-244.518, -58.794] as const,
    wayIds: [78455388, 78455395],
    sourceNames: ['Pennys Hill', 'Teignmouth Road'],
  },
  {
    id: 'cricketfield-teignmouth-junction',
    anchorXZ: [-307.96, -28.828] as const,
    wayIds: [23595196, 686711262, 689028452, 24806641, 30480035],
    sourceNames: ['Cricketfield Road', 'Teignmouth Road'],
  },
  {
    id: 'arthington-control',
    anchorXZ: [-511.744, 207.096] as const,
    wayIds: [30482119, 30482121],
    sourceNames: ['Arthington'],
  },
] as const;

function closestRoadPoint(
  features: RoadFeature[],
  wayIds: readonly number[],
  anchorXZ: readonly [number, number],
): ClosestRoadPoint {
  let closest: ClosestRoadPoint | undefined;
  for (const feature of features) {
    const wayId = feature.source.osmId;
    if (!wayIds.includes(wayId)) continue;
    for (const part of feature.centerlinePartsXZ) {
      for (let index = 0; index < part.length - 1; index += 1) {
        const first = part[index];
        const second = part[index + 1];
        if (!first || !second) continue;
        const dx = second[0]! - first[0]!;
        const dz = second[1]! - first[1]!;
        const lengthSquared = dx * dx + dz * dz;
        if (lengthSquared <= 0) continue;
        const amount = Math.max(
          0,
          Math.min(
            1,
            ((anchorXZ[0] - first[0]!) * dx + (anchorXZ[1] - first[1]!) * dz) /
              lengthSquared,
          ),
        );
        const x = first[0]! + amount * dx;
        const z = first[1]! + amount * dz;
        const distanceM = Math.hypot(x - anchorXZ[0], z - anchorXZ[1]);
        if (!closest || distanceM < closest.distanceM) {
          const segmentLength = Math.sqrt(lengthSquared);
          closest = {
            x,
            z,
            tangentX: dx / segmentLength,
            tangentZ: dz / segmentLength,
            distanceM,
            wayId,
            name: feature.sourceTags.name ?? String(wayId),
          };
        }
      }
    }
  }
  if (!closest)
    throw new Error(
      'No package centerline covers the selected candidate area.',
    );
  return closest;
}

function packageTerrainSampler(
  manifest: CurrentTerrainManifest,
  bytes: Buffer,
): (x: number, z: number) => { localM: number; orthometricM: number } {
  const { columns, rows, spacingM } = manifest.heightfield;
  if (bytes.byteLength !== columns * rows * 4) {
    throw new Error(
      'Current release heightfield has an unexpected byte length.',
    );
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const halfWidth = manifest.extentM.width / 2;
  const halfDepth = manifest.extentM.depth / 2;
  return (x, z) => {
    const gridX = (x + halfWidth) / spacingM;
    const gridZ = (z + halfDepth) / spacingM;
    if (gridX < 0 || gridX > columns - 1 || gridZ < 0 || gridZ > rows - 1) {
      throw new Error(
        'Selected camera pose falls outside the current terrain package.',
      );
    }
    const column = Math.min(Math.floor(gridX), columns - 2);
    const row = Math.min(Math.floor(gridZ), rows - 2);
    const u = gridX - column;
    const v = gridZ - row;
    const sample = (sampleRow: number, sampleColumn: number): number =>
      view.getFloat32((sampleRow * columns + sampleColumn) * 4, true);
    const a = sample(row, column);
    const b = sample(row, column + 1);
    const c = sample(row + 1, column);
    const d = sample(row + 1, column + 1);
    const localM =
      u + v <= 1
        ? a + (b - a) * u + (c - a) * v
        : d + (c - d) * (1 - u) + (b - d) * (1 - v);
    return {
      localM,
      orthometricM: localM + manifest.origin.elevationM,
    };
  };
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

test('Road-alignment current 2km captures the three candidate contexts', async ({
  page,
  browserName,
}) => {
  test.setTimeout(240_000);

  const worldRoot = resolve(process.cwd(), 'public/worlds/torquay-poc-001-2km');
  const ready = JSON.parse(
    await readFile(resolve(worldRoot, 'ready.json'), 'utf8'),
  ) as { releaseId: string };
  expect(ready.releaseId).toBe(roadAlignmentReleaseId);
  const releaseRoot = resolve(worldRoot, 'releases', ready.releaseId);
  const manifest = JSON.parse(
    await readFile(resolve(releaseRoot, 'manifest.json'), 'utf8'),
  ) as CurrentTerrainManifest;
  const roadManifest = JSON.parse(
    await readFile(resolve(releaseRoot, 'roads/manifest.json'), 'utf8'),
  ) as { sceneProfile: string; assets: { roads: { sha256: string } } };
  const roadPackage = JSON.parse(
    await readFile(resolve(releaseRoot, 'roads/roads.json'), 'utf8'),
  ) as { features: RoadFeature[] };
  const heightfieldBytes = await readFile(
    resolve(releaseRoot, manifest.heightfield.path),
  );
  expect(manifest.sceneProfile).toBe('current_2km');
  expect(roadManifest.sceneProfile).toBe('current_2km');
  const terrainAt = packageTerrainSampler(manifest, heightfieldBytes);

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

  await page.goto('/');
  const shell = page.locator('.viewer-shell');
  await expect(shell).toHaveAttribute('data-world-mode', 'real');
  await expect(shell).toHaveAttribute('data-scene-profile', 'current_2km');
  await expect(shell).toHaveAttribute('data-load-state', 'loaded', {
    timeout: 120_000,
  });
  await expect(shell).toHaveAttribute('data-renderer-ready', 'true');
  await expect(shell).toHaveAttribute('data-road-state', 'loaded', {
    timeout: 120_000,
  });
  await expect(shell).toHaveAttribute('data-building-state', 'loaded', {
    timeout: 120_000,
  });
  await expect(page.getByTestId('road-status')).toHaveAttribute(
    'data-way-count',
    '1044',
  );
  await expect(page.getByTestId('building-status')).toHaveAttribute(
    'data-building-count',
    '3613',
  );

  await page.getByTestId('start-button').click();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.pointerLockElement === document.querySelector('canvas'),
      ),
    )
    .toBe(true);

  const localOrigin = new URL(page.url()).origin;
  const evidence: Record<string, unknown>[] = [];
  const screenshotDirectory = resolve(
    process.cwd(),
    'docs/milestones/screenshots/Road-alignment',
  );
  await mkdir(screenshotDirectory, { recursive: true });

  for (const context of roadAlignmentContexts) {
    const target = closestRoadPoint(
      roadPackage.features,
      context.wayIds,
      context.anchorXZ,
    );
    const bearing =
      ((Math.atan2(target.tangentX, -target.tangentZ) * 180) / Math.PI + 360) %
      360;
    const views = [
      {
        id: 'overhead',
        offsetM: 0,
        eyeHeightAboveTerrainM: 110,
        pitchDegrees: -82,
      },
      {
        id: 'low-oblique',
        offsetM: 45,
        eyeHeightAboveTerrainM: 15,
        pitchDegrees: -24,
      },
    ] as const;

    for (const view of views) {
      const x = target.x - target.tangentX * view.offsetM;
      const z = target.z - target.tangentZ * view.offsetM;
      const ground = terrainAt(x, z);
      await page.evaluate(
        ({ poseX, poseY, poseZ, poseBearing, posePitch }) => {
          const qa = window.__torquayAlignmentQa;
          if (!qa)
            throw new Error(
              'Development-only alignment camera hook is missing.',
            );
          qa.setPose({
            x: poseX,
            y: poseY,
            z: poseZ,
            bearingDegrees: poseBearing,
            pitchDegrees: posePitch,
          });
        },
        {
          poseX: x,
          poseY: ground.orthometricM + view.eyeHeightAboveTerrainM,
          poseZ: z,
          poseBearing: bearing,
          posePitch: view.pitchDegrees,
        },
      );

      await expect
        .poll(async () => {
          const pose = await cameraPose(page);
          return Math.hypot(pose.x - x, pose.z - z);
        })
        .toBeLessThan(0.02);
      const pose = await cameraPose(page);
      expect(pose.y).toBeCloseTo(
        ground.orthometricM + view.eyeHeightAboveTerrainM,
        2,
      );
      expect(pose.bearing).toBeCloseTo(bearing, 1);
      expect(pose.pitch).toBeCloseTo(view.pitchDegrees, 1);
      const sampledGroundLocalM = Number(
        await page
          .getByTestId('ground-height')
          .getAttribute('data-height-meters'),
      );
      const sampledGroundOrthometricM = Number(
        await page
          .getByTestId('ground-height')
          .getAttribute('data-orthometric-meters'),
      );
      expect(sampledGroundLocalM).toBeCloseTo(ground.localM, 3);
      expect(sampledGroundOrthometricM).toBeCloseTo(ground.orthometricM, 3);

      const readVisibleRoadLabels = async (): Promise<VisibleRoadLabel[]> =>
        page
          .locator('.road-name-label:not(.road-name-measure):not([hidden])')
          .evaluateAll((labels) =>
            labels.map((element) => {
              const label = element as HTMLElement;
              const key = label.dataset.roadLabelKey ?? '';
              const parsedWayId = Number(key.split(':', 1)[0]);
              const parsedDistance = Number(label.dataset.distanceMeters);
              return {
                name: label.textContent?.trim() ?? '',
                key,
                wayId: Number.isSafeInteger(parsedWayId) ? parsedWayId : null,
                distanceM: Number.isFinite(parsedDistance)
                  ? parsedDistance
                  : null,
              };
            }),
          );

      if (view.id === 'overhead') {
        await expect
          .poll(async () => {
            const labels = await readVisibleRoadLabels();
            return labels.some(
              (label) =>
                label.wayId === target.wayId && label.name === target.name,
            );
          })
          .toBe(true);
      } else {
        await page.waitForTimeout(150);
      }
      const visibleRoadLabels = await readVisibleRoadLabels();
      expect(visibleRoadLabels.length).toBeGreaterThan(0);
      const candidateRoadLabels = visibleRoadLabels.filter(
        (label) =>
          label.wayId !== null &&
          context.wayIds.some((wayId) => wayId === label.wayId),
      );
      for (const label of candidateRoadLabels) {
        const feature = roadPackage.features.find(
          (item) => item.source.osmId === label.wayId,
        );
        expect(label.name).toBe(feature?.sourceTags.name);
      }
      if (view.id === 'overhead') {
        expect(
          candidateRoadLabels.some(
            (label) =>
              label.wayId === target.wayId && label.name === target.name,
          ),
        ).toBe(true);
      }

      const filename = `${context.id}-${view.id}.png`;
      const screenshotPath = resolve(screenshotDirectory, filename);
      await page.screenshot({ path: screenshotPath, animations: 'disabled' });
      const screenshotSha256 = createHash('sha256')
        .update(await readFile(screenshotPath))
        .digest('hex');
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
        contextId: context.id,
        screenshot: `docs/milestones/screenshots/Road-alignment/${filename}`,
        screenshotSha256,
        view: view.id,
        selectedWayId: target.wayId,
        selectedWayName: target.name,
        candidateSourceNames: [...context.sourceNames],
        visibleSourceNames: [
          ...new Set(visibleRoadLabels.map((label) => label.name)),
        ],
        visibleRoadLabels,
        candidateRoadLabels,
        candidateLabelNote:
          candidateRoadLabels.length > 0
            ? 'At least one visible DOM label belongs to a candidate context way; its name is checked against the current package source tags.'
            : 'No label for a candidate context way was rendered in this frame; the visible list is retained, and no placement cause is inferred.',
        candidateAnchorLocalXZ: [...context.anchorXZ],
        centerlineTargetLocalXZ: [target.x, target.z],
        centerlineTargetBngEN: [
          manifest.origin.eastingM + target.x,
          manifest.origin.northingM - target.z,
        ],
        distanceFromCandidateAnchorM: target.distanceM,
        centerlineTangentLocalXZ: [target.tangentX, target.tangentZ],
        poseDerivation:
          'nearest projected point on the named current-release package centerline; ' +
          'low-oblique camera is offset opposite its local tangent; bearing follows tangent',
        camera: pose,
        sampledGroundLocalM,
        sampledGroundOrthometricM,
        eyeHeightAboveSampledTerrainM: pose.y - sampledGroundOrthometricM,
        releaseId: ready.releaseId,
        sceneProfile: manifest.sceneProfile,
        roadManifestSha256: roadManifest.assets.roads.sha256,
        browserName,
        browserVersion: page.context().browser()?.version(),
        viewport: await page.evaluate(() => ({
          width: innerWidth,
          height: innerHeight,
          devicePixelRatio,
        })),
        runtime,
      });
    }
  }

  expect(
    requestedUrls.every((url) => new URL(url).origin === localOrigin),
  ).toBe(true);
  expect(
    requestedUrls.some((url) =>
      url.includes(`/releases/${roadAlignmentReleaseId}/heightfield.f32`),
    ),
  ).toBe(true);
  expect(
    requestedUrls.some((url) =>
      url.includes(`/releases/${roadAlignmentReleaseId}/roads/roads.json`),
    ),
  ).toBe(true);
  expect(
    requestedUrls.some((url) =>
      url.includes(
        `/releases/${roadAlignmentReleaseId}/buildings/buildings.json`,
      ),
    ),
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
    'docs/milestones/artifacts/Road-alignment/browser-evidence.json',
  );
  await writeFile(
    evidencePath,
    JSON.stringify(
      {
        title: 'Road-alignment current 2km',
        route: '/',
        releaseId: ready.releaseId,
        sceneProfile: manifest.sceneProfile,
        pointerLockVerifiedBeforeCaptures: true,
        consoleErrors,
        pageErrors,
        failedRequests,
        allRequestsLocal: requestedUrls.every(
          (url) => new URL(url).origin === localOrigin,
        ),
        requestedReleaseAssets: requestedUrls.filter((url) =>
          url.includes(`/releases/${roadAlignmentReleaseId}/`),
        ),
        evidence,
      },
      null,
      2,
    ),
    'utf8',
  );
});
