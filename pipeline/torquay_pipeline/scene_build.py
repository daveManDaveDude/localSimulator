"""Build and validate the isolated current 2 km real-world scene package."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from shapely.geometry import LineString, Polygon, box

from .aoi import generate_selection
from .building_export import (
    BuildingExportError,
    _json_bytes,
    _load_aoi_ring,
    build_building_package,
    validate_building_package,
)
from .building_heights import HeightPolicy
from .building_sources import verify_building_source
from .buildings import BuildingConfig, import_osm_buildings
from .config import AoiConfig, load_aoi_config, validate_stored_selection
from .road_config import load_road_config
from .road_export import RoadExportError, build_road_package, validate_road_package
from .roads import import_osm_roads
from .scene_release import publish_scene_release, validate_published_scene
from .terrain_coverage import analyze_coverage
from .terrain_export import TerrainExportError, build_terrain_package
from .terrain_sources import verify_source_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_HALF_SIZE_M = 500.0
SCENE_PROFILE = "current_2km"


class SceneBuildError(ValueError):
    """Raised when the bounded 2 km scene cannot be built or safely published."""


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve(path: Path, root: Path) -> Path:
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def _paths_overlap(first: Path, second: Path) -> bool:
    a = first.resolve(strict=False)
    b = second.resolve(strict=False)
    return a == b or a in b.parents or b in a.parents


def _validate_output_path(
    output_dir: Path,
    *,
    project_root: Path,
    protected_inputs: list[Path],
) -> Path:
    """Reject any destination overlap before creating or replacing output files."""
    output = output_dir.resolve(strict=False)
    if output.exists() and output.is_symlink():
        raise SceneBuildError(f"output directory must not be a symlink: '{output}'")
    protected = [
        project_root / "data/raw",
        project_root / "data/source-manifest.json",
        project_root / "config",
        project_root / "docs/aoi-selection.geojson",
        project_root / "docs/milestones/artifacts/AOI-1km-selection/aoi-selection.geojson",
        project_root / "public/worlds/torquay-poc-001",
        *protected_inputs,
    ]
    for value in protected:
        if _paths_overlap(output, value):
            raise SceneBuildError(
                f"output '{output}' overlaps protected input '{value.resolve(strict=False)}'"
            )
    try:
        output.relative_to(project_root.resolve())
    except ValueError as exc:
        raise SceneBuildError("output directory must remain inside the project workspace") from exc
    return output


def _load_building_config(path: Path) -> BuildingConfig:
    def number(value: Any, field: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{field} must be a JSON number")
        return float(value)

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        height = raw["height_policy"]
        config = BuildingConfig(
            acquisition_buffer_m=number(raw["acquisition_buffer_m"], "acquisition_buffer_m"),
            minimum_clipped_area_m2=number(
                raw["minimum_clipped_area_m2"], "minimum_clipped_area_m2"
            ),
            height_policy=HeightPolicy(
                levels_to_metres=number(
                    height["levels_to_metres"], "height_policy.levels_to_metres"
                ),
                default_height_m=number(
                    height["default_height_m"], "height_policy.default_height_m"
                ),
                minimum_height_m=number(
                    height["minimum_height_m"], "height_policy.minimum_height_m"
                ),
                maximum_height_m=number(
                    height["maximum_height_m"], "height_policy.maximum_height_m"
                ),
            ),
        )
        config.validate()
        return config
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise SceneBuildError(f"invalid building config '{path}': {exc}") from exc


def _current_aoi(config_path: Path) -> AoiConfig:
    config = load_aoi_config(config_path)
    if config.profile != SCENE_PROFILE:
        raise SceneBuildError("2 km scene requires config profile current_2km")
    selection, _geojson, _markdown = generate_selection(config)
    validate_stored_selection(
        config,
        selection["aoi"]["center_easting_m"],
        selection["aoi"]["center_northing_m"],
        selection["aoi"]["bbox_m"],
    )
    if config.bbox_m != (
        290108.9018176432,
        64353.48350844931,
        292108.9018176432,
        66353.48350844931,
    ):
        raise SceneBuildError("current_2km AOI differs from the exact pending TQ1 4HN bounds")
    if (
        config.selection_status != "selected_pending_coverage"
        or config.coverage_status != "not_checked"
    ):
        raise SceneBuildError(
            "current AOI status must remain selected_pending_coverage / not_checked"
        )
    return config


def _layer_hashes(package: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for layer, names in (
        ("terrain", ("manifest.json", "heightfield.f32", "qa.json")),
        ("buildings", ("manifest.json", "buildings.json", "qa.json")),
        ("roads", ("manifest.json", "roads.json", "qa.json")),
    ):
        directory = package if layer == "terrain" else package / layer
        result[layer] = {
            name: {
                "byteLength": (directory / name).stat().st_size,
                "sha256": _file_sha256(directory / name),
            }
            for name in names
        }
    return result


def _measure_outer_annulus(package: Path) -> dict[str, Any]:
    """Count exported source features intersecting the added 500–1000 m annulus."""
    annulus = box(-1000.0, -1000.0, 1000.0, 1000.0).difference(
        box(
            -HISTORICAL_HALF_SIZE_M,
            -HISTORICAL_HALF_SIZE_M,
            HISTORICAL_HALF_SIZE_M,
            HISTORICAL_HALF_SIZE_M,
        )
    )
    building_data = json.loads((package / "buildings/buildings.json").read_text(encoding="utf-8"))
    road_data = json.loads((package / "roads/roads.json").read_text(encoding="utf-8"))
    building_ids: list[str] = []
    for feature in building_data.get("buildings", []):
        geometry = feature.get("geometry", {})
        polygons = []
        for polygon in geometry.get("polygons", []):
            polygons.append(
                Polygon(
                    polygon.get("exteriorXZ", []),
                    polygon.get("interiorRingsXZ", []),
                )
            )
        if polygons and any(item.intersection(annulus).area > 0 for item in polygons):
            building_ids.append(str(feature.get("id", "")))
    road_ids: list[str] = []
    for feature in road_data.get("features", []):
        if any(
            len(part) >= 2 and LineString(part).intersection(annulus).length > 0
            for part in feature.get("centerlinePartsXZ", [])
        ):
            road_ids.append(f"way/{feature.get('source', {}).get('osmId', '')}")
    return {
        "definition": "local XZ outside former 1 km square and inside current 2 km square",
        "historicalHalfExtentM": HISTORICAL_HALF_SIZE_M,
        "currentHalfExtentM": 1000.0,
        "buildingFeatureCount": len(building_ids),
        "buildingFeatureIdsSample": sorted(building_ids)[:20],
        "roadWayCount": len(road_ids),
        "roadWayIdsSample": sorted(set(road_ids))[:20],
    }


def _scene_qa(package: Path, aoi: AoiConfig) -> dict[str, Any]:
    terrain_manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    building_manifest = json.loads(
        (package / "buildings/manifest.json").read_text(encoding="utf-8")
    )
    road_manifest = json.loads((package / "roads/manifest.json").read_text(encoding="utf-8"))
    hashes = _layer_hashes(package)
    return {
        "formatVersion": 1,
        "sceneProfile": SCENE_PROFILE,
        "worldId": aoi.id,
        "aoi": {
            "boundsM": list(aoi.bbox_m),
            "selectionStatus": aoi.selection_status,
            "coverageStatus": aoi.coverage_status,
            "m2Complete": False,
        },
        "terrain": {
            "columns": terrain_manifest["heightfield"]["columns"],
            "rows": terrain_manifest["heightfield"]["rows"],
            "spacingM": terrain_manifest["heightfield"]["spacingM"],
            "origin": terrain_manifest["origin"],
            "manifestSha256": hashes["terrain"]["manifest.json"]["sha256"],
        },
        "buildings": {
            "featureCount": building_manifest["buildings"]["count"],
            "manifestSha256": hashes["buildings"]["manifest.json"]["sha256"],
        },
        "roads": {
            "wayCount": road_manifest["counts"]["uniqueExportedWays"],
            "manifestSha256": hashes["roads"]["manifest.json"]["sha256"],
        },
        "outerAnnulus": _measure_outer_annulus(package),
        "packageHashes": hashes,
        "interpretation": (
            "Mapped counts are observations of this dated source, not completeness evidence."
        ),
    }


def validate_scene_package(
    package_dir: Path,
    *,
    aoi_config_path: Path,
    source_manifest_path: Path,
    source_dir: Path,
    source_path: Path,
    buildings_config_path: Path,
    roads_config_path: Path,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Validate all layer packages and their common current_2km identities."""
    aoi = _current_aoi(aoi_config_path)
    package = package_dir.resolve()
    _load_building_config(buildings_config_path)
    road_config, _root, _raw = load_road_config(roads_config_path)
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("sceneProfile") != SCENE_PROFILE or manifest.get("id") != aoi.id:
        raise SceneBuildError("terrain root manifest is not the current_2km world package")
    terrain_identity = {
        "columns": manifest.get("heightfield", {}).get("columns"),
        "rows": manifest.get("heightfield", {}).get("rows"),
        "spacingM": manifest.get("heightfield", {}).get("spacingM"),
        "boundsM": manifest.get("aoi", {}).get("boundsM"),
        "origin": manifest.get("origin"),
        "sha256": manifest.get("heightfield", {}).get("sha256"),
        "byteLength": manifest.get("heightfield", {}).get("byteLength"),
    }
    if (
        terrain_identity["columns"] != 1001
        or terrain_identity["rows"] != 1001
        or terrain_identity["spacingM"] != 2.0
        or terrain_identity["boundsM"] != list(aoi.bbox_m)
        or terrain_identity["byteLength"] != 4_008_004
    ):
        raise SceneBuildError(
            "terrain root manifest does not match the 1001 × 1001 current_2km grid"
        )
    manifest_bytes = (package / "manifest.json").read_bytes()
    terrain_hash = _file_sha256(package / "heightfield.f32")
    if terrain_hash != manifest.get("heightfield", {}).get("sha256"):
        raise SceneBuildError("terrain heightfield SHA-256 differs from its manifest")
    if (package / "heightfield.f32").stat().st_size != 4_008_004:
        raise SceneBuildError("terrain heightfield byte length is not 4,008,004")
    source_manifest, _verified_rasters = verify_source_manifest(source_manifest_path, source_dir)
    if not source_manifest:
        raise SceneBuildError("EA source manifest could not be verified")
    verify_building_source(source_path, source_manifest_path)
    building_validation = validate_building_package(
        package / "buildings",
        expected_aoi=aoi,
        expected_aoi_ring=_load_ring(project_root),
        terrain_package_path=package,
        source_path=source_path,
        source_manifest_path=source_manifest_path,
    )
    road_validation = validate_road_package(
        package / "roads",
        expected_aoi=aoi,
        expected_aoi_ring=_load_ring(project_root),
        terrain_package_path=package,
        source_path=source_path,
        source_manifest_path=source_manifest_path,
        aoi_geojson_path=project_root / "docs/aoi-selection.geojson",
        road_config=road_config,
        buildings_path=package / "buildings/buildings.json",
        preview_output_name="roads-preview.png",
    )
    try:
        scene_qa = json.loads((package / "scene-qa.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SceneBuildError(f"scene-qa.json is missing or invalid: {exc}") from exc
    expected_qa = _scene_qa(package, aoi)
    if scene_qa != expected_qa:
        raise SceneBuildError("scene-qa.json does not match the validated current_2km package")
    if expected_qa["outerAnnulus"]["buildingFeatureCount"] <= 0:
        raise SceneBuildError("no exported building features were measured in the outer annulus")
    if expected_qa["outerAnnulus"]["roadWayCount"] <= 0:
        raise SceneBuildError("no exported road ways were measured in the outer annulus")
    return {
        "sceneProfile": SCENE_PROFILE,
        "worldId": aoi.id,
        "packageDirectory": str(package),
        "terrainManifestSha256": _sha256(manifest_bytes),
        "terrainHeightfieldSha256": terrain_hash,
        "buildingValidation": building_validation,
        "roadValidation": road_validation,
        "sceneQa": scene_qa,
    }


def _load_ring(project_root: Path) -> list[list[float]]:
    return _load_aoi_ring(project_root / "docs/aoi-selection.geojson")


def validate_scene_root(
    package_root: Path,
    *,
    aoi_config_path: Path,
    source_manifest_path: Path,
    source_dir: Path,
    source_path: Path,
    buildings_config_path: Path,
    roads_config_path: Path,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Validate an active release root, or a direct package/stage when unactivated."""
    common = {
        "aoi_config_path": aoi_config_path,
        "source_manifest_path": source_manifest_path,
        "source_dir": source_dir,
        "source_path": source_path,
        "buildings_config_path": buildings_config_path,
        "roads_config_path": roads_config_path,
        "project_root": project_root,
    }
    root = package_root.resolve()
    if (root / "ready.json").is_file():
        return validate_published_scene(
            root,
            project_root=project_root,
            validator=lambda release: validate_scene_package(release, **common),
        )
    return validate_scene_package(root, **common)


def _cleanup_failed_stage(stage: Path, *, validated: bool) -> bool:
    """Discard an incomplete stage, but retain a validated stage for safe recovery."""
    if not stage.exists():
        return False
    if validated:
        return True
    shutil.rmtree(stage, ignore_errors=True)
    return False


def build_scene_package(
    *,
    aoi_config_path: Path,
    source_manifest_path: Path,
    source_dir: Path,
    source_path: Path,
    buildings_config_path: Path,
    roads_config_path: Path,
    output_dir: Path,
    project_root: Path = PROJECT_ROOT,
    missing_threshold: float = 0.01,
) -> dict[str, Any]:
    """Build, validate and atomically publish the isolated 2 km terrain/buildings/roads scene."""
    root = project_root.resolve()
    aoi_config_path = _resolve(aoi_config_path, root)
    source_manifest_path = _resolve(source_manifest_path, root)
    source_dir = _resolve(source_dir, root)
    source_path = _resolve(source_path, root)
    buildings_config_path = _resolve(buildings_config_path, root)
    roads_config_path = _resolve(roads_config_path, root)
    aoi = _current_aoi(aoi_config_path)
    road_config, _config_root, _road_raw = load_road_config(roads_config_path)
    building_config = _load_building_config(buildings_config_path)
    source_manifest, verified_rasters = verify_source_manifest(source_manifest_path, source_dir)
    if not verified_rasters:
        raise SceneBuildError("source manifest has no verified EA raster files")
    verify_building_source(source_path, source_manifest_path)
    raster_records = source_manifest.get("sources", [])
    raster_paths = [
        (source_dir / str(record["raster_relative_path"])).resolve()
        for record in raster_records
        if isinstance(record, dict) and isinstance(record.get("raster_relative_path"), str)
    ]
    if not raster_paths:
        raise SceneBuildError("EA source manifest contains no safe raster paths")
    coverage = analyze_coverage(aoi, raster_paths, missing_threshold)
    if coverage.report.get("analysis", {}).get("ea_dtm_threshold_result") != "pass":
        raise SceneBuildError(
            "EA DTM coverage did not pass the configured 1% missing-cell threshold"
        )

    protected_inputs = [
        aoi_config_path,
        source_manifest_path,
        source_dir,
        source_path,
        buildings_config_path,
        roads_config_path,
        project_root / "docs/aoi-selection.geojson",
        *(raster_paths),
    ]
    destination = _validate_output_path(
        output_dir, project_root=root, protected_inputs=protected_inputs
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Keep incomplete packages outside Vite's public tree while retaining an
    # atomic same-volume rename into the final destination.
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.stage-", dir=root))
    stage_validated = False
    try:
        terrain_qa = stage / "qa.json"
        terrain_preview = stage / "terrain-preview.png"
        terrain_built = build_terrain_package(
            aoi,
            raster_paths,
            source_manifest,
            verified_rasters,
            stage,
            terrain_qa,
            terrain_preview,
        )

        buildings = import_osm_buildings(source_path, source_manifest_path, aoi, building_config)
        build_building_package(
            buildings,
            aoi,
            source_path,
            source_manifest_path,
            stage,
            _resolve(project_root / "docs/aoi-selection.geojson", root),
            stage / "buildings",
            stage / "qa/buildings-qa.json",
            stage / "qa/buildings-preview.png",
            stage / "qa/buildings-intermediate.json",
        )

        roads = import_osm_roads(source_path, source_manifest_path, aoi, road_config)
        build_road_package(
            roads,
            aoi,
            road_config,
            source_path,
            source_manifest_path,
            stage,
            _resolve(project_root / "docs/aoi-selection.geojson", root),
            stage / "roads",
            stage / "qa/roads-qa.json",
            stage / "qa/roads-preview.png",
            stage / "qa/roads-intermediate.json",
            stage / "buildings/buildings.json",
        )

        scene_qa = _scene_qa(stage, aoi)
        scene_qa_bytes = _json_bytes(scene_qa)
        (stage / "scene-qa.json").write_bytes(scene_qa_bytes)
        if scene_qa["outerAnnulus"]["buildingFeatureCount"] <= 0:
            raise SceneBuildError("the 2 km build contains no buildings in its added outer annulus")
        if scene_qa["outerAnnulus"]["roadWayCount"] <= 0:
            raise SceneBuildError("the 2 km build contains no roads in its added outer annulus")

        # Validate while still in owned staging; the destination remains untouched on failure.
        validation_inputs = {
            "aoi_config_path": aoi_config_path,
            "source_manifest_path": source_manifest_path,
            "source_dir": source_dir,
            "source_path": source_path,
            "buildings_config_path": buildings_config_path,
            "roads_config_path": roads_config_path,
            "project_root": root,
        }
        validate_scene_package(stage, **validation_inputs)
        stage_validated = True
        result = publish_scene_release(
            stage,
            destination,
            project_root=root,
            validator=lambda package: validate_scene_package(package, **validation_inputs),
            stage_already_validated=True,
        )
        shutil.rmtree(stage, ignore_errors=True)
        result["terrainBuild"] = {
            "columns": terrain_built["manifest"]["heightfield"]["columns"],
            "rows": terrain_built["manifest"]["heightfield"]["rows"],
            "spacingM": terrain_built["manifest"]["heightfield"]["spacingM"],
        }
        return result
    except Exception as exc:
        preserved_stage = _cleanup_failed_stage(stage, validated=stage_validated)
        recovery_note = (
            f"; validated stage preserved for publication retry at '{stage}'"
            if preserved_stage
            else ""
        )
        if isinstance(exc, SceneBuildError):
            if recovery_note:
                raise SceneBuildError(f"{exc}{recovery_note}") from exc
            raise
        if isinstance(exc, (BuildingExportError, RoadExportError, TerrainExportError)):
            raise SceneBuildError(f"current_2km scene stage failed: {exc}{recovery_note}") from exc
        raise SceneBuildError(f"current_2km scene build failed: {exc}{recovery_note}") from exc
