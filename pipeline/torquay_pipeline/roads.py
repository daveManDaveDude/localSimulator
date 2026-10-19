"""Extract ordered, source-backed highway ways from the dated OSM PBF."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import osmium
from shapely.geometry import LineString, box

from .building_sources import verify_building_source
from .config import AoiConfig
from .coordinates import pinned_transformer
from .road_config import RoadConfig


class RoadImportError(ValueError):
    """Raised when dated OSM ways cannot be safely extracted."""


ROAD_TAGS = (
    "highway",
    "name",
    "ref",
    "access",
    "surface",
    "oneway",
    "junction",
    "width",
    "lanes",
    "bridge",
    "tunnel",
    "layer",
    "covered",
    "area",
    "area:highway",
)


@dataclass(frozen=True)
class RoadImportResult:
    features: list[dict[str, Any]]
    intermediate: dict[str, Any]
    qa: dict[str, Any]
    display_polygons: dict[str, Any]
    coordinate_operation: dict[str, Any]


def _timestamp(obj: Any) -> str | None:
    value = getattr(obj, "timestamp", None)
    if value is None:
        return None
    try:
        return value.to_datetime().isoformat().replace("+00:00", "Z")
    except AttributeError:
        return str(value)


def _tags(obj: Any) -> dict[str, str]:
    return {str(tag.k): str(tag.v) for tag in obj.tags}


def _strict_layer(value: str | None) -> tuple[bool, str | None]:
    if value is None:
        return True, None
    if not value or value.strip() != value:
        return False, "ambiguous_layer"
    body = value[1:] if value.startswith(("+", "-")) else value
    if not body.isdigit():
        return False, "ambiguous_layer"
    try:
        layer = int(value, 10)
    except ValueError:
        return False, "ambiguous_layer"
    return (True, None) if layer == 0 else (False, "nonzero_layer")


def ground_skip_reason(tags: dict[str, str]) -> str | None:
    for key, reason in (("bridge", "bridge"), ("tunnel", "tunnel")):
        value = tags.get(key)
        if value is not None and value != "no":
            return f"{reason}_{value or 'ambiguous'}"
    covered = tags.get("covered")
    if covered is not None and covered != "no":
        return f"covered_{covered or 'ambiguous'}"
    _valid, layer_reason = _strict_layer(tags.get("layer"))
    return layer_reason


def _canonical_line_key(points: list[tuple[float, float]]) -> tuple[tuple[int, int], ...]:
    """Normalize a line in millimetres, removing redundant collinear vertices."""
    millimetres = [(round(x * 1000), round(z * 1000)) for x, z in points]
    compact: list[tuple[int, int]] = []
    for point in millimetres:
        if not compact or point != compact[-1]:
            compact.append(point)
    changed = True
    while changed and len(compact) > 2:
        changed = False
        result = [compact[0]]
        for index in range(1, len(compact) - 1):
            a = result[-1]
            b = compact[index]
            c = compact[index + 1]
            ab = (b[0] - a[0], b[1] - a[1])
            bc = (c[0] - b[0], c[1] - b[1])
            if ab[0] * bc[1] - ab[1] * bc[0] == 0 and ab[0] * bc[0] + ab[1] * bc[1] >= 0:
                changed = True
            else:
                result.append(b)
        result.append(compact[-1])
        compact = result
    forward = tuple(compact)
    backward = tuple(reversed(compact))
    return min(forward, backward)


def _line_parts(geometry: Any) -> list[LineString]:
    if geometry.is_empty:
        return []
    if geometry.geom_type == "LineString":
        return [geometry]
    if geometry.geom_type == "MultiLineString" or hasattr(geometry, "geoms"):
        return [part for item in geometry.geoms for part in _line_parts(item)]
    return []


class _HighwayHandler(osmium.SimpleHandler):
    def __init__(self, aoi: AoiConfig, config: RoadConfig, source_path: Path) -> None:
        super().__init__()
        self.aoi_config = aoi
        self.config = config
        self.source_path = source_path
        self.to_bng, self.operation = pinned_transformer(4326, 27700)
        west, south, east, north = aoi.bbox_m
        self.aoi = box(west, south, east, north)
        self.buffered_aoi = self.aoi.buffer(config.acquisition_buffer_m)
        self.center_e, self.center_n = aoi.center_bng_m
        self.counts: dict[str, int] = {
            "highway_ways_seen": 0,
            "included_ground_ways_in_buffer": 0,
            "outside_acquisition_buffer": 0,
            "excluded_classes": 0,
            "excluded_area_surfaces": 0,
            "excluded_ground_assumption": 0,
            "invalid_missing_locations": 0,
            "invalid_too_few_vertices": 0,
            "invalid_transform_or_geometry": 0,
            "duplicate_source_ways": 0,
            "clipped_empty_or_non_line": 0,
            "clipped_ways_with_parts": 0,
        }
        self.exclusion_reasons: dict[str, int] = {}
        self.rejections: list[dict[str, Any]] = []
        self.incomplete_way_ids: list[int] = []
        self.duplicate_records: list[dict[str, Any]] = []
        self._dedupe: dict[tuple[Any, ...], dict[str, Any]] = {}

    def _reject(self, way_id: int, reason: str, count_key: str) -> None:
        self.counts[count_key] += 1
        self.exclusion_reasons[reason] = self.exclusion_reasons.get(reason, 0) + 1
        if len(self.rejections) < 5000:
            self.rejections.append({"wayId": way_id, "reason": reason})

    def way(self, way: Any) -> None:
        tags = _tags(way)
        highway = tags.get("highway")
        if highway is None:
            return
        self.counts["highway_ways_seen"] += 1
        way_id = int(way.id)

        if tags.get("area") == "yes" or "area:highway" in tags:
            self._reject(way_id, "area_highway_surface", "excluded_area_surfaces")
            return
        if highway in self.config.excluded_classes:
            self._reject(way_id, f"excluded_highway_{highway}", "excluded_classes")
            return
        width = self.config.widths_m.get(highway)
        if width is None:
            self._reject(way_id, f"unknown_highway_{highway}", "excluded_classes")
            return
        reason = ground_skip_reason(tags)
        if reason is not None:
            self._reject(way_id, reason, "excluded_ground_assumption")
            return

        node_ids: list[int] = []
        lon_lat: list[tuple[float, float]] = []
        missing: list[int] = []
        for node in way.nodes:
            node_ids.append(int(node.ref))
            location = node.location
            if not location.valid():
                missing.append(int(node.ref))
            else:
                lon_lat.append((float(location.lon), float(location.lat)))
        if missing:
            self.counts["invalid_missing_locations"] += 1
            self.exclusion_reasons["missing_node_location"] = (
                self.exclusion_reasons.get("missing_node_location", 0) + 1
            )
            self.incomplete_way_ids.append(way_id)
            if len(self.rejections) < 5000:
                self.rejections.append(
                    {
                        "wayId": way_id,
                        "reason": "missing_node_location",
                        "missingNodeIds": missing[:20],
                    }
                )
            return
        if len(lon_lat) < 2:
            self._reject(way_id, "fewer_than_two_vertices", "invalid_too_few_vertices")
            return

        try:
            longitudes = [point[0] for point in lon_lat]
            latitudes = [point[1] for point in lon_lat]
            eastings, northings = self.to_bng.transform(longitudes, latitudes, errcheck=True)
            projected = [
                (float(easting), float(northing))
                for easting, northing in zip(eastings, northings, strict=True)
            ]
            if not all(math.isfinite(x) and math.isfinite(y) for x, y in projected):
                raise ValueError("coordinate transform returned non-finite vertices")
            source_line = LineString(projected)
            if not source_line.is_valid or source_line.length <= 0:
                raise ValueError("projected source way is invalid or has zero length")
        except Exception as exc:
            self._reject(
                way_id, f"invalid_transform_or_geometry:{exc}", "invalid_transform_or_geometry"
            )
            return

        if not source_line.intersects(self.buffered_aoi):
            self.counts["outside_acquisition_buffer"] += 1
            return

        local_source: list[tuple[float, float]] = []
        normalized_node_ids: list[int] = []
        for node_id, (easting, northing) in zip(node_ids, projected, strict=True):
            x = (
                round((easting - self.center_e) / self.config.coordinate_quantization_m)
                * self.config.coordinate_quantization_m
            )
            z = (
                round((self.center_n - northing) / self.config.coordinate_quantization_m)
                * self.config.coordinate_quantization_m
            )
            if not local_source or (x, z) != local_source[-1]:
                local_source.append((x, z))
                normalized_node_ids.append(node_id)
        if len(set(local_source)) < 2:
            self._reject(way_id, "quantization_collapsed_way", "invalid_too_few_vertices")
            return
        local_line = LineString(local_source)
        if not local_line.is_valid or local_line.length <= 0:
            self._reject(way_id, "invalid_after_quantization", "invalid_transform_or_geometry")
            return

        exact_aoi_local = box(
            self.aoi_config.bbox_m[0] - self.center_e,
            self.center_n - self.aoi_config.bbox_m[3],
            self.aoi_config.bbox_m[2] - self.center_e,
            self.center_n - self.aoi_config.bbox_m[1],
        )
        clipped = local_line.intersection(exact_aoi_local)
        parts = _line_parts(clipped)
        parts = [part for part in parts if part.length > 1e-9 and len(set(part.coords)) >= 2]
        parts.sort(key=lambda part: (tuple(part.bounds), tuple(part.coords)))
        # A wide ribbon may enter the AOI while its centerline remains outside it.
        raw_ribbon = local_line.buffer(width / 2, cap_style="flat", join_style="bevel", quad_segs=1)
        if not raw_ribbon.intersects(exact_aoi_local):
            self.counts["clipped_empty_or_non_line"] += 1
            # Acquired context that does not enter the exact AOI is not rendered.
            self.exclusion_reasons["outside_exact_aoi"] = (
                self.exclusion_reasons.get("outside_exact_aoi", 0) + 1
            )
            return

        group = (
            "cycleway"
            if highway == "cycleway"
            else ("path" if highway in self.config.path_classes else "vehicular")
        )
        # Normalize only the identity key; retain the unmodified source direction and one-way tag.
        key = (highway, float(width), group, _canonical_line_key(local_source))
        feature = {
            "id": f"way/{way_id}",
            "source": {
                "dataset": "OpenStreetMap",
                "objectType": "way",
                "osmId": way_id,
                "version": int(way.version),
                "timestamp": _timestamp(way),
                "nodeIds": node_ids,
            },
            "highway": highway,
            "displayGroup": group,
            "estimatedWidthM": float(width),
            "widthMethod": "configured_visual_estimate",
            "widthEvidence": {
                "rawWidth": tags.get("width"),
                "rawLanes": tags.get("lanes"),
                "usedRawTags": False,
                "note": (
                    "Width is a configured visual estimate; OSM width/lanes "
                    "are retained but not used."
                ),
            },
            "groundAssumption": "ground_assumed_from_absent_or_explicit_no_vertical_tags",
            "sourceTags": {key: tags[key] for key in ROAD_TAGS if key in tags},
            "sourceCenterlineXZ": [[float(x), float(z)] for x, z in local_source],
            "sourceNodeIdsNormalized": normalized_node_ids,
            "centerlinePartsXZ": [[[float(x), float(z)] for x, z in part.coords] for part in parts],
            "partIds": [f"way/{way_id}/part/{index:03d}" for index in range(len(parts))],
            "clippedToAoi": True,
            "duplicateWayIds": [],
        }
        previous = self._dedupe.get(key)
        if previous is not None:
            winner, duplicate = sorted(
                (previous, feature), key=lambda item: item["source"]["osmId"]
            )
            winner["duplicateWayIds"].append(duplicate["source"]["osmId"])
            winner["duplicateWayIds"].sort()
            self._dedupe[key] = winner
            self.duplicate_records.append(
                {
                    "winnerWayId": winner["source"]["osmId"],
                    "suppressedWayId": duplicate["source"]["osmId"],
                }
            )
            self.counts["duplicate_source_ways"] += 1
            return
        self._dedupe[key] = feature
        self.counts["included_ground_ways_in_buffer"] += 1
        self.counts["clipped_ways_with_parts"] += 1


def import_osm_roads(
    source_path: Path,
    source_manifest_path: Path,
    aoi_config: AoiConfig,
    config: RoadConfig,
) -> RoadImportResult:
    """Read ordered way locations from the verified extract and buffer exact clipped lines."""
    config.validate()
    if (
        aoi_config.selection_status != "selected_pending_coverage"
        or aoi_config.coverage_status != "not_checked"
    ):
        raise RoadImportError(
            "overall AOI status must remain selected_pending_coverage / not_checked"
        )
    source_info = verify_building_source(source_path, source_manifest_path)
    handler = _HighwayHandler(aoi_config, config, source_path)
    try:
        handler.apply_file(str(source_path), locations=True, idx="flex_mem")
    except Exception as exc:
        raise RoadImportError(
            f"PyOsmium could not resolve complete highway way geometry in "
            f"'{source_path.name}': {exc}"
        ) from exc
    _to_wgs84, reverse_operation = pinned_transformer(27700, 4326)

    features = sorted(handler._dedupe.values(), key=lambda item: item["source"]["osmId"])
    handler.counts["unique_exported_ways"] = len(features)
    handler.counts["duplicate_contributor_ids"] = sum(
        len(feature["duplicateWayIds"]) for feature in features
    )
    handler.counts["incomplete_highway_way_ids_recorded"] = len(handler.incomplete_way_ids)
    intermediate = {
        "formatVersion": 1,
        "sourceFilename": source_info["filename"],
        "sourceSha256": source_info["sha256"],
        "pbfHeader": source_info["pbf_header"],
        "ways": features,
        "rejections": sorted(handler.rejections, key=lambda item: (item["wayId"], item["reason"])),
        "incompleteWayIds": sorted(handler.incomplete_way_ids),
        "duplicates": sorted(
            handler.duplicate_records,
            key=lambda item: (item["winnerWayId"], item["suppressedWayId"]),
        ),
    }
    qa = {
        "counts": dict(sorted(handler.counts.items())),
        "exclusionReasons": dict(sorted(handler.exclusion_reasons.items())),
        "rejections": intermediate["rejections"],
        "duplicates": intermediate["duplicates"],
        "sourceRejectionsTruncated": max(
            0, sum(handler.exclusion_reasons.values()) - len(handler.rejections)
        ),
        "sourceContext": {
            "waysSeen": handler.counts["highway_ways_seen"],
            "featureIds": [feature["id"] for feature in features],
            "incompleteWayIds": intermediate["incompleteWayIds"],
        },
    }
    # Surface polygons and display batches are produced by road_geometry after extraction.
    operation = {
        "axisOrder": "longitude-latitude for geographic input; easting-northing for BNG",
        "wgs84ToBng": handler.operation.as_dict(),
        "bngToWgs84": reverse_operation.as_dict(),
    }
    return RoadImportResult(features, intermediate, qa, {}, operation)
