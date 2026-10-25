# Review 18 — minimal S-only diagnostic close/image correction plan

2026-10-25. Sol 6.1 medium planner `/root/sol_review17_plan`. Planning only under disposition 82. Supplements the accepted `retry3-unexpected-member-evidence-plan.md` (SHA-256 `1e3bdb230ca7a1c2f7cbcea9ebe0c1dc6b1d9d960a51502adf5e5d40f46afbe4`) for exactly review 18's two findings.

**Feasible inside `_observe_selfcheck_unexpected_members` in S only.** Make the single mandatory native close attempt independent of optional telemetry, and require bounded observable endpoint stability before an image digest is marked observed. No acceptance/rejection or shared hash semantics change. Coordinator must accept/release this plan before implementation; no code/runtime operation is authorized here.

## Reconciled baseline

Read disposition 82, review 18 plus its image-stability addendum, the accepted diagnostics plan and actual S helper/image/close/aggregate blocks. Recalculated hashes:

| File | SHA-256 |
| --- | --- |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `81fcdc0b199497d92d17c09c758a62b8861e7fcb7b41bb6a1c1663a1f76256af` |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `c3f1f49cb574793c1cdbc2d905fd3d36f646b6f32ffb7c200a96c9792d5ce84f` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `cf1145b33397066559b89c11aa1cb0ebcf4d6d4d470f6521d96fe9e1f4ecccab` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| Disposition 82 | `d916411c64d9eda8705a90597704e301d1d1f5859d369ea8d68106a0af185898` |

Review 18 source hash is `9d4dfa9b32f141b3f5fd2d5775af7b4f8e2d12581b916d766b9fca92a947be7c`; addendum `8902b1cee5fe309a38075e4ea876acc4b38c11fb12429a42e72117d73ebe5267` (accepted disposition records). Neither finding establishes an actual historical leak, file mutation or process class. PID 20712 remains unidentified.

## 1. Mandatory close before any fallible optional telemetry

Affected code: helper's diagnostic-handle `finally` at current 2521–2548, and initial `handleClose` row at 2103.

The first cleanup operation in that finally must be a direct **single** `kernel.CloseHandle(handle)` attempt on the successfully opened local handle. No `time.monotonic()`, `bool(...)`, error formatting, dictionary/list creation or update, deadline test, process query or optional telemetry may precede it. The existing `try/finally` ownership boundary must continue to start immediately after successful OpenProcess; do not add fallible work between acquisition and that boundary.

Concrete structure:

- The mandatory operation is the direct CloseHandle call, whose result can be assigned to a local. The try around it catches native-call/dispatch exceptions only so reporting remains best-effort. Do not call a replacement helper, retry CloseHandle or transfer this diagnostic handle into the normal pair's cleanup list.
- In the close exception branch, put **all** optional exception/error/timestamp construction and row updates inside a separate guarded `try/except Exception`. If reporting fails, suppress only that secondary reporting failure. The close request has already been attempted; no claim is made that ctypes dispatch must reach the OS if dispatch itself fails.
- In the successful-call branch, likewise guard the entire error-code retrieval/formatting, timestamps and row update. True return can record `released`; false/error is `close-failed/release-unconfirmed`, never successful closure. GetLastError retrieval, if available, precedes other optional calls in this reporting block; inability to retrieve/report it remains unknown.
- Remove the current required pre-close timestamp. Leave `startedMonotonicSeconds=null` with a best-effort reason such as `pre-close-telemetry-omitted-for-cleanup-safety`; any post-attempt timestamp is labeled accordingly. Do not manufacture a close duration or a before-call time from a later observation. Deadline reporting after the attempt is also optional/guarded and cannot prevent the close.
- Initialize `handleClose` conservatively before OpenProcess with `status=unobserved`, `closeAttempted=null` and unknown release state. Open failure can best-effort refine it to not-opened/false. If close telemetry cannot be allocated, the unchanged conservative field is incomplete evidence, not a false claim that a successfully opened handle was never closed. The aggregate must remain partial unless release was actually reported.

This guarantees one **attempt** independent of timestamp/error-record allocation, not guaranteed API success, exception-free dispatch or durable telemetry under memory/filesystem failure. Every successfully opened handle has exactly this one finally-close path. Existing outer diagnostic attachment guards still preserve the primary snapshot/rejection if the whole diagnostic result cannot be reported. Eventual OS release at S exit is not an observed CloseHandle success.

## 2. Bounded same-path image stability around the unchanged hash helper

Affected code: initial image fields, helper image-path/hash block at current 2370–2449 and helper result aggregation at 2555–2573. Add only local metadata/compare routines in this helper as useful. **Do not modify `_sha256` or its callers elsewhere**, native API declarations/rights, same-process-handle identity queries or shared process identity helpers. Current `os`, `stat` and `Path` facilities suffice; no dependency/import is required.

Keep the native image query and its raw path as an observation from the same process handle. A disk-path hash is separate evidence. Add an `imageStability` nested field with explicit not-attempted/unverified/changed/observed-metadata-match/deadline status, before/after canonical paths and file metadata, and partial errors/reasons. These are fields within the existing invocation diagnostic row, not a new schema or artifact.

### Exact sequence

1. Preserve `QueryFullProcessImageNameW`'s raw result and native-query status. Check original deadline. Require a valid absolute path for the filesystem observation; malformed/relative/missing/unresolvable/unsafe types are partial/unverified, not silently normalized into trusted identity.
2. Resolve **that same original raw path** using `Path(raw_path).resolve(strict=True)` into `canonical_before`. Observe metadata of that resolved regular file with existing standard-library stat calls. Record metadata before hashing; do not infer a meaningful file identity from path text alone. Record any existing symlink/reparse/type concern as unsafe/unverified rather than accepting it as stable; do not expand the source trust boundary.
3. Hash exactly the stored `canonical_before` path through existing `_sha256(canonical_before, deadline)`. It remains the existing chunked path-opening hash function, with identical semantics. Treat its returned digest as provisional: no immediate `imageSha256.status=observed`.
4. Before success, re-stat **the identical stored canonical path** to obtain `metadata_after_same_path`; independently re-resolve the **same original raw path** into `canonical_after`; stat that resolved target as `metadata_after_resolve`. This detects both replacement/change at the hashed spelling and an observable change in the raw path's target. Do not switch to a new native path, a filename found by search or the post-resolved target for a second retry hash.
5. Compare canonical-before/after strings with exact canonical spelling (a casing/alias ambiguity may conservatively be changed/unverified), require all three observations to be regular files, and compare the metadata tuples below. Check original deadline before/after every resolve/stat and between hash chunks, and once more before labeling the observation matched. Any late result is partial/deadline-exhausted. No new relative timeout or attempt loop.

### Exact metadata tuple and comparability

Record and compare integer-valued `st_dev`, `st_ino` (device plus file identifier), `st_size`, `st_mtime_ns`, `st_ctime_ns`, `st_mode` and Windows `st_file_attributes` when available. Record `st_birthtime_ns` when available, comparing it consistently at all endpoints. Do not convert IDs/times to floating point or assume file identifiers fit 32/64-bit values.

For an observable match require a meaningful nonzero `st_ino`, available comparable device identity (device value zero is not automatically invalid), size and nanosecond timestamp fields at all three endpoints, regular-file type and equal required tuples. Missing/unsupported identity or timestamp fields, unusable identifiers, inconsistent optional-field availability, unsafe reparse/type observation, or unverifiable metadata becomes **unverified stability/partial**, never an assumed match. Compare birthtime/Windows attribute fields if present at any endpoint; absence only at some endpoints is unverified/change evidence, not something to drop to force equality. Treat timestamp names as observed platform metadata, without claiming they are a security audit of every mutation.

This is a finite endpoint identity/metadata check. No new native file-ID API, mapped-image read, file-lock/exclusive sharing policy, alternate hash method or shared hash behavior is proposed.

### Outcomes and aggregation

| Outcome | Required row/result meaning |
| --- | --- |
| Digest finished, all comparable endpoints/path/type match, still before deadline | `imageStability.status=observed-metadata-match`; `imageSha256.status=observed`, value is digest. This is only an observable disk-file endpoint match. |
| Resolved target, ID/device, size, timestamps/type or comparable metadata differ | `imageStability.status=changed`; image digest is **not verified**. `imageSha256.status=changed/unverified`, normal `value=null`; provisional digest may remain separately labeled `candidateValue` for traceability. Aggregate partial. Preserve path/metadata differences. |
| Any missing/unreadable/unsupported/uncomparable metadata, failed resolution/query/read, or stability cannot be established | `imageStability.status=unverified` with explicit partial reason; `imageSha256.status=unverified-stability` or existing unavailable status, normal `value=null`; provisional digest separately labeled if obtained. Aggregate partial. |
| Original deadline reached during any part | Existing deadlineReached plus deadline-exhausted image/stability status; no observed/matched promotion. Aggregate deadline-exhausted/partial as currently distinguished. |

Retain the observed native/raw path even when the filesystem observation is partial. If only disk metadata changes, do not falsely claim the process's native image path changed. If canonical target changes, explicitly distinguish that from the raw string. Partial image observations must not suppress earlier creation/membership/wait/exit facts or later same-handle observations that still fit the deadline.

Extend result aggregation to require `imageStability.status=observed-metadata-match` **and** the existing hash/path/other-field predicates before overall diagnostic status can be observed. Do not equate a completed hash or successful stat with stable observable identity. Any changed/unverified/late condition must remain partial even if another query later succeeds. No primary census or acceptance field is changed by this diagnostic aggregate.

### Explicit limits of this evidence

Equal endpoint metadata cannot rule out replacement/mutation restored between samples, same-metadata concurrent mutation, or all races between stat, shared `_sha256` opening/reading and post-stat. The shared hash function opens by pathname and is not bound to an atomically locked file object by these checks. A stable disk path/hash is **not mapped-image attestation**: the process may have mapped different historical bytes. No claim of atomicity, load confinement, crash durability or universal protection from concurrent replacement. These limits do not authorize admitting any unexpected PID; its rejection stays unconditional.

## Narrow ordered change set and static acceptance

1. Reconcile S's exact baseline. Change only the diagnostic finally/default-close field, the helper image endpoint-check/fields and its aggregate partial predicate. Preserve eight-PID cap, original query ordering/same-handle rights, no extra in-interval census, no retries or new files/roots. W/H/P remain byte-identical.
2. Keep all optional close/image diagnostic formatting/allocation within best-effort guards; native process handle close remains in finally even if metadata/query/error construction fails. Do not let new stat/hash exceptions mask the primary snapshot or original unexpected-PID rejection. Preserve accepted review-16/18 outer guards and normal cleanup.
3. After separate implementation authorization, run affected S Ruff check/format and only coordinator-authorized non-operational static syntax checks. Reuse unchanged W/H/P/API declaration evidence with exact hashes. No tests/fault injection/probe files, source imports, process inspection, wrapper/runtime operations or evidence creation. Record exact commands/results, preliminary failures and final/preserved hashes.
4. Independent non-implementing Sol reviewer inspects actual final S/delta against review 18/addendum and this plan. No syntax PASS substitutes for the following control-flow proof.

| Case | Required independent static proof |
| --- | --- |
| MemoryError in pre-close timestamp/error construction | There is no such operation before the one direct CloseHandle attempt; optional reporting can fail only after that attempt. |
| Query/body failure; close false/raises; close telemetry allocation failure | Finally still reaches exactly one close request; true/false/unavailable statuses truthful, no retry/transfer/double-close; missing telemetry defaults unobserved/partial. |
| Stable observable disk endpoints | Same raw path resolved before/after, same stored canonical path hashed/stat-checked; complete comparable metadata match before digest promoted. |
| Rename/replacement/target/ID/device/size/time/type change | Detected differences yield changed/unverified partial; no silent rehash/adoption or observed aggregate. |
| Missing/nonregular/unsafe/unsupported file identity or timestamps | Partial/unverified, not inferred stable; field-specific evidence retained if possible. |
| Hash completion followed by post-stat/resolve error or deadline | Provisional digest cannot remain simply observed/verified; no fallback identity/hash method or timeout extension. |
| Same-metadata concurrent mutation/mapped bytes | Explicitly outside claim; no atomicity/mapped-image inference. |
| Scope and accepted gates | Original accounting/census/timestamps/complete/unexpected set and sticky BLOCKED unchanged; diagnostics cannot reach normal PASS, erase unexpected PID after disappearance, alter exits/containment/tree/cleanup/path/deadline or touch W/H/P. |

## Stops and handback

Stop before implementation without coordinator acceptance/release. Stop if these checks need new native APIs/rights/dependencies/schema/path/root/file or shared `_sha256` changes, if required metadata cannot be compared, or if cleanup/error-isolation cannot be made independent of fallible optional reporting. Unavailable identity may be recorded as partial; it does not justify expanding scope or declaring a match. Any proposed atomic/mapped-image guarantee or process-class exemption needs separate user boundary direction, not a stronger label on this check.

The original inherited **10-second total** remains unchanged; native/filesystem call preemption and actual fit are unmeasured. All expiry/incomplete/unexpected-member cases remain non-PASS. No new in-interval census, clock/reset/retry or extended helper sleep. Retry-3 and all previous evidence remain immutable/consumed/non-PASS. Outer command exit 1 versus internal 2 and missing `957157…` S history remain unresolved; no PID20712 classification or historical image mutation/leak is inferred.

After a future correction/review, another self-check still requires a separately planned/reviewed fresh fixed path and coordinator gate; no consumed slot reuse. No collection/verification/manifests/GIS/numerical/candidate build/reservation/serving/browser action is authorized. Candidate remains NO-GO/unservable, build 3 unreserved; historical counters, geographic/source/recipe/geometry/numerical/product constraints unchanged. No commit/push/merge.

Planning performed only static source/document reads/searches/hashing and writing this one plan. No source/evidence/checkpoint/ledger/other artifact edits, root preparation, tests/imports/parsers/linters/compilers, process inspection/probes or operational/runtime/evidence writes occurred. Return plan hash to coordinator and stop.
