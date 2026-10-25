# Independent review — fixed exception fallback

2026-10-25. Independent Sol reviewer `/root/sol_review_face_diag`, disposition 99. **FIX REQUIRED: failed primary string conversion does not directly return the fixed literal as disposition 98 requires.** The prior unguarded f-string is removed, but the narrower accepted failure-path contract remains unmet. No correction or operation is authorized by this report.

Reviewed actual current S against fallback finding report `bafe857fb8554431c6a02d418c3df1435dbc75b1bd3977bbe8cbd68ccc40c7b5`, accepted plan and dispositions 92–99. Coordinator-reported Ruff check/format exit-0 results were read, not rerun.

| Artifact | Independently recalculated SHA-256 |
| --- | --- |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `376187f474f4e91739d732ba064ec1db39be5863cfd5ce746250d0863c35a997` |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| `selfcheck-note-serialization-fallback-handoff.md` | `aa14cf4baf1aa6b9898a1dabee093eb68575460af089368faf15fbeb0937621a` |

Reversing only the single literal-assignment line in memory restores exact previous S SHA-256 `a0ebfebbde4eabdba0dc3946d0222070b3ee8b28b8f8aa3a2d69234c01538e1e`. There is one matching changed line; every other S byte is unchanged. No reconstructed source was written or executed. W/H/P match unchanged bindings. No reliable Git index history is claimed.

## Concrete finding

**S 3600–3610:** disposition 98 expressly authorizes a failed `str(exc)` to “return[] a fixed preexisting literal directly, without another formatting, type lookup, allocation or unguarded operation.” Current line **3601** instead assigns `message = "exception message unavailable"`. Execution then continues to `getattr`, list slicing/construction, JSON serialization and an f-string return (3603–3610). With available string notes, the result is a newly formatted message containing notes rather than the fixed literal. Although that optional work is guarded and the previous unguarded-formatting failure is closed, it is still attempted in the branch required to return immediately.

The handoff's statement that this branch “returns the fixed literal” is therefore not accurate for a failed conversion with available notes. The coordinator explicitly confirmed during this review that disposition 98 intentionally requires direct return and no subsequent note extraction/allocation on that path; no relaxation or reinterpretation was granted.

**Concrete remedy, subject to separate authorization:** make the exception handler return the fixed literal directly. Retain the current bounded best-effort note path only after successful primary string conversion. No wider helper, serializer, schema, launch or cleanup change is needed. No source was changed by this review.

## Other criteria

- **PASS:** when `str(exc)` succeeds, its exact text remains the prefix; at most four string notes, each capped to 512 characters, are JSON-encoded with ASCII escaping. Optional extraction/formatting remains guarded.
- **PASS:** both existing persisted fields still call this helper: normal failure `primaryError.message` at 3703 and outer self-check `error.message` at 4192. Type, phase and bare propagation are unchanged. The earlier note-persistence omission remains closed on the successful-conversion path.
- **PASS, unchanged by exact inverse:** three stdio close attempts distinguish true/false/raised outcomes, false captures native last error immediately, and a created child with unconfirmed release fails before authorization/resume and enters bounded direct termination/observation/native-handle cleanup. All-confirmed assignment-before-resume remains.
- **PASS, unchanged:** lazy finite console precondition, exactly normal/tree opt-ins (3768/4030), three default callers (4361/4680/4778), original flags/deadlines, authenticated process/Job chain, strict complete census/unexpected-member rejection, zero/empty/zero prerequisite, diagnostic-only member evidence and cleanup gates remain intact.

Work comprised static source/document reading/searching, hashing, an in-memory inverse and this report. No source/checkpoint/disposition/manifest/evidence edits, retry-root access, new roots, tests/imports/scripts/linters/parsers/compilers, process inspection/probes, wrapper/self-check/preflight/runtime/collection, GIS/numerical/build or browser operation occurred. No runtime evidence was created. Native behavior, actual 10-second fit and **30-second runtime-profile fit remain unmeasured**.

Outer exit1/internal2 and unsaved `957157…` history remain unresolved. Consumed roots/counters remain intact. FIX REQUIRED grants no next action or self-check. Candidate remains **NO-GO and unservable**, build 3 **unreserved**; a separate coordinator decision remains required.
