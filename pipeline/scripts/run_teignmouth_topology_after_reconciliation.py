"""Run a later registered trial after the verified checkpoint-only transition."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
import sys
from pathlib import Path
from typing import Any

from torquay_pipeline.road_surface_patch import RoadSurfacePatchError
from torquay_pipeline.road_surface_study import TRIAL_ORDER
from torquay_pipeline.road_surface_study_reconciliation import (
    validate_reconciled_stage_order,
)

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "pipeline/scripts/run_teignmouth_topology_study.py"
STUDY_CONFIG_PATH = ROOT / "config/road-surface-teignmouth-topology-study.json"
RECONCILIATION_MODULE = "pipeline/torquay_pipeline/road_surface_study_reconciliation.py"
THIS_RUNNER = "pipeline/scripts/run_teignmouth_topology_after_reconciliation.py"
THIS_TEST = "pipeline/tests/test_road_surface_study_reconciliation.py"


def _digest_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _patch_runner(runner: dict[str, Any]) -> None:
    # runpy.run_path returns a namespace mapping separate from the globals used
    # by its function objects, so patch the live function namespace.
    namespace = runner["run_one_trial"].__globals__
    base_validator = namespace["validate_study_stage_order"]
    original_code_hashes = namespace["_code_hashes"]

    def stage_validator(
        raw_root: Path,
        trial_id: str,
        *,
        expected_study_config_sha256: str | None = None,
        expected_input_snapshot_sha256: str | None = None,
        expected_code_hashes: dict[str, str] | None = None,
    ) -> None:
        validate_reconciled_stage_order(
            raw_root,
            trial_id,
            expected_study_config_sha256=expected_study_config_sha256,
            expected_input_snapshot_sha256=expected_input_snapshot_sha256,
            expected_code_hashes=expected_code_hashes,
            base_validator=base_validator,
        )

    def code_hashes(root: Path) -> dict[str, str]:
        result = original_code_hashes(root)
        for relative in (RECONCILIATION_MODULE, THIS_RUNNER, THIS_TEST):
            path = root / relative
            runner["road_surface"]._assert_no_reparse_components(path)
            result[relative] = _digest_path(path)
        return result

    namespace["validate_study_stage_order"] = stage_validator
    namespace["_code_hashes"] = code_hashes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--trial", required=True, choices=TRIAL_ORDER[1:])
    args = parser.parse_args()
    requested_config = args.config if args.config.is_absolute() else ROOT / args.config
    if os.path.normcase(str(requested_config.resolve(strict=False))) != os.path.normcase(
        str(STUDY_CONFIG_PATH.resolve(strict=True))
    ):
        raise RoadSurfacePatchError("--config must name the exact frozen topology-study config")
    runner = runpy.run_path(str(RUNNER_PATH))
    _patch_runner(runner)
    status, _aggregate = runner["run_one_trial"](args.trial)
    return status


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RoadSurfacePatchError as exc:
        print(
            json.dumps({"passes": False, "error": str(exc)}, sort_keys=True),
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
