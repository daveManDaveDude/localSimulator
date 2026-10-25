# Retry-6 S wait/callback correction — final implementation handoff

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** D134 S-only correction, D137 inverse proof, D141 E501 wraps, D144 lambda collapse, and D145 corrected binding assertion. This handoff authorizes no runtime work or retry.

## Final source bindings

| Source | SHA-256 | Bytes |
| --- | --- | ---: |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `fda96d4edd66327e50c34ee1345d1a098aced4a7b58dcd1c088a4cd8c44c616f` | 239,737 |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `f600efc92fd040aa5b91cf543210be139ed50f895eba7d62c34175e73dc7dc8b` | — |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `75678b51d0e17d89862bf0a7ee3446014969ba73aae6cd31606288553b163e27` | — |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` | — |

D145 read-only source hashing confirmed these exact values and S byte length. W/H/P path bindings remain retry-6: W has two `.codex\build3-supervisor-selfcheck-retry-6` literals, S has one `.codex/build3-supervisor-selfcheck-retry-6`, H has one `.codex/build3-supervisor-selfcheck-retry-6/run-1`.

## Exact source delta and inverse chain

The D134 source implementation changed only the two authorized S regions: `_assert_tree_contained` and the self-check tree-wait block. Subsequent authorized formatting changes were limited to the two D141 `TimeoutError` call wraps and the one D144 `_sample_job` lambda collapse. No other source changed. The error types/messages and callback arguments are unchanged.

The complete in-memory inverse chain passed:

| Inverse stage | SHA-256 | Bytes |
| --- | --- | ---: |
| Current final S | `fda96d4edd66327e50c34ee1345d1a098aced4a7b58dcd1c088a4cd8c44c616f` | 239,737 |
| Reverse only D144 lambda collapse | `7a1c38fe72ea274777538135154200c03cd5de8eeb6f4cd3d8d0b89b169228cc` | 239,775 |
| Reverse only the two D141 E501 wraps | `96daa955ce2ebe7a6315c000c99f174189d26bcf8941684541703ef688d921c7` | 239,683 |
| D137 old-region replacement candidate before seam correction | `90c3e919e7e05f9cb4add4eca6e201ea97b42605c0173dec45e384bed53a009b` | 232,525 |
| Insert exactly one LF at B-end byte offset 183489, then one LF at A-end offset 16631 | `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff` | 232,527 |

The final step uses D137's bounded, independently reviewed seam proof, report SHA-256 `e424848a43bc48503b04a5ec15da550506907dd12ff3169e0575508b41edadef`. No reconstructed source was written or executed. The two E501 wraps preserve their exception classes and complete string values; the lambda collapse keeps the same deferred call and arguments.

## D144 Ruff gates and prior failures

Commands run in the existing pipeline virtual environment:

```powershell
& 'pipeline\.venv\Scripts\python.exe' -m ruff check pipeline/scripts/run_teignmouth_float32_build3.py
& 'pipeline\.venv\Scripts\python.exe' -m ruff format --check pipeline/scripts/run_teignmouth_float32_build3.py
```

Exact D144 output:

```text
All checks passed!
1 file already formatted
```

The earlier D138 Ruff check on pre-wrap S `96daa…` reported E501 at lines 4148 (103 columns) and 4173 (104 columns). D141's check passed after the two authorized wraps, but format-check then requested that the `_sample_job` lambda at line 4200 be collapsed to one line. D144 made only that plan-authorized formatting change; both D144 gates passed.

## D144 preservation results

The read-only filename/count/hash comparison passed for **70/70** immutable evidence files: original=2, retry-1=2, retry-2=11, retry-3=11, retry-4=11, retry-5=16, retry-6=17. No missing, changed, duplicate or unlisted file was found. Evidence contents were not opened for diagnosis or modified.

All six protected source/config/test hashes matched:

| Protected file | SHA-256 |
| --- | --- |
| `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| `pipeline/torquay_pipeline/road_surface_topology.py` | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| `pipeline/scripts/build_teignmouth_float32_candidate.py` | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| `pipeline/tests/test_teignmouth_float32_candidate.py` | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |
| `config/road-surface-teignmouth-float32.json` | `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228` |

## D145 corrected marker and binding check

The first D144 marker command matched the typed signature and all listed strict/proof/final-census/cleanup markers, then stopped because an additional assertion incorrectly searched for the untyped text `require_complete_snapshot=False`. No files changed. D145 authorized a corrected read-only check; the exact typed signature `require_complete_snapshot: bool = False` occurred once, all 13 required markers were present, and current S/W/H/P hashes and retry-6 path-literal counts matched the bindings above.

The static call-site search found the strict opt-in only in the tree census closure at S4151. Normal callers at S3876/S3906 and other containment calls at S4552/S4557/S4871/S4885/S4990 omit the keyword and retain the default false branch. The unchanged S call sites do not alter `_wait_process`; the strict proof retains terminal error 18, same-snapshot completion, bounded ancestry/Job comparison and snapshot `finally` close. These are implementer static observations for independent review, not runtime behavior proof.

## Limits and handback

No source or evidence changed after the D144 gate run. No tests, imports, parsers, compilers, processes, path/root operations, runtime, self-check, preflight, build, GIS/numerical, serving/publication or retry invocation ran. The D144 Ruff and preservation results are reused because D145 confirmed the same S/W/H/P bindings and no source/evidence change.

Retries 1–6 remain consumed, immutable and non-PASS; retry-7 remains unselected and unreserved. Candidate remains **NO-GO and unservable**; build 3 remains unreserved. Stop for independent Sol actual-byte review against D134/v2, D137, D141, D144 and this handoff. No subsequent runtime or retry is authorized.

## D145 exact read-only marker output

The corrected assertion searched the actual typed keyword-only signature (`require_complete_snapshot: bool = False`), then checked its single strict opt-in call, captured terminal last error and `ERROR_NO_MORE_FILES` comparison, all three completion predicates, final-census one-attempt guard/call/downstream completion flag, and snapshot cleanup in `finally`. All 12 assertions passed. The initial D144 typo was an extra search for untyped `require_complete_snapshot=False`; it is not the implemented signature.

Exact source path-literal count check: W `invoke_teignmouth_float32_build3.ps1` = 2; S `run_teignmouth_float32_build3.py` = 1; H `teignmouth_build3_supervisor_selfcheck.py` = 1; P `teignmouth_build3_runtime_preflight.py` = 0. Current SHA-256 values remain the table above. D144 Ruff output and the 70/70 evidence + 6/6 protected-hash results are carried forward from the same unchanged source/evidence state, per D145; those gates were not rerun.

Exact corrected check output:

```text
typed keyword-only default signature occurs once: PASS
strict call passes true once: PASS
last-error capture after failed strict advance: PASS
ERROR_NO_MORE_FILES equality proof: PASS
same-census proof requires snapshotComplete: PASS
same-census proof requires ancestryComplete: PASS
same-census proof requires comparisonComplete: PASS
final census attempted once guard: PASS
exactly one final complete census call: PASS
final completion asserted downstream: PASS
snapshot cleanup in finally: PASS
strict default remains false: PASS
```

The earlier exploratory D145 probe used an incorrect `final_snapshot` label and a literal-newline matcher for cleanup; it was discarded and not used as completion evidence. The bounded corrected check used the actual `finalComplete` state/guard and a newline-tolerant cleanup matcher. No files other than this handoff were modified.
