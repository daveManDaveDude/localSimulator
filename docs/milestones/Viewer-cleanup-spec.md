# v0.1.0 viewer cleanup specification

The user authorized one descriptive cleanup issue on 2026-10-20 and explicitly selected Sol for implementation. A follow-up instruction requires roads and road names on by default. This changes presentation and entry behavior of the existing MVP; it is not TVW-016 and authorizes no source-data or GIS changes.

## Acceptance

- `/` and the existing current 2 km bookmark load the active immutable terrain/buildings/roads release. Current-profile layer query flags do not disable layers.
- The product presents one map, Start, fly/walk, Reset, Controls help, concise load/error/retry feedback, Sources and attribution. Remove visible world/layer selectors, telemetry, grid/axes/north helpers, wireframes, debug landmarks and the unavailable overview. `G` must not change helpers. Roads and their OSM name labels are on by default in the current 2 km product, with no label toggle. Labels use only validated source names and retain the existing 20-label / 500 m / collision-filter limits.
- Show `2 km candidate · AOI pending; feature coverage not checked.` while the real current scene is active. Sources retain EA/OSM credit/licence links, vintages, 1 m source / 2 m mesh distinction and estimated-height/width caveats.
- A missing or invalid current package automatically loads clearly labelled fictional synthetic terrain, preserves the Torquay bookmark, states why it fell back, and offers Retry Torquay. Layer failures preserve terrain and offer focused retries. When named road features are in view, source-derived labels appear without user activation; labels must never invent names or imply complete road coverage.
- Preserve pointer lock, mouse look, WASD, fly vertical movement, Shift, F/R/H/Escape, 15/41.25 m/s speed, 1.7 m walk clearance, reset, bounds and resize behavior.
- Preserve synthetic fixtures and internal reproduction routes, historical 1 km package and provenance, exact TQ1 4HN center, pending statuses, and all source/current package bytes. No pipeline/config/source/package changes, resolution change, geometry repair, dependency or version change.

## Implementation and proof

Expected changes: app presentation/route defaults, CSS, focused current E2E profiles, README/current status documentation and new evidence. Retain invisible diagnostic observations for navigation and loader tests. Internal synthetic route: `/?world=synthetic`; M0 and explicit historical routes remain available for reproduction but are not app choices.

Run TypeScript/lint/format/Vitest, production and share builds, current 2 km and share fallback production browser checks, historical/internal regressions, and `git diff --check`. Test product controls for absence from the accessibility tree, not just missing screenshots. Capture new cleanup-specific default, active, outer-area, Sources and fallback images; preserve earlier evidence. Do not touch the user's port 5173, installer, recovery stages or coordinator-private checkpoint. Record executed gates, browser observations, limitations and protected-file identities in the handback, then obtain independent review before coordinator acceptance.

## Resolution and alignment context

Existing evidence distinguishes the 1 m EA Composite DTM cells from the current 2 m mesh. Saved time-stamped metadata has 0.5 m footprints over 9.9407% of the AOI, dated 2010; no finer raster was checked. The dated OSM extract is 2026-10-16. Three historical contexts passed qualitative placement comparisons, with no numeric offset measurement. The recorded coordinate operation reports 2 m accuracy and a missing preferred OSTN15 grid. These are limitations, not a road-offset diagnosis or authorization to change data.

Official sources: [EA composite catalogue](https://www.data.gov.uk/dataset/01b3ee39-da3f-47b6-83da-dc98e73a461f/lidar-composite-dtm-2022-1m), [EA time-stamped catalogue](https://www.data.gov.uk/dataset/8275e71e-1516-42a1-bb0c-4fa73807fe2b/lidar-dtm-time-stamped-tiles), [Geofabrik Devon](https://download.geofabrik.de/europe/united-kingdom/england/devon.html), and [OS transformation resources](https://www.ordnancesurvey.co.uk/geodesy-positioning/coordinate-transformations/resources). Local measured evidence remains in the 2 km handback, resolution-index assessment and current release QA.
