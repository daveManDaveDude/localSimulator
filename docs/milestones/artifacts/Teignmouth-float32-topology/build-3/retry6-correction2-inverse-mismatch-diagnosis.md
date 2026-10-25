# Correction-2 inverse mismatch — read-only diagnosis

2026-10-25. Issue `Teignmouth-float32-topology-representation-1`; disposition 118. **The mismatch is one extra LF in the attempted in-memory inverse, at the minimal-token serialization removal boundary. Exact recovery is possible in memory without changing current W.** This is diagnosis only, not implementation acceptance or a release to resume work.

## Exact bindings

| File/state | SHA-256 | Bytes where established |
| --- | --- | --- |
| Current W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `804ae8c42f6637a61505e53e825972d758b8ae2c1c2d0740ff5a076a0e703b45` | 132204 |
| Bound pre-correction W / independently reconstructed exact inverse | `d7351a1cdcd9e8f6ea2c554400ff34d4f281a8c15086c87b32a132d806e549cd` | 134567 |
| Reported failed inverse / independently reproduced extra-LF candidate | `ce7f6d2aa366c260a2b803165507c5cca53b1214507ab22b4c661cd3d47707de` | 134568 |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69` | — |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf` | — |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` | — |

S/H/P match the accepted source bindings. The correction-1 handoff/review bind pre-correction W to `d7351a1…`; the reviewer also retained the exact actual cycle-1 source read from that independent review. No persisted `d7351a1…` snapshot was found in the narrowly inspected retry-6 temporary records; the existing temporary snapshot is the older `dee858…` file. The recovery below uses the previously read cycle-1 spans and verifies their whole-file result against the already-bound hash, rather than treating an assumed or normalized baseline as authoritative.

## Exact byte and span

In `Convert-FalseMembershipObservation`, the failed inverse has an extra empty line between:

```powershell
    catch { return $null }
    $fallbackRequired = $false
```

The correct bound baseline has those lines adjacent. The failed inverse inserts **one `0A` byte at zero-based byte offset 83656** of the 134567-byte baseline, immediately before the four spaces beginning `$fallbackRequired = $false` (baseline line 1290). It is a duplicated LF at the removal boundary of the newly inserted `if ($Observation.minimalStatusToken)` serialization branch, current W1273–1287.

Independent reproduction:

1. Reverse the seven visible correction spans using the exact cycle-1 text, with no added separator when removing that inserted serialization block. UTF-8 length is **134567** and SHA-256 is **`d7351a1cdcd9e8f6ea2c554400ff34d4f281a8c15086c87b32a132d806e549cd`**.
2. Insert exactly one LF into that recovered string at offset **83656**. UTF-8 length becomes **134568** and SHA-256 becomes exactly **`ce7f6d2aa366c260a2b803165507c5cca53b1214507ab22b4c661cd3d47707de`**.

This reproduces both reported failed-inverse properties, including its complete digest. Adding a blank line at the earlier skipped-payload/originalJobIdCount boundary did not reproduce that digest; the identified serialization boundary does. No assumption that an arbitrary whitespace difference is harmless is needed.

## Delta confinement and proof-safe recovery

The exact inverse modifies only these current W spans:

| Current lines | Inverse operation / authorized finding |
| --- | --- |
| 1067 | Restore old row-index initialization; finding 1 |
| 1085 | Restore old row-index increment; finding 1 |
| 1197–1204 | Restore old no-reserve payload in place of the minimal token; finding 3 |
| 1205–1212 | Restore old cutoff-expired payload in place of the minimal token; finding 3 |
| 1220 | Restore old membership-start cast, removing the new nullable/status expression; finding 2 |
| 1273–1287 | Remove newly inserted post-cleanup minimal-token serialization branch, including exactly its own final LF; finding 3 |
| 1394 | Restore old close-telemetry guard, removing the token exclusion; finding 3 |

Because that bounded inverse yields the full already-bound `d7351a1…` hash, current W's byte delta is confined to these seven spans and the three authorized cycle-2 findings. This is a byte/scope diagnosis; it does not establish the behavioral correctness of those changes or replace independent implementation review.

Minimal recovery for a later authorized proof run: correct the **in-memory inverse operation**, removing the inserted serialization branch up to (but excluding) the existing first space of `$fallbackRequired = $false`, and concatenate the surviving text without an extra LF. Equivalently, for the specifically bound failed inverse `ce7f6…`, remove its one `0A` byte at offset 83656 in memory and require the exact `d7351a1…` digest and 134567 length. Validate both anchors/digests before accepting the proof; do not use a general trim, line normalization, source restore or broad whitespace replacement. **No current source correction is required merely to resolve this inverse mismatch.** Coordinator must separately authorize any resumed correction/gates/handoff.

## Limits and handback

Only static source/document reads, narrowly scoped existing-record inventory, hashing and in-memory string/byte comparison occurred. No source/evidence normalization, edit or restore; no evidence-content reads, preservation rerun, AST/parser/compiler/linter/test/import/runtime/process probe, wrapper/self-check/preflight, or retry-6 path/root work occurred. Only this diagnosis artifact was written. No runtime, implementation or self-check PASS is claimed.

Stop for coordinator decision with current W frozen at `804ae8…`. Retries 1–5 remain consumed, immutable and non-PASS; retry-6 unselected/unreserved, candidate NO-GO/unservable and build 3 unreserved. Historical exit discrepancy and unsaved `957157…` history remain unresolved.
