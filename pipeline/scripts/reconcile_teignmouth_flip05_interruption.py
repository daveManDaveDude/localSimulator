"""Write the missing aggregate for the consumed, interrupted flip-05 trial."""

from __future__ import annotations

import json
import runpy
from pathlib import Path
from typing import Any

from torquay_pipeline.road_surface_patch import (
    RoadSurfacePatchError,
    _protected_hash_snapshot,
    load_candidate_inputs,
)
from torquay_pipeline.road_surface_study_reconciliation import (
    reconcile_interrupted_flip_attempt,
)

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "pipeline/scripts/run_teignmouth_topology_study.py"
BASE_CONFIG_PATH = ROOT / "config/road-surface-teignmouth-candidate.json"


def _snapshot(runner: dict[str, Any]) -> tuple[dict[str, str], dict[str, str], str, str]:
    _study, study_digest, base_digest = runner["_load_frozen_configs"]()
    _config, inputs, _accepted, _preview = load_candidate_inputs(ROOT, BASE_CONFIG_PATH)
    protected = {
        **_protected_hash_snapshot(ROOT, inputs),
        **runner["_frozen_study_input_hashes"](ROOT),
    }
    code_hashes = runner["_code_hashes"](ROOT)
    return protected, code_hashes, study_digest, base_digest


def main() -> int:
    runner = runpy.run_path(str(RUNNER_PATH))
    before, code_before, study_before, base_before = _snapshot(runner)
    after, code_after, study_after, base_after = _snapshot(runner)
    if before != after or code_before != code_after:
        raise RoadSurfacePatchError(
            "protected files or implementation changed during interruption recovery"
        )
    if study_before != study_after or base_before != base_after:
        raise RoadSurfacePatchError("frozen configs changed during interruption recovery")
    report = reconcile_interrupted_flip_attempt(
        ROOT,
        protected_after=after,
        code_hashes_after=code_after,
        current_study_config_sha256=study_after,
        current_base_config_sha256=base_after,
    )
    result = {
        "trialId": report["trialId"],
        "passes": report["passes"],
        "finalClassification": report["finalClassification"],
        "solverConverged": report["solver"]["converged"],
        "solverIterations": report["solver"]["iterations"],
        "maximumConstraintResidualM": report["solver"]["maximumConstraintResidualM"],
        "inputSnapshotBeforeSha256": report["inputSnapshotSha256"],
        "inputSnapshotAfterSha256": report["postInterruptionInputSnapshotSha256"],
        "changedProtectedEntries": report["protectedHashDifferences"],
        "codeHashesMatch": report["codeUnchangedDuringTrial"],
        "candidateOutputStillAbsent": report["candidateOutputStillAbsent"],
        "aggregatePath": ".codex/evidence/teignmouth-topology-study/flip-05/offline-aggregate.json",
    }
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RoadSurfacePatchError as exc:
        print(json.dumps({"passes": False, "error": str(exc)}, sort_keys=True))
        raise SystemExit(2) from exc
