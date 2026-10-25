# Teignmouth topology study: validation transition v2

Status: fix 3 is under implementation and independent review. The v2 timing
policy remains **inactive**. No topology trial is authorized by this document.

## Scope

This is an additive, versioned validation and timing transition for the
remaining Teignmouth topology-study trials. It does not change the 84 × 82 m
domain, road station union, topology, source release, accepted preview, solver,
2,000-iteration limit, numeric gates, resource ceilings, default viewer, or
public package. It does not allow a retry of `flip-05` or `road-05`.

The transition binds accepted-height cache decisions to the exact array object,
shape, dtype, and canonical little-endian Float32 bytes. In-place mutation or
replacement invalidates the context. A fresh context recomputes baseline versus
accepted-grid equality from current bytes. The v2 validator retains all twelve
existing gate calculations and reports, while checking the validation deadline
inside building records, source-ownership faces, and exact overlay faces.

## Remaining-trial timing policy

One monotonic invocation timestamp, T0, anchors all windows:

| Phase | Absolute cutoff | Behavior |
| --- | ---: | --- |
| Input loading, preparation and solver | T0 + 120 s | Solver receives only the remaining time to this cutoff; 2,000 iterations remain the maximum. |
| Complete offline validation, including candidate asset assembly, independent asset checks, resource checks and deterministic hashes | T0 + 125 s | A check interrupted at this boundary and every later gate is recorded as unavailable and failed. |
| Preservation, serialization and finalization | T0 + 135 s | Bounded completion window. A timeout consumes the write-once trial. |

A later trial qualifies only when the complete projected end-to-end duration,
including finalization, is at most 125 seconds in both the implementer profile
and an independent Sol profile. The 135 second completion window is a hard
upper bound, not an automatic extension. The wrapper never retries, raises a
limit, or marks an incomplete validation as passed.

The frozen study manifest and runner retain their original 120 second policy.
`run_teignmouth_topology_validation_v2.py` is the named opt-in wrapper. It
captures one unshifted monotonic T0 before config and input preflight, gives the
frozen runner only the remaining time before T0+120, and refuses an aggregate
commit after T0+135. Asset assembly, both independent asset validations,
resource checks and deterministic comparisons run under bounded T0+125 waits.
The current config remains disabled; a 64-character digest or an enabled flag
alone can never activate it.

## Exact approval chain

The runtime implementation map is the union of the immutable road-05 code map
and the extension code map, including `road_surface_validation_v1.py` and its
transitive legacy dependencies. The config's own bytes are bound separately to
avoid a self-hash cycle. Static validation compares the full timing/resource
policy with constants in the versioned wrapper and validates every bound file.

Before any future trial, the coordinator must prepare one exact review config
with `activation.enabled=true` and status `approval_chain_required`, without
changing limits or inputs. Sol's independent review artifact must be JSON at
`docs/milestones/artifacts/Teignmouth-topology-validation-v2/independent-sol-review.json`
with disposition `PASS` and exact config path/hash, this spec path/hash, and the
complete runtime code map and its canonical digest. The coordinator then writes
`coordinator-acceptance.json` at the same directory, binding those exact values
and the Sol artifact's byte hash. Finally, the checkpoint contains exactly one
`TEIGNMOUTH_VALIDATION_V2_ACCEPTED receipt_sha256=<receipt file SHA-256>` line
and no pending marker. The runner independently validates both JSON artifacts,
the actual files and hashes, and the checkpoint receipt marker before creating
any trial directory. Any edit after Sol review invalidates the chain and
requires a new exact review and receipt. The activation remains disabled until
that complete chain is present.

## Prior input reconciliation

The consumed-trial inventory is pinned at
`docs/milestones/artifacts/Road-surface-treatment/teignmouth-topology-study/profiles/consumed-trials-inventory-v2.json`
(2,411 bytes; SHA-256
`9e9c9d083014dd2649fc2b4d284a235423358466b6e91b3d07959c2369f5d8d6`). The
transition config pins the old Road-surface-treatment evidence tree
`a83f7f30ebd3fba437364a570ee3349e72bec7b62e5bc9304708b1d50512c688` and its
current tree `4413d4fc79adcf846d578e51fa2d65ee46b674721b1e1e61759fae1a0214f94a`.
The input validator independently removes only that exact inventory entry and
requires the resulting tree digest to equal the old tree pin.

The current task checkpoint was SHA-256
`5b0cfb793f3780b9ee2af6087d643a22cde32b43c9b7442ed9940306b09a17a6` at
implementation start. The config records that baseline and requires one named
checkpoint marker for the v2 state. It does not embed the final checkpoint hash,
avoiding a circular reference. During a future trial, the runner snapshots and
binds the actual complete checkpoint bytes before and after the trial.

Prior `flip-05` and `road-05` maps may differ from the current map only at the
checkpoint and Road-surface-treatment evidence-tree entries, with their exact
legacy values pinned in the config. All other stable protected entries,
release bytes and accepted-preview assets must match. `flip-05` keeps its
original 12-key code map; `road-05` keeps its original 15-key map. The new
versioned module, wrapper, tests, profile and specification are added as
explicit code-hash extensions rather than rewriting those records.

## Candidate trial eligibility

The transition admits `collar-05`, then `local-025` only after all 0.5 m
topologies fail, then `local-0125` only after the 0.25 m stage fails. Existing
stage-order checks remain in force. Both consumed trials remain ineligible.
Every future trial is write-once under the existing raw evidence path. No
trial, candidate output, or browser work was run as part of this implementation.

## Evidence

The initial read-only profile remains at
`docs/milestones/artifacts/Teignmouth-topology-validation-v2/retained-road-05-profile.json`.
The fix-3 audit profile is
`docs/milestones/artifacts/Teignmouth-topology-validation-v2/retained-road-05-profile-fix3-audit.json`;
its detailed interpretation is in
`docs/milestones/artifacts/Teignmouth-topology-validation-v2/transition-evidence-fix3.md`.
It compares all twelve gate reports, including every record for 3,613 buildings,
against the retained road-05 aggregate; verifies before/after protected-map
equality; and verifies the consumed trial directory stayed byte-identical. Its
`passes` field means only that these evidence-equivalence and preservation
checks passed. The retained road-05 candidate itself fails offline gates. Its
road/path reclip failed before producing groups, so the conditional asset
assembly, independent asset validation, asset resource and deterministic-build
timings are unavailable. The profile therefore records a lower-bound projection
of 113.7475 seconds, leaves 11.2525 seconds unmeasured, and sets
`qualifiesForNextTrialTiming` to false. No timing qualification is established.
The independent Sol profile is pending; until both profiles meet the
qualification limit and independent review passes, the transition remains inactive.

## Sol escalation: measured trace cost and membership caching

The original complete retained flip-05 diagnostic reached its separate 1,800 s
trace ceiling without completing validation. Its immutable timing-only profile
is `flip-05-complete-traced-profile-sol.json` under the v2 evidence directory;
its corresponding report explicitly marks validation unavailable. It is not a
trial, qualification result, cap amendment, or candidate acceptance. The exact
measured script, supervisor, config and specification bytes are archived in
`sol-measured-runtime-before-cache/`. The earlier fix-4 profile remains unchanged.

The supervisor now caches workspace membership for each absolute-filename code
object during one validation phase. Its id key retains a strong reference to
the code object, preventing identity reuse. Relative filenames retain the old
CWD-sensitive per-line resolution. The cache is cleared on phase exit. Every
workspace Python line still polls the real monotonic clock: no sampling interval,
grace period or deadline extension is introduced. Pre-call, post-call, late-pass
rejection, explicit unavailable results, and the +120/+125/+135 policy remain
unchanged. Native calls remain non-preemptible; their late results are rejected
after control returns. No hard native-call preemption claim is made.

Additive tests cover one resolution per absolute code object, continued polling
on every workspace line, relative-name behavior, exact cutoff/overshoot,
external late return and trace restoration. The named runtime extension pins
both versioned complete-profile entrypoints and their tests. The optimized
read-only replay writes only `flip-05-complete-traced-profile-sol-optimized.json`
and `flip-05-complete-traced-report-sol-optimized.json`; package assembly remains
in memory with synthetic pass flags explicitly limited to structural timing.
It records data/source-manifest and release terrain manifest hashes separately.

Both profiles use a diagnostic-only extended trace deadline to measure work,
not to change the disabled transition's cap. A projection composed of retained
road preparation/solver durations and measured flip validation/assembly is only
a proxy: actual collar topology, solver behavior and geometry sizes have not
been measured. No new cap, trial admission or activation follows automatically.
Independent Sol review and coordinator approval remain required.


### All-code membership cache diagnostic continuation

The absolute-only replay completed in 288.096689 s traced versus 69.632109 s
untraced, with all twelve reports byte-identical. Its versioned outputs and exact
runtime archive remain immutable. The next bounded timing-only replay caches
both positive and negative code membership, resolving relative filenames once
per observed CWD value and invalidating after a CWD change. Reparse-component
paths remain uncached; ordinary source files are immutable during each phase.
Every workspace line still checks the deadline. Counters disclose line events,
relative events, resolutions, cache hits and clock polls. Fake-clock, external,
relative, changed-CWD and reparse tests guard those semantics. New write-once
outputs are `flip-05-complete-traced-profile-sol-all-codes.json` and corresponding
`flip-05-complete-traced-report-sol-all-codes.json`. This changes no cap, source,
trial inventory, activation, numerical gate or accepted package. Independent
review is required; timings remain diagnostic proxies rather than qualification.


### Reserved Sol correction resumed after authorized workflow metadata migration

The same reserved Sol correction continues; the four Luna corrections remain
used. Activation stays disabled. Before-images of the interrupted supervisor,
config, specification, transition module and affected tests are retained under
`sol-frame-resume-before/` in the v2 evidence directory, with their exact hashes.

Safe absolute Python code membership is selected at frame entry. Workspace
frames retain a deadline poll on every line; absolute external frames omit
local line events while global call tracing still observes workspace descendants.
Relative filenames and reparse/unknown paths retain per-line membership checks,
including CWD invalidation. This reduces tracing overhead without changing gate
calculations, timing offsets, cutoff behavior, or the native-call limitation.

The named `authorized-agent-workflow-2026-10-23` metadata exception admits only
the exact old/new AGENTS.md hashes, verifies the retained old AGENTS/checkpoint
bytes and archive manifest, and binds the authorization document. Historical
maps and evidence are unchanged. Current checkpoint bytes remain snapshot-bound
and marker-governed; arbitrary AGENTS changes or before-image corruption fail.
This exception itself requires independent review before activation.

One new retained diagnostic (`profile_teignmouth_frame_selected_sol.py`) uses an
80 second traced-validation ceiling and an external 150 second process limit.
It compares the twelve gates with the immutable optimized report rather than
repeating the untraced validator. It measures actual static/input-transition
preflight and conditional assembly where available. Missing activation-receipt
preflight and exact trial finalization remain explicitly unavailable; therefore
it cannot claim complete end-to-end qualification. If validation cannot complete
inside its bound, or the measured projection exceeds 125 seconds, stop without
another variant/replay or trial. No cap amendment follows from this diagnostic.
