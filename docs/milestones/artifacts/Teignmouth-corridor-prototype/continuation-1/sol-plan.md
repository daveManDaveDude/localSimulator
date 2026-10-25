# Sol plan — corridor prototype continuation 1

**Planner:** `/root/beamng_corridor_plan` (`gpt-6.1-sol`, medium; prior corridor implementation reviewer, not its implementer). **Status:** coordinator accepted, 24 October 2026.

## Finding and limits

The continuous station/lateral chart structurally removes the plausible nearest-segment station seam. Build 2 stopped before full mesh assembly at the first 5.011101 m earthwork violation, so the corrected global gradient and full candidate maximum remain unknown. The old 5 m earthwork cap conflicts with the registered steep section: approximately 94% transverse slope over the 4 m half-carriageway-plus-shoulder span implies about 3.76 m; fixed sigma-12 smoothing differs from source by about 1.374 m near station 148 m, for about 5.13 m combined. Use a candidate-local strict `<6.0 m` cap, not an automatic pass. This remains below build 1's reported 6.460917 m result.

Retain positive added edge gradient strictly `<1.0 m/m`, local complete-width cross-slope `≤5%`, and full-width span `≤0.30 m`. Set candidate-local centerline source-height deviation `≤2.0 m` because the approved fixed smoothing already differs by about 1.374 m; report the former `≤0.10 m` and `≤2 percentage-point` source-grade-change metrics as historical comparisons. Keep candidate absolute longitudinal grade `≤10%`. Do not change other global/source/building limits. These are visualization limits, not engineering certification or default-product policy.

## Implementation

Keep the fixed continuous chart, source centerline, recipe, rectangle, source version and provenance. Implement new continuation-specific Python module, builder, tests and config; leave both prior submissions untouched. Complete mesh/source overlay, Float32 validation, shared road/terrain, complete building-footprint checks and deterministic ownership. Only after offline gates pass may Luna add the isolated DEV harness and candidate assets. No public/default/site/package changes.

## Bounded execution

Create a new continuation spec/attempt ledger and start its counters at zero, preserving all earlier evidence. Budget: initial Luna implementation plus up to four completed independently Sol-reviewed Luna corrections; one Sol correction only if a finding remains after all four, reviewed by a different Sol session. Allow at most three cause-specific diagnostics (120 seconds each), no sweeps, one full build per implementation submission (180 seconds each), and one independent deterministic confirmation build for a passing winner: seven builds maximum. No arbitrary memory cap; bound the registered domain, recipe, run count and wall time, and measure actual working set/buffers/payload/load time. Reuse compatible hash-bound evidence and do not raise limits automatically if the continuation fails.

Run synthetic and relevant static checks first; persist complete witnesses on failure. Validate source/patch overlay extrema, topology/coverage, source boundaries, buildings, ownership, drape and walking. Then run same-camera Chromium comparisons only after all offline gates pass. Stop on any retained or candidate-local limit failure, invalid topology, unresolved ownership, building failure, protected-byte change, required domain expansion, timeout, or incoherent fallback. No prior attempt, test, build, or screenshot was rerun for this plan.
