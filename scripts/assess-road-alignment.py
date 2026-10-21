"""Run the read-only current-2km road alignment diagnostic."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))

from torquay_pipeline.road_alignment import RoadAlignmentError, run_assessment


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare current 2 km OSM road coordinates, estimated ribbon surfaces, "
            "terrain profiles, and registered OS map context without changing GIS inputs."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/milestones/artifacts/Road-alignment"),
        help="must be the dedicated docs/milestones/artifacts/Road-alignment directory",
    )
    args = parser.parse_args()
    try:
        result = run_assessment(PROJECT_ROOT, args.output_dir)
    except (RoadAlignmentError, OSError, ValueError) as exc:
        print(f"road alignment assessment failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
