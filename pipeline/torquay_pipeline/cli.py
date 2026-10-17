"""Offline CLI for AOI, terrain, and OSM building source/asset checks."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pyproj.network import is_network_enabled

from .aoi import generate_selection, write_selection
from .building_export import (
    BuildingExportError,
    build_building_package,
    validate_building_package,
)
from .building_heights import HeightPolicy
from .building_preview import render_building_preview
from .building_sources import (
    BuildingSourceError,
    inspect_building_source,
    verify_building_source,
)
from .buildings import BuildingConfig, BuildingImportError, import_osm_buildings
from .config import AoiConfig, AoiConfigError, load_aoi_config, validate_stored_selection
from .terrain_coverage import (
    DEFAULT_MISSING_THRESHOLD,
    CoverageResult,
    TerrainCoverageError,
    analyze_coverage,
    atomic_write_json,
)
from .terrain_export import TerrainExportError, build_terrain_package
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
    for name in ("inspect-sources", "preview-terrain", "build-terrain"):
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
        elif name == "preview-terrain":
            command.add_argument(
                "--output",
                type=Path,
                default=Path("../docs/milestones/screenshots/TVW-007-ea-dtm-preview.png"),
            )
        else:
            command.add_argument(
                "--package-dir",
                type=Path,
                default=Path("../public/worlds/torquay-poc-001"),
                help="ignored local browser package output directory",
            )
            command.add_argument(
                "--report",
                type=Path,
                default=Path("../docs/milestones/artifacts/TVW-008-qa.json"),
            )
            command.add_argument(
                "--preview",
                type=Path,
                default=Path("../docs/milestones/screenshots/TVW-008-terrain-preview.png"),
            )
    for name in (
        "inspect-building-source",
        "import-buildings",
        "validate-buildings",
        "preview-buildings",
    ):
        command = commands.add_parser(name)
        command.add_argument(
            "--config", type=Path, default=Path("../config/buildings.torquay.json")
        )
        command.add_argument(
            "--source-manifest", type=Path, default=Path("../data/source-manifest.json")
        )
        command.add_argument("--source", type=Path)
        if name in {"import-buildings", "validate-buildings", "preview-buildings"}:
            command.add_argument(
                "--aoi-config", type=Path, default=Path("../config/aoi.torquay.json")
            )
        if name == "import-buildings":
            command.add_argument(
                "--terrain-package", type=Path, default=Path("../public/worlds/torquay-poc-001")
            )
            command.add_argument(
                "--aoi-geojson", type=Path, default=Path("../docs/aoi-selection.geojson")
            )
        elif name in {"validate-buildings", "preview-buildings"}:
            command.add_argument(
                "--package", type=Path, default=Path("../data/generated/buildings/torquay-poc-001")
            )
        if name == "preview-buildings":
            command.add_argument(
                "--qa",
                type=Path,
                default=Path("../docs/milestones/artifacts/TVW-009-buildings-qa.json"),
            )
            command.add_argument(
                "--output",
                type=Path,
                default=Path("../docs/milestones/screenshots/TVW-009-buildings-preview.png"),
            )
    return parser


def _building_config(path: Path) -> tuple[BuildingConfig, Path, dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BuildingImportError(f"cannot read building config '{path}': {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BuildingImportError(f"building config '{path}' is invalid JSON: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("format_version") != 1:
        raise BuildingImportError("building config must be a JSON object with format_version=1")
    root = path.resolve().parent.parent
    height = raw.get("height_policy")
    if not isinstance(height, dict):
        raise BuildingImportError("height_policy must be a JSON object")
    try:
        config = BuildingConfig(
            acquisition_buffer_m=float(raw["acquisition_buffer_m"]),
            minimum_clipped_area_m2=float(raw["minimum_clipped_area_m2"]),
            height_policy=HeightPolicy(
                levels_to_metres=float(height["levels_to_metres"]),
                default_height_m=float(height["default_height_m"]),
                minimum_height_m=float(height["minimum_height_m"]),
                maximum_height_m=float(height["maximum_height_m"]),
            ),
        )
        config.validate()
        return config, root, raw
    except (KeyError, TypeError, ValueError) as exc:
        raise BuildingImportError(f"invalid building configuration: {exc}") from exc


def _root_path(root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    return candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()


def _write_bytes_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{path.name}.", suffix=".stage", dir=path.parent, delete=False
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            stage = Path(handle.name)
        os.replace(stage, path)
    except OSError as exc:
        raise OSError(f"cannot atomically write '{path}': {exc}") from exc


def _building_command(args: argparse.Namespace) -> int:
    height_config, root, raw_config = _building_config(args.config)
    default_source = _root_path(root, raw_config.get("source", {}).get("relative_path", ""))
    source_path = (args.source or default_source).resolve()
    source_manifest_path = args.source_manifest.resolve()
    if args.command == "inspect-building-source":
        observed = inspect_building_source(source_path)
        verified = verify_building_source(source_path, source_manifest_path)
        print(json.dumps({"source": observed, "manifestVerified": verified == observed}, indent=2))
        print("OSM source bytes and PBF metadata match the separate source-manifest namespace.")
        return 0
    if args.command == "validate-buildings":
        verify_building_source(source_path, source_manifest_path)
        result = validate_building_package(args.package.resolve())
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "preview-buildings":
        verify_building_source(source_path, source_manifest_path)
        package_status = validate_building_package(args.package.resolve())
        data = json.loads((args.package / "buildings.json").read_text(encoding="utf-8"))
        qa = json.loads(args.qa.read_text(encoding="utf-8"))
        content = render_building_preview(data["buildings"], qa)
        _write_bytes_atomic(args.output.resolve(), content)
        print(f"Regenerated QA map: {args.output.resolve()}")
        print(json.dumps(package_status, indent=2))
        return 0

    aoi_config = load_aoi_config(args.aoi_config)
    selection, _geojson, _markdown = generate_selection(aoi_config)
    validate_stored_selection(
        aoi_config,
        selection["aoi"]["center_easting_m"],
        selection["aoi"]["center_northing_m"],
        selection["aoi"]["bbox_m"],
    )
    imported = import_osm_buildings(source_path, source_manifest_path, aoi_config, height_config)
    path_config = {
        key: _root_path(root, raw_config[key])
        for key in ("intermediate_path", "package_path", "qa_path", "preview_path")
    }
    output = build_building_package(
        imported,
        aoi_config,
        source_path,
        source_manifest_path,
        args.terrain_package.resolve(),
        args.aoi_geojson.resolve(),
        path_config["package_path"],
        path_config["qa_path"],
        path_config["preview_path"],
        path_config["intermediate_path"],
    )
    counts = output["qa"]["counts"]
    print(
        f"Imported {counts['exported_buildings']} local buildings to {path_config['package_path']}"
    )
    print(f"Wrote QA: {path_config['qa_path']}")
    print(f"Wrote preview: {path_config['preview_path']}")
    print(f"Wrote raw-tag buffered intermediate: {path_config['intermediate_path']}")
    print(
        "AOI selection_status remains selected_pending_coverage; "
        "coverage_status remains not_checked."
    )
    return 0


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
        if is_network_enabled():
            raise RuntimeError("PROJ network access unexpectedly remained enabled")
        if args.command in {
            "inspect-building-source",
            "import-buildings",
            "validate-buildings",
            "preview-buildings",
        }:
            return _building_command(args)
        config = load_aoi_config(args.config)
        selection, geojson, markdown = generate_selection(config)
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
        if args.command == "build-terrain":
            config = _validated_selection_config(args.config)
            source_manifest, raster_paths, verified = _verified_sources(
                args.manifest, args.source_dir
            )
            coverage = analyze_coverage(config, raster_paths, args.missing_threshold)
            coverage_report = coverage.report
            if coverage_report["analysis"]["ea_dtm_threshold_result"] != "pass":
                raise TerrainExportError(
                    "EA DTM coverage did not meet the configured missing-cell threshold; "
                    "real browser terrain was not published"
                )
            built = build_terrain_package(
                config,
                raster_paths,
                source_manifest,
                verified,
                args.package_dir,
                args.report,
                args.preview,
            )
            print(f"Built verified local terrain package at {args.package_dir.resolve()}")
            print(
                f"Grid {built['qa']['outputGrid']['columns']} × "
                f"{built['qa']['outputGrid']['rows']} vertices; "
                f"source missing fraction {coverage_report['coverage']['missing_fraction']:.3%}."
            )
            print(
                f"Wrote deterministic QA to {args.report.resolve()} and preview to "
                f"{args.preview.resolve()}. AOI coverage_status remains not_checked."
            )
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
        BuildingExportError,
        BuildingImportError,
        BuildingSourceError,
        TerrainCoverageError,
        TerrainSourceError,
        TerrainExportError,
        ValueError,
        OSError,
        RuntimeError,
    ) as exc:
        print(f"torquay-aoi: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
