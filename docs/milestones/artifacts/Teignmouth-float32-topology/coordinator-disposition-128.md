# Coordinator disposition 128 — one-use retry-6 supervisor self-check gate

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User's continuing authorization for bounded attempts; dispositions 124–127; completed independent actual-byte PASS and immediate coordinator preflight.

## Independent review gates accepted

- Cycle-2 W diagnostic implementation: PASS, report SHA-256 `f465d1987338551da0d7f093db358eca05143c806591e933e27f6093c0b4279a`.
- Retry-6 exact fixed-path plan: PASS, independent plan review SHA-256 `b96b2e89c738f2e61a41410cb1775321a22c8da53e393a47e6dc854fae2e6bc3`.
- Four-literal path-only implementation: handoff SHA-256 `72c8363ee53b4c71a909a162f20513525fbcbf1c1bc1b5c11ffd5e1663bc17db`; independent actual-byte/path review PASS, SHA-256 `c6e54bf9b26c945c9124e0cd6306f9b79b531ac0852a0084fb88e6cba66ebdbf`.

The reviewed source bindings remain W `f600efc92fd040aa5b91cf543210be139ed50f895eba7d62c34175e73dc7dc8b`, S `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff`, H `75678b51d0e17d89862bf0a7ee3446014969ba73aae6cd31606288553b163e27`, and unchanged P `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`.

## Immediate coordinator preflight

At **2026-10-25T12:17:49.3508119+00:00 local / 2026-10-25T12:17:49.3542259+00:00 UTC through 2026-10-25T12:17:49.4753726+00:00 UTC**, coordinator read-only checks confirmed:

- W/S/H/P hashes match the reviewed source bindings. Exact raw-byte inverses for W/S/H restored the disposition-124 hashes `804ae8…`, `ba39cb…`, and `bec312…`; the four replacement counts remain 2/1/1, with old retry-5 path literals 0/0/0.
- The complete prior evidence matrix matched **53/53**, including retry-5 **16/16**, with exact names/counts/hashes. The six protected source/config/test hashes matched.
- `C:\`, `C:\vibe`, workspace and `.codex` resolve to existing canonical directories with no reparse/link target. The proposed retry-6 root is absent as file and directory; normalized aliases are absent. Both candidate-output blocker paths are absent; their existing ancestors are safe and contained.
- No path was created, reserved, adopted, repaired or deleted. These observations are point-in-time only and do not guarantee race-free creation; W's existing runtime fresh-root/reparse/exclusive ownership checks and S/H one-use validation remain mandatory.

## One-use authorization — exactly one command

Select and reserve the proposed root **only for this single invocation**: `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6`. Authorize exactly one run of the existing supervisor **self-check** from `C:\vibe\localSimulator`:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File pipeline/scripts/invoke_teignmouth_float32_build3.ps1 -Mode self-check
```

Do not run any wrapper, S/H directly, build mode, preflight, or second invocation. The fresh root may be created only by W under its existing runtime checks; S alone may create `run-1` after authenticated handoff. This one-use authorization is consumed when the command is attempted, including refusal, partial startup, timeout, failure or incomplete persistence. Preserve every resulting file, including empty logs, updates, pending or fallback files. No cleanup, retry, automatic next root or replay is authorized. Capture outer exit, internal/chosen/native/S outcomes, elapsed/QPC and persisted states separately; incomplete or nonzero outcomes remain non-PASS. The 10-second total QPC deadline, all rejection semantics, and existing cleanup/containment gates remain unchanged.

This gate authorizes no candidate/GIS/numerical build, reservation, serving/publication, browser work, M1/TVW-016 or unrelated change. Candidate remains **NO-GO and unservable** regardless of the self-check result. Retry-1 through retry-5 remain consumed, immutable and non-PASS. No counters reset; build 3 remains unreserved.
