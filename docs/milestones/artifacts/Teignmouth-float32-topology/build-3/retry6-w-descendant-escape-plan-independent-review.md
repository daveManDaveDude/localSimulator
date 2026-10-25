# Independent review — W descendant diagnostic plan

2026-10-25. **PASS (plan only).** Issue `Teignmouth-float32-topology-representation-1`; independent Sol plan review under disposition 112. No actionable plan finding remains. This approves the specified design for coordinator consideration; it grants no implementation, self-check, runtime or path-selection authority.

## Reviewed bindings

Read only the named plan, disposition 111 and bound diagnosis. Rehashed these documents and the four source files without reading or executing source contents. Actual hashes match:

| Binding | SHA-256 |
| --- | --- |
| `retry6-w-descendant-escape-diagnostic-plan.md` | `b99f339316ab10d29dcb3346b7b05e2d75b48684acecafc6e24951dc50de83ed` |
| Disposition 111 | `f8fc45f6b6f427369519885720048bc2556b0e2734d2ee8c52bbecc779f793cd` |
| `retry5-descendant-escape-diagnosis.md` | `5e0d6eaa558e695276c399246a0ff991bad36147619963520baa1acf574456b4` |
| W | `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0` |
| S | `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69` |
| H | `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf` |
| P | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

## Findings against the plan

- **W-only scope:** Exact scope and ordered changes 1–5 bind native enumeration, ancestry bookkeeping, assertion, private helpers and catch attachment. Default paths retain their original behavior; S/H/P, roots, rejection predicate and launch/identity/acceptance rules are preserved. No exemption or later-census override is proposed.
- **Toolhelp completion:** Change 1 requires immediate last-error capture after false `Process32Next`; successful first entry, error 18 and bounded completion are required before claiming enumeration complete. Other terminal errors retain rows as unverified; first/snapshot/limit/deadline exceptions retain existing failure behavior. Payload snapshot completeness additionally requires convergence before deadline. This avoids equating every false return with complete enumeration.
- **Ancestry:** Changes 2 and 4 retain the original row collection and first-discovery predecessor row indices. Chain reconstruction may use only those recorded edges, never a replacement snapshot or alternative parent search. First-discovery predecessors describe discovery from the existing roots, not independently authenticated parent incarnations. Duplicate PID ambiguity is explicit and cannot change the descendant set. The payload caps storage at 64 edges, identifies truncation and unknown root connection, and the review matrix expressly requires duplicate/cyclic/capped cases. Any cyclic or otherwise incomplete reconstruction must remain bounded and cannot satisfy the contract's complete root-to-target claim. Original census and deadline bounds remain in force.
- **Same-handle evidence:** Fixed API order 1–4 preserves access `0x1000`, the exact membership-query handle and the authoritative successful false result. Only that first false result permits up to one `GetProcessTimes` and one fixed-buffer `QueryFullProcessImageName` call. BOOL and native errors are captured before subsequent native/clock work; invalid lengths and insufficient buffer are explicit failures. No reopen, new right, liveness wait or identity attestation is introduced.
- **Close ownership:** Fixed API order 5 requires exactly one close attempt as the first finally operation, before optional close telemetry. False/raised close remains secondary on an established false-membership path; no global handle or ownership transfer exists. The implementation review must establish this on every branch, including optional allocation/clock failures.
- **Bounds and failure isolation:** The fixed payload contract limits targets, roots, Job IDs, chain, image length and depth, and checks the complete compact JSON against 16384 UTF-8 bytes. One bounded minimal fallback is allowed, otherwise omission; byte truncation is forbidden. Optional failures may omit evidence but cannot replace the primary rejection or leak pipeline output. Pending state resets per assertion, carries no handles and cannot attach to a persistence failure or later success.
- **QPC and cleanup:** Capture budget and cleanup priority retains the original ten-second deadline, requires a one-second reserve and limits diagnostic opportunity to 20 ms within that deadline. Checks precede optional allocation and surround native calls/chain work; closure remains mandatory. Catch attachment follows existing mandatory termination/wait/member/clock work and is skipped when expired or unavailable. The plan explicitly disclaims native-call preemption, guaranteed cleanup duration, measured runtime fit and guaranteed durable telemetry. Its feasibility claim is appropriately best effort, not a hard timing guarantee.
- **Identity limitations:** The payload mandates `snapshot-incarnation-unproven`. Its explicit limitations deny authentication of snapshot-to-handle incarnation, parent incarnations, helper/conhost class or mapped bytes. Unknown, late, ambiguous and unavailable evidence cannot excuse the false member or produce acceptance.
- **Gates:** Static and independent review gates require a tight W diff, final hash, unchanged S/H/P, authorized AST/compile-only checks and branch review. The 53-file preservation comparison and six protected bindings require separate express release. Fresh path planning, actual-byte independent review and immediate one-use coordinator gating remain separate. No retry-6 root is selected or reserved by this PASS.

## Review limit and preserved status

This is a review of the specified plan and its bound diagnosis, not an implementation audit or behavioral proof. No other consumed evidence was inspected. No source edit, parser, compiler, linter, test, import, invocation, live-process query, root selection/creation or runtime work occurred. The only new file is this authorized review artifact.

Retry-1 through retry-5 remain consumed, immutable and non-PASS; candidate NO-GO/unservable and build 3 unreserved. The outer exit-1/internal-2 discrepancy and unsaved `957157…` history remain unresolved. Stop for coordinator acceptance and a separate implementation release.
