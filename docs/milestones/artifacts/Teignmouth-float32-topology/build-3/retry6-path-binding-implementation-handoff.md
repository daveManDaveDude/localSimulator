# Retry-6 fixed-path implementation handoff

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Coordinator disposition 126; accepted path plan PASS in `retry-6-path-binding-plan-independent-review.md`. This is a four-literal path-only implementation handoff. It does not select or reserve a path and authorizes no invocation.

## Exact source changes and hashes

Only the four exact retry-parent/leaf literals in the accepted plan changed. Each replacement changes the final `5` to `6` and no other character.

| File and span | Old literal → new literal | Replaced | Final SHA-256 | Exact inverse SHA-256 |
| --- | --- | ---: | --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1`, W23 `baseEvidence` | `.codex\build3-supervisor-selfcheck-retry-5` → `.codex\build3-supervisor-selfcheck-retry-6` | 1 | `f600efc92fd040aa5b91cf543210be139ed50f895eba7d62c34175e73dc7dc8b` | `804ae8c42f6637a61505e53e825972d758b8ae2c1c2d0740ff5a076a0e703b45` |
| W, W344 independent terminal-fallback `expectedRoot` | `.codex\build3-supervisor-selfcheck-retry-5` → `.codex\build3-supervisor-selfcheck-retry-6` | 1 | same W hash above | same W inverse above |
| S `pipeline/scripts/run_teignmouth_float32_build3.py`, S39 `SELF_ROOT` | `.codex/build3-supervisor-selfcheck-retry-5` → `.codex/build3-supervisor-selfcheck-retry-6` | 1 | `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff` | `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py`, H17 `EVIDENCE` | `.codex/build3-supervisor-selfcheck-retry-5/run-1` → `.codex/build3-supervisor-selfcheck-retry-6/run-1` | 1 | `75678b51d0e17d89862bf0a7ee3446014969ba73aae6cd31606288553b163e27` | `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | unchanged | — | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` | unchanged |

The exact new-literal counts are W=2, S=1, H=1. The exact old retry-5 root literals are W=0, S=0, H=0 after the patch. In-memory byte inverses replacing only the four new literals with their corresponding old literals restored all three accepted whole-file hashes exactly. Reconstructed source was not written or invoked. The replacements are length-preserving; whole-file inverses establish that all non-literal bytes, encoding and newline bytes match the accepted baselines.

The static consumer search covered `pipeline/scripts`, `pipeline/tests` and `config` for both slash forms of the retry-5/retry-6 literal. Its only retry-6 consumer results were W23, W344, S39 and H17 above; no additional consumer or retry-5 active root literal appeared.

## Released static gates

Affected S/H Ruff checks and format checks ran in the existing `pipeline\.venv` environment:

```powershell
& 'pipeline\.venv\Scripts\python.exe' -m ruff check 'pipeline/scripts/run_teignmouth_float32_build3.py' 'pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py'
& 'pipeline\.venv\Scripts\python.exe' -m ruff format --check 'pipeline/scripts/run_teignmouth_float32_build3.py' 'pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py'
```

Exact output:

```text
All checks passed!
2 files already formatted
```

W was parsed with `System.Management.Automation.Language.Parser.ParseFile`; the AST check passed. W was not invoked. The embedded C# was not recompiled because the four authorized changes are path literals and the accepted compile-only evidence remains applicable. No Python imports, tests, C# method calls, runtime/process probes or operational commands ran.

## Immutable evidence and protected files

The full accepted matrix in the [cycle-1 preservation handoff](retry6-w-descendant-escape-correction-1-handoff.md), SHA-256 `4701ddc210ef755832a0bb8cebf3c561e51868ac961b499ddf97867fb3b25704`, was re-read as metadata and rechecked against file names, counts and SHA-256 values. **53/53** files matched, with zero missing, changed or unlisted files; retry-5 remained **16/16** unchanged. Consumed evidence contents were not opened.

All six protected source/config/test hashes matched:

| Protected file | SHA-256 |
| --- | --- |
| `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| `pipeline/torquay_pipeline/road_surface_topology.py` | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| `pipeline/scripts/build_teignmouth_float32_candidate.py` | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| `pipeline/tests/test_teignmouth_float32_candidate.py` | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |
| `config/road-surface-teignmouth-float32.json` | `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228` |

## Point-in-time read-only path observations

Observed at **2026-10-25 12:07:58.6470838 +00:00 local** (**2026-10-25 12:07:58.6508480 UTC**). No path was created, reserved, adopted, renamed, repaired or deleted; no scratch/probe path was created.

| Check | Observation |
| --- | --- |
| `C:\`, `C:\vibe`, `C:\vibe\localSimulator`, `.codex` | All existed as directories. `Get-Item` reported no reparse attribute, `LinkType` or `Target`. `GetFullPath` and `Resolve-Path.ProviderPath` agreed for each. |
| Proposed root `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6` | Absent as a file and directory. Contained under the canonical workspace. Immediate `.codex` enumeration found zero case-insensitive names equal after trailing-dot/space normalization. |
| Proposed root and plan-listed descendants | All 26 plan-listed paths were absent, checked read-only with `Test-Path`. |
| Candidate-output blocker `C:\vibe\localSimulator\data\generated\teignmouth-float32-topology` | Absent. |
| Candidate-output blocker `C:\vibe\localSimulator\docs\milestones\artifacts\Teignmouth-float32-topology\build-3\run-1` | Absent. |

The read-only checks establish only a point-in-time observation. They do not reserve the proposed root, remove races or authorize execution. Existing W fresh-root/reparse/exclusive ownership checks and S/H one-use validators remain necessary. Any changed or ambiguous path premise is a stop.

## Handback and limits

The path-only implementation matches the four-span plan; this handoff is not independent actual-byte review or a runtime result. Retries 1–5 remain consumed, immutable and non-PASS. Retry-6 remains proposed, unselected, unreserved and absent. The candidate remains **NO-GO and unservable**; build 3 remains unreserved; the 10-second QPC deadline is unchanged.

Stop for independent Sol review of the actual W/S/H bytes and point-in-time paths, followed by a separate coordinator decision. No self-check, preflight, candidate/GIS/numerical build, reservation, browser/publication, commit, push or merge occurred.
