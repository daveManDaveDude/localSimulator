# Agent workflow

The user authorized this workflow update on 23 October 2026. It changes agent instructions and handoff records. Product scope, geographic acceptance criteria, trial limits and publication permissions continue to come from the user's authorization, AGENTS.md and the accepted issue specification.

## Models and coordination

Use the current `torquay-plan-implementation` skill at `C:\Users\david\.codex\skills\torquay-plan-implementation\SKILL.md`. Its default routing is Luna medium for routine coordination, Sol 6.1 medium for planning/review and difficult coordination, Luna high for clear implementation, and Sol 6.1 medium for coupled numerical/validation implementation. Luna xhigh requires a concrete task-specific reason. Astra is for a separately selected deep assessment.

The invoking chat is the only coordinator. Settings are chosen in the app; the skill must report actual settings when available and cannot silently change them. Do not wrap the project skill in the generic orchestration skill. Reuse compatible role agents, keep edits serial, and preserve an independent reviewer who has not implemented the issue.

## Corrections and evidence

- For new issues: initial implementation, at most two Luna corrections, then at most one Sol correction. Hard issues may start with Sol and have at most one Sol correction. These are maximum allowances.
- If the same substantive failure survives a correction, obtain a bounded Sol diagnosis before further implementation. Investigate numerical feasibility before broad integration. Choose a diagnostic question, useful result, resource budget and stop condition before expensive experiments.
- Existing issues retain their recorded limits and used/reserved attempts. The paused Teignmouth v2 issue retains its legacy four-Luna/one-Sol ceiling. Its Sol correction has started and is reserved; a new chat or skill revision does not create another slot. Reconcile and resume the same interrupted correction only when authorized.
- Preserve independent review of actual changes. On corrections, rerun affected checks and reuse unchanged valid evidence linked to exact revisions/hashes and compatible environments. Mandatory specification and milestone gates still apply. Formatting or prose corrections alone do not require GIS rebuilds or new browser evidence.
- Before more timing-supervisor work, reassess the approach against the demo's needs. Distinguish rejection of a late result from preempting a native computation. An optimization, cap change or simpler architecture needs appropriate evidence and review under the existing scope; this workflow does not approve one.

## Current-state record

Keep `.codex/torquay-plan-implementation.md` short, with exactly one authoritative current-state section. Update after each dispatch/result, review and pause. Link active specifications, the latest review and relevant evidence; put detailed history in archives. Record attempts, role settings, correction causes and elapsed time. Attribute usage to an issue only when supporting telemetry exists.

The pre-update checkpoint and skill files are preserved byte-for-byte in `.codex/history/2026-10-23-workflow-update/`; `manifest.json` records their original paths, sizes and SHA-256 hashes. Those snapshots are history, not current operational instructions. The old checkpoint's SHA-256 is `83c734c06760708b6b5ea737f861a234b3b46833aeec55c2a3abe609c0532814`.

Checkpoint compaction and this AGENTS.md amendment are authorized metadata changes. Preserve historical reports, manifests, consumed trials and accepted assets. Where execution binds metadata hashes, reconcile this documented transition explicitly under the existing review/approval mechanism before execution. Do not rewrite old evidence, silently refresh frozen pins, or claim historical hashes match the new metadata. Activation remains disabled until its actual current requirements pass independent review and coordinator acceptance.

## Paused work and resumption

The user paused the implementation to regroup. Updating these instructions does not resume it. The compact checkpoint records the interrupted Sol correction, retained profiling evidence and next action. On an explicit resume, inspect that state and the actual workspace/agent status first. Complete bounded diagnosis and reconcile the existing attempt before starting any further execution. TVW-016 and later remain unauthorized.

If using a fresh chat, select Sol 6.1, medium reasoning, Standard speed for this difficult phase. Read the skill files from disk rather than relying on an older conversation's cached description. Existing agent IDs are recovery references; they are not a reason to send messages to unrelated chats or assume access to another chat's agent roster.
