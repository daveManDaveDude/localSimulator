# Independent Sol review — correction 2

**Verdict: FIX REQUIRED.** Geometry remains untested.

The package-path correction works: build 3 reached `teignmouth_corridor_continuation.py:16`, then stopped while importing NumPy. Build 2 had failed earlier because `torquay_pipeline` was unavailable from the repository-root invocation. The documented unqualified `python` command selected an interpreter without the required project dependencies.

The repository interpreter is available at `pipeline/.venv/Scripts/python.exe`. Sol verified that its site-packages contain NumPy 2.5.4, Shapely 2.2.0 and PyProj 3.8.0, without executing Python or testing imports. The recorded GIS-free import smoke passed under this virtual environment.

Correction 1's findings are addressed in code: builder import-path setup and GIS-free smoke, a combined primary-error/telemetry-failure regression, existing strict-config and final Float32 section-sampler tests, and durable primary-error/working-set/preservation reporting. Sol independently rehashed all 915 preservation entries and found zero mismatches; before/after snapshots are identical. Raw GIS remains excluded. The reported 20 passing tests and static/import-smoke results were inspected, not rerun.

The build report truthfully records that candidate geometry was not evaluated, road/building/walk coherence gates are false, candidate serving is blocked, and no browser was run.

## Required bounded correction

Use Luna correction cycle 3 to standardize the command on the existing repository virtual environment, update the build-path guard and preservation exclusion, and record interpreter identity in evidence. Do not install dependencies, inject another interpreter's site-packages, or add automatic interpreter-relaunch machinery.

Before reserving build ordinal 4, run the GIS-free import smoke with that exact interpreter. The build command should begin:

```powershell
pipeline/.venv/Scripts/python.exe pipeline/scripts/build_teignmouth_corridor_continuation.py
```

Correct the stale error text at builder line 148, which still names `correction-1/build-2` while enforcing `correction-2/build-3`. Preserve build 3 unchanged. This review justifies the third Luna correction; no new geographic diagnostic is needed.

All candidate numerical, final-mesh, ownership, building, road/walk, determinism and browser gates remain unverified. Keep serving blocked and all limits unchanged. The separate topology-validation v2 work remains inactive.

No code edits, tests, builds, diagnostics, profiles or browser runs were performed during this review.
