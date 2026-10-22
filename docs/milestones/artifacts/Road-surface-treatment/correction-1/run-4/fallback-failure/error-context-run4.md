# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: road-surface.spec.ts >> preview load failures keep the validated source terrain
- Location: tests\e2e\road-surface.spec.ts:608:1

# Error details

```
Error: route.fetch: read ECONNRESET
Call log:
  - → GET http://127.0.0.1:4213/worlds/torquay-road-surface-preview/manifest.json
    - user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.8078.4 Safari/537.36
    - accept: */*
    - accept-encoding: gzip,deflate,br
    - accept-language: en-US
    - referer: http://127.0.0.1:4213/?roadSurface=preview
    - sec-ch-ua: "Not:A-Brand";v="8", "Chromium";v="156", "HeadlessChrome";v="156"
    - sec-ch-ua-mobile: ?0
    - sec-ch-ua-platform: "Windows"

```

```
Error: expect(locator).toHaveAttribute(expected) failed

Locator:  locator('.viewer-shell')
Expected: "loaded"
Received: "loading"

Call log:
  - Expect "toHaveAttribute" locator('.viewer-shell') with timeout 45000ms
  - waiting for locator('.viewer-shell')
    5 × locator resolved to <main data-triangles="0" data-draw-calls="0" class="viewer-shell" data-road-state="off" data-world-mode="real" data-texture-count="0" data-building-count="0" data-road-way-count="0" data-geometry-count="0" data-road-part-count="0" data-load-state="loading" data-building-state="off" data-road-visible="false" data-renderer-ready="false" data-building-components="0" data-building-mesh-count="0" data-building-visible="false" data-road-qa-marker-count="0" data-scene-profile="current_2km" data-road-surfac…>…</main>
      - unexpected value "loading"
  - Test ended.

```

```yaml
- main:
    - paragraph: REAL DATA · EA DTM 2022 composite
    - status: Loading the local Environment Agency DTM…
    - status: Loading and validating the local Environment Agency DTM package…
    - region "Torquay Virtual World"
    - button "Enter walk mode F"
    - button "Reset view"
    - button "Show controls"
    - paragraph: 2 km candidate · AOI pending; feature coverage not checked.
    - status: Loading local road-surface preview…
    - group: Sources
    - paragraph
```

# Test source

```ts
  558 |   expect(
  559 |     requests.some((url) => url.includes('torquay-road-surface-preview')),
  560 |   ).toBe(true);
  561 |   const runtime = await runtimeInfo(page);
  562 |   const report = {
  563 |     issue: 'Road-surface treatment preview',
  564 |     route: '/?roadSurface=preview',
  565 |     releaseId,
  566 |     sceneProfile: 'current_2km',
  567 |     sourceHashes: qa.source,
  568 |     baselineHeightfieldSha256: createHash('sha256')
  569 |       .update(baselineBytes)
  570 |       .digest('hex'),
  571 |     derivativeHeightfieldSha256: qa.derivative.sha256,
  572 |     derivativeByteLength: qa.derivative.byteLength,
  573 |     derivativeLoadMilliseconds: Number(
  574 |       await page
  575 |         .locator('.viewer-shell')
  576 |         .getAttribute('data-road-surface-load-ms'),
  577 |     ),
  578 |     gradientQa: qa.gridTreatment,
  579 |     profileComparisons: qa.profiles.ways,
  580 |     browserName,
  581 |     browserVersion: page.context().browser()?.version(),
  582 |     playwrightProject: testInfo.project.name,
  583 |     runtime,
  584 |     screenshots: screenshotRecords,
  585 |     walkChecks,
  586 |     requestedUrls: [...new Set(requests)],
  587 |     externalRequests,
  588 |     failedRequests,
  589 |     consoleErrors,
  590 |     pageErrors,
  591 |     notes: [
  592 |       'Screenshots are from the loaded Chromium scenes after Start; camera positions are set by the existing development-only alignment QA camera hook.',
  593 |       'Each connected candidate region meeting the added-gradient fallback heuristic has a registered before/after low-oblique view, keyed by source way IDs and local bounds in browserContexts.',
  594 |       'Camera Y and clearance use package-local display-grid metres; orthometric ground telemetry is recorded independently.',
  595 |       'Screenshot contexts are map-derived local coordinates and source centerlines, not Google imagery pixel matches.',
  596 |       'The two highest candidate added-gradient fallback regions receive matched Chromium views; registered per-region terrain and footing sections numerically cover every fallback region.',
  597 |       'Source heightfield, road centerlines and configured widths are unchanged; terrain treatment is an ignored local visual derivative.',
  598 |       'The EA preferred OSTN15 operation grid remains unavailable; the recorded conversion operation reports 2 m accuracy.',
  599 |     ],
  600 |   };
  601 |   await writeFile(
  602 |     resolve(evidenceDirectory, 'browser-evidence.json'),
  603 |     `${JSON.stringify(report, null, 2)}\n`,
  604 |     'utf8',
  605 |   );
  606 | });
  607 |
  608 | test('preview load failures keep the validated source terrain', async ({
  609 |   page,
  610 | }) => {
  611 |   const fallbackCases: { id: string; install: () => Promise<void> }[] = [];
  612 |   const requests: string[] = [];
  613 |   page.on('request', (request) => requests.push(request.url()));
  614 |
  615 |   fallbackCases.push({
  616 |     id: 'missing',
  617 |     install: async () => {
  618 |       await page.route(
  619 |         '**/torquay-road-surface-preview/manifest.json',
  620 |         (route) => route.fulfill({ status: 404, body: 'missing derivative' }),
  621 |       );
  622 |     },
  623 |   });
  624 |   fallbackCases.push({
  625 |     id: 'corrupt',
  626 |     install: async () => {
  627 |       await page.route(
  628 |         '**/torquay-road-surface-preview/heightfield.f32',
  629 |         async (route) => {
  630 |           const response = await route.fetch();
  631 |           const bytes = await response.body();
  632 |           bytes[100]! ^= 1;
  633 |           await route.fulfill({ response, body: bytes });
  634 |         },
  635 |       );
  636 |     },
  637 |   });
  638 |   fallbackCases.push({
  639 |     id: 'stale',
  640 |     install: async () => {
  641 |       await page.route(
  642 |         '**/torquay-road-surface-preview/manifest.json',
  643 |         async (route) => {
  644 |           const response = await route.fetch();
  645 |           const value = (await response.json()) as {
  646 |             source: { readySha256: string };
  647 |           };
  648 |           value.source.readySha256 = '0'.repeat(64);
  649 |           await route.fulfill({ json: value });
  650 |         },
  651 |       );
  652 |     },
  653 |   });
  654 |
  655 |   for (const testCase of fallbackCases) {
  656 |     await testCase.install();
  657 |     await page.goto('/?roadSurface=preview');
> 658 |     await expect(page.locator('.viewer-shell')).toHaveAttribute(
      |                                                 ^ Error: expect(locator).toHaveAttribute(expected) failed
  659 |       'data-load-state',
  660 |       'loaded',
  661 |     );
  662 |     await expect(page.locator('.viewer-shell')).toHaveAttribute(
  663 |       'data-road-surface-state',
  664 |       'fallback',
  665 |     );
  666 |     await expect(page.getByTestId('road-surface-preview-notice')).toHaveText(
  667 |       'Road-surface preview unavailable; showing source terrain.',
  668 |     );
  669 |     await expect(page.getByTestId('world-source-mode')).toHaveText(
  670 |       'LOCAL HEIGHTFIELD · EPSG:27700',
  671 |     );
  672 |     expect(
  673 |       requests.filter((url) => url.includes('torquay-road-surface-preview')),
  674 |     ).toContain(
  675 |       `http://127.0.0.1:4213/worlds/torquay-road-surface-preview/manifest.json`,
  676 |     );
  677 |     await page.unrouteAll({ behavior: 'wait' });
  678 |   }
  679 | });
  680 |
  681 | test('synthetic and historical profiles ignore the preview parameter; cancellation cannot install stale preview state', async ({
  682 |   page,
  683 | }) => {
  684 |   const requests: string[] = [];
  685 |   page.on('request', (request) => requests.push(request.url()));
  686 |   await page.goto('/?world=synthetic&roadSurface=preview');
  687 |   await expect(page.locator('.viewer-shell')).toHaveAttribute(
  688 |     'data-load-state',
  689 |     'loaded',
  690 |   );
  691 |   expect(
  692 |     requests.some((url) => url.includes('torquay-road-surface-preview')),
  693 |   ).toBe(false);
  694 |   await expect(page.locator('.viewer-shell')).toHaveAttribute(
  695 |     'data-road-surface-state',
  696 |     'off',
  697 |   );
  698 |
  699 |   requests.length = 0;
  700 |   await page.goto('/?world=torquay-poc-001&roadSurface=preview');
  701 |   await expect(page.locator('.viewer-shell')).toHaveAttribute(
  702 |     'data-load-state',
  703 |     'loaded',
  704 |   );
  705 |   await expect(page.locator('.viewer-shell')).toHaveAttribute(
  706 |     'data-scene-profile',
  707 |     'historical_1km',
  708 |   );
  709 |   expect(
  710 |     requests.some((url) => url.includes('torquay-road-surface-preview')),
  711 |   ).toBe(false);
  712 |   await expect(page.locator('.viewer-shell')).toHaveAttribute(
  713 |     'data-road-surface-state',
  714 |     'off',
  715 |   );
  716 |
  717 |   let releaseStalled: (() => void) | undefined;
  718 |   let requestStarted: (() => void) | undefined;
  719 |   const stalled = new Promise<void>((resolveStalled) => {
  720 |     releaseStalled = resolveStalled;
  721 |   });
  722 |   const started = new Promise<void>((resolveStarted) => {
  723 |     requestStarted = resolveStarted;
  724 |   });
  725 |   await page.route(
  726 |     '**/torquay-road-surface-preview/heightfield.f32',
  727 |     async (route) => {
  728 |       requestStarted?.();
  729 |       const response = await route.fetch();
  730 |       await stalled;
  731 |       try {
  732 |         await route.fulfill({ response });
  733 |       } catch {
  734 |         // The browser cancels the pending derivative request when the scene is replaced.
  735 |       }
  736 |     },
  737 |   );
  738 |   await page.evaluate(() => {
  739 |     window.history.pushState({}, '', '/?roadSurface=preview');
  740 |     window.dispatchEvent(new PopStateEvent('popstate'));
  741 |   });
  742 |   await started;
  743 |   await page.evaluate(() => {
  744 |     window.history.pushState({}, '', '/?world=synthetic');
  745 |     window.dispatchEvent(new PopStateEvent('popstate'));
  746 |   });
  747 |   await expect(page.locator('.viewer-shell')).toHaveAttribute(
  748 |     'data-scene-profile',
  749 |     '',
  750 |   );
  751 |   await expect(page.locator('.viewer-shell')).toHaveAttribute(
  752 |     'data-load-state',
  753 |     'loaded',
  754 |   );
  755 |   await expect(page.locator('.viewer-shell')).toHaveAttribute(
  756 |     'data-road-surface-state',
  757 |     'off',
  758 |   );
```
