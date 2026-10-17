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
from .building_preview import OSM_ATTRIBUTION, render_building_preview
from .building_sources import BuildingSourceError, read_source_manifest, verify_building_source
from .buildings import BuildingImportResult
from .config import AoiConfig


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


def _terrain_identity(path: Path, expected_aoi: AoiConfig) -> dict[str, Any]:
    manifest_path = path / "manifest.json"
    binary_path = path / "heightfield.f32"
    try:
        terrain = json.loads(manifest_path.read_text(encoding="utf-8"))
        origin = terrain["origin"]
        heightfield = terrain["heightfield"]
        terrain_aoi = terrain["aoi"]
        actual_hash = hashlib.sha256(binary_path.read_bytes()).hexdigest()
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise BuildingExportError(
            f"cannot establish the local EA terrain identity from '{path}': {exc}"
        ) from exc
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
    return {
        "worldId": terrain["id"],
        "origin": origin,
        "heightfieldSha256": actual_hash,
        "heightfieldByteLength": heightfield.get("byteLength"),
        "verticalReference": terrain.get("provenance", {}).get("verticalReference"),
    }


def _library_versions() -> dict[str, str]:
    return {
        package: importlib.metadata.version(package)
        for package in ("osmium", "shapely", "pyproj", "numpy", "matplotlib")
    }


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
    try:
        source = verify_building_source(source_path, source_manifest_path)
        source_manifest = read_source_manifest(source_manifest_path)
        osm_product = source_manifest["osm"]["product"]
        acquisition = source_manifest["osm"]["acquisition"]
    except (BuildingSourceError, KeyError, TypeError) as exc:
        raise BuildingExportError(f"cannot build OSM provenance: {exc}") from exc
    terrain = _terrain_identity(terrain_package_path, aoi_config)
    ring = _load_aoi_ring(aoi_geojson_path)
    buildings_payload = {
        "formatVersion": 1,
        "worldId": aoi_config.id,
        "axisConvention": "+X east, +Y up, -Z north",
        "units": "metres",
        "geometryCoordinates": "local XZ metres; no absolute BNG coordinates per vertex",
        "buildings": result.buildings,
    }
    buildings_bytes = _json_bytes(buildings_payload)
    package_manifest = {
        "formatVersion": 1,
        "worldId": aoi_config.id,
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
        "qaReport": "TVW-009-buildings-qa.json",
    }
    qa = dict(result.qa)
    qa["package"] = {
        "worldId": aoi_config.id,
        "manifestPath": "manifest.json",
        "buildingsPath": "buildings.json",
        "buildingsByteLength": len(buildings_bytes),
        "buildingsSha256": _sha256(buildings_bytes),
    }
    preview_bytes = render_building_preview(result.buildings, qa)
    manifest_bytes = _json_bytes(package_manifest)
    qa_bytes = _json_bytes(qa)
    intermediate_bytes = _json_bytes(result.intermediate)
    manifest_path = package_path / "manifest.json"
    _publish_transaction(
        [
            (package_path / "buildings.json", buildings_bytes),
            (qa_path, qa_bytes),
            (preview_path, preview_bytes),
            (intermediate_path, intermediate_bytes),
            (manifest_path, manifest_bytes),
        ],
        manifest_path,
    )
    return {"manifest": package_manifest, "qa": qa, "paths": {"manifest": str(manifest_path)}}


def validate_building_package(package_path: Path) -> dict[str, Any]:
    """Validate package schema basics, byte length, checksum, identity and AOI status."""
    manifest_path = package_path / "manifest.json"
    buildings_path = package_path / "buildings.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        content = buildings_path.read_bytes()
    except OSError as exc:
        raise BuildingExportError(
            f"cannot read local building package '{package_path}': {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise BuildingExportError(f"building manifest contains invalid JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise BuildingExportError("building manifest must be a JSON object")
    expected = manifest.get("buildings", {})
    if not isinstance(expected, dict):
        raise BuildingExportError("building manifest buildings field must be an object")
    if len(content) != expected.get("byteLength"):
        raise BuildingExportError("buildings.json byteLength differs from manifest")
    if _sha256(content) != expected.get("sha256"):
        raise BuildingExportError("buildings.json SHA-256 differs from manifest")
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise BuildingExportError(f"buildings.json contains invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise BuildingExportError("buildings.json must be a JSON object")
    if manifest.get("formatVersion") != 1 or data.get("formatVersion") != 1:
        raise BuildingExportError("building package formatVersion must be 1")
    if manifest.get("worldId") != data.get("worldId"):
        raise BuildingExportError("building package world IDs do not match")
    if data.get("axisConvention") != "+X east, +Y up, -Z north" or data.get("units") != "metres":
        raise BuildingExportError("buildings.json must use the documented local metre axes")
    if data.get("geometryCoordinates") != "local XZ metres; no absolute BNG coordinates per vertex":
        raise BuildingExportError("buildings.json geometry must be local XZ metres")
    features = data.get("buildings")
    if not isinstance(features, list) or len(features) != expected.get("count") or not features:
        raise BuildingExportError("building count is empty or differs from manifest")
    coverage = manifest.get("coverage")
    aoi = manifest.get("aoi")
    if not isinstance(coverage, dict) or not isinstance(aoi, dict):
        raise BuildingExportError("manifest must include AOI and coverage provenance objects")
    if (
        coverage.get("selectionStatus") != "selected_pending_coverage"
        or coverage.get("coverageStatus") != "not_checked"
        or aoi.get("selectionStatus") != "selected_pending_coverage"
        or aoi.get("coverageStatus") != "not_checked"
    ):
        raise BuildingExportError("building package must preserve the pending AOI status")
    bounds = aoi.get("boundsM")
    if (
        not isinstance(bounds, list)
        or len(bounds) != 4
        or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in bounds)
    ):
        raise BuildingExportError("manifest AOI boundsM must contain four finite values")
    west, south, east, north = (float(value) for value in bounds)
    if east - west != aoi.get("widthM") or north - south != aoi.get("heightM"):
        raise BuildingExportError("manifest AOI bounds do not match its declared dimensions")
    ring_record = aoi.get("boundaryWgs84")
    ring = ring_record.get("ring") if isinstance(ring_record, dict) else None
    if (
        not isinstance(ring, list)
        or len(ring) < 5
        or ring[0] != ring[-1]
        or ring_record.get("coordinateOrder") != "longitude-latitude"
    ):
        raise BuildingExportError(
            "manifest WGS84 AOI boundary must be a closed longitude-latitude ring"
        )
    for index, point in enumerate(ring):
        if (
            not isinstance(point, list)
            or len(point) != 2
            or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in point)
            or not -180 <= point[0] <= 180
            or not -90 <= point[1] <= 90
        ):
            raise BuildingExportError(f"manifest WGS84 boundary ring point {index} is invalid")
    terrain_identity = manifest.get("terrainIdentity")
    terrain_origin = terrain_identity.get("origin") if isinstance(terrain_identity, dict) else None
    if (
        not isinstance(terrain_identity, dict)
        or terrain_identity.get("worldId") != manifest.get("worldId")
        or not isinstance(terrain_identity.get("heightfieldSha256"), str)
        or len(terrain_identity["heightfieldSha256"]) != 64
        or not isinstance(terrain_origin, dict)
        or not all(
            isinstance(terrain_origin.get(key), (int, float)) and math.isfinite(terrain_origin[key])
            for key in ("eastingM", "northingM", "elevationM")
        )
    ):
        raise BuildingExportError(
            "manifest terrain identity and finite terrain origin are required"
        )
    seen_ids: set[str] = set()
    for index, feature in enumerate(features):
        if not isinstance(feature, dict) or not isinstance(feature.get("id"), str):
            raise BuildingExportError(f"buildings[{index}] must have a string id")
        if feature["id"] in seen_ids:
            raise BuildingExportError(f"buildings[{index}] repeats feature id {feature['id']}")
        seen_ids.add(feature["id"])
        source = feature.get("source")
        if (
            not isinstance(source, dict)
            or source.get("objectType") not in {"way", "relation"}
            or not isinstance(source.get("osmId"), int)
            or source["osmId"] <= 0
            or not isinstance(source.get("version"), int)
            or source["version"] <= 0
        ):
            raise BuildingExportError(
                f"buildings[{index}] has incomplete OSM source identity/version"
            )
        if feature.get("heightMethod") not in {
            "osm_height",
            "estimated_levels",
            "estimated_default",
        }:
            raise BuildingExportError(f"buildings[{index}] has an unsupported heightMethod")
        height = feature.get("heightM")
        if not isinstance(height, (int, float)) or not math.isfinite(height) or height <= 0:
            raise BuildingExportError(f"buildings[{index}] heightM must be finite and positive")
        geometry = feature.get("geometry")
        components = geometry.get("polygons") if isinstance(geometry, dict) else None
        if (
            geometry.get("type") != "MultiPolygon"
            or not isinstance(components, list)
            or not components
        ):
            raise BuildingExportError(f"buildings[{index}] has no polygon components")
        polygons = []
        for component_index, component in enumerate(components):
            if not isinstance(component, dict):
                raise BuildingExportError(
                    f"buildings[{index}] polygon {component_index} is malformed"
                )
            exterior = component.get("exteriorXZ")
            holes = component.get("interiorRingsXZ")
            if not isinstance(exterior, list) or not isinstance(holes, list):
                raise BuildingExportError(f"buildings[{index}] polygon rings are missing")
            rings = [exterior, *holes]
            for ring_index, ring_points in enumerate(rings):
                if (
                    not isinstance(ring_points, list)
                    or len(ring_points) < 4
                    or ring_points[0] != ring_points[-1]
                ):
                    raise BuildingExportError(
                        f"buildings[{index}] polygon ring {ring_index} is not a closed polygon ring"
                    )
                if any(
                    not isinstance(point, list)
                    or len(point) != 2
                    or not all(
                        isinstance(value, (int, float)) and math.isfinite(value) for value in point
                    )
                    or abs(point[0]) > 500.001
                    or abs(point[1]) > 500.001
                    for point in ring_points
                ):
                    raise BuildingExportError(
                        f"buildings[{index}] contains invalid or out-of-AOI XZ coordinates"
                    )
                signed_area_twice = sum(
                    ring_points[point_index][0] * ring_points[point_index + 1][1]
                    - ring_points[point_index + 1][0] * ring_points[point_index][1]
                    for point_index in range(len(ring_points) - 1)
                )
                if (ring_index == 0 and signed_area_twice <= 0) or (
                    ring_index > 0 and signed_area_twice >= 0
                ):
                    raise BuildingExportError(f"buildings[{index}] polygon ring winding is invalid")
            polygon = Polygon(exterior, holes)
            if polygon.is_empty or not polygon.is_valid or polygon.area <= 0:
                raise BuildingExportError(
                    f"buildings[{index}] polygon is empty, invalid, or degenerate"
                )
            polygons.append(polygon)
        full_geometry = MultiPolygon(polygons)
        if not full_geometry.is_valid:
            raise BuildingExportError(
                f"buildings[{index}] MultiPolygon components overlap or are invalid"
            )
        area_value = feature.get("footprintAreaM2")
        if (
            not isinstance(area_value, (int, float))
            or not math.isfinite(area_value)
            or not math.isclose(full_geometry.area, area_value, rel_tol=0, abs_tol=0.002)
        ):
            raise BuildingExportError(
                f"buildings[{index}] footprintAreaM2 does not match its rings"
            )
    return {
        "worldId": manifest["worldId"],
        "buildingCount": len(features),
        "sha256": expected["sha256"],
    }
