# Correction 3 evidence plan — Float32 topology representation 1

Status: Luna correction cycle 3 implementation submitted for coordinator review and independent Sol review. No source load, candidate build, diagnostic, browser or screenshot was run.

## Frozen evidence and preservation

`input-manifest.json` binds 199 protected inputs and the exact `pipeline/.venv/Scripts/python.exe` identity. The coordinator-owned attempt ledger is recorded separately as mutable metadata. All 199 manifest file hashes were rechecked after creation: zero missing files and zero hash mismatches. The candidate output `data/generated/teignmouth-float32-topology/` was absent at freeze. The prior correction-2 manifest/evidence, build-1 report/evidence, reviews and coordinator dispositions remain in place and were not edited.

Three already-bound implementation paths changed from correction 2: `pipeline/scripts/build_teignmouth_float32_candidate.py`, `pipeline/tests/test_teignmouth_float32_candidate.py`, and `pipeline/torquay_pipeline/teignmouth_float32_candidate.py`. No source, config, origin, topology guard, recipe, geometry domain or numerical limit was changed. The attempt ledger is unchanged by this submission; counters are 2 Luna corrections used / 1 reserved (this cycle), 1 implementation build used / 0 reserved, and 1 diagnostic used / 0 reserved.

## Findings addressed

- Added exact chart-support validation against the frozen generated stations, chart points, triangle list, support polygon union and triangle ownership. Candidate vertices outside influence retain source terrain. Vertices inside influence but outside the validated chart support also retain source terrain and are counted with representative coordinates and source-to-candidate height differences. A vertex inside expected support without an owner fails. Required carriageway/shoulder samples fail when coverage or ownership is missing.
- Added synthetic regressions for broad influence beyond chart support, missing owner inside support, incomplete/corrupted support, required target coverage, and zero treatment at lateral ±16 m and stations 108/187 with active just-inside samples.
- Kept the outside-influence source overlay gate and added an exact source-plane overlay check for the classified inside-influence/outside-chart-support region.
- Worker logical status and return code now propagate through the child process. The supervisor records logical worker status/result, actual child exit, runner-chosen exit, and an explicitly uncaptured external command exit. Synthetic subprocess regressions confirm logical return 2 exits 2 and handled worker launch errors persist failure evidence and exit 2.
- All earlier local Float32 topology, actual-mesh section sampling, source/construction/serialized evidence durability, bounded supervisor and serialization-order corrections remain in place.

## Commands and actual results

Commands were run from `C:\vibe\localSimulator\pipeline` with the exact venv tools:

```powershell
.venv/Scripts/ruff.exe format torquay_pipeline/teignmouth_float32_candidate.py scripts/build_teignmouth_float32_candidate.py tests/test_teignmouth_float32_candidate.py
.venv/Scripts/ruff.exe check torquay_pipeline/road_surface_float32_frame.py torquay_pipeline/teignmouth_float32_candidate.py scripts/build_teignmouth_float32_candidate.py tests/test_road_surface_float32_frame.py tests/test_teignmouth_float32_candidate.py
.venv/Scripts/ruff.exe format --check torquay_pipeline/road_surface_float32_frame.py torquay_pipeline/teignmouth_float32_candidate.py scripts/build_teignmouth_float32_candidate.py tests/test_road_surface_float32_frame.py tests/test_teignmouth_float32_candidate.py
.venv/Scripts/python.exe -m pytest tests/test_road_surface_float32_frame.py tests/test_teignmouth_float32_candidate.py -q
.venv/Scripts/python.exe -m py_compile torquay_pipeline/road_surface_float32_frame.py torquay_pipeline/teignmouth_float32_candidate.py scripts/build_teignmouth_float32_candidate.py
.venv/Scripts/python.exe scripts/build_teignmouth_float32_candidate.py --import-smoke
```

Results: Ruff passed; format check reported 5 files already formatted; focused tests passed (18 passed); `py_compile` passed; GIS-free import smoke returned `PASS_IMPORT_ONLY`, frame `teignmouth-float32-local-v1`, origin `[-140.0, 0.0, -95.0]`, and `candidateBuildExecuted: false`. The first focused pytest attempt had two synthetic-fixture failures; the owner query was moved into expected support and subprocess test setup was corrected. The final focused run passed. No GIS source was loaded.

The post-freeze preservation verification reported 199 entries, 0 missing files and 0 hash mismatches. Candidate numerical gates remain unmeasured; road/building/walk and all real-data gates remain unavailable/false. Candidate remains ineligible for serving. Coordinator review and independent Sol review are the next step; no further correction or build is authorized by this submission.
