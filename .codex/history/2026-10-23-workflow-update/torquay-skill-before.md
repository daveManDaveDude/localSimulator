---
name: torquay-plan-implementation
description: Implement or resume steps from the Torquay JS Virtual World PoC plan through Sol 6.1 specification, Luna 6.0 implementation at xhigh, and independent Sol 6.1 review at medium, with four Luna fixes and one Sol escalation before stopping. Use for this Torquay project rather than unrelated specifications.
---

# Torquay Plan Implementation

Implement the requested issues or milestones from `C:\vibe\localSimulator\Torquay_JS_Virtual_World_PoC_Codex_Plan.md` in `C:\vibe\localSimulator`, unless the user explicitly supplies a different workspace or source.

Creating or editing this skill does not authorize starting the project implementation. Run this workflow when invoked to implement or resume the plan. Honor explicit user scope. If no range is specified, complete the next unfinished backlog issue and its applicable gates. For a requested milestone or the whole plan, continue serially through that scope after each PASS without asking whether to continue at issue boundaries.

## Model assignments and delegation

The invoking agent coordinates; delegate specification, implementation, and review to these roles:

| Role | Exact host model ID | Reasoning |
|---|---|---|
| Planner: inspect requirements and specify work | `gpt-6.1-sol` | `medium` |
| Implementer: initial change and up to four fixes | `gpt-6-luna` | `xhigh` |
| Independent reviewer | `gpt-6.1-sol` | `medium` |
| Escalated implementer: one fix only | `gpt-6.1-sol` | `medium` |

“Luna 6.0” maps to `gpt-6-luna`; “Sol 6.1” maps to `gpt-6.1-sol`. Pass the exact `model` and `reasoning_effort` to `collaboration.spawn_agent`, with `fork_turns="none"` when overrides require it. Supply each agent a self-contained assignment: role, source paths and relevant requirement text, current state, accepted specification, criteria, and expected report. Do not assume inherited context with no history.

Inspect available delegation controls and model/settings. If an assignment is unavailable, checkpoint and ask the user how to proceed, identifying the unavailable role. Never silently substitute another model, reasoning level, or the coordinator's own implementation.

Keep delegation serial. Reuse compatible agents through `collaboration.followup_task`; inspect the roster before spawning. With four slots including the coordinator, retain a Sol planner, Luna implementer, and Sol reviewer. Reuse the completed Sol planner as the escalated implementer when needed, keeping the reviewer separate. A reviewer must never have implemented any part of the current issue. Planner and reviewer may be the same agent only if that agent did not implement the issue; it must check its own specification against the original source as well.

Do not create an extra orchestrator or user-facing chats. Wait for delegated turns to finish and remain responsible until the authorized scope completes or requires user intervention. Interruption does not close an agent or free its slot. If capacity prevents independent review after compatible reuse is exhausted, checkpoint and explain the missing role rather than marking PASS.

## Select and specify one issue

1. Read the entire source plan, applicable `AGENTS.md`, repository status, existing milestone records, and checkpoint. Preserve user changes. If the source is missing, inspect `docs/project-plan.md`; ask if the authoritative source remains unclear.
2. Use section 15 backlog IDs (`TVW-001` through `TVW-014`), section 10 acceptance/exit gates, and documented dependencies. Select the earliest unfinished issue within scope. Existing code alone does not establish PASS.
3. Treat section 18's M0-only prompt as an example for a first assignment, not a command to reset progress or override user scope. During the first scaffolding issue, preserve the supplied plan and create `docs/project-plan.md` and the section 14 `AGENTS.md` rules as required.
4. Ask the Sol planner to inspect the original requirements and repository, then return a work specification: source references, current gaps, scope, affected files, implementation approach, dependencies, concrete observable acceptance criteria, verification commands, and browser evidence requirements. Resolve material omissions before handing it to Luna.

Keep one focused issue active. Review the combined milestone exit gate when its last issue is ready; individual issue passes alone do not establish a milestone PASS.

Preserve applicable project constraints in handoffs: strict TypeScript/Vite/Three.js and offline Python GIS; a working synthetic scene without real downloads; one frozen 500 m AOI; documented metre-based coordinates with north at negative Z; source provenance and clearly labelled estimated heights. Do not invent coordinates, source files, executed checks, or browser evidence. Follow the plan's restrictions on bulk data, dependencies, external services, and publication.

## Implement and independently review

1. Give Luna the accepted specification and original requirement context. Require actual changes, appropriate checks, and a report of changed files, commands/results, browser observations/screenshots, and limitations. Wait for completion before review because agents share the workspace.
2. Give the independent Sol reviewer the original requirements, accepted specification, actual diff/current files, implementation report, and check evidence. Require inspection of the actual changes and meaningful verification of acceptance criteria, regressions, and applicable milestone gates. The reviewer inspects and verifies; it must not fix code.
3. Require one explicit verdict:
   - `PASS`: evidence for every mandatory criterion and any nonblocking limitations.
   - `FIX REQUIRED`: specific defects or unmet criteria, locations where useful, and observable expected corrections.
4. Missing mandatory evidence cannot support PASS. Distinguish code defects from unavailable verification and external blockers. An implementer's summary alone is not independent evidence. If mandatory verification is blocked, checkpoint and seek necessary intervention rather than claiming completion or endlessly cycling fixes.
5. Send complete actionable findings and the original criteria to each correction agent. Re-review actual changes after every correction with the independent Sol reviewer. Preserve unresolved findings; do not weaken acceptance criteria to obtain PASS.
6. On PASS, record evidence and update the checklist/handback. Advance only within authorized scope and with prerequisites and applicable milestone gates satisfied.

## Exact correction budget

Track `luna_fixes_used=0` and `sol_fix_used=false` per issue. The initial implementation and its first failed review are not fix attempts.

| Event | Next action |
|---|---|
| Initial Luna implementation passes review | Complete the issue |
| Initial review returns FIX REQUIRED | Luna fix 1 |
| Luna fix 1, 2, or 3 fails review | Next numbered Luna fix |
| Luna fix 4 fails review | One Sol 6.1 medium fix |
| Sol fix passes independent Sol medium review | Complete the issue |
| Sol fix fails independent review | Stop the entire workflow and ask the user for next steps |

A fix attempt counts when the implementer returns a completed correction for review. Record the in-flight attempt before dispatch and increment the completed counter on return. Planning, re-reviewing an unchanged artifact, tool transport errors before completion, and interrupted dispatches do not consume additional attempts. Reconcile partial work before resuming; never blindly repeat or reset an attempt. Stop for real blockers rather than retrying without progress.

Stop correcting on any PASS. The maximum rejected sequence is six implementation submissions and six verdicts: initial Luna, four Luna fixes, one Sol fix. Never assign a second Sol fix or return to Luna after escalation. If the escalated implementer cannot complete its correction, stop and ask the user rather than launching another attempt.

At exhaustion, preserve changes and evidence, mark the issue `NEEDS USER DECISION`, and stop all dispatch, including later backlog issues. Explain remaining defects, attempts used, and the last review; link the checkpoint and relevant files. Ask how the user wants to proceed. Do not grant extra attempts or reset the budget without new user direction.

## Checkpoint, resume, and handback

Maintain `<workspace>/.codex/torquay-plan-implementation.md`. Inspect any existing file before updating it. Keep one authoritative current-state section and a concise history containing:

- Exact source/workspace paths and authorized scope.
- Current issue/stage, accepted specification, criteria, unresolved findings.
- Agent IDs and role/model/reasoning assignments and status.
- `luna_fixes_used`, `sol_fix_used`, and any in-flight attempt.
- Every review verdict with evidence and remaining findings.
- Passed issues/milestone gates, blockers, and one next action.

Update after specification, implementation, each correction/review, scope transition, and before stopping. Read back the current state and reconcile it with actual files and agent status. Resume the recorded next action, preserving counters and valid PASS evidence unless changes invalidate it. A new session or agent does not reset the budget. A `NEEDS USER DECISION` checkpoint remains stopped until the user supplies direction; a generic continue does not silently authorize extra attempts.

Use section 14's milestone handback: implemented behavior, visible demonstration, files, commands/results, actual browser verification, provenance, screenshot paths if created, limitations, and next issue. Give the equivalent concise report for smaller completed scopes. Mark unexecuted checks as unexecuted. Do not report the full PoC complete while requested issues or mandatory gates remain unfinished.
