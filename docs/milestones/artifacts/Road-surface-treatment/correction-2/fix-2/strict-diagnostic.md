# Correction 2 — Luna fix 2 strict numerical diagnostic

**Result:** strict full-corridor acceptance failed. This is a read-only in-memory candidate, not an accepted derivative. No derivative bytes, build record, browser profile, screenshot, or runtime geometry evidence was produced for fix 2.

## Reproduction and global grid checks

The diagnostic loaded the pinned current release `616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a` and source heightfield `c61bd03d4172bffb07be596c4f63cc11a0681d0cacd884bb7dfcf3411be815af`. It called the in-memory `_grade_grid` path against the 1001 × 1001 grid at 2 m spacing using all 4,395 eligible segments. The diagnostic was repeated to extract bounded corridor, longitudinal and footing summaries after a verbose console result was truncated. It did not call the builder or write assets.

| Gate                                  |                  Measured result |        Limit | Result |
| ------------------------------------- | -------------------------------: | -----------: | ------ |
| Maximum absolute terrain change       |                       4.831289 m |         <5 m | Pass   |
| Maximum positive added edge gradient  |                   0.99900055 m/m |     <1.0 m/m | Pass   |
| Float32 constraint residual           |                     0.00000110 m |   ≤0.00005 m | Pass   |
| Building-base p95 absolute shift      |                       0.089387 m |     ≤0.183 m | Pass   |
| Building-base maximum absolute shift  |                       0.179241 m |     ≤2.424 m | Pass   |
| Centerline maximum absolute deviation | 0.099157 m across 86,005 samples |      ≤0.10 m | Pass   |
| Newton legacy building base shifts    |                0 to 0.00000327 m | ≤0.05 m each | Pass   |

The maximum added gradient occurs on edge `[692,-570]`–`[694,-570]`: baseline magnitude 0.546886 m/m and preview magnitude 1.545887 m/m, an increase of 0.99900055 m/m. No positive edge exceeds the strict 1.0 m/m cap. This leaves only approximately 0.001 m/m numerical margin and is reported as the measured value, not as an engineering threshold.

## Full mandatory corridors

Every corridor used centerline stations at no more than 1 m, included original source vertices and registered controls, and sampled full configured width at no more than 0.25 m. Treated/transition/untreated lengths classify a station by whether 100%, some, or none of its lateral samples differ from baseline by more than 0.01 m; lengths are Voronoi-allocated along the source part. These are visual-grid measurements.

| Corridor / way             | Width |    Length | Stations / max spacing | Severe baseline stations ≥10%: meeting 50% / total | Treated / transition / untreated length | Baseline max / p90 / p95 / median (%) | Preview max / p90 / p95 / median (%) |
| -------------------------- | ----: | --------: | ---------------------: | -------------------------------------------------: | --------------------------------------: | ------------------------------------: | -----------------------------------: |
| Parkfield Road / 30480989  |   6 m | 501.035 m |         530 / 0.9981 m |                                          180 / 186 |                  22.309 / 478.725 / 0 m |  44.8595 / 28.2917 / 33.9839 / 4.6725 |    8.3724 / 0.2174 / 1.1025 / 0.0285 |
| Pennys Hill / 78455388     |   7 m | 145.870 m |         155 / 0.9991 m |                                           64 / 108 |              2.997 / 122.891 / 19.982 m | 47.8641 / 38.5130 / 42.5752 / 19.1922 | 47.8641 / 35.3981 / 38.0408 / 0.4727 |
| Teignmouth Road / 78455395 |   6 m | 232.352 m |         252 / 0.9972 m |                                           73 / 145 |             14.868 / 138.167 / 79.317 m | 94.0281 / 21.5777 / 55.6784 / 11.3429 | 62.6111 / 15.7557 / 35.4571 / 4.6685 |

The strict severe-station gate fails at all three corridors:

- **Parkfield:** six of 186 baseline-severe stations miss the required 50% decrease. Exact misses are 249.5193 m (10.4987% → 5.2785%), 250.5173 m (10.7819% → 5.9301%), 251.2032 m (11.0219% → 6.5883%), 251.5154 m (10.8976% → 6.3952%), 252.5135 m (12.1762% → 6.8694%), and 253.5116 m (13.4565% → 7.3204%). Their surface classifications are transition, transition, transition, transition, treated, transition.
- **Pennys Hill:** 44 of 108 severe stations miss the 50% reduction. Its baseline-worst station at 31.9715 m is untreated: crossfall remains 47.8641%, and full-width span remains 3.44090 m. The corridor maximum is unchanged at 47.8641%; therefore its maximum-crossfall reduction gate fails even though p95 falls from 42.5752% to 38.0408% and median falls from 19.1922% to 0.4727%.
- **Teignmouth:** 72 of 145 severe stations miss the 50% reduction. The baseline-worst station at 148.1510 m is treated, but falls only from 94.0281% to 62.6111%. Corridor maximum and p95 both decrease, but the severe-station gate fails.

Both registered Parkfield controls pass the full-width thresholds:

|    Station | Baseline crossfall / span | Preview crossfall / span | Centerline deviation | Result |
| ---------: | ------------------------: | -----------------------: | -------------------: | ------ |
| 396.0108 m |      35.9306% / 2.15584 m |     0.24791% / 0.01822 m |           +0.01316 m | Pass   |
| 409.2610 m |      42.7097% / 2.56258 m |     0.05491% / 0.00707 m |           +0.00244 m | Pass   |

Each section used 25 samples at 0.25 m spacing across the configured 6 m width. The exact control passes do not excuse missed severe stations elsewhere on Parkfield.

## Signed longitudinal profiles

All source stations were sampled at no more than 5 m, including original vertices. Every measured centerline elevation change is within 0.10 m and every signed grade change is within 2 percentage points. Ranges below are signed preview-minus-baseline grade deltas; maxima are absolute.

|                  Way | Max absolute elevation change | Signed grade-change range | Max absolute grade change |
| -------------------: | ----------------------------: | ------------------------: | ------------------------: |
|   Parkfield 30480989 |                    0.046511 m |   −1.41796 to +1.27631 pp |                1.41796 pp |
|  Arthington 30482119 |                    0.005714 m |   −0.10155 to +0.13143 pp |                0.13143 pp |
|  Arthington 30482121 |                    0.005476 m |   +0.05666 to +0.20300 pp |                0.20300 pp |
|      Newton 46348326 |                    0.012437 m |   −0.84646 to +0.24100 pp |                0.84646 pp |
| Pennys Hill 78455388 |                    0.036546 m |   −0.37620 to +0.73717 pp |                0.73717 pp |
|  Teignmouth 78455395 |                    0.044755 m |   −1.67385 to +1.15756 pp |                1.67385 pp |
| Lymington 1363931058 |                    0.036546 m |   −1.38735 to +1.54975 pp |                1.54975 pp |

## Registered building footing sections

Each section is a 1 m-spaced local-X line through the footprint-bounds midpoint Z. “Whole base” is the terrain-derived building-base change, while “section maximum” is the largest pointwise terrain change along that registered slice.

| Area    | Building ID | Whole-base change | Samples | Maximum absolute section change |
| ------- | ----------- | ----------------: | ------: | ------------------------------: |
| Newton  | 196536218   |     +0.00000327 m |      21 |                    0.00001144 m |
| Newton  | 196536220   |               0 m |       5 |                             0 m |
| Newton  | 196536221   |               0 m |      20 |                             0 m |
| Newton  | 196536227   |               0 m |      20 |                             0 m |
| Newton  | 196536217   |               0 m |      21 |                             0 m |
| Sanford | 194444458   |       −0.089250 m |       5 |                      0.284855 m |
| Cavern  | 207341667   |               0 m |       4 |                             0 m |
| Cavern  | 207341692   |               0 m |       6 |                             0 m |
| Cavern  | 207341702   |               0 m |       5 |                             0 m |
| Cavern  | 207341535   |               0 m |      14 |                             0 m |
| Cavern  | 207341753   |               0 m |      20 |                             0 m |

The Sanford section’s largest sample is local X/Z `[-647, 911.789]`, with baseline `-32.763652 m`, preview `-32.478797 m`, and `+0.284855 m` difference. This pointwise section change is distinct from the whole-base value and must remain visible in review.

## Commands and stopping decision

The no-write diagnostic loaded `config/road-surface-preview.json`, called `load_release_inputs`, `_segments_from_payload` and `_grade_grid(..., inputs=inputs)`, and emitted only an in-memory summary. It was repeated after truncation of the initial verbose output; all reported values came from the same pinned inputs and deterministic path. The project quality command passed:

```powershell
$env:PYTHONPATH=(Resolve-Path pipeline).Path
pipeline/.venv/Scripts/pytest.exe pipeline/tests/test_road_surface.py pipeline/tests/test_road_alignment.py pipeline/tests/test_roads.py pipeline/tests/test_terrain_export.py -q
pipeline/.venv/Scripts/ruff.exe check pipeline/torquay_pipeline/road_surface.py pipeline/tests/test_road_surface.py
pipeline/.venv/Scripts/ruff.exe format --check pipeline/torquay_pipeline/road_surface.py pipeline/tests/test_road_surface.py
```

Results: **67 passed, 1 skipped**; Ruff check passed; format check passed. The skipped test needs Windows directory-symlink privilege unavailable to this account. No TypeScript/runtime files changed. No builder, browser, screenshot, share, or server command ran because the corridor numerical gate failed. The implementation now makes the builder refuse to write preview files or an execution record if these full-corridor or signed-longitudinal acceptance flags fail.

The failure is a treatment-coverage and mandatory-station problem, not a longitudinal or global-grid safety failure. Do not loosen thresholds, treat corridor-level percentiles as a substitute for failed severe stations, or call Correction 2 accepted. The next step requires a new reviewed treatment approach; the current candidate is withheld.
