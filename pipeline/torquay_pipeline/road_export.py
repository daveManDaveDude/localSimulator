"""Deterministic road-ribbon package assembly, validation and QA binding."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.strtree import STRtree

from . import __version__
from .aoi import generate_selection
from .building_export import (
    BuildingExportError,
    _configured_aoi_ring,
    _json_bytes,
    _load_aoi_ring,
    _terrain_identity,
    _validate_operation,
)
from .building_sources import read_source_manifest, verify_building_source
from .config import AoiConfig, validate_stored_selection
from .coordinates import pinned_transformer
from .road_config import RoadConfig, load_road_config
from .road_geometry import (
    FLOAT32_SLIVER_POLICY,
    _polygon_parts,
    build_display_polygons,
    tessellate_display_polygons,
)
from .road_preview import render_road_preview
from .roads import RoadImportError, RoadImportResult, import_osm_roads


class RoadExportError(ValueError):
    """Raised when road package provenance, geometry, or outputs are invalid."""


ROAD_MANIFEST_MAX_BYTES = 64 * 1024
ROAD_QA_MAX_BYTES = 2 * 1024 * 1024
ROAD_PAYLOAD_MAX_BYTES = 32 * 1024 * 1024
ROAD_MAX_WAYS = 100_000
ROAD_MAX_VERTICES = 1_000_000
ROAD_MAX_TRIANGLES = 1_000_000
ROAD_ASSETS = ("roads.json", "qa.json")

OSM_ATTRIBUTION = "© OpenStreetMap contributors; extract provided by Geofabrik GmbH."
OSM_LICENSE_URL = "https://www.openstreetmap.org/copyright"

LANDMARKS = (
    {
        "id": "ne-second-avenue",
        "label": "NE · Second Avenue",
        "buildingWayId": 208552436,
        "longitude": -3.5332476398607215,
        "latitude": 50.480951244856804,
        "targetRoadNames": ["Second Avenue"],
    },
    {
        "id": "nw-baron-lindfield",
        "label": "NW · Baron Road / Lindfield Close",
        "buildingWayId": 193285347,
        "longitude": -3.54291445782617,
        "latitude": 50.48047580317829,
        "targetRoadNames": ["Baron Road", "Lindfield Close"],
    },
    {
        "id": "sw-mount-stuart",
        "label": "SW · Mount Stuart Hospital / St Vincent’s Road / Chapel Court",
        "buildingWayId": 181620525,
        "longitude": -3.5417691183482414,
        "latitude": 50.475127986993755,
        "targetRoadNames": ["St. Vincent's Road", "Chapel Court"],
    },
)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stage: Path | None = None
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
        if stage is not None:
            stage.unlink(missing_ok=True)
        raise RoadExportError(f"cannot atomically write '{path}': {exc}") from exc


def _package_transaction(artifacts: dict[Path, bytes], manifest_path: Path) -> None:
    staged: dict[Path, Path] = {}
    backups: dict[Path, Path] = {}
    replaced: list[Path] = []
    try:
        for target, content in artifacts.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                prefix=f".{target.name}.", suffix=".stage", dir=target.parent, delete=False
            ) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                staged[target] = Path(handle.name)
        order = [path for path in artifacts if path != manifest_path]
        order.append(manifest_path)
        for target in order:
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
        for path in staged.values():
            path.unlink(missing_ok=True)
        for path in backups.values():
            path.unlink(missing_ok=True)


def _terrain_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RoadExportError(f"cannot read local terrain manifest at '{path}': {exc}") from exc
    if not isinstance(value, dict):
        raise RoadExportError("local terrain manifest must be an object")
    return value


def _validate_aoi(
    expected: AoiConfig, geojson_path: Path, terrain: dict[str, Any]
) -> dict[str, Any]:
    selection, _geojson, _markdown = generate_selection(expected)
    validate_stored_selection(
        expected,
        selection["aoi"]["center_easting_m"],
        selection["aoi"]["center_northing_m"],
        selection["aoi"]["bbox_m"],
    )
    ring = _load_aoi_ring(geojson_path)
    configured = _configured_aoi_ring(expected)
    if ring != configured:
        raise RoadExportError(
            "aoi GeoJSON WGS84 boundary differs from the configured candidate AOI"
        )
    terrain_aoi = terrain.get("aoi")
    if not isinstance(terrain_aoi, dict) or terrain_aoi.get("boundsM") != list(expected.bbox_m):
        raise RoadExportError("terrain package AOI bounds differ from the configured candidate AOI")
    return {
        "crs": "EPSG:27700",
        "boundsM": list(expected.bbox_m),
        "centerBngM": list(expected.center_bng_m),
        "widthM": expected.width_m,
        "heightM": expected.height_m,
        "boundaryWgs84": {
            "crs": "EPSG:4326",
            "coordinateOrder": "longitude-latitude",
            "closedRing": True,
            "ring": ring,
        },
        "selectionStatus": expected.selection_status,
        "coverageStatus": expected.coverage_status,
    }


def _terrain_contract(terrain: dict[str, Any], terrain_identity: dict[str, Any]) -> dict[str, Any]:
    heightfield = terrain.get("heightfield")
    origin = terrain.get("origin")
    extent = terrain.get("extentM")
    if (
        not isinstance(heightfield, dict)
        or not isinstance(origin, dict)
        or not isinstance(extent, dict)
    ):
        raise RoadExportError("terrain manifest heightfield, origin, and extent must be objects")
    columns, rows = heightfield.get("columns"), heightfield.get("rows")
    spacing, width, depth = heightfield.get("spacingM"), extent.get("width"), extent.get("depth")
    if (
        isinstance(columns, bool)
        or not isinstance(columns, int)
        or isinstance(rows, bool)
        or not isinstance(rows, int)
        or columns < 2
        or rows < 2
        or not isinstance(spacing, (int, float))
        or isinstance(spacing, bool)
        or not math.isfinite(spacing)
        or spacing <= 0
        or not isinstance(width, (int, float))
        or isinstance(width, bool)
        or not isinstance(depth, (int, float))
        or isinstance(depth, bool)
        or not math.isfinite(width)
        or not math.isfinite(depth)
        or abs((columns - 1) * spacing - width) > 1e-8
        or abs((rows - 1) * spacing - depth) > 1e-8
    ):
        raise RoadExportError("terrain manifest grid dimensions and extents are inconsistent")
    return {
        **terrain_identity,
        "manifestSha256": _sha256(_json_bytes(terrain)),
        "origin": {
            "eastingM": float(origin["eastingM"]),
            "northingM": float(origin["northingM"]),
            "elevationM": float(origin["elevationM"]),
        },
        "extentM": {"width": float(width), "depth": float(depth)},
        "columns": columns,
        "rows": rows,
        "spacingM": float(spacing),
        "axisConvention": terrain.get("axisConvention"),
        "verticalReference": terrain_identity["verticalReference"],
    }


def _source_provenance(source_manifest_path: Path, source_path: Path) -> dict[str, Any]:
    manifest = read_source_manifest(source_manifest_path)
    osm = manifest.get("osm")
    if not isinstance(osm, dict):
        raise RoadExportError("source manifest has no OSM namespace")
    product = osm.get("product")
    acquisition = osm.get("acquisition")
    sources = osm.get("sources")
    if (
        not isinstance(product, dict)
        or not isinstance(acquisition, dict)
        or not isinstance(sources, list)
    ):
        raise RoadExportError("source manifest OSM product, acquisition, or sources is invalid")
    verified = verify_building_source(source_path, source_manifest_path)
    if len(sources) != 1 or not isinstance(sources[0], dict):
        raise RoadExportError("source manifest must bind exactly one recorded OSM PBF")
    record = sources[0]
    return {
        "publisher": product.get("publisher"),
        "product": product.get("name"),
        "downloadPageUrl": product.get("download_page_url"),
        "fileUrl": record.get("download_url"),
        "checksumUrl": record.get("publisher_checksum_url"),
        "acquisitionDate": record.get("download_date"),
        "acquiredAtUtc": record.get("downloaded_at_utc"),
        "filename": verified["filename"],
        "sizeBytes": verified["size_bytes"],
        "sha256": verified["sha256"],
        "publisherMd5": verified["md5"],
        "extractTimestamp": verified["pbf_header"].get("replication_timestamp"),
        "replicationSequence": verified["pbf_header"].get("replication_sequence_number"),
        "generator": verified["pbf_header"].get("generator"),
        "boundsWgs84LonLat": verified["pbf_header"].get("bounds_wgs84_lon_lat"),
        "licence": product.get("licence"),
        "licenceUrl": product.get("licence_url"),
        "attribution": product.get("credit"),
        "attributionRequirement": product.get("attribution_requirement"),
        "userMetadataNote": product.get("metadata_note"),
        "sourceStorage": acquisition.get("source_storage"),
    }


def _building_conflicts(display: dict[str, Any], buildings_path: Path) -> dict[str, Any]:
    if not buildings_path.is_file():
        return {
            "status": "not_checked",
            "buildingFeatureCount": None,
            "intersectingPairs": 0,
            "overlapAreaM2": 0.0,
        }
    try:
        payload = json.loads(buildings_path.read_text(encoding="utf-8"))
        building_records = payload["buildings"]
        building_geometries = []
        building_ids = []
        for feature in building_records:
            polygons = feature["geometry"]["polygons"]
            for polygon in polygons:
                geom = Polygon(polygon["exteriorXZ"], polygon["interiorRingsXZ"])
                if not geom.is_valid:
                    raise ValueError(f"invalid building geometry {feature.get('id')}")
                building_geometries.append(geom)
                building_ids.append(feature["id"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise RoadExportError(f"cannot check road/building source conflicts: {exc}") from exc
    if not building_geometries:
        return {
            "status": "checked",
            "buildingFeatureCount": len(building_records),
            "intersectingPairs": 0,
            "overlapAreaM2": 0.0,
        }
    index = STRtree(building_geometries)
    pairs: set[tuple[int, int, int]] = set()
    area = 0.0
    for display_group, road_geometry in display.items():
        for polygon in _polygon_parts(road_geometry):
            for idx in index.query(polygon):
                building_index = int(idx)
                intersection_area = float(
                    polygon.intersection(building_geometries[building_index]).area
                )
                if intersection_area > 0.001:
                    pairs.add((building_index, display_group, polygon.wkb_hex))
                    area += intersection_area
    return {
        "status": "checked",
        "buildingFeatureCount": len(building_records),
        "intersectingPairs": len(pairs),
        "overlapAreaM2": round(area, 6),
        "interpretation": (
            "Visible source geometry conflicts are reported only; "
            "no road/building repair was applied."
        ),
    }


def _public_feature(feature: dict[str, Any]) -> dict[str, Any]:
    result = dict(feature)
    result.pop("sourceCenterlineXZ", None)
    result.pop("sourceNodeIdsNormalized", None)
    return result


def _landmark_contexts(features: list[dict[str, Any]], aoi: AoiConfig) -> list[dict[str, Any]]:
    """Bind existing building-context markers to nearby highway source ways."""
    to_bng, _operation = pinned_transformer(4326, 27700)
    center_e, center_n = aoi.center_bng_m
    contexts: list[dict[str, Any]] = []
    indexed: list[tuple[dict[str, Any], LineString]] = []
    for feature in features:
        points = feature.get("sourceCenterlineXZ")
        if isinstance(points, list) and len(points) >= 2:
            try:
                line = LineString(points)
            except (TypeError, ValueError):
                continue
            if line.is_valid and line.length > 0:
                indexed.append((feature, line))

    for landmark in LANDMARKS:
        easting, northing = to_bng.transform(
            landmark["longitude"], landmark["latitude"], errcheck=True
        )
        local_point = Point(float(easting) - center_e, center_n - float(northing))
        candidates = [
            (feature, line)
            for feature, line in indexed
            if feature["sourceTags"].get("name") in landmark["targetRoadNames"]
        ]
        named_match = bool(candidates)
        if not candidates:
            candidates = indexed
        if not candidates:
            contexts.append(
                {
                    "id": landmark["id"],
                    "label": landmark["label"],
                    "buildingWayId": landmark["buildingWayId"],
                    "buildingRepresentativeWgs84": [
                        landmark["longitude"],
                        landmark["latitude"],
                    ],
                    "buildingRepresentativeLocalXZ": [
                        float(local_point.x),
                        float(local_point.y),
                    ],
                    "targetRoadNames": landmark["targetRoadNames"],
                    "targetRoadNamePresent": False,
                    "nearestRoad": None,
                    "observation": (
                        "no eligible extracted highway feature is available "
                        "for a placement observation"
                    ),
                }
            )
            continue

        feature, line = min(
            candidates, key=lambda pair: (pair[1].distance(local_point), pair[0]["source"]["osmId"])
        )
        distance_along = line.project(local_point)
        nearest = line.interpolate(distance_along)
        points = feature["sourceCenterlineXZ"]
        node_ids = feature.get("sourceNodeIdsNormalized", feature["source"].get("nodeIds", []))
        segment_index = 0
        cumulative = 0.0
        for index, (first, second) in enumerate(zip(points, points[1:], strict=False)):
            segment_length = math.dist(first, second)
            if distance_along <= cumulative + segment_length + 1e-9:
                segment_index = index
                break
            cumulative += segment_length
        node_pair = node_ids[segment_index : segment_index + 2]
        tags = feature["sourceTags"]
        target_name = tags.get("name")
        observation = (
            "a named target road in the dated extract lies near the existing building-context point"
            if named_match
            else (
                "the named Baron Road / Lindfield Close target was absent from this export; "
                "the nearest eligible source way is recorded without treating it as that road"
            )
        )
        contexts.append(
            {
                "id": landmark["id"],
                "label": landmark["label"],
                "buildingWayId": landmark["buildingWayId"],
                "pointRole": (
                    "existing building representative point, not an inferred road junction"
                ),
                "buildingRepresentativeWgs84": [
                    landmark["longitude"],
                    landmark["latitude"],
                ],
                "buildingRepresentativeLocalXZ": [
                    float(local_point.x),
                    float(local_point.y),
                ],
                "targetRoadNames": landmark["targetRoadNames"],
                "targetRoadNamePresent": named_match,
                "nearestRoad": {
                    "wayId": feature["source"]["osmId"],
                    "name": target_name,
                    "highway": feature["highway"],
                    "nodeIds": list(node_pair),
                    "nearestPointLocalXZ": [float(nearest.x), float(nearest.y)],
                    "distanceFromBuildingRepresentativeM": float(line.distance(local_point)),
                },
                "observation": observation,
                "limitations": (
                    "placement check against one dated OSM extract; "
                    "not an independent survey or completeness measure"
                ),
            }
        )
    return contexts


def build_road_package(
    imported: RoadImportResult,
    aoi: AoiConfig,
    config: RoadConfig,
    source_path: Path,
    source_manifest_path: Path,
    terrain_package_path: Path,
    aoi_geojson_path: Path,
    package_path: Path,
    external_qa_path: Path,
    preview_path: Path,
    intermediate_path: Path,
    buildings_path: Path | None = None,
) -> dict[str, Any]:
    """Build, integrity-bind and atomically publish a local road package and reports."""
    try:
        if len(imported.features) > ROAD_MAX_WAYS:
            raise RoadExportError(f"road feature count exceeds {ROAD_MAX_WAYS:,} ways")
        terrain = _terrain_manifest(terrain_package_path)
        terrain_identity = _terrain_identity(terrain_package_path, aoi)
        terrain_contract = _terrain_contract(terrain, terrain_identity)
        aoi_contract = _validate_aoi(aoi, aoi_geojson_path, terrain)
        source = _source_provenance(source_manifest_path, source_path)
        operation = imported.coordinate_operation
        _validate_operation(operation)
        display_polygons, display_areas = build_display_polygons(imported.features, aoi, config)
        batches, tessellated_areas, mesh_numerics = tessellate_display_polygons(
            display_polygons,
            columns=terrain_contract["columns"],
            rows=terrain_contract["rows"],
            spacing_m=terrain_contract["spacingM"],
            width_m=terrain_contract["extentM"]["width"],
            depth_m=terrain_contract["extentM"]["depth"],
            vertex_limit=ROAD_MAX_VERTICES,
            triangle_limit=ROAD_MAX_TRIANGLES,
        )
    except BuildingExportError as exc:
        raise RoadExportError(f"validated terrain or AOI identity failed: {exc}") from exc
    except (KeyError, TypeError, ValueError, OSError, RuntimeError) as exc:
        if isinstance(exc, RoadExportError):
            raise
        raise RoadExportError(f"road package preparation failed: {exc}") from exc

    source_counts = imported.qa["counts"]
    package_features = [_public_feature(feature) for feature in imported.features]
    road_payload = {
        "formatVersion": 1,
        "worldId": aoi.id,
        "features": package_features,
        "surfaceBatches": batches,
    }
    payload_bytes = _json_bytes(road_payload)
    if len(payload_bytes) > ROAD_PAYLOAD_MAX_BYTES:
        raise RoadExportError(
            f"roads.json is {len(payload_bytes):,} bytes, above the "
            f"{ROAD_PAYLOAD_MAX_BYTES:,}-byte limit"
        )
    total_vertices = sum(len(batch["verticesXZ"]) for batch in batches.values())
    total_triangles = sum(len(batch["indices"]) for batch in batches.values())
    if total_vertices > ROAD_MAX_VERTICES or total_triangles > ROAD_MAX_TRIANGLES:
        raise RoadExportError("combined road mesh exceeds its safe structural limits")

    feature_counts: dict[str, int] = {group: 0 for group in ("vehicular", "cycleway", "path")}
    parts_by_group: dict[str, int] = {group: 0 for group in feature_counts}
    for feature in imported.features:
        group = feature["displayGroup"]
        feature_counts[group] += 1
        parts_by_group[group] += len(feature.get("partIds", []))
    batch_counts = {
        group: {
            "uniqueWayCount": feature_counts[group],
            "clippedCenterlinePartCount": parts_by_group[group],
            "vertexCount": len(batch["verticesXZ"]),
            "triangleCount": len(batch["indices"]),
            "surfaceAreaM2": round(tessellated_areas[group], 6),
            "bufferedAreaBeforePriorityM2": round(display_areas[group], 6),
        }
        for group, batch in batches.items()
    }
    source_features_count = len(imported.features)
    long_segments = []
    for feature in imported.features:
        max_segment = max(
            (
                math.dist(first, second)
                for part in feature["centerlinePartsXZ"]
                for first, second in zip(part, part[1:], strict=False)
            ),
            default=0.0,
        )
        if max_segment > 250:
            long_segments.append(
                {"wayId": feature["source"]["osmId"], "maximumSegmentM": round(max_segment, 3)}
            )

    conflict_report = _building_conflicts(
        display_polygons,
        buildings_path or terrain_package_path / "buildings" / "buildings.json",
    )
    qa = {
        "formatVersion": 1,
        "worldId": aoi.id,
        "status": "pass" if total_triangles > 0 else "fail",
        "selectionStatus": aoi.selection_status,
        "coverageStatus": aoi.coverage_status,
        "source": source,
        "counts": {
            **source_counts,
            "uniqueExportedWays": source_features_count,
            "uniquePartIds": sum(parts_by_group.values()),
            "uniqueRibbonPartIds": sum(
                len(feature.get("ribbonPartIds", [])) for feature in imported.features
            ),
            "float32CollapsedSliverTriangleCount": int(
                mesh_numerics["float32CollapsedSliverTriangleCount"]
            ),
            "surfaceBatchCount": sum(bool(batch["indices"]) for batch in batches.values()),
            "renderVertexCount": total_vertices,
            "renderTriangleCount": total_triangles,
        },
        "displayBatches": batch_counts,
        "areas": {
            "byDisplayGroupM2": {key: round(value, 6) for key, value in tessellated_areas.items()},
            "totalDisjointSurfaceM2": round(sum(tessellated_areas.values()), 6),
            "overlayPriority": ["vehicular", "cycleway", "path"],
            "areaDifferenceWithinDeclaredTolerance": True,
        },
        "meshNumerics": {
            "float32CollapsedSliverTriangleCount": int(
                mesh_numerics["float32CollapsedSliverTriangleCount"]
            ),
            "float32CollapsedSliverAreaM2": round(
                float(mesh_numerics["float32CollapsedSliverAreaM2"]), 12
            ),
            "maximumOmittedAreaM2": 1e-6,
            "policy": FLOAT32_SLIVER_POLICY,
        },
        "longSourceSegmentsOver250m": long_segments,
        "landmarkContexts": _landmark_contexts(imported.features, aoi),
        "buildingSourceConflicts": conflict_report,
        "coordinateOperation": operation,
        "surfacePolicy": {
            "fullWidthsM": {key: float(value) for key, value in sorted(config.widths_m.items())},
            "widthSource": (
                "configured visual estimates; raw width and lanes tags retained but not applied"
            ),
            "buffer": "flat caps, bevel joins, 2.0 bevel limit",
            "clip": "exact unbuffered AOI in EPSG:27700 before terrain triangle subdivision",
            "terrainTriangulation": (
                "constrained Delaunay inside each actual fixed terrain triangle"
            ),
            "surfaceOffsetM": config.surface_offset_m,
            "float32SliverPolicy": FLOAT32_SLIVER_POLICY,
        },
        "interpretation": (
            "Extracted and rendered mapped OSM highway ways are not a completeness measure. "
            "Width is estimated; absent vertical tags imply only a ground-level visual assumption."
        ),
    }
    preview_info = render_road_preview(
        display_polygons, imported.features, qa, terrain_package_path, preview_path
    )
    preview_info["output"] = preview_path.name
    qa["preview"] = preview_info
    qa_bytes = _json_bytes(qa)
    if len(qa_bytes) > ROAD_QA_MAX_BYTES:
        raise RoadExportError("road qa.json exceeds the 2 MiB package limit")

    manifest = {
        "formatVersion": 1,
        "worldId": aoi.id,
        "name": "Local OSM road ribbons on EA terrain (pending candidate AOI)",
        "packageType": "osm-road-ribbons",
        "sourceCrs": "EPSG:27700",
        "axisConvention": "+X east, +Y up, -Z north",
        "units": "metres",
        "aoi": aoi_contract,
        "terrainIdentity": terrain_contract,
        "coordinateOperation": {
            **operation,
        },
        "source": source,
        "policies": {
            "version": 1,
            "acquisitionBufferM": config.acquisition_buffer_m,
            "coordinateQuantizationM": config.coordinate_quantization_m,
            "minimumRibbonAreaM2": config.minimum_ribbon_area_m2,
            "fullWidthsM": {key: float(value) for key, value in sorted(config.widths_m.items())},
            "pathClasses": sorted(config.path_classes),
            "excludedClasses": sorted(config.excluded_classes),
            "groundAssumption": {
                "bridge": "absent or exactly 'no' accepted; otherwise exclude whole way",
                "tunnel": "absent or exactly 'no' accepted; otherwise exclude whole way",
                "covered": "absent or exactly 'no' accepted; otherwise exclude whole way",
                "layer": "absent or strict integer zero accepted; all others excluded",
                "tagAbsence": "visual ground assumption only, not verified elevation",
            },
            "areaSurfacePolicy": "exclude area=yes and any area:highway tag",
            "buffer": {
                "widthMeaning": "estimated full display width; radius is width/2",
                "capStyle": "flat",
                "joinStyle": "bevel",
                "mitreLimit": 2.0,
                "quantization": (
                    "centerline coordinates quantized to configured millimetres before buffering"
                ),
            },
            "clip": (
                "buffered polygons clipped to exact AOI; centerline parts are "
                "also clipped for inspection"
            ),
            "displayPriority": ["vehicular", "cycleway", "path"],
            "triangulation": (
                "fixed TerrainGrid triangles (NW,SW,NE) and (NE,SW,SE); "
                "constrained Delaunay per clipped triangle"
            ),
            "surfaceOffsetM": config.surface_offset_m,
            "float32SliverPolicy": FLOAT32_SLIVER_POLICY,
        },
        "generator": {
            "name": "torquay_pipeline.road_export",
            "version": __version__,
            "shapelyVersion": shapely.__version__,
            "geosVersion": shapely.geos_version_string,
        },
        "limits": {
            "maxManifestBytes": ROAD_MANIFEST_MAX_BYTES,
            "maxQaBytes": ROAD_QA_MAX_BYTES,
            "maxPayloadBytes": ROAD_PAYLOAD_MAX_BYTES,
            "maxWays": ROAD_MAX_WAYS,
            "maxVertices": ROAD_MAX_VERTICES,
            "maxTriangles": ROAD_MAX_TRIANGLES,
        },
        "counts": qa["counts"],
        "assets": {
            "roads": {
                "path": "roads.json",
                "byteLength": len(payload_bytes),
                "sha256": _sha256(payload_bytes),
            },
            "qa": {"path": "qa.json", "byteLength": len(qa_bytes), "sha256": _sha256(qa_bytes)},
        },
        "coverage": {
            "selectionStatus": aoi.selection_status,
            "coverageStatus": aoi.coverage_status,
            "note": "Mapped OSM counts do not establish completeness; overall AOI remains pending.",
        },
        "attribution": {
            "text": OSM_ATTRIBUTION,
            "licence": source.get("licence"),
            "licenceUrl": OSM_LICENSE_URL,
            "geofabrikCredit": "Extract provided by Geofabrik GmbH.",
            "environmentAgency": terrain.get("provenance", {}).get("attribution"),
            "environmentAgencySourceUrl": terrain.get("provenance", {}).get("catalogueUrl"),
        },
    }
    manifest_bytes = _json_bytes(manifest)
    if len(manifest_bytes) > ROAD_MANIFEST_MAX_BYTES:
        raise RoadExportError("road manifest exceeds the 64 KiB package limit")

    package_path.mkdir(parents=True, exist_ok=True)
    try:
        _package_transaction(
            {
                package_path / "roads.json": payload_bytes,
                package_path / "qa.json": qa_bytes,
                package_path / "manifest.json": manifest_bytes,
            },
            package_path / "manifest.json",
        )
        _atomic_write(external_qa_path, qa_bytes)
        _atomic_write(intermediate_path, _json_bytes(imported.intermediate))
    except Exception as exc:
        raise RoadExportError(f"cannot write deterministic road package: {exc}") from exc
    return {
        "manifest": manifest,
        "qa": qa,
        "roads": road_payload,
        "displayPolygons": display_polygons,
        "packagePath": str(package_path.resolve()),
        "payloadSha256": _sha256(payload_bytes),
        "qaSha256": _sha256(qa_bytes),
        "manifestSha256": _sha256(manifest_bytes),
    }


def validate_road_package(
    package_path: Path,
    *,
    expected_aoi: AoiConfig,
    expected_aoi_ring: list[list[float]],
    terrain_package_path: Path,
    source_path: Path,
    source_manifest_path: Path,
    aoi_geojson_path: Path | None = None,
    road_config: RoadConfig | None = None,
) -> dict[str, Any]:
    """Validate bytes and deterministically re-derive the package from the bound source.

    Rebuilding the small local candidate package makes hashes insufficient as a
    source of truth: a caller cannot make edited geometry or counts valid merely
    by refreshing the JSON checksums.
    """
    try:
        manifest_bytes = (package_path / "manifest.json").read_bytes()
        if len(manifest_bytes) > ROAD_MANIFEST_MAX_BYTES:
            raise RoadExportError("manifest exceeds the 64 KiB limit")
        manifest = json.loads(manifest_bytes)
        if not isinstance(manifest, dict):
            raise RoadExportError("manifest must be a JSON object")
        if manifest.get("formatVersion") != 1 or manifest.get("worldId") != expected_aoi.id:
            raise RoadExportError("manifest formatVersion/worldId is unsupported")
        if manifest.get("packageType") != "osm-road-ribbons":
            raise RoadExportError("manifest packageType must be osm-road-ribbons")
        if (
            manifest.get("coverage", {}).get("selectionStatus") == "approved"
            or manifest.get("coverage", {}).get("coverageStatus") == "pass"
        ):
            raise RoadExportError("road package must not claim AOI approval or complete coverage")
        if manifest.get("aoi", {}).get("boundsM") != list(expected_aoi.bbox_m):
            raise RoadExportError("manifest AOI bounds differ from configured candidate")
        if (
            manifest.get("coverage", {}).get("selectionStatus") != "selected_pending_coverage"
            or manifest.get("coverage", {}).get("coverageStatus") != "not_checked"
        ):
            raise RoadExportError(
                "manifest coverage must remain selected_pending_coverage / not_checked"
            )
        expected_ring = _configured_aoi_ring(expected_aoi)
        if manifest.get("aoi", {}).get("boundaryWgs84", {}).get("ring") != expected_ring:
            raise RoadExportError("manifest WGS84 AOI ring differs from the configured candidate")
        if expected_aoi_ring != expected_ring:
            raise RoadExportError(
                "expected GeoJSON WGS84 ring differs from the configured candidate"
            )
        terrain = _terrain_manifest(terrain_package_path)
        terrain_identity = _terrain_contract(
            terrain, _terrain_identity(terrain_package_path, expected_aoi)
        )
        if manifest.get("terrainIdentity") != terrain_identity:
            raise RoadExportError(
                "manifest terrain identity differs from the local terrain package"
            )
        source = _source_provenance(source_manifest_path, source_path)
        if manifest.get("source") != source:
            raise RoadExportError(
                "manifest OSM source identity differs from the verified local PBF"
            )
        for asset_name, maximum in (("roads", ROAD_PAYLOAD_MAX_BYTES), ("qa", ROAD_QA_MAX_BYTES)):
            descriptor = manifest.get("assets", {}).get(asset_name)
            if not isinstance(descriptor, dict) or descriptor.get("path") != f"{asset_name}.json":
                raise RoadExportError(f"manifest assets.{asset_name} path is unsafe or missing")
            data = (package_path / f"{asset_name}.json").read_bytes()
            if len(data) > maximum or len(data) != descriptor.get("byteLength"):
                raise RoadExportError(f"{asset_name}.json byte length is invalid")
            if _sha256(data) != descriptor.get("sha256"):
                raise RoadExportError(f"{asset_name}.json SHA-256 mismatch")
        payload = json.loads((package_path / "roads.json").read_bytes())
        qa = json.loads((package_path / "qa.json").read_bytes())
        if not isinstance(payload, dict) or payload.get("worldId") != expected_aoi.id:
            raise RoadExportError("roads.json worldId differs from the expected AOI")
        if not isinstance(qa, dict) or qa.get("worldId") != expected_aoi.id:
            raise RoadExportError("qa.json worldId differs from the expected AOI")
        if (
            qa.get("selectionStatus") != "selected_pending_coverage"
            or qa.get("coverageStatus") != "not_checked"
        ):
            raise RoadExportError("QA must preserve pending candidate coverage state")
        if qa.get("counts") != manifest.get("counts"):
            raise RoadExportError("QA counts differ from manifest counts")
        features = payload.get("features")
        batches = payload.get("surfaceBatches")
        if not isinstance(features, list) or not isinstance(batches, dict):
            raise RoadExportError("roads.json feature or surface batch collections are invalid")
        if len(features) > ROAD_MAX_WAYS:
            raise RoadExportError("roads.json feature count exceeds the 100,000 way limit")
        if road_config is None:
            config_path = Path(__file__).resolve().parents[2] / "config" / "roads.torquay.json"
            road_config, _root, _raw_config = load_road_config(config_path)
        imported = import_osm_roads(source_path, source_manifest_path, expected_aoi, road_config)
        with tempfile.TemporaryDirectory(prefix="torquay-road-validate-") as temporary_name:
            temporary = Path(temporary_name)
            expected_package = temporary / "package"
            expected_qa = temporary / "qa.json"
            expected_preview = temporary / Path(road_config.preview_path).name
            expected_intermediate = temporary / "intermediate.json"
            geojson_path = aoi_geojson_path
            if geojson_path is None:
                geojson_path = temporary / "aoi.geojson"
                geojson_path.write_text(
                    json.dumps(
                        {
                            "type": "FeatureCollection",
                            "features": [
                                {
                                    "type": "Feature",
                                    "geometry": {"type": "Polygon", "coordinates": [expected_ring]},
                                    "properties": {},
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
            build_road_package(
                imported,
                expected_aoi,
                road_config,
                source_path,
                source_manifest_path,
                terrain_package_path,
                geojson_path,
                expected_package,
                expected_qa,
                expected_preview,
                expected_intermediate,
            )
            for filename in ("manifest.json", "roads.json", "qa.json"):
                if (package_path / filename).read_bytes() != (
                    expected_package / filename
                ).read_bytes():
                    raise RoadExportError(
                        f"{filename} does not match deterministic output re-derived "
                        "from the verified source, AOI, terrain, and policy"
                    )
        return {
            "worldId": expected_aoi.id,
            "featureCount": len(features),
            "batchNames": sorted(batches),
            "roadsSha256": manifest["assets"]["roads"]["sha256"],
            "qaSha256": manifest["assets"]["qa"]["sha256"],
            "status": "package checksums and source bindings valid",
        }
    except RoadExportError:
        raise
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        BuildingExportError,
        RoadImportError,
    ) as exc:
        raise RoadExportError(f"cannot validate road package '{package_path}': {exc}") from exc
