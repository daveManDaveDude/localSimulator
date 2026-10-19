# TVW-012 milestone handback

**Status:** PASS after independent Sol review on 2026-10-19. The coordinator accepted the combined M5 exit gate after that review.

**Scope:** compare the local OSM road/building package at three bounded junction contexts with an independent OS OpenMap–Local raster source. No source geometry, terrain, AOI, or production package was retuned as part of this issue.

## Outcome

- Three comparisons passed as **qualitative placement matches**: Second Avenue / Main Avenue; Pencorse Road / Audley Avenue; Teignmouth Road / Snowberry Close.
- The former St. Vincent’s Road / Chapel Court candidate remains inconclusive and uncounted. Pencorse Road / Audley Avenue replaced the unavailable Baron Road / Lindfield Close NW candidate; Teignmouth Road / Snowberry Close replaced the inconclusive St. Vincent’s / Chapel Court SW candidate.
- The generated [comparison report](TVW-012.md) contains the registered reference, overlay, package and WebGL scene evidence. Each of the three checks has four panels. The four panels for the prior inconclusive candidate remain available there too.
- No numeric alignment offset was measured. The screening threshold and OS map generalization do not provide a survey tolerance or accuracy guarantee.
- AOI status remains `selected_pending_coverage` / `not_checked`; TQ1 4HN remains the anchor. These spot checks do not prove dataset completeness or approve/freeze the AOI.
- TVW-013 walk mode was not started and requires separate authorization.

## Source and provenance

- Ordnance Survey OS OpenMap–Local GeoTIFF Full Colour, April 2026; ZIP archive size 349,405,146 bytes; SHA-256 `d9a01900c4dd5c26af50d6aed79f419a1957acf4167aedef97bb905ffcdff853`.
- EPSG:27700 palette GeoTIFF, 1 m pixels, `AREA_OR_POINT=Area`; selected comparison tiles are `SX96SW` and `SX96NW`.
- Attribution: `Contains Ordnance Survey data © Crown copyright and database right 2026`, under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
- OSM-to-BNG used the recorded EPSG:1314 plus EPSG:19916 operation, reported accuracy 2 m. The preferred OSTN15 grid is unavailable; the recorded `best_available` value is false.
- The archive and comparison outputs remain separate from production GIS assets. No live map service or paid key is used.

## Commands and results

From `C:\vibe\localSimulator\pipeline`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_alignment_report.py -q
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m torquay_pipeline.cli inspect-comparison-source
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-alignment-report
.\.venv\Scripts\python.exe -m torquay_pipeline.cli compare-alignment
```

The focused validator suite passed **29 tests** and the full Python suite passed **199 tests**. Ruff check/format and `pip check` passed. Source inspection verified the archive and both selected tiles. Report validation returned three spots, 12 current evidence files and one prior candidate. `compare-alignment` ran twice; the report JSON, generated Markdown and 12 static reference/overlay/package PNGs (three panel types across the three accepted contexts and retained prior candidate) hashed by the command below matched across both generations. The three accepted WebGL scene captures were produced in the Playwright run and were not part of that hash command.

The hash comparison command, also run from `pipeline`, was:

```powershell
.\.venv\Scripts\python.exe -c "import hashlib,pathlib; p=pathlib.Path('../docs/milestones'); fs=[p/'TVW-012.md',p/'artifacts/TVW-012-alignment.json',*sorted((p/'screenshots').glob('TVW-012-*-reference.png')),*sorted((p/'screenshots').glob('TVW-012-*-overlay.png')),*sorted((p/'screenshots').glob('TVW-012-*-package.png'))]; [print(hashlib.sha256(x.read_bytes()).hexdigest(),x.as_posix()) for x in fs]"
```

From `C:\vibe\localSimulator`:

```powershell
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run format:check
npm.cmd test
npm.cmd run build
npm.cmd run test:e2e -- --output=test-results/tvw012-fix2
git diff --check
```

Typecheck, lint, format check and build passed; Vitest passed **224 tests**; Playwright passed **14 tests**; `git diff --check` passed. Vite emitted its existing advisory for a JavaScript chunk over 500 kB. E2E-mutated historical screenshots were restored; the historical screenshot diff is empty.

The generated comparison report retains its generation-time field `Combined M5: pending coordinator review`. This handback records the subsequent coordinator acceptance after the independent review passed; the report's qualitative findings and data-integrity record were not edited by hand.

## Browser evidence and review

Playwright Chromium `156.0.8078.4`, viewport 1440×900, device pixel ratio 1.5, using ANGLE/Vulkan SwiftShader software rendering. The run completed without console, page or network errors. The independent reviewer reinspected the three existing WebGL scene captures; it did not run a fresh E2E capture.

- NE: [Second Avenue / Main Avenue scene](screenshots/TVW-012-ne-second-main-scene.png)
- NW: [Pencorse Road / Audley Avenue scene](screenshots/TVW-012-nw-audley-pencorse-scene.png)
- SW: [Teignmouth Road / Snowberry Close scene](screenshots/TVW-012-sw-teignmouth-snowberry-scene.png)

Sol 6.1 medium independently reviewed commit `734a0a13a6b41140c454bc7cfaab3d73da59f91d` and returned PASS. It confirmed rejection of contradictory archive/tile/raster/window/dimension/selection/registration/panel mutations and the earlier control, coordinate, digest, browser pose and evidence mutations. It also confirmed that an injected publication failure preserved all 11 outputs and all 17 local Markdown links resolve.

## Known limits and next issue

OS OpenMap–Local is generalized cartography; OSM is a mapped database. Source labels, symbol widths and dates, the 2 m reported coordinate-operation accuracy, and the unavailable preferred OSTN15 grid limit conclusions. The original NW Baron Road / Lindfield Close target remains unavailable/ambiguous. The prior SW St. Vincent’s / Chapel Court comparison remains inconclusive and is not counted. No completeness claim is made; remaining feature coverage checks and M2 remain pending.

Next proposed issue: TVW-013 walk mode. It remains unauthorized and was not started.
