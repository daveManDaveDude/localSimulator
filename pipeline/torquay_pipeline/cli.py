"""Command-line interface for validating and selecting the TVW-006 candidate AOI."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pyproj.network import is_network_enabled

from .aoi import generate_selection, write_selection
from .config import AoiConfigError, load_aoi_config


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="torquay-aoi", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate-aoi", "select-aoi"):
        command = commands.add_parser(name)
        command.add_argument("--config", type=Path, required=True, help="editable AOI JSON config")
        if name == "select-aoi":
            command.add_argument(
                "--output-dir",
                type=Path,
                default=Path("../docs"),
                help="directory for aoi-selection.{json,geojson,md} (default: ../docs)",
            )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = load_aoi_config(args.config)
        selection, geojson, markdown = generate_selection(config)
        if is_network_enabled():
            raise RuntimeError("PROJ network access unexpectedly remained enabled")
        if args.command == "validate-aoi":
            print(json.dumps(selection, ensure_ascii=False, indent=2, allow_nan=False))
            print("AOI config valid; candidate coverage remains not_checked.", file=sys.stderr)
            return 0
        write_selection(args.output_dir, selection, geojson, markdown, args.config)
        print(f"Wrote candidate selection outputs to {args.output_dir.resolve()}")
        print("selection_status=selected_pending_coverage; coverage_status=not_checked")
        return 0
    except (AoiConfigError, ValueError, OSError, RuntimeError) as exc:
        print(f"torquay-aoi: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
