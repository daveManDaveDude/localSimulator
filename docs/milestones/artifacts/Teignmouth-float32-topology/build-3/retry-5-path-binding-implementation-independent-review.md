# Independent implementation review — retry-5 binding

2026-10-25. Independent Sol reviewer `/root/sol_review_face_diag`, under disposition 108. **PASS for the exact path/indentation implementation only.** No residual implementation blocker was found. No invocation or downstream action is authorized.

Read dispositions 107–108, accepted retry-5 plan/review, current source, Sol's inverse-mismatch diagnosis and Luna's full implementation handoff. Independently verified diagnosis SHA-256 `67246c232cb9590f6f79c86b4f67ea3ddfd8014844c7997bdb9a0f117398c08d` and handoff SHA-256 `a1d92d36edd10dffbe892ddaa8bdef0979aceea19cb68125e722db63830b353e`. Review is against actual bytes, not reported static success alone.

## Exact source and inverse proof

| File | Independently recalculated current SHA-256 | New/old root counts | Exact path-only inverse SHA-256 |
| --- | --- | --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0` | 2 / 0 | `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69` | 1 / 0 | `28c92cc60e38ae23dcf58874eca67b8308b22772eee03b36d69471624fcdb089` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf` | 1 / 0 | `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` | 0 / 0 | Unchanged |

**PASS — allowed delta.** W 23/344 each now has exactly four leading U+0020 spaces. Reversing only these two indentation spans in memory reproduces the diagnosed failed W SHA-256 `26350581425f4853f25eeac3c05a14c32a94ab1f6e6589d5a5a67dcf3df497af`. Reversing only W's two root literals instead reproduces the exact accepted W baseline above. W remains 107257 bytes, UTF-8 without BOM, 1728 LF and zero CRLF. Thus the two authorized indentation repairs account exactly for the mismatch; there are no additional W changes. S/H inverses independently bind their complete accepted bytes. No reconstructed source was written or executed. No Git index diff is claimed; the diagnosis's derived-and-hash-verified historical W recovery does not resolve the separate missing `957157…` S history.

**PASS — consumers and unchanged behavior.** Search of `pipeline/scripts`, `pipeline/tests` and `config` found exactly W 23 (parent), W 344 (independent fallback), S 39 (`SELF_ROOT`) and H 17 (`EVIDENCE` leaf), with no active retry-4 consumer. W caller/update, separate Handoff PREPARED/identity ownership, terminal fallback and parent startup/stdio all derive the new fixed parent; S owns the matching exclusive `run-1`, and S/H authorization/consumption/markers/logs agree. Earlier reviewed derivations are unchanged by the exact inverses. No arbitrary path, old-root fallback, adoption, run-2 or alternate slot was added. Accepted console precondition/two opt-ins/default callers, stdio confirmation/suspended cleanup, bounded persisted notes/direct literal fallback, process identities/Jobs, original deadline, actual exit7/7, complete census/unconditional unexpected rejection and zero/empty/zero/tree gates remain unchanged.

## Preservation and path safety

**PASS — every prior evidence file.** Independently enumerated all five old roots and compared every filename/count/hash: **2 + 2 + 11 + 11 + 11 = 37 files; 37 matches; zero missing/extra names; zero hash mismatches**. The handoff's complete matrix was checked against the accepted original/retry-1/2/3/4 bindings in dispositions 56/63/67/78/89 and the prior review matrices, rather than accepted solely as an implementer assertion. All pending/consumed/markers/logs, including empty logs, match. In particular the authoritative retry-4 startup hash is `72f9f46afadbd1199b5bffb091ed9dba06a23297c194f6de985f07a27e0d306d`; the earlier transcription is not a changed source of truth. All old roots remain consumed/non-PASS and immutable.

**PASS — six protected files.** Independently rehashed all six; all match accepted bindings and the handoff:

| Protected file | SHA-256 |
| --- | --- |
| `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| `pipeline/torquay_pipeline/road_surface_topology.py` | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| `pipeline/scripts/build_teignmouth_float32_candidate.py` | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| `pipeline/tests/test_teignmouth_float32_candidate.py` | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |
| `config/road-surface-teignmouth-float32.json` | `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228` |

**PASS — fresh path.** Retry-5 is absent and unconsumed; force `.codex` enumeration found zero case-insensitive and trailing-dot/space-normalized equals. `C:\`, `C:\vibe`, workspace and `.codex` are canonical directories without ReparsePoint, LinkType or Target; exact Resolve-Path spellings match. No unsafe/inaccessible check was treated as absence. The absent parent implies absent fixed descendants. These are point-in-time observations, not a reservation or concurrent-replacement guarantee. No retry-5 root/leaf was created. Immediate source/evidence/root/path checks remain the coordinator's separate pre-invocation gate.

## Authorized static checks independently rerun

All ran from `C:\vibe\localSimulator\pipeline`, exactly within disposition 108's static scope:

- `.venv/Scripts/python.exe -m ruff check scripts/run_teignmouth_float32_build3.py scripts/teignmouth_build3_supervisor_selfcheck.py` — exit **0**, `All checks passed!`.
- `.venv/Scripts/python.exe -m ruff format --check scripts/run_teignmouth_float32_build3.py scripts/teignmouth_build3_supervisor_selfcheck.py` — exit **0**, `2 files already formatted`.
- `System.Management.Automation.Language.Parser.ParseFile` on resolved W, retaining tokens/errors, rejecting any parse errors without dot-sourcing/invoking W — exit **0**, `PowerShell AST parse passed`.

These match the handoff outputs. No formatter write occurred. Historical failed inverse, transcription, alias/command errors and their diagnosis remain preserved; successful static gates do not retroactively make them PASS or establish runtime behavior.

Work otherwise comprised read-only source/document reads/searches, hashes, in-memory inverse comparisons and path/evidence inventory checks, plus writing this report. No source/evidence/checkpoint/disposition edit, operational source import/execution, tests, process inspection/probes, wrapper/self-check/preflight/runtime/collection, root creation, manifest preparation, GIS/numerical/build or browser work occurred. W was neither dot-sourced nor invoked. No runtime evidence was created.

Actual native console/cleanup/persistence efficacy, 10-second fit and **30-second runtime-profile fit remain unmeasured**. Outer exit1/internal2 and historical untraceable `957157…` remain unresolved. PASS is implementation review only. Retry-5 may be created only by the later separately gated one-use W call; no invocation is authorized here. Candidate remains **NO-GO and unservable**, build 3 **unreserved**, with fixed constraints and historical counters unchanged.
