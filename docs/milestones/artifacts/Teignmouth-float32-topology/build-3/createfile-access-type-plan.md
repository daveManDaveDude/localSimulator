# Bounded CreateFile access-mask type correction plan

2026-10-25. Sol 6.1 medium planner `/root/sol_review17_plan`. Read-only planning under disposition 64 for the exact disposition-63 interop failure. **The type correction is feasible in W only.** No implementation, static gate or operational invocation is performed or authorized by this plan.

## Actual evidence and baseline

Read dispositions 63/64, current W, and the preserved retry-1 caller/handoff records. Static SHA-256 values match disposition 63:

| File | SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `c8fcd7c3d4ae8b1535f930533c838bd7e1818624c83798961b388f90660ccb74` |
| `.codex/build3-supervisor-selfcheck-retry-1/caller-invocation.json` | `f992b356191d202a5e2357cffb1d64d90b4dd7f8ac54cd0b76ab2e0d7540dcf3` |
| `.codex/build3-supervisor-selfcheck-retry-1/self-check-handoff.json` | `b73738fc81644b942ea4f84890146e1bdfc73d925005552cb34db1af05aadc79` |
| Disposition 64 | `6ebe46dd237e81f3fda248780609c175747424b5ff6784bc246172fa848682a9` |

The caller's structured primary error is `System.Management.Automation.MethodException`, error ID `MethodArgumentConversionInvalidCastArgument`, with inner `PSInvalidCastException`: `CreateFile`'s `access` argument had value `-2147483648` and could not convert to `System.UInt32`. Actual wrapper exit was 2. Caller fields `launcherCreated`, `launcherAssigned`, `launcherResumed`, `nativeProcessLaunched` and `candidateBuildExecuted` are false; native/script exit fields remain null. Handoff is PREPARED with null launcher-observation fields. This is an argument-conversion failure before the native file-opening call/launcher creation, not a Windows file-access denial, GIS defect or measured containment result.

## Official basis and exact minimal change

Microsoft's [PowerShell numeric-literal documentation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_Numeric_Literals) explains signed interpretation of unsuffixed eight-digit hexadecimal values with the high bit set; an unsigned `u` suffix suppresses that sign interpretation and gives UInt32 when the value fits. Thus `0x80000000` supplies the negative Int32 seen in the actual record. An explicit unsigned literal avoids converting that already-negative value. Simply prepending a UInt32 cast to the original signed literal is not the proposed repair.

Microsoft's [CreateFileW documentation](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew) specifies `dwDesiredAccess` as DWORD and permits generic read/write access. Current W's C# declaration at line 1274 correctly uses `uint access`; retain it. Fix the PowerShell literal typing, not the native ABI or requested permissions.

At current W lines 1437–1439, change only the three `access` argument literals:

| Call | Current | Planned |
| --- | --- | --- |
| `CreateFile('NUL', access, ...)` | `0x80000000` | `0x80000000u` |
| `CreateFile($stdoutPath, access, ...)` | `0x40000000` | `0x40000000u` |
| `CreateFile($stderrPath, access, ...)` | `0x40000000` | `0x40000000u` |

Only the read mask has the observed signed-high-bit defect. The write masks already fit positive Int32 and are convertible to UInt32; suffixing those two explicitly is a small consistency improvement at the same three-call interop boundary, not a claim that they failed. These edits retain the exact bit patterns, file/device destinations, sharing, security/inheritance, creation dispositions, flags and handle ownership. No helper, runtime numeric probe, wrapper invocation or declaration change is needed. No new named global/system variable is needed.

Static inspection found three other PowerShell access-mask calls: `OpenProcess(0x1000 -bor 0x0400,...)` at 983 and 1532, and `OpenProcess(0x1000,...)` at 1039. Their masks are positive `0x1400`/`0x1000`, with no sign-bit problem; **no correction is required at those sites**. No additional high-bit eight-digit PowerShell access literal was found. Do not broaden this cycle into general P/Invoke, numeric-style, access-rights or process-flag cleanup. Other uint flags/lengths/exit values are outside this defect; retain their existing semantics.

## Implementation and static acceptance

1. Reconcile this plan and exact current W/evidence hashes, then Luna changes the three literals in W only. S/H/P, schemas/modes/commands/environment, recent exact caller/handoff ownership checks, immutable PREPARED snapshot/hash comparison, supported same-directory persistence/fallback, source/candidate/test/config/GIS/product/historical bytes remain unchanged.
2. Run affected non-operational static gates only: PowerShell AST parsing without invoking W; inspect the three corrected access argument nodes for unsigned literal spelling/type, and compile the unchanged embedded C# declarations without calling any method if needed by the gate. Existing pinned S/P/H Ruff/format evidence and unchanged C# declaration evidence may be reused under disposition 64; disclose exact reused hashes/references. No runtime literal-evaluation probe, native call, import, test or wrapper repro is necessary or authorized at this stage.
3. Report exact final W hash, unchanged S/P/H and preserved original/retry evidence hashes, exact static commands/results and any preliminary failures. The source delta must contain only the three literal suffix edits. A parser/compiler PASS is syntax/ABI evidence, not proof of a successful self-check.
4. An independent non-implementing Sol session reviews actual final W against the original failure, these two official references, and every preservation constraint. Mandatory criteria: UInt32-valued positive read/write arguments with unchanged bit patterns; `uint access` unchanged; positive OpenProcess masks not unnecessarily altered; no security/share/creation/flags/handle/cleanup/deadline change; caller/handoff checks retained; all prior evidence preserved. FIX_REQUIRED permits another bounded correction/review under disposition 64, but no operational invocation before a fresh PASS.

Preserve the reviewed W → venv launcher → base interpreter → S → H chain, exclusive one-use evidence, nonce/native PID/creation/image checks, suspended Job assignment before resume, nested Jobs, truthful non-PASS/error/termination telemetry and cleanup. Self-check remains **10 seconds total from its own original QPC start**; standalone/build deadlines and all candidate limits remain unchanged. No unsigned access cast is a reason to increase time, memory or privileges. Runtime fit/behavior remains unmeasured.

## Execution and stop conditions

Disposition 64 authorizes serial defect-specific plan → Luna implementation → independent review → **one** wrapper self-check after PASS. This plan does not authorize or perform that run. Preserve its actual result/evidence, then stop if it fails and diagnose/plan/review the next defect; do not issue repeated wrapper calls within a cycle.

**The current fixed retry-1 root is already consumed and must not be reused.** W's existing root refusal remains correct. A numeric-only W change does not provide a fresh usable evidence slot, and this plan does not rename paths, delete/relocate old records, create new directories, add auto-numbering or weaken one-shot refusal. Before the eventual self-check, the coordinator must resolve and independently review the exact fresh fixed evidence-path binding required by the serial-attempt authorization. If that requires synchronized S/H path changes or another boundary beyond this W-only interop fix, return a separate narrowly scoped plan/review before execution. Do not present an unchanged consumed-path refusal as a retest of the corrected access mask.

Stop for any need to change W beyond this access-type boundary, modify the C# ABI/entrypoint, security rights/flags/destinations, caller/handoff contract, source/geometry/recipe/numerical limits, dependencies, schemas, roots or deadlines. Preserve every failed attempt and historical counter; disposition 64 is additive repair authority, not an evidence/budget reset. No commit, push or merge.

No runtime identity collection/verification, manifest preparation, GIS/numerical work, candidate build, serving or browser action follows a self-check PASS under this authorization. Candidate remains **NO-GO/unservable**, build 3 unreserved. Later phases need their own user direction.

Planning used only static document/source/evidence reads, searches/hashes and official documentation retrieval, plus writing this one plan. The first attempted version-specific numeric-document URL was unavailable; the official canonical page/search content supplied the cited literal rules. No code/evidence/other file edits, parser/linters/compiler/tests, imports, scripts/wrapper/runtime/self-check, new evidence directory, manifest/candidate/GIS/build or browser application work occurred. Return for coordinator reconciliation and bounded Luna dispatch; stop here.
