# Two S E501 wraps — plan only

2026-10-25. Issue `Teignmouth-float32-topology-representation-1`; D139. **Propose only two parenthesized exception-call wraps.** No source edit or check was run. Required pre-edit S binding: `96daa955ce2ebe7a6315c000c99f174189d26bcf8941684541703ef688d921c7`; this planning turn inspected the two current source excerpts but did not rerun its hash/check gates.

File: `pipeline/scripts/run_teignmouth_float32_build3.py`. Both lines are in the already authorized self-check tree replacement region of D134/v2, inside its local containment closure. Replace pinned line4148:

```python
                    raise TimeoutError("tree containment census started at/after containment deadline")
```

with:

```python
                    raise TimeoutError(
                        "tree containment census started at/after containment deadline"
                    )
```

Replace pinned line4173 (line4175 after the preceding wrap):

```python
                    raise TimeoutError("tree containment census returned at/after containment deadline")
```

with:

```python
                    raise TimeoutError(
                        "tree containment census returned at/after containment deadline"
                    )
```

The resulting longest lines are at most88 columns, within the reported Ruff line-length constraint. Exception types and complete message strings remain identical; only whitespace/newlines inside the calls change. No string concatenation, message edit, pragma, formatter-driven unrelated change or new statement is proposed. Immediate last-error capture, strict census checks, control flow, clock/deadline/reserve/count/proof bounds, primary-error behavior, cleanup, default callers, path literals and output schema remain unchanged.

## Later authorized verification

After coordinator release only, first bind actual pre-edit S to the required hash; drift or a non-exact target line is a stop. Implement just these two spans. Record a tight byte diff/final hash; reverse these two wraps **in memory** and require exact restoration to `96daa955…`. Then apply the already bound two-region inverse, with the proven A-end/B-end LF ownership, and require accepted baseline `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff`,232527 bytes. No source restoration/normalization or reconstructed-file execution.

Required reruns after separate release:

- Existing pipeline-venv Ruff check and Ruff format-check for S only; record exact commands/results and preliminary E501 failures. A formatting failure is a stop; do not broaden this plan automatically.
- Unchanged W/H/P hashes and exact path/default/strict-capture/proof/cleanup inspection; six protected source/config/test hashes.
- Read-only full filename/count/hash comparison of all70 immutable evidence files (53 original/retry1–5 plus17 retry6), using the accepted matrices, without consumed evidence-content diagnosis or edits.
- Independent actual-byte review against D134/v2 and this two-wrap scope. No implementation/runtime acceptance follows from a formatting PASS alone.

If the source binding drifts, either wrap still fails the configured checks, or a wider edit is needed, stop for coordinator decision. Do not edit configuration, reformat other regions, change any error text or relax a gate. No tests/imports/parsers/compiler, process inspection, path/root/retry7 work, runtime/self-check/preflight/build or invocation is proposed. Current S remains unreviewed at the stated expected binding; consumed retry1–6 evidence/counters remain unchanged, candidate NO-GO/unservable and build3 unreserved. Stop after this plan for coordinator decision.
