# Agent workflow

The user authorized this workflow update on 24 October 2026. It changes agent instructions and handoff records. Product scope, geographic acceptance criteria, trial limits and publication permissions continue to come from the user's authorization, AGENTS.md and the accepted issue specification.

## Models and coordination

Use the current `torquay-plan-implementation` skill at `C:\Users\david\.codex\skills\torquay-plan-implementation\SKILL.md`. Its default routing is Luna medium for orchestration, Sol 6.1 medium for planning, bounded diagnosis and independent review, and Luna high for implementation and corrections. Sol may make one correction only if an actionable finding remains after all four completed Luna correction cycles have been reviewed. Astra is for a separately selected deep assessment.

Luna is the orchestrator for each issue. Settings are chosen in the app; the skill must report actual settings when available and cannot silently change them. Do not wrap the project skill in the generic orchestration skill. Reuse compatible role agents, keep edits serial, and preserve an independent Sol reviewer who has not implemented the issue. If Sol implements an escalated correction, a different Sol session reviews it.

## Corrections and evidence

- For new issues: initial implementation, up to four completed Luna correction cycles, then one Sol 6.1 correction only if an actionable finding remains after all four cycles have been reviewed. A correction cycle is one completed Luna correction submitted for independent review. These are maximum allowances, not targets; stop sooner if authorization, preservation or contradictory criteria make further work unsafe or meaningless.
- If the same substantive failure survives a Luna correction, obtain a bounded Sol diagnosis before another dispatch. Investigate feasibility before broad integration. Define the diagnostic question, useful result, resource budget and stop condition before expensive experiments. Sol plans and reviews from the outset; do not escalate the correction implementation to Sol until all four Luna correction cycles have been reviewed, unless the user explicitly changes the policy.
- Existing issues retain their recorded limits and used/reserved attempts. This metadata update does not replenish an exhausted budget, convert a used Sol correction into Luna cycles, or resume paused work. The Teignmouth v2 issue retains its legacy ceiling and its already reserved Sol correction; the separate corridor prototype remains exhausted at its recorded budget. Reconcile each issue from its own checkpoint before any authorized continuation.
- Preserve independent review of actual changes. On corrections, rerun affected checks and reuse unchanged valid evidence linked to exact revisions/hashes and compatible environments. Mandatory specification and milestone gates still apply. Formatting or prose corrections alone do not require GIS rebuilds or new browser evidence.
- Before more timing-supervisor work, reassess the approach against the demo's needs. Distinguish rejection of a late result from preempting a native computation. An optimization, cap change or simpler architecture needs appropriate evidence and review under the existing scope; this workflow does not approve one.

## Current-state record

Keep `.codex/torquay-plan-implementation.md` short, with exactly one authoritative current-state section. Update after each dispatch/result, review and pause. Link active specifications, the latest review and relevant evidence; put detailed history in archives. Record attempts, role settings, correction causes and elapsed time. Attribute usage to an issue only when supporting telemetry exists.

The pre-update checkpoint and skill files are preserved byte-for-byte in `.codex/history/2026-10-23-workflow-update/`; `manifest.json` records their original paths, sizes and SHA-256 hashes. Those snapshots are history, not current operational instructions. The old checkpoint's SHA-256 is `83c734c06760708b6b5ea737f861a234b3b46833aeec55c2a3abe609c0532814`.

Checkpoint compaction and this AGENTS.md amendment are authorized metadata changes. Preserve historical reports, manifests, consumed trials and accepted assets. Where execution binds metadata hashes, reconcile this documented transition explicitly under the existing review/approval mechanism before execution. Do not rewrite old evidence, silently refresh frozen pins, or claim historical hashes match the new metadata. Activation remains disabled until its actual current requirements pass independent review and coordinator acceptance.

## Paused work and resumption

This workflow update changes role defaults only; it does not resume paused or exhausted implementation. The compact checkpoint and issue artifacts retain their existing counters, findings and status. On a separately authorized resume, inspect the relevant state and actual workspace/agent status first. TVW-016 and later remain unauthorized.

For a fresh chat under this workflow, select Luna medium for orchestration, Sol 6.1 medium for planning/review, and Luna high for implementation when the app allows it. Read the skill files from disk rather than relying on an older conversation's cached description. Existing agent IDs are recovery references; they are not a reason to send messages to unrelated chats or assume access to another chat's agent roster.
