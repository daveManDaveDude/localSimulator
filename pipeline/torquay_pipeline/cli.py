"""Offline CLI for AOI, terrain, and OSM building source/asset checks."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pyproj.network import is_network_enabled
from shapely.geometry import Polygon
from shapely.ops import unary_union

from .alignment_report import (
    AlignmentReportError,
    build_alignment_artifacts,
    render_alignment_panels,
    validate_alignment_report,
)
from .aoi import generate_selection, write_selection
from .building_export import (
    BuildingExportError,
    _load_aoi_ring,
    build_building_package,
    validate_building_package,
)
from .building_heights import HeightPolicy
from .building_preview import render_building_preview
from .building_publish import BuildingPublishError, publish_building_package
from .building_sources import (
    BuildingSourceError,
    inspect_building_source,
    verify_building_source,
)
from .buildings import BuildingConfig, BuildingImportError, import_osm_buildings
from .comparison_sources import ComparisonSourceError, verify_comparison_source
from .config import AoiConfig, AoiConfigError, load_aoi_config, validate_stored_selection
from .elevation_index import (
    ElevationIndexError,
    assess_ea_resolution_index,
    capture_ea_resolution_index,
)
from .overview_export import (
    DEFAULT_AOI_CONFIG as DEFAULT_OVERVIEW_AOI_CONFIG,
)
from .overview_export import (
    DEFAULT_BUILDINGS_DIR as DEFAULT_OVERVIEW_BUILDINGS_DIR,
)
from .overview_export import (
    DEFAULT_OUTPUT_DIR as DEFAULT_OVERVIEW_OUTPUT_DIR,
)
from .overview_export import (
    DEFAULT_ROADS_DIR as DEFAULT_OVERVIEW_ROADS_DIR,
)
from .overview_export import (
    DEFAULT_SOURCE_MANIFEST as DEFAULT_OVERVIEW_SOURCE_MANIFEST,
)
from .overview_export import (
    DEFAULT_TERRAIN_DIR as DEFAULT_OVERVIEW_TERRAIN_DIR,
)
from .overview_export import (
    OverviewExportError,
    build_overview_package,
    validate_overview_package,
)
from .overview_publish import OverviewPublishError, publish_overview_package
from .road_config import RoadConfigError, load_road_config
from .road_export import RoadExportError, build_road_package, validate_road_package
from .road_geometry import DISPLAY_GROUPS
from .road_preview import render_road_preview
from .road_publish import RoadPublishError, publish_road_package
from .roads import RoadImportError, import_osm_roads
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

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _aoi_geojson_path(profile: str, override: Path | None) -> Path:
    """Select the frozen AOI ring matching a config profile unless overridden."""
    if override is not None:
        return override.resolve()
    if profile == "historical_1km":
        return PROJECT_ROOT / "docs/milestones/artifacts/AOI-1km-selection/aoi-selection.geojson"
    return PROJECT_ROOT / "docs/aoi-selection.geojson"


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
                default=Path("../docs/milestones/artifacts/AOI-2km-1m-coverage.json"),
            )
        elif name == "preview-terrain":
            command.add_argument(
                "--output",
                type=Path,
                default=Path("../docs/milestones/screenshots/AOI-2km-1m-preview.png"),
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
    capture_command = commands.add_parser(
        "capture-resolution-index",
        help="explicitly capture one bounded official EA WFS response for offline assessment",
    )
    capture_command.add_argument("--config", type=Path, default=Path("../config/aoi.torquay.json"))
    capture_command.add_argument(
        "--output-dir",
        type=Path,
        default=Path("../data/raw/ea_dtm_time_stamped_index/capture"),
        help="new local directory for the raw WFS response and provenance sidecar",
    )
    capture_command.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
        help="bounded request timeout (1–120 seconds; default 30)",
    )
    index_command = commands.add_parser(
        "assess-resolution-index",
        help="measure official EA time-stamped DTM index footprints (metadata only)",
    )
    index_command.add_argument("--config", type=Path, default=Path("../config/aoi.torquay.json"))
    index_command.add_argument(
        "--index",
        type=Path,
        default=Path("../data/elevation-index/ea-dtm-time-stamped-2km-2026-10-20.geojson"),
        help="saved official EA WFS FeatureCollection snapshot",
    )
    index_command.add_argument(
        "--source-metadata",
        type=Path,
        default=Path("../data/elevation-index/ea-dtm-time-stamped-2km-2026-10-20.source.json"),
        help="query, retrieval and snapshot integrity metadata",
    )
    index_command.add_argument(
        "--report",
        type=Path,
        default=Path("../docs/milestones/artifacts/AOI-2km-resolution-index.json"),
        help="deterministic assessment JSON output",
    )
    for name in (
        "inspect-building-source",
        "import-buildings",
        "validate-buildings",
        "preview-buildings",
        "publish-buildings",
    ):
        command = commands.add_parser(name)
        command.add_argument(
            "--config", type=Path, default=Path("../config/buildings.torquay.json")
        )
        command.add_argument(
            "--source-manifest", type=Path, default=Path("../data/source-manifest.json")
        )
        command.add_argument("--source", type=Path)
        if name in {
            "import-buildings",
            "validate-buildings",
            "preview-buildings",
            "publish-buildings",
        }:
            command.add_argument(
                "--aoi-config", type=Path, default=Path("../config/aoi.torquay.json")
            )
        if name == "import-buildings":
            command.add_argument(
                "--terrain-package", type=Path, default=Path("../public/worlds/torquay-poc-001")
            )
            command.add_argument("--aoi-geojson", type=Path)
        elif name in {"validate-buildings", "preview-buildings", "publish-buildings"}:
            command.add_argument(
                "--package", type=Path, default=Path("../data/generated/buildings/torquay-poc-001")
            )
            command.add_argument(
                "--terrain-package", type=Path, default=Path("../public/worlds/torquay-poc-001")
            )
            command.add_argument("--aoi-geojson", type=Path)
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
    for name in (
        "inspect-road-source",
        "import-roads",
        "validate-roads",
        "preview-roads",
        "publish-roads",
    ):
        command = commands.add_parser(name)
        command.add_argument("--config", type=Path, default=Path("../config/roads.torquay.json"))
        command.add_argument(
            "--source-manifest", type=Path, default=Path("../data/source-manifest.json")
        )
        command.add_argument("--source", type=Path)
        if name in {"import-roads", "validate-roads", "preview-roads", "publish-roads"}:
            command.add_argument(
                "--aoi-config", type=Path, default=Path("../config/aoi.torquay.json")
            )
            command.add_argument("--aoi-geojson", type=Path)
            command.add_argument(
                "--terrain-package", type=Path, default=Path("../public/worlds/torquay-poc-001")
            )
        if name in {"validate-roads", "preview-roads", "publish-roads"}:
            command.add_argument(
                "--package", type=Path, default=Path("../data/generated/roads/torquay-poc-001")
            )
        if name == "import-roads":
            command.add_argument("--output", type=Path, help="override generated package directory")
        if name == "preview-roads":
            command.add_argument(
                "--qa",
                type=Path,
                default=Path("../docs/milestones/artifacts/TVW-011-roads-qa.json"),
            )
            command.add_argument(
                "--output",
                type=Path,
                default=Path("../docs/milestones/screenshots/TVW-011-roads-preview.png"),
            )
    for name in ("build-overview", "validate-overview", "publish-overview"):
        command = commands.add_parser(
            name, help=f"{name.replace('-', ' ')} from validated local packages"
        )
        command.add_argument("--terrain-dir", type=Path, default=DEFAULT_OVERVIEW_TERRAIN_DIR)
        command.add_argument("--roads-dir", type=Path, default=DEFAULT_OVERVIEW_ROADS_DIR)
        command.add_argument("--buildings-dir", type=Path, default=DEFAULT_OVERVIEW_BUILDINGS_DIR)
        command.add_argument("--aoi-config", type=Path, default=DEFAULT_OVERVIEW_AOI_CONFIG)
        command.add_argument("--aoi-geojson", type=Path)
        command.add_argument(
            "--source-manifest", type=Path, default=DEFAULT_OVERVIEW_SOURCE_MANIFEST
        )
        if name == "build-overview":
            command.add_argument("--layers", default="aoi,roads,buildings")
            command.add_argument("--output-dir", type=Path, default=DEFAULT_OVERVIEW_OUTPUT_DIR)
        else:
            command.add_argument(
                "--package-dir", type=Path, default=Path("data/generated/overview")
            )
        if name == "publish-overview":
            command.add_argument(
                "--output-dir", type=Path, default=Path("public/worlds/torquay-poc-001/overview")
            )
    command = commands.add_parser(
        "inspect-comparison-source",
        help="verify the comparison-only OS archive, extracted members, and raster metadata",
    )
    command.add_argument(
        "--manifest", type=Path, default=Path("../data/comparison-source-manifest.json")
    )
    command.add_argument(
        "--source-root", type=Path, default=Path("../data/raw/comparison/os_openmap_local")
    )
    command = commands.add_parser(
        "compare-alignment",
        help="render registered comparison panels and, when browser evidence exists, report them",
    )
    command.add_argument("--config", type=Path, default=Path("../config/alignment.torquay.json"))
    command.add_argument(
        "--manifest", type=Path, default=Path("../data/comparison-source-manifest.json")
    )
    command.add_argument(
        "--source-root", type=Path, default=Path("../data/raw/comparison/os_openmap_local")
    )
    command.add_argument(
        "--terrain-package", type=Path, default=Path("../public/worlds/torquay-poc-001")
    )
    command.add_argument(
        "--road-package", type=Path, default=Path("../data/generated/roads/torquay-poc-001")
    )
    command.add_argument(
        "--building-package",
        type=Path,
        default=Path("../data/generated/buildings/torquay-poc-001"),
    )
    command.add_argument("--project-root", type=Path, default=Path(".."))
    command.add_argument(
        "--render-panels-only",
        action="store_true",
        help="generate the three static map panels without requiring browser screenshots",
    )
    command = commands.add_parser(
        "validate-alignment-report", help="validate report status and integrity-bound evidence"
    )
    command.add_argument(
        "--report", type=Path, default=Path("../docs/milestones/artifacts/TVW-012-alignment.json")
    )
    command.add_argument("--project-root", type=Path, default=Path(".."))
    return parser


def _alignment_command(args: argparse.Namespace) -> int:
    if args.command == "inspect-comparison-source":
        source = verify_comparison_source(args.manifest.resolve(), args.source_root.resolve())
        result = {
            "sourceId": source.record["sourceId"],
            "archive": {
                "path": str(source.archive_path),
                "byteLength": source.archive_path.stat().st_size,
                "sha256": source.record["archive"]["sha256"],
                "memberCount": source.record["archive"]["archiveMemberCount"],
            },
            "verifiedTiles": [tile.to_dict() for tile in source.tiles],
            "coversReviewedAoi": source.cover(
                (290608.9018176432, 64853.48350844931, 291608.9018176432, 65853.48350844931)
            ),
            "supportFiles": list(source.support_files),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "compare-alignment":
        common = (
            args.config.resolve(),
            args.manifest.resolve(),
            args.source_root.resolve(),
            args.terrain_package.resolve(),
            args.road_package.resolve(),
            args.building_package.resolve(),
            args.project_root.resolve(),
        )
        result = (
            render_alignment_panels(*common)
            if args.render_panels_only
            else build_alignment_artifacts(*common)
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
    except OSError as exc:
        raise AlignmentReportError(f"cannot read alignment report '{args.report}': {exc}") from exc
    except json.JSONDecodeError as exc:
        raise AlignmentReportError(
            f"alignment report '{args.report}' is invalid JSON: {exc}"
        ) from exc
    print(json.dumps(validate_alignment_report(report, args.project_root.resolve()), indent=2))
    return 0


def _road_command(args: argparse.Namespace) -> int:
    config, root, raw = load_road_config(args.config)
    source_path = (args.source or _root_path(root, config.source_relative_path)).resolve()
    source_manifest_path = args.source_manifest.resolve()
    if args.command == "inspect-road-source":
        observed = inspect_building_source(source_path)
        verified = verify_building_source(source_path, source_manifest_path)
        print(json.dumps({"source": observed, "manifestVerified": verified == observed}, indent=2))
        print("Road extraction reuses the recorded dated OSM PBF; it does not fetch a replacement.")
        return 0

    aoi_config = load_aoi_config(args.aoi_config)
    selection, _geojson, _markdown = generate_selection(aoi_config)
    validate_stored_selection(
        aoi_config,
        selection["aoi"]["center_easting_m"],
        selection["aoi"]["center_northing_m"],
        selection["aoi"]["bbox_m"],
    )
    aoi_geojson_path = _aoi_geojson_path(aoi_config.profile, args.aoi_geojson)
    expected_ring = _load_aoi_ring(aoi_geojson_path)
    terrain_path = args.terrain_package.resolve()
    if args.command == "validate-roads":
        result = validate_road_package(
            args.package.resolve(),
            expected_aoi=aoi_config,
            expected_aoi_ring=expected_ring,
            terrain_package_path=terrain_path,
            source_path=source_path,
            source_manifest_path=source_manifest_path,
            aoi_geojson_path=aoi_geojson_path,
            road_config=config,
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "publish-roads":
        result = publish_road_package(
            args.package.resolve(),
            terrain_path,
            expected_aoi=aoi_config,
            expected_aoi_ring=expected_ring,
            source_path=source_path,
            source_manifest_path=source_manifest_path,
            aoi_geojson_path=aoi_geojson_path,
            road_config=config,
        )
        print(f"Published byte-identical validated roads to {result['outputDirectory']}")
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "preview-roads":
        result = validate_road_package(
            args.package.resolve(),
            expected_aoi=aoi_config,
            expected_aoi_ring=expected_ring,
            terrain_package_path=terrain_path,
            source_path=source_path,
            source_manifest_path=source_manifest_path,
            aoi_geojson_path=aoi_geojson_path,
            road_config=config,
        )
        qa_bytes = (args.package / "qa.json").read_bytes()
        if qa_bytes != args.qa.read_bytes():
            raise RoadExportError("external QA differs from integrity-bound package qa.json")
        payload = json.loads((args.package / "roads.json").read_text(encoding="utf-8"))
        display: dict[str, Any] = {}
        for group in DISPLAY_GROUPS:
            batch = payload["surfaceBatches"][group]
            vertices = batch["verticesXZ"]
            polygons = [
                Polygon([vertices[index] for index in triangle]) for triangle in batch["indices"]
            ]
            display[group] = unary_union(polygons) if polygons else Polygon()
        preview = render_road_preview(
            display,
            payload["features"],
            json.loads(qa_bytes),
            terrain_path,
            args.output.resolve(),
        )
        print(json.dumps({"package": result, "preview": preview}, indent=2))
        return 0

    imported = import_osm_roads(source_path, source_manifest_path, aoi_config, config)
    output_dir = args.output.resolve() if args.output else _root_path(root, config.package_path)
    qa_path = _root_path(root, config.qa_path)
    preview_path = _root_path(root, config.preview_path)
    intermediate_path = _root_path(root, config.intermediate_path)
    built = build_road_package(
        imported,
        aoi_config,
        config,
        source_path,
        source_manifest_path,
        terrain_path,
        aoi_geojson_path,
        output_dir,
        qa_path,
        preview_path,
        intermediate_path,
    )
    print(f"Imported {built['qa']['counts']['uniqueExportedWays']:,} unique highway ways.")
    print(f"Road package: {output_dir}")
    print(f"QA: {qa_path}")
    print(f"Preview: {preview_path}")
    print(f"Intermediate with source node IDs and tags: {intermediate_path}")
    print("AOI remains selected_pending_coverage; coverage_status remains not_checked.")
    print(json.dumps(built["qa"]["counts"], indent=2))
    return 0


def _overview_command(args: argparse.Namespace) -> int:
    aoi_config_path = (
        args.aoi_config if args.aoi_config.is_absolute() else PROJECT_ROOT / args.aoi_config
    ).resolve()
    aoi_config = load_aoi_config(aoi_config_path)
    aoi_geojson_override = args.aoi_geojson
    if aoi_geojson_override is not None and not aoi_geojson_override.is_absolute():
        aoi_geojson_override = PROJECT_ROOT / aoi_geojson_override
    aoi_geojson_path = _aoi_geojson_path(aoi_config.profile, aoi_geojson_override)
    common = {
        "terrain_dir": args.terrain_dir,
        "roads_dir": args.roads_dir,
        "buildings_dir": args.buildings_dir,
        "aoi_config_path": aoi_config_path,
        "aoi_geojson_path": aoi_geojson_path,
        "source_manifest_path": args.source_manifest,
    }
    if args.command == "build-overview":
        layers = tuple(item.strip() for item in args.layers.split(",") if item.strip())
        result = build_overview_package(
            **common,
            layers=layers,
            output_dir=args.output_dir,
        )
    elif args.command == "validate-overview":
        result = validate_overview_package(args.package_dir, **common)
    else:
        result = publish_overview_package(
            args.package_dir,
            output_dir=args.output_dir,
            **common,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


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
            acquisition_buffer_m=_building_config_number(
                raw["acquisition_buffer_m"], "acquisition_buffer_m"
            ),
            minimum_clipped_area_m2=_building_config_number(
                raw["minimum_clipped_area_m2"], "minimum_clipped_area_m2"
            ),
            height_policy=HeightPolicy(
                levels_to_metres=_building_config_number(
                    height["levels_to_metres"], "height_policy.levels_to_metres"
                ),
                default_height_m=_building_config_number(
                    height["default_height_m"], "height_policy.default_height_m"
                ),
                minimum_height_m=_building_config_number(
                    height["minimum_height_m"], "height_policy.minimum_height_m"
                ),
                maximum_height_m=_building_config_number(
                    height["maximum_height_m"], "height_policy.maximum_height_m"
                ),
            ),
        )
        config.validate()
        return config, root, raw
    except (KeyError, TypeError, ValueError) as exc:
        raise BuildingImportError(f"invalid building configuration: {exc}") from exc


def _root_path(root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    return candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()


def _building_config_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BuildingImportError(
            f"{field} must be a finite JSON number; booleans are not accepted"
        )
    if not math.isfinite(value):
        raise BuildingImportError(f"{field} must be finite")
    return float(value)


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
    aoi_config = load_aoi_config(args.aoi_config)
    aoi_geojson_path = _aoi_geojson_path(aoi_config.profile, args.aoi_geojson)
    if args.command == "validate-buildings":
        verify_building_source(source_path, source_manifest_path)
        aoi_config = load_aoi_config(args.aoi_config)
        selection, _geojson, _markdown = generate_selection(aoi_config)
        validate_stored_selection(
            aoi_config,
            selection["aoi"]["center_easting_m"],
            selection["aoi"]["center_northing_m"],
            selection["aoi"]["bbox_m"],
        )
        result = validate_building_package(
            args.package.resolve(),
            expected_aoi=aoi_config,
            expected_aoi_ring=_load_aoi_ring(aoi_geojson_path),
            terrain_package_path=args.terrain_package.resolve(),
            source_path=source_path,
            source_manifest_path=source_manifest_path,
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "publish-buildings":
        verify_building_source(source_path, source_manifest_path)
        aoi_config = load_aoi_config(args.aoi_config)
        selection, _geojson, _markdown = generate_selection(aoi_config)
        validate_stored_selection(
            aoi_config,
            selection["aoi"]["center_easting_m"],
            selection["aoi"]["center_northing_m"],
            selection["aoi"]["bbox_m"],
        )
        result = publish_building_package(
            args.package.resolve(),
            args.terrain_package.resolve(),
            expected_aoi=aoi_config,
            expected_aoi_ring=_load_aoi_ring(aoi_geojson_path),
            source_path=source_path,
            source_manifest_path=source_manifest_path,
        )
        print(f"Published byte-identical validated buildings to {result['outputDirectory']}")
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "preview-buildings":
        verify_building_source(source_path, source_manifest_path)
        aoi_config = load_aoi_config(args.aoi_config)
        selection, _geojson, _markdown = generate_selection(aoi_config)
        validate_stored_selection(
            aoi_config,
            selection["aoi"]["center_easting_m"],
            selection["aoi"]["center_northing_m"],
            selection["aoi"]["bbox_m"],
        )
        package_status = validate_building_package(
            args.package.resolve(),
            expected_aoi=aoi_config,
            expected_aoi_ring=_load_aoi_ring(aoi_geojson_path),
            terrain_package_path=args.terrain_package.resolve(),
            source_path=source_path,
            source_manifest_path=source_manifest_path,
        )
        data = json.loads((args.package / "buildings.json").read_text(encoding="utf-8"))
        package_qa = (args.package / "qa.json").read_bytes()
        external_qa = args.qa.read_bytes()
        if package_qa != external_qa:
            raise BuildingExportError(
                "external QA report differs from integrity-bound package qa.json"
            )
        qa = json.loads(package_qa)
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
        aoi_geojson_path,
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
            "publish-buildings",
        }:
            return _building_command(args)
        if args.command in {
            "inspect-road-source",
            "import-roads",
            "validate-roads",
            "preview-roads",
            "publish-roads",
        }:
            return _road_command(args)
        if args.command in {"build-overview", "validate-overview", "publish-overview"}:
            return _overview_command(args)
        if args.command == "assess-resolution-index":
            config = _validated_selection_config(args.config)
            report = assess_ea_resolution_index(config, args.index, args.source_metadata)
            atomic_write_json(args.report, report)
            footprint = report["halfMetreIndexFootprint"]
            print(f"Wrote EA time-stamped DTM index assessment to {args.report.resolve()}")
            print(
                f"0.5 m index polygons intersect {footprint['coveredUnionAreaM2']:.3f} m² of "
                f"{footprint['aoiAreaM2']:.3f} m² ({footprint['aoiPercent']:.4f}%); "
                "this is metadata footprint only, not raster-cell coverage."
            )
            print(
                "AOI selection_status remains selected_pending_coverage; "
                "coverage_status remains not_checked."
            )
            return 0
        if args.command == "capture-resolution-index":
            config = _validated_selection_config(args.config)
            output_dir = args.output_dir.resolve()
            day = datetime.now(UTC).date()
            stem = f"ea-dtm-time-stamped-{config.profile}-{day.isoformat()}"
            index_path = output_dir / f"{stem}.geojson"
            source_path = output_dir / f"{stem}.source.json"
            metadata = capture_ea_resolution_index(
                config,
                index_path,
                source_path,
                timeout_seconds=args.timeout_seconds,
            )
            assessment = assess_ea_resolution_index(config, index_path, source_path)
            print(f"Captured raw EA WFS response: {index_path}")
            print(f"Captured provenance sidecar: {source_path}")
            print(
                f"Complete single page: {metadata['response']['numberReturned']} of "
                f"{metadata['response']['numberMatched']} records; "
                f"SHA-256 {metadata['response']['sha256']}"
            )
            print(
                "0.5 m index footprint: "
                f"{assessment['halfMetreIndexFootprint']['aoiPercent']:.4f}% metadata only; "
                "no raster coverage claim."
            )
            return 0
        if args.command in {
            "inspect-comparison-source",
            "compare-alignment",
            "validate-alignment-report",
        }:
            return _alignment_command(args)
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
        AlignmentReportError,
        BuildingExportError,
        BuildingPublishError,
        BuildingImportError,
        BuildingSourceError,
        ComparisonSourceError,
        RoadConfigError,
        RoadImportError,
        RoadExportError,
        RoadPublishError,
        OverviewExportError,
        OverviewPublishError,
        ElevationIndexError,
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
