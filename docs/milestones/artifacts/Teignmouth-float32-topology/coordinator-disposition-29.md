# Coordinator disposition 29 — authorize replacement-supervision planning only

Date: 2026-10-24

**Decision: GO for one Sol planning document only, responding to the user's “Continue” after being offered a new bounded plan for the remaining supervisor blockers. This does not authorize another implementation correction, a self-check, runtime preflight, diagnostic or candidate build.**

Current failure basis: independent supervisor review 15, `build-3/independent-supervisor-review-2.md`, SHA-256 `d3a436805fe736f5096b16a5fca44bb5b5e2981157badd795c05a5b51e60db91`. The single operational-preparation correction remains consumed and failed; disposition 28 remains immutable.

Prepare a read-only replacement-supervision plan that addresses the review-15 blockers without assuming the current venv launcher PID is the executed Python process. Use and cite the official CPython Windows `venvlauncher.c` source (`https://github.com/python/cpython/blob/main/PC/venvlauncher.c`), which documents the redirector behavior and its base-interpreter child launch. Assess a directly contained base interpreter with a reviewed bootstrap/site-package contract versus any other fixed design that preserves the approved venv runtime identity and full installed dependency closure. Do not change the approved interpreter/runtime in the plan without documenting its consequences and the required separate runtime-identity review.

The plan must cover the PowerShell syntax/launch defects, per-mode one-use handoff names, actual parent/child PID and creation-identity evidence, truthful telemetry, durable early caller records, reservation snapshot/control-record sequencing, and exact implementation file scope. Preserve all time ceilings (180 s total, 150 s numerical, 10 s self-check, 30 s standalone preflight), fail-closed process containment, every candidate gate/limit and all counters. State concrete files, static checks, independent review criteria, later execution gates and a stop condition if no safe design exists.

No source/code/metadata aside from the planning artifact may change during this planning-only authorization. Do not execute/import scripts, run a parser/compiler, self-check, runtime preflight, build, diagnostic, GIS load or browser. Do not reset, extend, transfer, or rename any candidate or operational attempt budget. If the plan recommends implementation, it must return to the coordinator for a distinct future disposition; this disposition is not implementation permission.

## Unchanged candidate counters and status

- Diagnostics 2/2, candidate Luna corrections 4/4, candidate Sol correction 1/1.
- Candidate implementation builds 2/6 used, zero reserved; independent confirmation 0/1 and ineligible.
- The one dispatch-preparation correction remains consumed and FIX REQUIRED. This planning document creates no correction/build/diagnostic allowance.
- Candidate remains NO-GO and unservable; build 3 remains unreserved.
