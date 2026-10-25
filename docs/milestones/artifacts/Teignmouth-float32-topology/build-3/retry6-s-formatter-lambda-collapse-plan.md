# S sample callback formatter request — diagnosis and plan only

2026-10-25. Issue `Teignmouth-float32-topology-representation-1`; D142. **One exact formatting-only replacement is sufficient for the reported diff.** No source edit or Ruff command was run. Stop for separate independent Sol plan review and coordinator decision.

## Exact observed binding and scope

Current `pipeline/scripts/run_teignmouth_float32_build3.py` independently hashes to **`7a1c38fe72ea274777538135154200c03cd5de8eeb6f4cd3d8d0b89b169228cc`**,239775 bytes, matching D142. The exact target occurs once, at current lines4200–4202, in the D134/v2-authorized self-check tree wait replacement block. It is the optional sampling callback argument of the existing `_wait_process` call, before the periodic containment callback. No drift or need for a broader edit was found in this targeted diagnosis.

D141 reports Ruff check passed and format-check failed with this one requested collapse; the preservation gate did not run. Those are prior reported results, not checks repeated here. The accepted E501 plan/review remain bound to `5a1eec1464cabbc962b5d79ef07e8987c5a668665139834f461afb704f86ae3a` / `52a4725ae556f69d59d05be02e08c2224ea346e70b2c9023bd12afbe1cc505b5`.

## Exact proposed edit

Replace only:

```python
                lambda: _sample_job(
                    kernel, psapi, job, tree["pid"], containment_deadline
                ),
```

with:

```python
                lambda: _sample_job(kernel, psapi, job, tree["pid"], containment_deadline),
```

The proposed entire line, including16 leading spaces, is **91 columns**. The configured Ruff limit is100, established by the authorized E501 independent review; this planning turn did not reread unrelated configuration. Width arithmetic is not a formatter PASS.

Both forms create the same zero-argument lambda, defer the same `_sample_job` invocation, and pass exactly `kernel`, `psapi`, `job`, `tree["pid"]` and `containment_deadline`, in the same order, with the same surrounding argument comma. Only whitespace/newlines within the call change. No eager call, changed capture, new argument, control-flow change or callback reordering is proposed. The existing two E501 exception wraps, strict immediate last-error capture, default call paths, three-second horizon, containment/cleanup reserve, proof/count bounds, output schema, marker/identity/Job/termination checks, path literals and W/H/P remain unchanged. Following lines shift by minus2; future edits must use exact text, not line numbers alone.

## Required future inverse and gates

Only after a separate implementation release:

1. Bind pre-edit S to `7a1c38fe…`,239775 bytes; require the exact target once. Replace only that span and record actual final hash plus tight byte diff. Reverse only the collapse in memory to the exact original three-line bytes and require **`7a1c38fe72ea274777538135154200c03cd5de8eeb6f4cd3d8d0b89b169228cc` /239775**.
2. Reverse only the two already authorized E501 exception wraps and require **`96daa955ce2ebe7a6315c000c99f174189d26bcf8941684541703ef688d921c7` /239683**.
3. Apply D137's exact two-region inverse, with its proven one LF at A-end and one LF at B-end, and require **`1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff` /232527**. The D137 proof report is `e424848a43bc48503b04a5ec15da550506907dd12ff3169e0575508b41edadef`. No guessed separators, trim/normalization, source restoration or reconstructed-file execution.
4. Rerun only the separately released S Ruff check, then S Ruff format-check. Stop on either failure; do not broaden formatting or proceed to later gates after a required failure. Record exact commands/results and all preliminary E501/formatter failures.
5. After preceding gates pass, perform the expressly released read-only full70-file filename/count/hash preservation comparison and six protected source/config/test hash checks, plus unchanged W/H/P/path/default/strict-proof/cleanup bindings. No consumed evidence-content diagnosis or modification.
6. Obtain independent actual-byte implementation review against D134/v2, D137, the E501 plan and this single-span scope. Formatting success does not accept the broader implementation or authorize execution.

No inverse, preservation comparison or gate was executed in this planning turn. Any changed baseline, unexpected target/count, still-failing formatter or additional requested change is a stop for coordinator decision. Do not change configuration, suppress a rule, alter error text or automatically reformat other spans.

## Boundary

Only authorized non-consumed document/current-source reads, the current S binding/length, exact-occurrence and width arithmetic, and this plan artifact write occurred. No source/other-artifact edit, Ruff command including `--diff`, preservation gate, test/import/parser/compiler, process inspection, path/root work, runtime/self-check/preflight/build or consumed evidence read occurred. Current S stays frozen at `7a1c38fe…`. Retries1–6 remain consumed/immutable/non-PASS, counters unchanged, retry7 unselected/unreserved, candidate NO-GO/unservable and build3 unreserved. Stop for independent plan review/coordinator decision.
