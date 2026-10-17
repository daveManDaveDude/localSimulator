"""Offline CLI for AOI checks and the TVW-007 EA DTM coverage inspection."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pyproj.network import is_network_enabled

from .aoi import generate_selection, write_selection
from .config import AoiConfig, AoiConfigError, load_aoi_config, validate_stored_selection
from .terrain_coverage import (
    DEFAULT_MISSING_THRESHOLD,
    CoverageResult,
    TerrainCoverageError,
    analyze_coverage,
    atomic_write_json,
)
from .terrain_preview import write_terrain_preview
from .terrain_sources import TerrainSourceError, verify_source_manifest


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
    for name in ("inspect-sources", "preview-terrain"):
        command = commands.add_parser(name)
        command.add_argument("--config", type=Path, default=Path("../config/aoi.torquay.json"))
        command.add_argument("--manifest", type=Path, default=Path("../data/source-manifest.json"))
        command.add_argument("--source-dir", type=Path, default=Path("../data/raw/ea_dtm"))
        command.add_argument(
            "--missing-threshold",
            type=float,
            default=DEFAULT_MISSING_THRESHOLD,
            help="maximum missing AOI-cell fraction (default: 0.01)",
        )
        if name == "inspect-sources":
            command.add_argument(
                "--report",
                type=Path,
                default=Path("../docs/milestones/artifacts/TVW-007-coverage.json"),
            )
        else:
            command.add_argument(
                "--output",
                type=Path,
                default=Path("../docs/milestones/screenshots/TVW-007-ea-dtm-preview.png"),
            )
    return parser


def _verified_sources(
    manifest_path: Path, source_dir: Path
) -> tuple[dict[str, Any], list[Path], list[dict[str, Any]]]:
    manifest, verified = verify_source_manifest(manifest_path, source_dir)
    records = manifest.get("sources")
    if not isinstance(records, list):
        raise TerrainSourceError("source manifest sources must be an array")
    paths: list[Path] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise TerrainSourceError(f"source manifest sources[{index}] must be an object")
        relative = record.get("raster_relative_path")
        if not isinstance(relative, str) or not relative:
            raise TerrainSourceError(
                f"source manifest sources[{index}].raster_relative_path is missing"
            )
        path = (source_dir / Path(relative)).resolve()
        try:
            path.relative_to(source_dir.resolve())
        except ValueError as exc:
            raise TerrainSourceError(
                f"source manifest sources[{index}].raster_relative_path escapes source directory"
            ) from exc
        paths.append(path)
    return manifest, paths, verified


def _validated_selection_config(config_path: Path) -> AoiConfig:
    config = load_aoi_config(config_path)
    selection, _geojson, _markdown = generate_selection(config)
    validate_stored_selection(
        config,
        selection["aoi"]["center_easting_m"],
        selection["aoi"]["center_northing_m"],
        selection["aoi"]["bbox_m"],
    )
    return config


def _coverage_report(
    config_path: Path, manifest_path: Path, source_dir: Path, threshold: float
) -> CoverageResult:
    config = _validated_selection_config(config_path)
    manifest, raster_paths, verified = _verified_sources(manifest_path, source_dir)
    result = analyze_coverage(config, raster_paths, threshold)
    records = manifest.get("sources", [])
    source_by_filename = {
        Path(record["raster_relative_path"]).name: record
        for record in records
        if isinstance(record, dict) and isinstance(record.get("raster_relative_path"), str)
    }
    verified_by_filename = {
        record["raster"]["filename"]: record
        for record in verified
        if isinstance(record.get("raster"), dict)
        and isinstance(record["raster"].get("filename"), str)
    }
    for source in result.report["sources"]:
        record = source_by_filename.get(source["filename"])
        if isinstance(record, dict):
            archive = record.get("archive", {})
            source.update(
                {
                    "tile_name": record.get("tile_name"),
                    "archive_filename": record.get("archive_filename"),
                    "download_url": record.get("download_url"),
                    "download_date": record.get("download_date"),
                    "archive_size_bytes": archive.get("size_bytes")
                    if isinstance(archive, dict)
                    else None,
                    "archive_sha256": archive.get("sha256") if isinstance(archive, dict) else None,
                }
            )
        actual = verified_by_filename.get(source["filename"])
        if isinstance(actual, dict):
            source["archive_metadata"] = actual.get("archive")
            source["raster_metadata"] = actual.get("raster")
            source["full_tile_measurements"] = actual.get("measured_full_tile")
    product = manifest.get("product", {})
    acquisition = manifest.get("acquisition", {})
    if isinstance(product, dict):
        result.report["product"] = {
            "name": product.get("name"),
            "publisher": product.get("publisher"),
            "licence": product.get("licence"),
            "attribution": product.get("attribution"),
            "vertical_reference": manifest.get("raster_contract", {}).get("vertical_reference")
            if isinstance(manifest.get("raster_contract"), dict)
            else None,
        }
    if isinstance(acquisition, dict):
        result.report["acquisition"] = {
            "download_date": acquisition.get("download_date"),
            "source_storage": acquisition.get("source_storage"),
        }
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = load_aoi_config(args.config)
        selection, geojson, markdown = generate_selection(config)
        if is_network_enabled():
            raise RuntimeError("PROJ network access unexpectedly remained enabled")
        if args.command == "validate-aoi":
            validate_stored_selection(
                config,
                selection["aoi"]["center_easting_m"],
                selection["aoi"]["center_northing_m"],
                selection["aoi"]["bbox_m"],
            )
            print(json.dumps(selection, ensure_ascii=False, indent=2, allow_nan=False))
            print("AOI config valid; candidate coverage remains not_checked.", file=sys.stderr)
            return 0
        if args.command == "select-aoi":
            write_selection(args.output_dir, selection, geojson, markdown, args.config)
            print(f"Wrote candidate selection outputs to {args.output_dir.resolve()}")
            print("selection_status=selected_pending_coverage; coverage_status=not_checked")
            return 0
        result = _coverage_report(
            args.config, args.manifest, args.source_dir, args.missing_threshold
        )
        if args.command == "inspect-sources":
            atomic_write_json(args.report, result.report)
            print(f"Wrote coverage report to {args.report.resolve()}")
        else:
            preview = write_terrain_preview(result, args.output)
            print(f"Wrote north-up DTM preview to {args.output.resolve()}")
            print(json.dumps(preview, indent=2))
        coverage = result.report["coverage"]
        print(
            f"DTM coverage {result.report['analysis']['ea_dtm_threshold_result']}: "
            f"{coverage['valid_cells']}/{result.report['analysis_grid']['cell_count']} valid; "
            f"{coverage['missing_cells']} missing ({coverage['missing_fraction']:.3%})."
        )
        print("AOI coverage_status remains not_checked until all M2 sources are reviewed.")
        return 0 if result.report["analysis"]["ea_dtm_threshold_result"] == "pass" else 2
    except (
        AoiConfigError,
        TerrainCoverageError,
        TerrainSourceError,
        ValueError,
        OSError,
        RuntimeError,
    ) as exc:
        print(f"torquay-aoi: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
