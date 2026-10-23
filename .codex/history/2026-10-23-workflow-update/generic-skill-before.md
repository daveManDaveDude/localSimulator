---
name: spec-implementation-orchestrator
description: Implement a task specification item by item through separate planning, implementation, and independent review agents, with review failures returned for fixes. Use when the user wants work carried out from a spec or task document.
---

# Specification implementation orchestrator

Use this workflow when the user asks you to implement work listed in a specification or task document. Complete one item at a time, with a written plan, implementation, and independent review before moving to the next item. Preserve the requested scope; do not introduce features that the specification does not call for.

## Model assignments

Use the model IDs exposed by the Codex host:

- **Orchestrator:** `gpt-6-luna`, medium reasoning.
- **Planner:** `gpt-6.1-sol`, medium reasoning.
- **Implementer:** `gpt-6-luna`, xhigh reasoning.
- **Reviewer:** `gpt-6.1-sol`, medium reasoning.
- **Escalated implementer:** `gpt-6.1-sol`, medium reasoning.

“Luna 6.0” in the user's request maps to `gpt-6-luna`; “Sol 6.1” maps to `gpt-6.1-sol`. Do not silently substitute another model if either ID or reasoning level is unavailable. Report the unavailable assignment and ask the user how to proceed.

A skill cannot change the model of the conversation that invokes it. Therefore, the invoking agent acts only as a launcher: it starts one `gpt-6-luna` agent as the authoritative orchestrator, giving it the user's request, the specification path, relevant conversation context, and this skill's location. That Luna agent runs the complete workflow below. Do not spawn another orchestrator from inside it. If the required orchestrator cannot be started, stop and explain the model limitation.

## Workflow

1. **Read and order the specification.** The Luna orchestrator reads the whole supplied document, extracts its actionable items without changing their intent, and identifies dependencies. Work in specification order, respecting dependencies. If an item is ambiguous, ask the user only when the answer materially changes implementation; continue independent items while waiting when safe.

2. **Plan one item.** Use a `gpt-6.1-sol` planner at medium reasoning. Reuse a compatible completed planner from the role roster with `followup_task` when possible; spawn a new planner only when none is available and agent capacity allows it. Supply the exact item and relevant surrounding requirements, the current repository state, and the requirement to return:
   - a concise interpretation and scope boundary;
   - affected areas/files and likely risks;
   - an ordered implementation approach;
   - concrete, observable acceptance criteria and the checks needed to verify them.

   The orchestrator checks that the plan matches the specification and does not add unrelated work. Resolve omissions with the planner before implementation.

3. **Implement the accepted plan.** Use a `gpt-6-luna` implementer at xhigh reasoning. Reuse a compatible completed implementer from the role roster with `followup_task` when possible; spawn a new implementer only when none is available and agent capacity allows it. Provide the full item context, accepted plan, acceptance criteria, repository context, and relevant prior review comments. Ask it to make the change, run the appropriate checks, and report changed files, results, and remaining limitations. Do not start the reviewer until the implementation agent has finished and its changes are visible.

4. **Review independently.** Use a `gpt-6.1-sol` reviewer at medium reasoning that is separate from the current item's implementer. Reuse a compatible completed reviewer from the role roster with `followup_task` when possible; spawn a new reviewer only when none is available and agent capacity allows it. A planner may serve as reviewer if no reviewer-only agent is available, provided it did not implement the item; ask it to re-check the plan against the original specification rather than defend its own plan. Never assign the current item's implementer to review its own changes. Provide the original item, accepted plan, acceptance criteria, implementation diff, and test results. The reviewer must inspect the actual changes against those requirements and report either:
   - **PASS**, with evidence for each criterion and any residual limitations; or
   - **FIX REQUIRED**, with specific defects, missed criteria, and actionable corrections.

   Keep the reviewer independent: do not ask the implementer to review its own work, and do not present the implementer's summary as proof that a criterion passed. A criterion that could not be checked must be marked unverified; it cannot support PASS when it is necessary to the item.

5. **Return failures and escalate after three rejected rounds.** On **FIX REQUIRED**, send the reviewer’s actionable findings to the current implementer and ask it to correct the item. Re-review the resulting diff with an independent reviewer before continuing. Count one round each time a reviewer returns FIX REQUIRED; do not count planning or a passing review.

   After three rejected review rounds for the same item, assign the next correction to a distinct `gpt-6.1-sol` implementer at medium reasoning. Reuse an existing compatible agent with `followup_task` if needed, but do not use the current reviewer to implement the correction because that agent must independently review it. Have a separate `gpt-6.1-sol` reviewer inspect the correction. Continue the fix/review cycle with the Sol implementer until the item passes or a real blocker requires the user's decision. Keep the full review history and round count with that item.

6. **Advance only on PASS.** Record the item as complete only after review passes. Then plan the next specification item. If a review exposes a contradiction in the specification or a need to change scope, pause that item and ask the user rather than inventing a requirement.

7. **Report completion.** Summarize implemented items, important decisions, checks and results, and anything left blocked or unverified. Link relevant changed files. Do not claim all items passed if any remain incomplete.

## Long-running plans and resume

- When the user asks to complete a multi-item plan or all phases, treat that as one continuing objective. After an item passes review, proceed to the next item in specification order without asking whether to continue. A phase boundary is not a stopping point unless the specification or user explicitly makes it one.
- For a multi-phase task, an explicit request to finish all items, or work likely to span sessions, maintain a durable checkpoint in addition to chat context. Use `<workspace>/.codex/spec-implementation-orchestrator/<spec-stem>.md`; if that path already belongs to a different task, inspect it and choose a distinct filename. Put the exact absolute spec path and workspace path at the top so a later session can identify it. Do not overwrite an unrelated file or change ignore rules to hide the checkpoint. If the workspace cannot hold the checkpoint, use a sidecar next to the specification and record that location in the active task.
- The top-level orchestrator must remain responsible for the whole requested objective: launching a delegated orchestrator does not end the caller's responsibility. Track that agent with the available wait/status tools and continue coordinating until the requested plan is complete or a genuine blocker requires user input.
- The checkpoint is a concise audit trail, not an authority to claim completion. Keep a single authoritative **Current state and next action** section near the top containing the phase/item, stage, last independent verdict, delegated role/task status, blocker (if any), and one concrete next action. Rewrite this section in place whenever state changes; never append a newer competing next-action section. Keep detailed plans, evidence, and review rounds in a separate history section. Retire superseded operational notes or label them clearly as history. Capture reviewer conclusions yourself rather than relying on agent history remaining accessible. Avoid copying large logs or secrets into it.
- Update the checkpoint after planning, implementation, each review/fix round, and before any pause or phase transition. After updating, read back the current-state section and verify it matches the actual working tree, evidence, and agent status. Do not report a checkpoint update as complete until that reconciliation succeeds. If work changes while a delegated agent is running, mark that status explicitly and reconcile again when its turn completes.
- When a task starts or resumes, locate the checkpoint from the workspace/spec path before asking the user for a handoff. Inspect the working tree, evidence, and available agent/task results; reconcile the authoritative current state with reality. Reuse valid PASS reviews; do not redo passed work without a concrete regression. Never infer PASS from an implementer's report alone. If no checkpoint exists, reconstruct one from the spec, current files, and available task history, then continue from the earliest item without an independent PASS. Ask only if multiple plausible task states or an unresolved scope decision materially changes the next action.
- Treat "continue" or an equivalent request in a fresh, active Codex task as authorization to resume from the checkpoint and proceed through the remaining items. Do not require the user to recreate a handoff prompt, stop at phase boundaries, or ask whether to continue. An intervening status question does not replace or cancel the ongoing objective; answer it briefly, then resume.
- If a runtime or context limit is approaching, checkpoint the exact next action while the workspace is available and complete safe independent verification. If agent capacity is the issue, exhaust the documented reuse/follow-up options before pausing. Do not stop merely to produce a handoff prompt when the current host can continue. If a genuine host shutdown ends the task, leave the verified checkpoint and report the minimal resume instruction. Be explicit that a skill cannot wake a stopped host, create a new Codex task, or execute after the host ends; only a future user/app action or explicitly configured app-level automation can restart execution. Do not create an automation unless the user requests that behavior. Do not describe the overall plan as complete while items or gates remain.

## Coordination rules

- Keep delegation serial: finish planning before implementation, finish implementation before review, and finish review before the next item. Agents share the workspace, so do not run concurrent edits to the same task.
- Give each agent the minimum context needed to perform its assigned role, along with the source requirement and acceptance criteria. The reviewer receives the actual diff and test evidence.
- Keep work inside the user's authorized repository and task scope. Do not commit, publish, deploy, or make unrelated external changes unless the user or specification explicitly authorizes that action.
- Run checks appropriate to the change. If a required check is unavailable, report that limitation clearly; do not convert an unverified criterion into a pass.
- If the same unclear requirement, environment failure, or external dependency prevents meaningful progress, describe the blocker and ask the user for the missing decision rather than cycling agents without new evidence.

## Agent thread lifecycle

- Agent controls vary by client. Inspect the available controls instead of assuming that completed agent threads can be closed.
- Keep a small reusable role roster across a multi-item task. When an agent completes its turn but remains available, use `followup_task` to assign it another turn rather than spawning another identity just to obtain a fresh thread. Supply the full current item context and ask the agent to focus on that assignment. Prefer keeping planner, implementer, and reviewer roles separate.
- Independence is an item-level constraint: the reviewer must be a different agent from that item's implementer. An agent may review multiple items, and an agent may implement multiple items, provided the reviewer and implementer are distinct for every item. A planner may review an item if it did not implement that item; it must independently check both the implementation against the spec and any gaps in its prior plan. Never use the current item's implementer as its reviewer.
- Before spawning, inspect the agent list and reuse a compatible completed agent with `followup_task` when possible. Spawn a fresh role agent when needed and capacity is available. If spawning returns `agent thread limit reached`, try a compatible existing agent with `followup_task` before retrying a spawn. Do not archive user-facing Codex tasks or alter unrelated threads to free agent capacity.
- Do not treat `interrupt_agent` as a close operation: it stops the current turn but leaves the agent available for follow-up. If the client exposes no close operation, that alone is not a blocker; reuse a compatible agent. If no compatible non-implementer agent can provide the required independent review and the client has no supported close operation or available capacity, stop before the reviewer role. Preserve the current item's plan, diff, test evidence, and review history in a concise handoff. Do not mark the item passed or advance. Report the exact missing role and the unavailable lifecycle/capacity control to the user.
