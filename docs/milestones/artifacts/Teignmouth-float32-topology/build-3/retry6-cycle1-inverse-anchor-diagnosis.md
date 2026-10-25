# Cycle-1 inverse anchor — bounded diagnosis

2026-10-25. Issue `Teignmouth-float32-topology-representation-1`; disposition 121. **The existing independent cycle-1 proof composes transitively with the exact cycle-2 inverse. A repeated initialization-anchor search is unnecessary to establish that proof chain.** No source edit or normalization is needed.

## Exact bindings

| Binding | SHA-256 |
| --- | --- |
| Current W, independently rehashed, 132204 UTF-8 bytes | `804ae8c42f6637a61505e53e825972d758b8ae2c1c2d0740ff5a076a0e703b45` |
| Exact cycle-2 inverse result, 134567 bytes | `d7351a1cdcd9e8f6ea2c554400ff34d4f281a8c15086c87b32a132d806e549cd` |
| Accepted retry-5 W | `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0` |
| Cycle-1 handoff, independently rehashed | `4701ddc210ef755832a0bb8cebf3c561e51868ac961b499ddf97867fb3b25704` |
| Cycle-1 independent review, independently rehashed | `6ab1b80d82a6aaccad3e93ef4fa63b5016c62f8d0fa8f2844a1e5b4b4d4ce49f` |

## Anchor observation and limits

The exact literal `$pendingDescendantDiagnostic = $null` followed by LF occurs **once** in the bound current W, at line 1555. The cycle-2 delta does not remove that initialization. Its absence from Luna's search is therefore not evidence of source drift or a missing source edit.

The exact anchor-search expression was not retained in Luna's stop report. Its precise failure cause is **unknown**: the available records cannot distinguish a quoting/interpolation problem, a different intermediate string, or another proof-script mistake. No particular cause is asserted. A failed anchor lookup before hash comparison is a failed proof-script step, not a conflicting whole-file hash result.

## Minimal accepted proof method

1. Verify the current W binding `804ae8…` and the exact seven-span in-memory cycle-2 inverse result `d7351a1…`, length 134567. This inverse has already been independently established under disposition 118 and reported again by Luna under disposition 120; do not substitute the earlier extra-LF `ce7f6…` result.
2. Rehash and bind the cycle-1 handoff and independent review above. Their exact cycle-1 input is the same `d7351a1…` whole-file byte binding. The independent review explicitly establishes a direct inverse from those bytes to accepted `e9a0794…`, including exact string/UTF-8 equality to the independently derived accepted baseline. It also verifies the bounded cycle-1 inverse to `dee858…`.
3. Compose those exact byte bindings: **`804ae8… → d7351a1… → e9a0794…`**. This proves the current delta chain against the accepted baseline using the existing independently verified edge; it does not require reexecuting the cycle-1 inverse's anchor lookup.

The documented accepted baseline derivation used Git blob `a742ddc1aea8cf05b8059879d83bcf8230b1f005`, the historical retry-parent substitutions and three unsigned `CreateFile` access-literal suffixes. The cycle-1 review verified the resulting `e9a0794…` hash and exact equality after reversing only the diagnostic region, one pending initialization, added native overload and catch attachment. No different baseline is introduced here.

This diagnosis establishes a proof method, not new implementation acceptance or behavioral correctness. A later authorized handoff should state transparently that its current `804→d735` inverse is newly verified and its `d735→e9` edge is the pinned, previously independent proof. It must not claim the failed anchor script itself completed or that AST/compile/preservation gates were rerun during this diagnosis.

## Handback

Only authorized static document/source observations, hashing and literal-string counting occurred; only this diagnosis artifact was written. No source/evidence edit, normalization/restore, consumed evidence-content read, AST/parser/compiler/linter/test/import/runtime/process probe, path/root work or invocation occurred. Current W remains frozen at `804ae8…`. Stop for coordinator decision. Retries 1–5 remain consumed/immutable/non-PASS, retry-6 absent/unselected, candidate NO-GO/unservable and build 3 unreserved; the 10-second deadline remains unchanged. No self-check is authorized.
