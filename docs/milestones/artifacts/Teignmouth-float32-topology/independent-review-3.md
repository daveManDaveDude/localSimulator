# Independent Sol review 3 — correction 2

Date: 2026-10-24

## Decision

**GO for coordinator reservation of implementation build ordinal 1, limited to the bounded offline build.** This is not candidate acceptance or serving authorization.

## Verification

Recomputed all 193 files in `correction-2/input-manifest.json`; sizes and SHA-256 values match. Candidate output was absent. The reviewer made no edits and ran no tests, build, diagnostic, or source load.

Candidate serialization now constructs XYZ explicitly, preserves stored local X/Z, and reconstructs world XYZ correctly. Horizontal, vertical and Euclidean displacement compare decoded stored positions with correctly ordered construction X/Z and unrounded candidate Y. The synthetic regression checks stored X/Z bytes, decoded XYZ, and per-axis displacement; it would fail the previous XZY implementation.

Correction-1 safeguards remain: decoded Float64 section sampling, chart/construction/serialized/gate evidence, a parent-supervised 180-second worker with no CLI bypass, pre/post input checks, elapsed/peak-memory reporting, and failed-output archival. Only the candidate module and test changed from correction 1; frame, source, limits, recipe and runner did not change.

## Limits

The Windows watchdog/memory telemetry have not been exercised in a candidate run. Luna reports 13 focused tests passing; the initial repository-root pytest collection failed, then the run from `pipeline/` passed. No candidate geometry or numerical gates have been measured. Road/contact/shared-surface/confirmation gates remain blocked. Candidate output remains unservable; no browser/product integration is authorized.
