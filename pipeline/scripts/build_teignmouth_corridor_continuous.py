"""Single authorized build 2; no diagnostic, retries, public output or byte caps."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import threading
import time
import traceback
from pathlib import Path


def write_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    started = time.perf_counter()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    evidence = args.evidence.resolve()
    expected = root / "docs/milestones/artifacts/Teignmouth-corridor-prototype/correction-1/build-2"
    if evidence != expected.resolve() or evidence.exists():
        raise ValueError("build 2 requires its fresh fixed evidence directory; retries prohibited")
    evidence.mkdir(parents=True)
    write_json(
        evidence / "attempt.json",
        {"diagnosticsConsumed": 1, "buildOrdinal": 2, "correctionOrdinal": 1, "limitSeconds": 180},
    )

    def timeout() -> None:
        write_json(evidence / "timeout.json", {"status": "STOP", "reason": "180s build 2 deadline"})
        os._exit(124)

    watchdog = threading.Timer(max(0.001, 180.0 - (time.perf_counter() - started)), timeout)
    watchdog.daemon = True
    watchdog.start()
    try:
        from build_teignmouth_corridor_prototype import peak_working_set, protected_snapshot

        def snapshot():
            result = protected_snapshot(root)
            old = root / "docs/milestones/artifacts/Teignmouth-corridor-prototype"
            for path in old.rglob("*"):
                if path.is_file() and not path.is_relative_to(old / "correction-1"):
                    with path.open("rb") as stream:
                        result[path.relative_to(root).as_posix()] = hashlib.file_digest(
                            stream, "sha256"
                        ).hexdigest()
            return result

        before = snapshot()
        write_json(evidence / "preservation-before.json", before)
        from torquay_pipeline.teignmouth_corridor_continuous import build_corrected

        try:
            report = build_corrected(root, evidence)
        except Exception as exc:
            report = {
                "status": "STOP",
                "stopReasons": [f"{type(exc).__name__}: {exc}"],
                "traceback": traceback.format_exc(),
                "geometryVerdict": "not reached",
            }
        after = snapshot()
        changed = [name for name, digest in before.items() if after.get(name) != digest]
        report["preservation"] = {
            "passes": not changed,
            "comparedPaths": len(before),
            "changedPaths": changed,
            "scope": (
                "repository/public packages and original prototype evidence; "
                "raw GIS not fully rehashed"
            ),
        }
        if changed:
            report["status"] = "STOP"
            report.setdefault("stopReasons", []).append("protected-byte change")
        report["resources"] = {
            "wallSeconds": time.perf_counter() - started,
            "peakWorkingSetBytes": peak_working_set(),
            "wallLimitSeconds": 180,
            "buildOrdinal": 2,
            "correctionOrdinal": 1,
        }
        report["determinismLimitation"] = (
            "Only one corrected full build; not an independent second build of this algorithm."
        )
        write_json(evidence / "preservation-after.json", after)
        write_json(evidence / "report.json", report)
        print(
            json.dumps(
                {
                    key: report.get(key)
                    for key in (
                        "status",
                        "stopReasons",
                        "necessaryEarthworkPreflight",
                        "ownership",
                        "finalSafety",
                        "resources",
                    )
                }
            )
        )
        return 0 if report["status"] == "GEOMETRY_READY" else 2
    finally:
        watchdog.cancel()


if __name__ == "__main__":
    raise SystemExit(main())
