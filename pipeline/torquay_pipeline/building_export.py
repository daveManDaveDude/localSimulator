"""Deterministic, local OSM building package and QA publication."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

import shapely
from shapely.geometry import MultiPolygon, Polygon

from . import __version__
from .aoi import generate_selection
from .building_heights import HeightPolicy, HeightResult, resolve_building_height
from .building_preview import OSM_ATTRIBUTION, render_building_preview
from .building_sources import BuildingSourceError, read_source_manifest, verify_building_source
from .buildings import BuildingImportResult
from .config import AoiConfig, validate_stored_selection
from .coordinates import pinned_transformer


class BuildingExportError(ValueError):
    """Raised when a deterministic OSM building package cannot be validated or published."""


OSM_LICENSE_URL = "https://www.openstreetmap.org/copyright"
GEOFABRIK_CREDIT_URL = "https://www.geofabrik.de/"
OSM_SOURCE_URL = "https://download.geofabrik.de/europe/united-kingdom/england/devon.html"


def _json_bytes(value: Any) -> bytes:
    try:
        return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode(
            "utf-8"
        )
    except (TypeError, ValueError) as exc:
        raise BuildingExportError(f"cannot serialize building package metadata: {exc}") from exc


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, ValueError):
        return False


def _finite_number(value: Any, field: str) -> float:
    if not _is_finite_number(value):
        raise BuildingExportError(
            f"{field} must be a finite JSON number (booleans are not numbers)"
        )
    try:
        return float(value)
    except (OverflowError, ValueError) as exc:
        raise BuildingExportError(f"{field} cannot be represented as a finite number") from exc


def _required_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BuildingExportError(f"{field} must be a JSON object")
    return value


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BuildingExportError(f"{field} must be a non-empty string")
    return value


def _stage_file(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{path.name}.", suffix=".stage", dir=path.parent, delete=False
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            return Path(handle.name)
    except OSError as exc:
        raise BuildingExportError(f"cannot stage output '{path}': {exc}") from exc


def _publish_transaction(artifacts: list[tuple[Path, bytes]], manifest_path: Path) -> None:
    staged: dict[Path, Path] = {}
    backups: dict[Path, Path] = {}
    replaced: list[Path] = []
    try:
        for target, content in artifacts:
            staged[target] = _stage_file(target, content)
        target_order = [target for target, _content in artifacts if target != manifest_path]
        target_order.append(manifest_path)
        for target in target_order:
            if target.exists():
                with tempfile.NamedTemporaryFile(
                    prefix=f".{target.name}.", suffix=".backup", dir=target.parent, delete=False
                ) as handle:
                    backup = Path(handle.name)
                backup.unlink(missing_ok=True)
                os.replace(target, backup)
                backups[target] = backup
            os.replace(staged[target], target)
            replaced.append(target)
    except Exception:
        for target in reversed(replaced):
            target.unlink(missing_ok=True)
            backup = backups.get(target)
            if backup is not None and backup.exists():
                os.replace(backup, target)
        for target, backup in backups.items():
            if backup.exists() and not target.exists():
                os.replace(backup, target)
        raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)
        for backup in backups.values():
            backup.unlink(missing_ok=True)


def _load_aoi_ring(path: Path) -> list[list[float]]:
    try:
        geojson = json.loads(path.read_text(encoding="utf-8"))
        polygon = next(
            feature["geometry"]
            for feature in geojson["features"]
            if feature.get("geometry", {}).get("type") == "Polygon"
        )
        ring = polygon["coordinates"][0]
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise ValueError("AOI GeoJSON polygon ring is not closed")
        return [[float(point[0]), float(point[1])] for point in ring]
    except (OSError, json.JSONDecodeError, KeyError, StopIteration, TypeError, ValueError) as exc:
        raise BuildingExportError(f"cannot read exact WGS84 AOI ring from '{path}': {exc}") from exc


def _configured_aoi_ring(config: AoiConfig) -> list[list[float]]:
    try:
        selection, _geojson, _markdown = generate_selection(config)
        validate_stored_selection(
            config,
            selection["aoi"]["center_easting_m"],
            selection["aoi"]["center_northing_m"],
            selection["aoi"]["bbox_m"],
        )
        corners = selection["aoi"]["corner_coordinates_wgs84"]
        return [[float(point[0]), float(point[1])] for point in [*corners, corners[0]]]
    except (KeyError, TypeError, ValueError) as exc:
        raise BuildingExportError(
            f"cannot derive the approved AOI boundary from its config: {exc}"
        ) from exc


def _terrain_identity(path: Path, expected_aoi: AoiConfig) -> dict[str, Any]:
    manifest_path = path / "manifest.json"
    binary_path = path / "heightfield.f32"
    try:
        terrain = json.loads(manifest_path.read_text(encoding="utf-8"))
        origin = terrain["origin"]
        heightfield = terrain["heightfield"]
        terrain_aoi = terrain["aoi"]
        binary_bytes = binary_path.read_bytes()
        actual_hash = hashlib.sha256(binary_bytes).hexdigest()
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise BuildingExportError(
            f"cannot establish the local EA terrain identity from '{path}': {exc}"
        ) from exc
    if (
        not isinstance(origin, dict)
        or not isinstance(heightfield, dict)
        or not isinstance(terrain_aoi, dict)
    ):
        raise BuildingExportError(
            "local terrain manifest origin, heightfield, and AOI must be objects"
        )
    expected_byte_length = heightfield.get("byteLength")
    if (
        isinstance(expected_byte_length, bool)
        or not isinstance(expected_byte_length, int)
        or expected_byte_length != len(binary_bytes)
    ):
        raise BuildingExportError(
            "local terrain heightfield byteLength differs from actual file bytes"
        )
    if heightfield.get("path") != "heightfield.f32":
        raise BuildingExportError("local terrain heightfield path must be heightfield.f32")
    if actual_hash != heightfield.get("sha256"):
        raise BuildingExportError(
            "local EA heightfield does not match its terrain manifest SHA-256"
        )
    if terrain.get("id") != expected_aoi.id:
        raise BuildingExportError("terrain package world ID does not match the configured AOI")
    if (
        terrain_aoi.get("selectionStatus") != expected_aoi.selection_status
        or terrain_aoi.get("coverageStatus") != expected_aoi.coverage_status
    ):
        raise BuildingExportError("terrain manifest does not preserve the pending AOI status")
    if terrain_aoi.get("boundsM") != list(expected_aoi.bbox_m):
        raise BuildingExportError(
            "terrain manifest AOI bounds differ from the configured building AOI"
        )
    expected_size = expected_aoi.width_m
    expected_dimension = int(expected_size / 2.0) + 1
    expected_profile = expected_aoi.profile
    manifest_profile = terrain.get("sceneProfile")
    if expected_profile == "current_2km":
        if manifest_profile != "current_2km":
            raise BuildingExportError(
                "terrain manifest must explicitly identify the current_2km scene profile"
            )
    elif manifest_profile not in (None, "historical_1km"):
        raise BuildingExportError("historical AOI requires the historical_1km terrain profile")
    columns = heightfield.get("columns")
    rows = heightfield.get("rows")
    if (
        isinstance(columns, bool)
        or not isinstance(columns, int)
        or isinstance(rows, bool)
        or not isinstance(rows, int)
        or columns != expected_dimension
        or rows != expected_dimension
    ):
        raise BuildingExportError(
            f"local terrain grid dimensions do not match the {expected_size:,.0f} m project AOI"
        )
    if expected_byte_length != rows * columns * 4:
        raise BuildingExportError(
            "local terrain heightfield byteLength does not match its grid dimensions"
        )
    if _finite_number(heightfield.get("spacingM"), "terrain.heightfield.spacingM") != 2.0:
        raise BuildingExportError("local terrain grid spacing must be the reviewed 2 m spacing")
    for coordinate, expected_coordinate, field in zip(
        (origin.get("eastingM"), origin.get("northingM")),
        expected_aoi.center_bng_m,
        ("eastingM", "northingM"),
        strict=True,
    ):
        actual_coordinate = _finite_number(coordinate, f"terrain.origin.{field}")
        if not math.isclose(actual_coordinate, expected_coordinate, rel_tol=0, abs_tol=1e-8):
            raise BuildingExportError(
                f"terrain origin {field} differs from the configured AOI center"
            )
    elevation = _finite_number(origin.get("elevationM"), "terrain.origin.elevationM")
    terrain_provenance = terrain.get("provenance")
    if not isinstance(terrain_provenance, dict):
        raise BuildingExportError("terrain manifest provenance must be an object")
    vertical_reference = terrain_provenance.get("verticalReference")
    if not isinstance(vertical_reference, str) or not vertical_reference.strip():
        raise BuildingExportError("terrain manifest must identify its vertical reference")
    return {
        "worldId": terrain["id"],
        "origin": {
            "eastingM": float(origin["eastingM"]),
            "northingM": float(origin["northingM"]),
            "elevationM": elevation,
        },
        "heightfieldPath": "heightfield.f32",
        "heightfieldSha256": actual_hash,
        "heightfieldByteLength": len(binary_bytes),
        "heightfieldDimensions": [expected_dimension, expected_dimension],
        "verticalReference": vertical_reference,
        **({"sceneProfile": "current_2km"} if expected_profile == "current_2km" else {}),
    }


def _library_versions() -> dict[str, str]:
    return {
        package: importlib.metadata.version(package)
        for package in ("osmium", "shapely", "pyproj", "numpy", "matplotlib")
    }


def _validate_operation(value: Any) -> None:
    operation = _required_mapping(value, "coordinateOperation")
    if operation.get("axisOrder") != (
        "longitude-latitude for geographic input; easting-northing for BNG"
    ):
        raise BuildingExportError("coordinateOperation.axisOrder is missing or unsupported")
    for direction in ("wgs84ToBng", "bngToWgs84"):
        record = _required_mapping(operation.get(direction), f"coordinateOperation.{direction}")
        if record.get("name") != "EPSG:1314 + EPSG:19916":
            raise BuildingExportError(
                f"coordinateOperation.{direction}.name is not the pinned operation"
            )
        _required_string(record.get("definition"), f"coordinateOperation.{direction}.definition")
        if (
            _finite_number(
                record.get("reported_accuracy_m"),
                f"coordinateOperation.{direction}.reported_accuracy_m",
            )
            != 2.0
        ):
            raise BuildingExportError(
                f"coordinateOperation.{direction} must retain its reported 2 m accuracy"
            )
        if record.get("uses_grids") is not False or record.get("best_available") is not False:
            raise BuildingExportError(
                f"coordinateOperation.{direction} must preserve the selected grid-free "
                "fallback status"
            )
        missing = record.get("preferred_missing_operations")
        if (
            not isinstance(missing, list)
            or not missing
            or not any(
                isinstance(item, dict)
                and any(
                    isinstance(grid, dict)
                    and grid.get("short_name") == "uk_os_OSTN15_NTv2_OSGBtoETRS.tif"
                    for grid in item.get("grids", [])
                )
                for item in missing
            )
        ):
            raise BuildingExportError(
                f"coordinateOperation.{direction} must record the missing preferred OSTN15 "
                "grid operation"
            )
        caveat = record.get("grid_status")
        if caveat != "selected EPSG:1314 + EPSG:19916 operation uses no grid files":
            raise BuildingExportError(
                f"coordinateOperation.{direction}.grid_status differs from the pinned operation"
            )
        if record.get("grids") != []:
            raise BuildingExportError(f"coordinateOperation.{direction}.grids must be empty")
    try:
        _to_bng, to_bng_info = pinned_transformer(4326, 27700)
        _to_wgs, to_wgs_info = pinned_transformer(27700, 4326)
    except ValueError as exc:
        raise BuildingExportError(
            f"cannot verify the pinned EPSG:1314 + EPSG:19916 operation: {exc}"
        ) from exc
    expected = {
        "axisOrder": "longitude-latitude for geographic input; easting-northing for BNG",
        "wgs84ToBng": to_bng_info.as_dict(),
        "bngToWgs84": to_wgs_info.as_dict(),
    }
    if operation != expected:
        raise BuildingExportError(
            "coordinateOperation definition or grid diagnostics differ from the pinned "
            "local operation"
        )


def _validate_policies(value: Any) -> None:
    policies = _required_mapping(value, "policies")
    height = _required_mapping(policies.get("height"), "policies.height")
    geometry = _required_mapping(policies.get("geometry"), "policies.geometry")
    if any(
        isinstance(record.get("version"), bool) or record.get("version") != 1
        for record in (height, geometry)
    ):
        raise BuildingExportError("height and geometry policy versions must be integer 1")
    for field in ("levelsToMetres", "defaultHeightM", "minimumHeightM", "maximumHeightM"):
        if _finite_number(height.get(field), f"policies.height.{field}") <= 0:
            raise BuildingExportError(f"policies.height.{field} must be positive")
    if height["minimumHeightM"] > height["maximumHeightM"]:
        raise BuildingExportError("policies.height minimumHeightM exceeds maximumHeightM")
    if height.get("precedence") != ["height", "building:levels", "configured_default"]:
        raise BuildingExportError("policies.height.precedence is missing or unsupported")
    if height.get("taggedHeightConfidence") != "tagged_but_unverified":
        raise BuildingExportError(
            "policies.height.taggedHeightConfidence is missing or unsupported"
        )
    if height.get("defaultConfidence") != "visual_default_estimate":
        raise BuildingExportError("policies.height.defaultConfidence is missing or unsupported")
    for field in ("acquisitionBufferM", "minimumClippedAreaM2", "coordinateQuantizationM"):
        if _finite_number(geometry.get(field), f"policies.geometry.{field}") < 0:
            raise BuildingExportError(f"policies.geometry.{field} must be nonnegative")
    expected_literals = {
        "exteriorWinding": "counter-clockwise in local XZ coordinates",
        "interiorWinding": "clockwise in local XZ coordinates",
        "invalidGeometryPolicy": "reject without automatic repair",
        "duplicatePolicy": (
            "prefer relation then stable identity; collapse exact canonical geometry"
        ),
        "nearOverlapPolicy": "report; do not merge",
    }
    for field, expected in expected_literals.items():
        if geometry.get(field) != expected:
            raise BuildingExportError(f"policies.geometry.{field} is missing or unsupported")


def _validate_height(feature: dict[str, Any], index: int, policy: dict[str, Any]) -> HeightResult:
    tags = feature.get("tags")
    if not isinstance(tags, dict) or any(
        not isinstance(key, str) or not isinstance(value, str) for key, value in tags.items()
    ):
        raise BuildingExportError(
            f"buildings[{index}].tags must map strings to strings before height validation"
        )
    height_policy = HeightPolicy(
        levels_to_metres=_finite_number(
            policy.get("levelsToMetres"), "policies.height.levelsToMetres"
        ),
        default_height_m=_finite_number(
            policy.get("defaultHeightM"), "policies.height.defaultHeightM"
        ),
        minimum_height_m=_finite_number(
            policy.get("minimumHeightM"), "policies.height.minimumHeightM"
        ),
        maximum_height_m=_finite_number(
            policy.get("maximumHeightM"), "policies.height.maximumHeightM"
        ),
    )
    try:
        expected = resolve_building_height(tags, height_policy)
    except ValueError as exc:
        raise BuildingExportError(
            f"buildings[{index}] height tags or effective policy cannot be resolved: {exc}"
        ) from exc

    if feature.get("heightMethod") != expected.method:
        raise BuildingExportError(
            f"buildings[{index}].heightMethod does not match the retained tags and policy"
        )
    if feature.get("heightConfidence") != expected.confidence:
        raise BuildingExportError(
            f"buildings[{index}].heightConfidence does not match the resolved height method"
        )
    height = _finite_number(feature.get("heightM"), f"buildings[{index}].heightM")
    if not math.isclose(height, expected.height_m, rel_tol=0, abs_tol=1e-9):
        raise BuildingExportError(
            f"buildings[{index}].heightM does not match the retained tags and height policy"
        )

    provenance = _required_mapping(
        feature.get("heightProvenance"), f"buildings[{index}].heightProvenance"
    )
    expected_provenance = expected.as_dict()
    missing_fields = sorted(set(expected_provenance).difference(provenance))
    if missing_fields:
        raise BuildingExportError(
            f"buildings[{index}].heightProvenance is missing fields: {', '.join(missing_fields)}"
        )
    for field, expected_value in expected_provenance.items():
        actual_value = provenance.get(field)
        context = f"buildings[{index}].heightProvenance.{field}"
        if field in {"heightM", "parsedHeightM"} and expected_value is not None:
            actual_number = _finite_number(actual_value, context)
            if not math.isclose(actual_number, expected_value, rel_tol=0, abs_tol=1e-9):
                raise BuildingExportError(
                    f"{context} differs from the resolved retained tags and policy"
                )
        elif actual_value != expected_value:
            raise BuildingExportError(
                f"{context} differs from the resolved retained tags and policy"
            )
    return expected


def _validate_feature_geometry(
    feature: dict[str, Any], index: int, *, half_extent_m: float = 500.0
) -> None:
    geometry = _required_mapping(feature.get("geometry"), f"buildings[{index}].geometry")
    components = geometry.get("polygons")
    if geometry.get("type") != "MultiPolygon" or not isinstance(components, list) or not components:
        raise BuildingExportError(f"buildings[{index}].geometry must contain polygon components")
    polygons = []
    for component_index, component_value in enumerate(components):
        component = _required_mapping(
            component_value, f"buildings[{index}].geometry.polygons[{component_index}]"
        )
        exterior = component.get("exteriorXZ")
        holes = component.get("interiorRingsXZ")
        if not isinstance(exterior, list) or not isinstance(holes, list):
            raise BuildingExportError(f"buildings[{index}] polygon rings are missing")
        rings = [exterior, *holes]
        for ring_index, ring_points in enumerate(rings):
            field = f"buildings[{index}].geometry.polygons[{component_index}].ring[{ring_index}]"
            if not isinstance(ring_points, list) or len(ring_points) < 4:
                raise BuildingExportError(f"{field} must contain a closed polygon ring")
            validated_points: list[list[float]] = []
            for point_index, point in enumerate(ring_points):
                point_field = f"{field}[{point_index}]"
                if not isinstance(point, list) or len(point) != 2:
                    raise BuildingExportError(f"{point_field} must contain local XZ coordinates")
                x = _finite_number(point[0], f"{point_field}[0]")
                z = _finite_number(point[1], f"{point_field}[1]")
                if abs(x) > half_extent_m + 0.001 or abs(z) > half_extent_m + 0.001:
                    raise BuildingExportError(
                        f"{point_field} is outside the {half_extent_m * 2:,.0f} m AOI bounds"
                    )
                validated_points.append([x, z])
            if validated_points[0] != validated_points[-1]:
                raise BuildingExportError(f"{field} must be closed")
            signed_area_twice = sum(
                validated_points[point_index][0] * validated_points[point_index + 1][1]
                - validated_points[point_index + 1][0] * validated_points[point_index][1]
                for point_index in range(len(validated_points) - 1)
            )
            if (ring_index == 0 and signed_area_twice <= 0) or (
                ring_index > 0 and signed_area_twice >= 0
            ):
                raise BuildingExportError(f"{field} has invalid documented winding")
        try:
            polygon = Polygon(exterior, holes)
        except Exception as exc:
            raise BuildingExportError(
                f"buildings[{index}] polygon geometry could not be constructed: {exc}"
            ) from exc
        if (
            polygon.is_empty
            or not polygon.is_valid
            or not math.isfinite(polygon.area)
            or polygon.area <= 0
        ):
            raise BuildingExportError(
                f"buildings[{index}] polygon is empty, invalid, or degenerate"
            )
        polygons.append(polygon)
    try:
        full_geometry = MultiPolygon(polygons)
        valid = full_geometry.is_valid
        area = float(full_geometry.area)
    except Exception as exc:
        raise BuildingExportError(f"buildings[{index}] MultiPolygon is invalid: {exc}") from exc
    if not valid:
        raise BuildingExportError(
            f"buildings[{index}] MultiPolygon components overlap or are invalid"
        )
    area_value = _finite_number(
        feature.get("footprintAreaM2"), f"buildings[{index}].footprintAreaM2"
    )
    if not math.isclose(area, area_value, rel_tol=0, abs_tol=0.002):
        raise BuildingExportError(f"buildings[{index}].footprintAreaM2 does not match its rings")


def build_building_package(
    result: BuildingImportResult,
    aoi_config: AoiConfig,
    source_path: Path,
    source_manifest_path: Path,
    terrain_package_path: Path,
    aoi_geojson_path: Path,
    package_path: Path,
    qa_path: Path,
    preview_path: Path,
    intermediate_path: Path,
) -> dict[str, Any]:
    """Write the data package, report, preview, and raw-tag intermediate atomically."""
    if not isinstance(result, BuildingImportResult):
        raise BuildingExportError("building import result must be a BuildingImportResult")
    if not isinstance(result.buildings, list) or not isinstance(result.qa, dict):
        raise BuildingExportError("building import result must contain feature and QA objects")
    try:
        source = verify_building_source(source_path, source_manifest_path)
        source_manifest = read_source_manifest(source_manifest_path)
        osm_product = source_manifest["osm"]["product"]
        acquisition = source_manifest["osm"]["acquisition"]
    except (BuildingSourceError, KeyError, TypeError) as exc:
        raise BuildingExportError(f"cannot build OSM provenance: {exc}") from exc
    if (
        aoi_config.selection_status != "selected_pending_coverage"
        or aoi_config.coverage_status != "not_checked"
    ):
        raise BuildingExportError(
            "package AOI must preserve selected_pending_coverage / not_checked"
        )
    terrain = _terrain_identity(terrain_package_path, aoi_config)
    ring = _load_aoi_ring(aoi_geojson_path)
    if ring != _configured_aoi_ring(aoi_config):
        raise BuildingExportError("AOI GeoJSON ring differs from the configured anchor and square")
    operation = result.qa.get("coordinateOperation")
    _validate_operation(operation)
    height_policy = result.qa.get("heightPolicy")
    geometry_policy = result.qa.get("geometryPolicy")
    _validate_policies({"height": height_policy, "geometry": geometry_policy})
    buildings_payload = {
        "formatVersion": 1,
        "worldId": aoi_config.id,
        "axisConvention": "+X east, +Y up, -Z north",
        "units": "metres",
        "geometryCoordinates": "local XZ metres; no absolute BNG coordinates per vertex",
        "buildings": result.buildings,
    }
    buildings_bytes = _json_bytes(buildings_payload)
    qa = dict(result.qa)
    qa["package"] = {
        "worldId": aoi_config.id,
        "manifestPath": "manifest.json",
        "buildingsPath": "buildings.json",
        "buildingsByteLength": len(buildings_bytes),
        "buildingsSha256": _sha256(buildings_bytes),
    }
    qa_bytes = _json_bytes(qa)
    package_manifest = {
        "formatVersion": 1,
        "worldId": aoi_config.id,
        **({"sceneProfile": "current_2km"} if aoi_config.profile == "current_2km" else {}),
        "name": "Torquay candidate OSM building footprint package",
        "sourceCrs": "EPSG:27700",
        "axisConvention": "+X east, +Y up, -Z north",
        "units": "metres",
        "aoi": {
            "crs": "EPSG:27700",
            "boundsM": list(aoi_config.bbox_m),
            "widthM": aoi_config.width_m,
            "heightM": aoi_config.height_m,
            "boundaryWgs84": {
                "crs": "EPSG:4326",
                "coordinateOrder": "longitude-latitude",
                "closedRing": True,
                "ring": ring,
            },
            "selectionStatus": aoi_config.selection_status,
            "coverageStatus": aoi_config.coverage_status,
        },
        "terrainIdentity": terrain,
        "coordinateOperation": operation,
        "policies": {"height": height_policy, "geometry": geometry_policy},
        "provenance": {
            "publisher": osm_product["publisher"],
            "product": osm_product["name"],
            "downloadUrl": osm_product["download_page_url"],
            "fileUrl": source_manifest["osm"]["sources"][0]["download_url"],
            "downloadDate": acquisition["download_date"],
            "extractTimestamp": source["pbf_header"]["replication_timestamp"],
            "filename": source["filename"],
            "sizeBytes": source["size_bytes"],
            "sha256": source["sha256"],
            "publisherMd5": source_manifest["osm"]["sources"][0]["publisher_md5"],
            "licence": osm_product["licence"],
            "licenceUrl": osm_product["licence_url"],
            "attribution": OSM_ATTRIBUTION,
            "geofabrikCredit": osm_product["credit"],
            "objectUserNamesOmitted": True,
            "notes": [
                "OSM heights are tagged-but-unverified or explicitly estimated.",
                "The local derived package is ignored and not published.",
                "ODbL obligations must be reviewed before external redistribution.",
            ],
        },
        "generator": {
            "name": "torquay_pipeline.building_export",
            "version": __version__,
            "pythonDependencies": _library_versions(),
            "geosVersion": shapely.geos_version_string,
        },
        "coverage": {
            "selectionStatus": aoi_config.selection_status,
            "coverageStatus": aoi_config.coverage_status,
            "note": "Building extraction counts describe mapped OSM features, not completeness.",
        },
        "buildings": {
            "path": "buildings.json",
            "byteLength": len(buildings_bytes),
            "sha256": _sha256(buildings_bytes),
            "count": len(result.buildings),
        },
        "qaReport": {
            "path": "qa.json",
            "byteLength": len(qa_bytes),
            "sha256": _sha256(qa_bytes),
        },
    }
    manifest_bytes = _json_bytes(package_manifest)
    intermediate_bytes = _json_bytes(result.intermediate)
    manifest_path = package_path / "manifest.json"
    # Validate all caller-provided records and bindings before replacing any outputs.
    with tempfile.TemporaryDirectory(prefix="tvw-building-validate-") as temporary_directory:
        validation_package = Path(temporary_directory)
        (validation_package / "manifest.json").write_bytes(manifest_bytes)
        (validation_package / "buildings.json").write_bytes(buildings_bytes)
        (validation_package / "qa.json").write_bytes(qa_bytes)
        validate_building_package(
            validation_package,
            expected_aoi=aoi_config,
            expected_aoi_ring=ring,
            terrain_package_path=terrain_package_path,
            source_path=source_path,
            source_manifest_path=source_manifest_path,
        )
    try:
        preview_bytes = render_building_preview(result.buildings, qa)
    except Exception as exc:
        raise BuildingExportError(f"cannot render validated building QA preview: {exc}") from exc
    _publish_transaction(
        [
            (package_path / "buildings.json", buildings_bytes),
            (package_path / "qa.json", qa_bytes),
            (qa_path, qa_bytes),
            (preview_path, preview_bytes),
            (intermediate_path, intermediate_bytes),
            (manifest_path, manifest_bytes),
        ],
        manifest_path,
    )
    return {"manifest": package_manifest, "qa": qa, "paths": {"manifest": str(manifest_path)}}


def validate_building_package(
    package_path: Path,
    *,
    expected_aoi: AoiConfig,
    expected_aoi_ring: list[list[float]],
    terrain_package_path: Path,
    source_path: Path,
    source_manifest_path: Path,
) -> dict[str, Any]:
    """Validate package bytes, provenance, policies, features, and approved local inputs."""
    manifest_path = package_path / "manifest.json"
    configured_ring = _configured_aoi_ring(expected_aoi)
    if expected_aoi_ring != configured_ring:
        raise BuildingExportError(
            "provided AOI GeoJSON ring differs from the configured project AOI"
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        content = (package_path / "buildings.json").read_bytes()
        qa_bytes = (package_path / "qa.json").read_bytes()
    except OSError as exc:
        raise BuildingExportError(
            f"cannot read local building package '{package_path}': {exc}"
        ) from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BuildingExportError(f"building package JSON is invalid: {exc}") from exc
    manifest = _required_mapping(manifest, "manifest")
    if manifest.get("formatVersion") != 1 or isinstance(manifest.get("formatVersion"), bool):
        raise BuildingExportError("manifest.formatVersion must be integer 1")
    if manifest.get("worldId") != expected_aoi.id:
        raise BuildingExportError("manifest.worldId does not match the configured AOI")
    if expected_aoi.profile == "current_2km":
        if manifest.get("sceneProfile") != "current_2km":
            raise BuildingExportError("manifest.sceneProfile must be current_2km")
    elif manifest.get("sceneProfile") not in (None, "historical_1km"):
        raise BuildingExportError("historical building package has an incompatible sceneProfile")
    expected_buildings = _required_mapping(manifest.get("buildings"), "manifest.buildings")
    byte_length = expected_buildings.get("byteLength")
    if (
        isinstance(byte_length, bool)
        or not isinstance(byte_length, int)
        or len(content) != byte_length
    ):
        raise BuildingExportError("buildings.json byteLength differs from manifest")
    buildings_hash = _required_string(expected_buildings.get("sha256"), "manifest.buildings.sha256")
    if len(buildings_hash) != 64 or _sha256(content) != buildings_hash:
        raise BuildingExportError("buildings.json SHA-256 differs from manifest")
    count = expected_buildings.get("count")
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise BuildingExportError("manifest.buildings.count must be a positive integer")
    qa_record = _required_mapping(manifest.get("qaReport"), "manifest.qaReport")
    if qa_record.get("path") != "qa.json":
        raise BuildingExportError("manifest.qaReport.path must be package-local qa.json")
    qa_length = qa_record.get("byteLength")
    if isinstance(qa_length, bool) or not isinstance(qa_length, int) or len(qa_bytes) != qa_length:
        raise BuildingExportError("package qa.json byteLength differs from manifest.qaReport")
    qa_hash = _required_string(qa_record.get("sha256"), "manifest.qaReport.sha256")
    if len(qa_hash) != 64 or _sha256(qa_bytes) != qa_hash:
        raise BuildingExportError("package qa.json SHA-256 differs from manifest.qaReport")
    try:
        data = json.loads(content)
        qa = json.loads(qa_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BuildingExportError(
            f"building payload or qa.json contains invalid JSON: {exc}"
        ) from exc
    data = _required_mapping(data, "buildings.json")
    qa = _required_mapping(qa, "qa.json")
    if qa.get("formatVersion") != 1 or isinstance(qa.get("formatVersion"), bool):
        raise BuildingExportError("qa.json.formatVersion must be integer 1")
    if data.get("formatVersion") != 1 or isinstance(data.get("formatVersion"), bool):
        raise BuildingExportError("buildings.json.formatVersion must be integer 1")
    if manifest.get("worldId") != data.get("worldId") or data.get("worldId") != qa.get("aoiId"):
        raise BuildingExportError("manifest, payload, and QA world IDs do not match")
    if data.get("axisConvention") != "+X east, +Y up, -Z north" or data.get("units") != "metres":
        raise BuildingExportError("buildings.json must use the documented local metre axes")
    if data.get("geometryCoordinates") != "local XZ metres; no absolute BNG coordinates per vertex":
        raise BuildingExportError("buildings.json geometry must use local XZ metres")

    features = data.get("buildings")
    if not isinstance(features, list) or len(features) != count or not features:
        raise BuildingExportError("buildings count must be non-empty and match manifest")
    coverage = _required_mapping(manifest.get("coverage"), "manifest.coverage")
    aoi = _required_mapping(manifest.get("aoi"), "manifest.aoi")
    for label, record in (("coverage", coverage), ("aoi", aoi)):
        if (
            record.get("selectionStatus") != "selected_pending_coverage"
            or record.get("coverageStatus") != "not_checked"
        ):
            raise BuildingExportError(f"manifest.{label} must preserve pending AOI status")
    if (
        coverage.get("note")
        != "Building extraction counts describe mapped OSM features, not completeness."
    ):
        raise BuildingExportError("manifest.coverage.note must preserve the mapped-data limitation")
    if aoi.get("crs") != "EPSG:27700":
        raise BuildingExportError("manifest.aoi.crs must be EPSG:27700")
    bounds = aoi.get("boundsM")
    if not isinstance(bounds, list) or len(bounds) != 4:
        raise BuildingExportError("manifest.aoi.boundsM must contain four finite numbers")
    bounds_values = [
        _finite_number(value, f"manifest.aoi.boundsM[{index}]")
        for index, value in enumerate(bounds)
    ]
    if bounds_values != list(expected_aoi.bbox_m):
        raise BuildingExportError("manifest AOI BNG bounds differ from the approved project AOI")
    width = _finite_number(aoi.get("widthM"), "manifest.aoi.widthM")
    height = _finite_number(aoi.get("heightM"), "manifest.aoi.heightM")
    if width != expected_aoi.width_m or height != expected_aoi.height_m:
        raise BuildingExportError("manifest AOI dimensions differ from the approved project AOI")
    west, south, east, north = bounds_values
    if east - west != width or north - south != height:
        raise BuildingExportError("manifest AOI bounds do not match its declared dimensions")
    ring_record = _required_mapping(aoi.get("boundaryWgs84"), "manifest.aoi.boundaryWgs84")
    ring = ring_record.get("ring")
    if (
        ring_record.get("crs") != "EPSG:4326"
        or ring_record.get("coordinateOrder") != "longitude-latitude"
        or ring_record.get("closedRing") is not True
        or not isinstance(ring, list)
        or len(ring) < 5
        or ring[0] != ring[-1]
    ):
        raise BuildingExportError("manifest WGS84 AOI boundary must be a closed lon/lat ring")
    normalized_ring: list[list[float]] = []
    for index, point in enumerate(ring):
        if not isinstance(point, list) or len(point) != 2:
            raise BuildingExportError(f"manifest.aoi.boundaryWgs84.ring[{index}] is malformed")
        longitude = _finite_number(point[0], f"manifest.aoi.boundaryWgs84.ring[{index}][0]")
        latitude = _finite_number(point[1], f"manifest.aoi.boundaryWgs84.ring[{index}][1]")
        if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
            raise BuildingExportError(f"manifest WGS84 boundary ring point {index} is out of range")
        normalized_ring.append([longitude, latitude])
    if normalized_ring != expected_aoi_ring:
        raise BuildingExportError(
            "manifest WGS84 AOI boundary differs from the approved GeoJSON ring"
        )

    actual_terrain = _terrain_identity(terrain_package_path, expected_aoi)
    terrain_identity = _required_mapping(
        manifest.get("terrainIdentity"), "manifest.terrainIdentity"
    )
    if terrain_identity != actual_terrain:
        raise BuildingExportError(
            "manifest terrain identity differs from the actual local terrain package"
        )
    _validate_operation(manifest.get("coordinateOperation"))
    _validate_policies(manifest.get("policies"))
    manifest_policies = _required_mapping(manifest.get("policies"), "manifest.policies")
    height_policy = _required_mapping(manifest_policies.get("height"), "manifest.policies.height")
    if manifest.get("coordinateOperation") != qa.get("coordinateOperation"):
        raise BuildingExportError("manifest coordinateOperation differs from package QA")
    if manifest["policies"].get("height") != qa.get("heightPolicy"):
        raise BuildingExportError("manifest height policy differs from package QA")
    if manifest["policies"].get("geometry") != qa.get("geometryPolicy"):
        raise BuildingExportError("manifest geometry policy differs from package QA")
    qa_package = _required_mapping(qa.get("package"), "qa.package")
    qa_buildings_length = qa_package.get("buildingsByteLength")
    if isinstance(qa_buildings_length, bool) or not isinstance(qa_buildings_length, int):
        raise BuildingExportError("qa.package.buildingsByteLength must be an integer")
    if (
        qa_package.get("worldId") != manifest.get("worldId")
        or qa_package.get("manifestPath") != "manifest.json"
        or qa_package.get("buildingsPath") != "buildings.json"
        or qa_package.get("buildingsByteLength") != len(content)
        or qa_package.get("buildingsSha256") != buildings_hash
    ):
        raise BuildingExportError("package QA payload identity does not match buildings.json")
    qa_counts = _required_mapping(qa.get("counts"), "qa.counts")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in qa_counts.values()
    ):
        raise BuildingExportError("qa.counts must contain nonnegative integer values")
    if qa_counts.get("exported_buildings") != len(features):
        raise BuildingExportError("qa.counts.exported_buildings does not match the package")
    qa_summary = _required_mapping(qa.get("summary"), "qa.summary")
    for field in (
        "aoiAreaM2",
        "buildingFootprintAreaM2",
        "footprintAreaPerAoiKm2",
        "minimumHeightM",
        "maximumHeightM",
        "meanHeightM",
    ):
        _finite_number(qa_summary.get(field), f"qa.summary.{field}")
    if qa_summary.get("densityInterpretation") != (
        "Mapped OSM coverage only; this is not a completeness estimate."
    ):
        raise BuildingExportError("qa.summary.densityInterpretation is required")
    qa_quality = _required_mapping(qa.get("quality"), "qa.quality")
    for field in (
        "rejectedGeometryCount",
        "candidateGeometryRejectionCount",
        "relationAreaAssemblyFailures",
        "nearOverlapCount",
    ):
        value = qa_quality.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise BuildingExportError(f"qa.quality.{field} must be a nonnegative integer")
    for field in ("rejectedGeometrySamples", "exactDuplicateConflicts", "nearOverlapSamples"):
        if not isinstance(qa_quality.get(field), list):
            raise BuildingExportError(f"qa.quality.{field} must be an array")
    if qa_quality.get("taggedHeightsAreUnverified") is not True:
        raise BuildingExportError("qa.quality.taggedHeightsAreUnverified must remain true")
    if not isinstance(qa_quality.get("areaGeometryErrorScope"), str):
        raise BuildingExportError("qa.quality.areaGeometryErrorScope must be documented")
    unsupported = qa_quality.get("unsupportedBuildingRelations")
    if not isinstance(unsupported, list):
        raise BuildingExportError("qa.quality.unsupportedBuildingRelations must be an array")
    for relation_index, relation_value in enumerate(unsupported):
        relation = _required_mapping(
            relation_value, f"qa.quality.unsupportedBuildingRelations[{relation_index}]"
        )
        relation_id = relation.get("osmRelationId")
        member_count = relation.get("memberCount")
        if (
            isinstance(relation_id, bool)
            or not isinstance(relation_id, int)
            or relation_id <= 0
            or isinstance(member_count, bool)
            or not isinstance(member_count, int)
            or member_count < 0
        ):
            raise BuildingExportError(
                f"qa.quality.unsupportedBuildingRelations[{relation_index}] "
                "has invalid numeric identity"
            )
        _required_string(
            relation.get("relationType"), f"unsupported relation {relation_id}.relationType"
        )
        _required_string(relation.get("reason"), f"unsupported relation {relation_id}.reason")
        if not isinstance(relation.get("locationEvidenceNote"), str):
            raise BuildingExportError(
                f"unsupported relation {relation_id} location evidence note is missing"
            )
        way_evidence = relation.get("memberWayEvidence")
        if not isinstance(way_evidence, list):
            raise BuildingExportError(
                f"unsupported relation {relation_id} memberWayEvidence must be an array"
            )
        for way_index, way_value in enumerate(way_evidence):
            way = _required_mapping(
                way_value,
                f"unsupported relation {relation_id}.memberWayEvidence[{way_index}]",
            )
            way_id = way.get("wayId")
            if isinstance(way_id, bool) or not isinstance(way_id, int) or way_id <= 0:
                raise BuildingExportError(
                    f"unsupported relation {relation_id} contains an invalid member way id"
                )
            if "boundsWgs84" in way:
                way_bounds = way["boundsWgs84"]
                if not isinstance(way_bounds, list) or len(way_bounds) != 4:
                    raise BuildingExportError(
                        f"unsupported relation {relation_id} member bounds are malformed"
                    )
                way_bounds = [
                    _finite_number(
                        value, f"unsupported relation {relation_id} way {way_id} bounds[{i}]"
                    )
                    for i, value in enumerate(way_bounds)
                ]
                if way_bounds[0] > way_bounds[2] or way_bounds[1] > way_bounds[3]:
                    raise BuildingExportError(
                        f"unsupported relation {relation_id} member bounds are unordered"
                    )
                node_count = way.get("nodeCountWithLocation")
                if (
                    isinstance(node_count, bool)
                    or not isinstance(node_count, int)
                    or node_count <= 0
                ):
                    raise BuildingExportError(
                        f"unsupported relation {relation_id} member location count is invalid"
                    )
                if not isinstance(way.get("intersectsAcquisitionEnvelope"), bool):
                    raise BuildingExportError(
                        f"unsupported relation {relation_id} envelope result must be boolean"
                    )
    if qa_quality.get("relationAreaAssemblyFailures") != qa_counts.get(
        "relation_area_assembly_failures"
    ):
        raise BuildingExportError("QA relation assembly failure counts disagree")
    height_method_counts = _required_mapping(
        qa_quality.get("heightMethodCounts"), "qa.quality.heightMethodCounts"
    )
    height_clamp_counts = _required_mapping(
        qa_quality.get("heightClampCounts"), "qa.quality.heightClampCounts"
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in [*height_method_counts.values(), *height_clamp_counts.values()]
    ):
        raise BuildingExportError("QA height method and clamp counts must be nonnegative integers")
    if sum(height_method_counts.values()) != len(features):
        raise BuildingExportError("QA height method counts do not match exported buildings")
    map_candidates = qa.get("mapComparisonCandidates")
    if not isinstance(map_candidates, list):
        raise BuildingExportError("qa.mapComparisonCandidates must be an array")
    for candidate_index, candidate_value in enumerate(map_candidates):
        candidate = _required_mapping(
            candidate_value, f"qa.mapComparisonCandidates[{candidate_index}]"
        )
        _required_string(
            candidate.get("group"), f"qa.mapComparisonCandidates[{candidate_index}].group"
        )
        _required_string(
            candidate.get("osmFeatureId"),
            f"qa.mapComparisonCandidates[{candidate_index}].osmFeatureId",
        )
        _finite_number(
            candidate.get("footprintAreaM2"),
            f"qa.mapComparisonCandidates[{candidate_index}].footprintAreaM2",
        )
        point = candidate.get("representativePointWgs84LonLat")
        if not isinstance(point, list) or len(point) != 2:
            raise BuildingExportError(
                f"qa.mapComparisonCandidates[{candidate_index}] point must be lon/lat"
            )
        longitude = _finite_number(
            point[0], f"qa.mapComparisonCandidates[{candidate_index}].longitude"
        )
        latitude = _finite_number(
            point[1], f"qa.mapComparisonCandidates[{candidate_index}].latitude"
        )
        if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
            raise BuildingExportError(
                f"qa.mapComparisonCandidates[{candidate_index}] point is out of range"
            )
        if candidate.get("placementCheckOnly") is not True:
            raise BuildingExportError(
                f"qa.mapComparisonCandidates[{candidate_index}] must remain placement-only"
            )

    try:
        actual_source = verify_building_source(source_path, source_manifest_path)
        source_manifest = read_source_manifest(source_manifest_path)
        osm_product = source_manifest["osm"]["product"]
        osm_acquisition = source_manifest["osm"]["acquisition"]
        osm_source = source_manifest["osm"]["sources"][0]
    except (BuildingSourceError, KeyError, IndexError, TypeError) as exc:
        raise BuildingExportError(f"cannot verify package source provenance: {exc}") from exc
    provenance = _required_mapping(manifest.get("provenance"), "manifest.provenance")
    expected_provenance = {
        "publisher": osm_product["publisher"],
        "product": osm_product["name"],
        "downloadUrl": osm_product["download_page_url"],
        "fileUrl": osm_source["download_url"],
        "downloadDate": osm_acquisition["download_date"],
        "extractTimestamp": actual_source["pbf_header"]["replication_timestamp"],
        "filename": actual_source["filename"],
        "sizeBytes": actual_source["size_bytes"],
        "sha256": actual_source["sha256"],
        "publisherMd5": osm_source["publisher_md5"],
        "licence": osm_product["licence"],
        "licenceUrl": osm_product["licence_url"],
        "attribution": OSM_ATTRIBUTION,
        "geofabrikCredit": osm_product["credit"],
        "objectUserNamesOmitted": True,
    }
    for field, expected_value in expected_provenance.items():
        if provenance.get(field) != expected_value:
            raise BuildingExportError(
                f"manifest.provenance.{field} differs from the verified source manifest"
            )
    source_size = provenance.get("sizeBytes")
    if isinstance(source_size, bool) or not isinstance(source_size, int) or source_size <= 0:
        raise BuildingExportError("manifest.provenance.sizeBytes must be a positive integer")
    for field, length in (("sha256", 64), ("publisherMd5", 32)):
        digest = provenance.get(field)
        if (
            not isinstance(digest, str)
            or len(digest) != length
            or any(char not in "0123456789abcdef" for char in digest.lower())
        ):
            raise BuildingExportError(
                f"manifest.provenance.{field} must be a {length}-character hex digest"
            )
    notes = provenance.get("notes")
    if (
        not isinstance(notes, list)
        or len(notes) < 3
        or any(not isinstance(note, str) for note in notes)
    ):
        raise BuildingExportError(
            "manifest.provenance.notes must document height, publication, and ODbL limits"
        )
    if qa.get("source") != actual_source:
        raise BuildingExportError("qa.source differs from the currently verified source PBF")
    if (
        qa.get("selectionStatus") != "selected_pending_coverage"
        or qa.get("coverageStatus") != "not_checked"
    ):
        raise BuildingExportError(
            "qa AOI status must remain selected_pending_coverage / not_checked"
        )
    geometry_policy = manifest_policies["geometry"]
    if (
        _finite_number(qa.get("acquisitionBufferM"), "qa.acquisitionBufferM")
        != geometry_policy["acquisitionBufferM"]
    ):
        raise BuildingExportError("qa acquisition buffer differs from the recorded geometry policy")
    if (
        _finite_number(qa.get("minimumClippedAreaM2"), "qa.minimumClippedAreaM2")
        != geometry_policy["minimumClippedAreaM2"]
    ):
        raise BuildingExportError("qa minimum area differs from the recorded geometry policy")
    generator = _required_mapping(manifest.get("generator"), "manifest.generator")
    if generator.get("name") != "torquay_pipeline.building_export" or not _required_string(
        generator.get("version"), "manifest.generator.version"
    ):
        raise BuildingExportError("manifest.generator identity is incomplete")
    dependencies = _required_mapping(
        generator.get("pythonDependencies"), "manifest.generator.pythonDependencies"
    )
    if not all(
        isinstance(dependencies.get(name), str) and dependencies[name]
        for name in ("osmium", "shapely", "pyproj", "numpy", "matplotlib")
    ):
        raise BuildingExportError("manifest.generator.pythonDependencies is incomplete")
    _required_string(generator.get("geosVersion"), "manifest.generator.geosVersion")

    seen_ids: set[str] = set()
    resolved_heights: list[HeightResult] = []
    for index, feature_value in enumerate(features):
        feature = _required_mapping(feature_value, f"buildings[{index}]")
        feature_id = _required_string(feature.get("id"), f"buildings[{index}].id")
        if feature_id in seen_ids:
            raise BuildingExportError(f"buildings[{index}] repeats feature id {feature_id}")
        seen_ids.add(feature_id)
        source = _required_mapping(feature.get("source"), f"buildings[{index}].source")
        if not isinstance(source.get("objectType"), str) or source["objectType"] not in {
            "way",
            "relation",
        }:
            raise BuildingExportError(f"buildings[{index}].source.objectType is unsupported")
        if source.get("dataset") != "Geofabrik Devon OpenStreetMap extract":
            raise BuildingExportError(
                f"buildings[{index}].source.dataset is missing or unsupported"
            )
        for field in ("osmId", "version"):
            value = source.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise BuildingExportError(
                    f"buildings[{index}].source.{field} must be a positive integer"
                )
        if feature_id != f"osm:{source['objectType']}:{source['osmId']}":
            raise BuildingExportError(
                f"buildings[{index}].id does not match its OSM source identity"
            )
        if source.get("timestamp") is not None and not isinstance(source.get("timestamp"), str):
            raise BuildingExportError(f"buildings[{index}].source.timestamp must be text or null")
        resolved_heights.append(_validate_height(feature, index, height_policy))
        _validate_feature_geometry(feature, index, half_extent_m=expected_aoi.width_m / 2.0)
        if not isinstance(feature.get("clippedToAoi"), bool):
            raise BuildingExportError(f"buildings[{index}].clippedToAoi must be boolean")
        flags = feature.get("qualityFlags")
        duplicates = feature.get("duplicateReferences")
        tags = feature.get("tags")
        if not isinstance(flags, list) or any(not isinstance(value, str) for value in flags):
            raise BuildingExportError(f"buildings[{index}].qualityFlags must be a string array")
        if not isinstance(duplicates, list) or any(
            not isinstance(value, str) for value in duplicates
        ):
            raise BuildingExportError(
                f"buildings[{index}].duplicateReferences must be a string array"
            )
        if not isinstance(tags, dict) or any(
            not isinstance(key, str) or not isinstance(value, str) for key, value in tags.items()
        ):
            raise BuildingExportError(f"buildings[{index}].tags must map strings to strings")
        building_tag = tags.get("building")
        if not isinstance(building_tag, str) or not building_tag.strip() or building_tag == "no":
            raise BuildingExportError(
                f"buildings[{index}].tags must include an eligible building value"
            )
        if ("clipped_to_aoi" in flags) is not feature["clippedToAoi"]:
            raise BuildingExportError(
                f"buildings[{index}] clipping flag and qualityFlags are inconsistent"
            )
        if feature_id in duplicates:
            raise BuildingExportError(f"buildings[{index}] cannot reference itself as a duplicate")

    resolved_method_counts: dict[str, int] = {}
    resolved_clamp_counts: dict[str, int] = {}
    for resolved in resolved_heights:
        resolved_method_counts[resolved.method] = resolved_method_counts.get(resolved.method, 0) + 1
        if resolved.clamp is not None:
            resolved_clamp_counts[resolved.clamp] = resolved_clamp_counts.get(resolved.clamp, 0) + 1
    if height_method_counts != resolved_method_counts:
        raise BuildingExportError(
            "qa.quality.heightMethodCounts does not match the validated building features"
        )
    if height_clamp_counts != resolved_clamp_counts:
        raise BuildingExportError(
            "qa.quality.heightClampCounts does not match the validated building features"
        )
    resolved_values = [height.height_m for height in resolved_heights]
    expected_summary = {
        "minimumHeightM": min(resolved_values),
        "maximumHeightM": max(resolved_values),
        "meanHeightM": round(sum(resolved_values) / len(resolved_values), 3),
    }
    for field, expected_value in expected_summary.items():
        actual_value = _finite_number(qa_summary.get(field), f"qa.summary.{field}")
        if actual_value != expected_value:
            raise BuildingExportError(
                f"qa.summary.{field} does not match the validated building features"
            )

    return {
        "worldId": manifest["worldId"],
        "buildingCount": len(features),
        "sha256": buildings_hash,
    }
