# Independent Sol review 9 — diagnostic 2 final static re-review

Date: 2026-10-24. Reviewer: `/root/sol_review_face_diag`, independent non-implementing Sol session.

## Decision

**PASS for static review and complete input-manifest preparation/freezing.** All findings from independent review 8 and the subsequent static supervision reviews are resolved in the reviewed versions. This is not execution authorization. The coordinator must still prepare the complete input manifest, freeze runtime/source identities and the immutable ledger snapshot, reserve the single diagnostic invocation and authorize execution. Candidate serving remains **NO-GO**, regardless of harness status.

## Exact reviewed versions

- `pipeline/scripts/run_teignmouth_overlay_face_diagnostic.py`: SHA-256 `9f1d20086f0e2b26cd972101bda1b3d224f53e176c2f57e480e3dacb4ca7a17a`.
- `pipeline/scripts/diagnose_teignmouth_overlay_face.py`: SHA-256 `298f5865fc0cc3262e6e36ecde7383f01cd5ba91dd3e37199c16b5f573a7ff5c`.
- `docs/milestones/artifacts/Teignmouth-float32-topology/diagnostic-2/plan.md`: SHA-256 `017d81efdce6f2a6e8f28d29b3fb7b5fef34f8d0ff84e16c9bca5447bd9a219a`.
- Supporting runtime identity schema previously reviewed: `pipeline/scripts/teignmouth_overlay_diagnostic_runtime_identity.schema.json`, SHA-256 `7096ef9a9f6cf47ebe7d4b54a7edcdebf9e26ecd2d2ce75d63e286c52f8f804a`.

## Resolution

Review-8 findings 1–7 are resolved: correct verification-result unpacking and preflight enforcement; the target-line callable contract; manifest closure and manifest hash pinning; frozen runtime and release metadata checks; zero-area and mixed-contact retention; invalid/nonfinite geometry stops; accurate source-union coverage accounting; and preservation of worker reports separately from runner errors/process evidence.

The final supervisor resolves review-8 finding 8 and subsequent supervision findings. It creates durable parent invocation evidence before preflight, creates the runner suspended, configures a Windows Job Object with kill-on-close, assigns the process before resuming it, and fails closed if containment cannot be established. Numerical descendants remain within that job. Only the diagnostic runner creates the absent execution leaf; the supervisor mirrors its record only when that leaf exists. Post-stop verification compares frozen inputs and pins the manifest across the invocation.

All explicit wait paths now use the remaining absolute 120-second budget. In the final supervisor, launch-failure cleanup uses remaining-budget clamps at lines 281–282 and 290–291; the absolute deadline is passed into launch at lines 364–368. Main and exception cleanup waits are likewise bounded by that deadline. Child exit is refreshed after confirmed termination at lines 392–396. The coordinator's calling command must separately capture the actual supervisor process exit; the supervisor's outer exit field represents its chosen exit value.

The one-face/local-source-cell scope, original target-road extraction, stations 140–155 reconstruction, unchanged default 35 m buffer, original operation order and inclusive area filter remain intact. No source/domain/origin/recipe/guard/limit change, candidate repair/build, product integration, ledger mutation, browser work or later issue is authorized by this review.

## Review boundary

The review used static file inspection and SHA-256 checks only. No diagnostic, implementation build, import, compilation, numerical reconstruction, test, browser action or source geometry load was executed. No implementation, source, product, candidate, ledger or test files were edited. This document is the subsequent authorized persistence of the completed review, and its SHA-256 is calculated solely for handback. Static PASS does not assert runtime success or geometric correctness of the failed candidate.
