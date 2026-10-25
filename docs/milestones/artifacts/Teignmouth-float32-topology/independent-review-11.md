# Independent Sol review 11 — diagnostic 2 saved evidence

Date: 2026-10-24. Reviewer: `/root/sol_review_face_diag`, independent non-implementing Sol session.

## Disposition

**Diagnostic evidence supports a per-fragment area-filter/accounting defect, with small clipping-arithmetic differences. It does not establish a source-partition gap, overlap or physical topology hole. Candidate serving remains NO-GO.**

The saved diagnostic reproduced the recorded face, outside clip and filtered-coverage failure. It is useful evidence for a separately reviewed, bounded correction proposal. The report's automatic `SOURCE_PARTITION_GAP_OR_OVERLAP` label is not supported by its explicit gap/overlap geometries. Do not treat exit zero or `COMPLETE_DIAGNOSTIC_OBSERVATION` as candidate acceptance.

## Reproduction and area accounting

Saved face 19669 uses vertex IDs 6359, 6361 and 51721. Its serialized local positions decode exactly to the saved world positions, with candidate Y agreeing across buffers. Full face area is **0.020639419555664062 m²**; expected outside-influence clip area is **1.1028883815799223e-12 m²**. Both equal the recorded build-2 values. Exact source extraction reports one target-way match among 1,044 features and no source break inside stations 140–155. The saved reconstruction uses the frozen default 35 m buffer and domain.

Only source triangles **894822 and 894823**, the two original triangles of cell row 447/column 411, intersect this face. The local query records four heightfield nodes, source triangle geometry/IDs/heights and boundary-neighbour enumeration. Their production-order positive clipped areas are:

| Source triangle | Positive area (m²) | Frozen <=1e-12 filter |
| --- | ---: | --- |
| 894822 | 9.50339172070107e-13 | discarded |
| 894823 | 1.5254924997951674e-13 | discarded |

Ordinary sum, `math.fsum` and discarded-positive-area sum are each **1.1028884220496237e-12 m²**. Filtered accumulated area is **0**, exactly reproducing the failure. Its signed coverage residual is **-1.1028883815799223e-12 m²**, outside the unchanged **1e-12 m²** tolerance. The inclusive filter discards both fragments before coverage and extrema accounting; the aggregate expected clip is larger than the per-fragment threshold. That mechanism directly explains this failure.

The production-fragment union area is **1.1028884220496235e-12 m²**. Expected clip minus that union is empty; union excess and symmetric difference have area **4.046970140728338e-20 m²**. Sum minus union is **2.0194839173657902e-28 m²**. These tiny nonzero arithmetic residuals must remain visible, but do not explain the approximately 1.1e-12 m² of coverage removed by the filter. This is evidence consistent with covered fragments disappearing from accounting, not an exact floating-point partition proof.

## Source coverage and clipping order

The union of the two original source triangles is the 4 m² square `[-178,-176] × [-106,-104]`. Its intersection with the expected clip has the exact reported expected area **1.1028883815799223e-12 m²**. The saved source-coverage gap is empty and positive-area pairwise source-overlap count is **0**.

Separately clipping each source triangle to the expected clip gives a summed area **1.1028884013354613e-12 m²**, exceeding the clipped source-union area by **1.9755539019577796e-20 m²**. The automatic classifier calls any positive value of this subtraction a source overlap (`diagnose_teignmouth_overlay_face.py:1336–1337`), before considering clipping order. Here, explicit pairwise overlap geometry reports no overlap. The positive subtraction is therefore not sufficient evidence of an indexed partition defect; it is consistent with operation-order/area arithmetic sensitivity.

Alternative-association fragment areas are **9.5033916772122e-13** and **1.5254923361424128e-13 m²**. Their union area is **1.1028884013354611e-12 m²**. Production versus alternative union symmetric-difference area is **2.0714162387705586e-20 m²**; per-source symmetric differences are also saved. Both associations leave each fragment individually below the filter threshold. Neither supplies evidence that changing association alone fixes the accounting defect. Preserve both constructions; do not choose whichever appears numerically preferable or change tolerances.

Seven polygon vertices were evaluated for candidate-minus-source plane extrema, including the discarded fragments. Saved signed extrema range from **-2.816597444166291e-7 m** to **-1.529312960713014e-7 m**; maximum absolute delta is **2.816597444166291e-7 m**. These are nonzero observations, not proof of exact source-plane zero or full candidate compliance. No zero-area contacts were reported for this query. The plane condition numbers and signed/absolute witnesses are retained in the report.

## Preservation, completion and telemetry

Frozen manifest SHA-256 remains `6e9b1b77b5451e40ea12be0787db3c025ff591d628a3fce7f99a55ea1c7e7b9e`. Saved runner pre/post and worker pre-run records each report **291** checked bindings, zero changes and preservation PASS. External supervisor pre/post records agree, include all **225** build-2 protected bindings and pin the same manifest. This review independently rehashed all **291** current bindings with zero mismatches. The invocation record and run-leaf supervisor mirror are byte-identical. Candidate output remains absent.

Worker status is `COMPLETE_DIAGNOSTIC_OBSERVATION`; actual worker exit and runner-chosen exit are **0**. The external supervisor records runner child exit **0**, termination confirmed, `RUNNER_EXITED`, no timeout and chosen outer exit **0**. Recorded worker time is **59.494137900008354 s**, runner elapsed **62.55960039998172 s**, external elapsed **63.26575180000509 s**, below 120 seconds. The saved outer-exit field is the supervisor's chosen value; these artifacts do not independently capture the supervisor's exit as observed by its own caller. Exit zero means the observation completed, not that a candidate gate passed.

The reported **4,927,488-byte** peak working set is sampled using `GetProcessMemoryInfo` on `Popen.pid` only (`diagnose_teignmouth_overlay_face.py:1624–1627`). It is not a process-tree peak. On Windows, the venv executable can be a redirector launching the base interpreter; `pyvenv.cfg` points to `C:\Python313\python.exe`. Sampling a launcher is a plausible explanation for the very small value. No saved process-tree census establishes that interpretation, so the numerical worker's true peak memory remains unverified. Do not present this number as complete numerical-workload memory or as evidence supporting a memory limit.

`report.json` retains `currentStage=source-fragment-enumeration` and `stageStatus=IN_PROGRESS` despite its final complete status. This is stale checkpoint metadata: the final report update does not replace those fields, while `progress.json` explicitly records `diagnostic-complete`, fragmentCount=2, and the process exits confirm completion. It weakens status-field consistency but does not imply a still-running worker. Preserve the original artifacts and annotate this limitation rather than rewriting evidence.

## Narrowest safe next action

Have Sol scope and independently review a prototype-local correction proposal for the remaining authorized Luna correction cycle, subject to coordinator reservation and the carried-forward issue budget. Positive-area fragments must contribute consistently to coverage and extrema; several individually subthreshold fragments must not disappear. Preserve the historical shared helper unless separately authorized. Retain fixed source, origin, domain, recipe, collision guards and every numeric limit.

The proposal should require focused regression coverage for this saved failure pattern, complete and empty overlays, genuinely missing coverage, genuine source overlaps and clipping-order arithmetic sensitivity. A positive sum-minus-union rounding residual alone must not be interpreted as proof of physical source overlap. Correct diagnostic labels/status bookkeeping and memory-telemetry scope only within separately authorized work; do not rerun this consumed diagnostic to polish its report. No correction, test or build is authorized by this review. No source-height, earthwork or exact source-plane-zero requirement is relaxed. Full candidate validation and any independent confirmation remain outstanding.

## Evidence and review boundary

Inspected the frozen plan/manifest/runtime record and saved `run-1/report.json`, `runner-report.json`, `progress.json`, `source-query.json`, `source-fragments.jsonl`, reconstruction records and preservation records, plus parent `invocation.json`, logs and relevant static harness code. Geometry/plane values above are saved observations, not independently recomputed geometry. No diagnostic, build, import, numerical reconstruction, test, browser run, product edit, candidate correction or ledger/checkpoint edit occurred. Only this explicitly requested review document was written. The review does not prove source completeness outside this one-face query or repair/accept the failed build-2 candidate.
