"""Fixed child entrypoint; never dispatches a solver, trial or publisher."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))


def main() -> int:
    from torquay_pipeline.road_surface_validation_process_v1 import worker_main

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, required=True)
    args = parser.parse_args()
    return worker_main(ROOT, args.scratch)


if __name__ == "__main__":
    raise SystemExit(main())
