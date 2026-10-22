"""Build the ignored, source-bound road-surface display preview."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))

from torquay_pipeline.road_surface import RoadSurfaceError, build_preview, load_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--execution-record", type=Path)
    args = parser.parse_args()
    project_root = PROJECT_ROOT
    config_path = (
        args.config if args.config.is_absolute() else project_root / args.config
    )
    try:
        result = build_preview(
            project_root, load_config(config_path), args.execution_record
        )
    except (RoadSurfaceError, OSError, ValueError) as exc:
        print(f"road-surface preview build failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
