"""Assemble, clip, localise, and canonicalise OSM building polygons."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import osmium
import shapely
from shapely import Geometry, from_wkb
from shapely.geometry import MultiPolygon, Polygon, box, mapping
from shapely.strtree import STRtree

from .building_heights import HeightPolicy, resolve_building_height
from .building_sources import verify_building_source
from .config import AoiConfig
from .coordinates import pinned_transformer


class BuildingImportError(ValueError):
    """Raised when the OSM area geometry cannot safely produce a building package."""


@dataclass(frozen=True)
class BuildingConfig:
    acquisition_buffer_m: float = 50.0
    minimum_clipped_area_m2: float = 1.0
    height_policy: HeightPolicy = HeightPolicy()

    def validate(self) -> None:
        if (
            isinstance(self.acquisition_buffer_m, bool)
            or not isinstance(self.acquisition_buffer_m, (int, float))
            or not math.isfinite(self.acquisition_buffer_m)
            or self.acquisition_buffer_m < 0
        ):
            raise BuildingImportError("acquisition_buffer_m must be finite and nonnegative")
        if (
            isinstance(self.minimum_clipped_area_m2, bool)
            or not isinstance(self.minimum_clipped_area_m2, (int, float))
            or not math.isfinite(self.minimum_clipped_area_m2)
            or self.minimum_clipped_area_m2 < 0
        ):
            raise BuildingImportError("minimum_clipped_area_m2 must be finite and nonnegative")
        try:
            self.height_policy.validate()
        except ValueError as exc:
            raise BuildingImportError(str(exc)) from exc


@dataclass(frozen=True)
class BuildingImportResult:
    buildings: list[dict[str, Any]]
    intermediate: dict[str, Any]
    qa: dict[str, Any]


def _project(geometry: Geometry, transformer: Any) -> Geometry:
    def transform_coordinates(coordinates: np.ndarray) -> np.ndarray:
        first, second = transformer.transform(coordinates[:, 0], coordinates[:, 1])
        return np.column_stack((first, second))

    return shapely.transform(geometry, transform_coordinates, include_z=False)


def _to_local_xz(geometry: Geometry, center_easting_m: float, center_northing_m: float) -> Geometry:
    def transform_coordinates(coordinates: np.ndarray) -> np.ndarray:
        return np.column_stack(
            (coordinates[:, 0] - center_easting_m, center_northing_m - coordinates[:, 1])
        )

    return shapely.transform(geometry, transform_coordinates, include_z=False)


class _AreaHandler(osmium.SimpleHandler):
    """Collect source building classifications and libosmium-assembled area geometry."""

    def __init__(self, filter_bbox_wgs84: Geometry) -> None:
        super().__init__()
        self.filter_bbox_wgs84 = filter_bbox_wgs84
        self.factory = osmium.geom.WKBFactory()
        self.candidate_relations: dict[int, dict[str, Any]] = {}
        self.areas: list[dict[str, Any]] = []
        self.assembled_building_relations: set[int] = set()
        self.counts: dict[str, int] = {
            "building_ways_tagged": 0,
            "building_no_ways": 0,
            "building_part_only_ways": 0,
            "building_relations_tagged": 0,
            "building_no_relations": 0,
            "building_part_only_relations": 0,
            "area_callbacks": 0,
            "building_areas_assembled": 0,
            "building_relation_areas_assembled": 0,
            "building_no_areas": 0,
            "building_part_only_areas": 0,
            "candidate_areas_in_geographic_filter": 0,
            "area_geometry_errors": 0,
        }
        self.geometry_errors: list[dict[str, Any]] = []

    @staticmethod
    def _tags(obj: Any) -> dict[str, str]:
        return {str(tag.k): str(tag.v) for tag in obj.tags}

    @staticmethod
    def _members(relation: Any) -> list[dict[str, Any]]:
        return [
            {"type": member.type, "ref": int(member.ref), "role": str(member.role)}
            for member in relation.members
        ]

    @staticmethod
    def _timestamp(obj: Any) -> str | None:
        value = getattr(obj, "timestamp", None)
        if value is None:
            return None
        try:
            return value.to_datetime().isoformat().replace("+00:00", "Z")
        except AttributeError:
            return str(value)

    def way(self, way: Any) -> None:
        tags = self._tags(way)
        building = tags.get("building")
        if building is not None:
            if building == "no":
                self.counts["building_no_ways"] += 1
            else:
                self.counts["building_ways_tagged"] += 1
        elif "building:part" in tags:
            self.counts["building_part_only_ways"] += 1

    def relation(self, relation: Any) -> None:
        tags = self._tags(relation)
        building = tags.get("building")
        if building == "no":
            self.counts["building_no_relations"] += 1
        elif building is not None:
            self.counts["building_relations_tagged"] += 1
            self.candidate_relations[int(relation.id)] = {
                "tags": tags,
                "members": self._members(relation),
                "version": int(relation.version),
                "timestamp": self._timestamp(relation),
            }
        elif "building:part" in tags:
            self.counts["building_part_only_relations"] += 1

    def area(self, area: Any) -> None:
        self.counts["area_callbacks"] += 1
        tags = self._tags(area)
        building = tags.get("building")
        if building == "no":
            self.counts["building_no_areas"] += 1
            return
        if building is None:
            if "building:part" in tags:
                self.counts["building_part_only_areas"] += 1
            return
        self.counts["building_areas_assembled"] += 1
        source_type = "way" if bool(area.from_way()) else "relation"
        source_id = int(area.orig_id())
        if source_type == "relation":
            self.assembled_building_relations.add(source_id)
            self.counts["building_relation_areas_assembled"] += 1
        try:
            raw_wkb = self.factory.create_multipolygon(area)
            wkb = bytes.fromhex(raw_wkb) if isinstance(raw_wkb, str) else bytes(raw_wkb)
            geometry = from_wkb(wkb)
        except Exception as exc:
            self.counts["area_geometry_errors"] += 1
            if len(self.geometry_errors) < 100:
                self.geometry_errors.append(
                    {"sourceType": source_type, "sourceId": source_id, "reason": str(exc)}
                )
            return
        if geometry.is_empty or not geometry.intersects(self.filter_bbox_wgs84):
            return
        self.counts["candidate_areas_in_geographic_filter"] += 1
        if source_type == "way":
            source = {}
        else:
            source = self.candidate_relations.get(source_id, {})
        self.areas.append(
            {
                "sourceType": source_type,
                "sourceId": source_id,
                "version": source.get("version", int(area.version)),
                "timestamp": source.get("timestamp", self._timestamp(area)),
                "tags": tags,
                "geometryWgs84": geometry,
            }
        )


class _RelationMemberBoundsHandler(osmium.SimpleHandler):
    """Find locations for the small set of ways referenced by skipped relations."""

    def __init__(self, wanted_way_ids: set[int]) -> None:
        super().__init__()
        self.wanted_way_ids = wanted_way_ids
        self.bounds: dict[int, dict[str, Any]] = {}

    def way(self, way: Any) -> None:
        way_id = int(way.id)
        if way_id not in self.wanted_way_ids:
            return
        points: list[tuple[float, float]] = []
        for node in way.nodes:
            location = node.location
            if location.valid():
                points.append((float(location.lon), float(location.lat)))
        if not points:
            return
        self.bounds[way_id] = {
            "nodeCountWithLocation": len(points),
            "boundsWgs84": [
                min(point[0] for point in points),
                min(point[1] for point in points),
                max(point[0] for point in points),
                max(point[1] for point in points),
            ],
        }


def _ring_is_closed_and_distinct(coordinates: Any) -> bool:
    points = [(float(point[0]), float(point[1])) for point in coordinates]
    return len(points) >= 4 and points[0] == points[-1] and len(set(points[:-1])) >= 3


def _polygon_parts(geometry: Geometry) -> list[Polygon]:
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)
    if hasattr(geometry, "geoms"):
        return [part for child in geometry.geoms for part in _polygon_parts(child)]
    return []


def _valid_source_geometry(geometry: Geometry) -> str | None:
    if geometry.is_empty:
        return "empty geometry"
    if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        return f"unsupported geometry type {geometry.geom_type}"
    if not shapely.is_valid(geometry):
        return f"invalid polygon geometry: {shapely.is_valid_reason(geometry)}"
    if not math.isfinite(geometry.area) or geometry.area <= 0:
        return "geometry area must be finite and positive"
    for polygon in _polygon_parts(geometry):
        rings = [polygon.exterior, *polygon.interiors]
        if any(not _ring_is_closed_and_distinct(ring.coords) for ring in rings):
            return "polygon contains an unclosed or degenerate ring"
        if any(
            not (math.isfinite(float(x)) and math.isfinite(float(y)))
            for ring in rings
            for x, y in ring.coords
        ):
            return "polygon contains non-finite coordinates"
    return None


def _canonical_ring(coordinates: Any, *, counter_clockwise: bool) -> list[list[float]]:
    points = [
        (round(float(x) * 1000) / 1000, round(float(z) * 1000) / 1000) for x, z in coordinates
    ]
    if points and points[0] == points[-1]:
        points.pop()
    compact: list[tuple[float, float]] = []
    for point in points:
        if not compact or point != compact[-1]:
            compact.append(point)
    if len(compact) < 3:
        raise BuildingImportError("1 mm coordinate canonicalisation collapsed a polygon ring")
    signed_area = (
        sum(
            compact[index][0] * compact[(index + 1) % len(compact)][1]
            - compact[(index + 1) % len(compact)][0] * compact[index][1]
            for index in range(len(compact))
        )
        / 2
    )
    if not math.isfinite(signed_area) or signed_area == 0:
        raise BuildingImportError("1 mm coordinate canonicalisation collapsed polygon area")
    if (signed_area > 0) != counter_clockwise:
        compact.reverse()
    rotations = [compact[index:] + compact[:index] for index in range(len(compact))]
    compact = min(rotations)
    compact.append(compact[0])
    return [[x, z] for x, z in compact]


def _canonical_polygon(polygons: list[Polygon]) -> tuple[list[dict[str, Any]], tuple[Any, ...]]:
    canonical: list[dict[str, Any]] = []
    for polygon in polygons:
        exterior = _canonical_ring(polygon.exterior.coords, counter_clockwise=True)
        holes = sorted(
            (_canonical_ring(ring.coords, counter_clockwise=False) for ring in polygon.interiors),
            key=lambda ring: tuple(tuple(point) for point in ring),
        )
        local_polygon = Polygon(exterior, holes)
        if not local_polygon.is_valid or local_polygon.area <= 0:
            raise BuildingImportError(
                "polygon became invalid after 1 mm coordinate canonicalisation"
            )
        canonical.append({"exteriorXZ": exterior, "interiorRingsXZ": holes})
    canonical.sort(
        key=lambda item: (
            tuple(tuple(point) for point in item["exteriorXZ"]),
            tuple(tuple(tuple(point) for point in ring) for ring in item["interiorRingsXZ"]),
        )
    )
    signature = tuple(
        (
            tuple(tuple(point) for point in item["exteriorXZ"]),
            tuple(tuple(tuple(point) for point in ring) for ring in item["interiorRingsXZ"]),
        )
        for item in canonical
    )
    return canonical, signature


def _timestamp_iso(value: Any) -> str | None:
    try:
        return value.to_datetime().isoformat().replace("+00:00", "Z")
    except AttributeError:
        return str(value) if value else None


def _safe_tags(tags: dict[str, str]) -> dict[str, str]:
    relevant = {
        "building",
        "building:part",
        "building:use",
        "height",
        "building:levels",
        "min_height",
        "roof:height",
        "roof:shape",
        "name",
        "addr:street",
        "addr:housenumber",
        "type",
    }
    return {key: tags[key] for key in sorted(relevant.intersection(tags))}


def _near_overlaps(buildings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    geometries = []
    for building in buildings:
        components = building["geometry"]["polygons"]
        geometries.append(
            MultiPolygon(
                [Polygon(item["exteriorXZ"], item["interiorRingsXZ"]) for item in components]
            )
        )
    if not geometries:
        return []
    index = STRtree(geometries)
    overlaps = []
    seen: set[tuple[int, int]] = set()
    for left_index, geometry in enumerate(geometries):
        for right_index_value in index.query(geometry):
            right_index = int(right_index_value)
            if right_index <= left_index or (left_index, right_index) in seen:
                continue
            seen.add((left_index, right_index))
            area = float(geometry.intersection(geometries[right_index]).area)
            if area > 0.001:
                overlaps.append(
                    {
                        "left": buildings[left_index]["id"],
                        "right": buildings[right_index]["id"],
                        "overlapAreaM2": round(area, 3),
                    }
                )
    return overlaps


def _map_comparison_candidates(
    buildings: list[dict[str, Any]],
    center_easting_m: float,
    center_northing_m: float,
    transformer: Any,
) -> list[dict[str, Any]]:
    best: dict[str, tuple[float, dict[str, Any], float, float]] = {}
    for building in buildings:
        components = building["geometry"]["polygons"]
        geometry = MultiPolygon(
            [Polygon(item["exteriorXZ"], item["interiorRingsXZ"]) for item in components]
        )
        point = geometry.representative_point()
        x = float(point.x)
        local_z = float(point.y)
        quadrant = ("N" if local_z < 0 else "S") + ("W" if x < 0 else "E")
        area = float(building["footprintAreaM2"])
        current = best.get(quadrant)
        if current is None or area > current[0]:
            best[quadrant] = (area, building, x, local_z)
    candidates = []
    for quadrant, (area, building, x, local_z) in sorted(best.items()):
        longitude, latitude = transformer.transform(
            center_easting_m + x,
            center_northing_m - local_z,
        )
        candidates.append(
            {
                "group": quadrant,
                "osmFeatureId": building["id"],
                "footprintAreaM2": round(area, 3),
                "representativePointWgs84LonLat": [float(longitude), float(latitude)],
                "placementCheckOnly": True,
                "note": (
                    "Candidate for a manual map placement check; not evidence of OSM completeness."
                ),
            }
        )
    return candidates


def import_osm_buildings(
    source_path: Path,
    source_manifest_path: Path,
    aoi_config: AoiConfig,
    config: BuildingConfig,
) -> BuildingImportResult:
    """Create a deterministic clipped local building feature collection."""
    config.validate()
    if (
        aoi_config.selection_status != "selected_pending_coverage"
        or aoi_config.coverage_status != "not_checked"
    ):
        raise BuildingImportError(
            "overall AOI status must remain selected_pending_coverage / not_checked"
        )
    source_info = verify_building_source(source_path, source_manifest_path)
    to_bng, to_bng_info = pinned_transformer(4326, 27700)
    to_wgs, to_wgs_info = pinned_transformer(27700, 4326)

    west, south, east, north = aoi_config.bbox_m
    aoi = box(west, south, east, north)
    buffered_aoi = aoi.buffer(config.acquisition_buffer_m, quad_segs=8)
    filter_bbox_wgs84 = _project(buffered_aoi, to_wgs).envelope
    handler = _AreaHandler(filter_bbox_wgs84)
    try:
        handler.apply_file(str(source_path))
    except Exception as exc:
        raise BuildingImportError(
            f"PyOsmium area assembly failed for '{source_path.name}': {exc}"
        ) from exc

    area_relation_types = {"multipolygon", "boundary"}
    unsupported_relation_ids = {
        relation_id
        for relation_id, relation in handler.candidate_relations.items()
        if relation["tags"].get("type") not in area_relation_types
    }
    unsupported_member_way_ids = {
        int(member["ref"])
        for relation_id in unsupported_relation_ids
        for member in handler.candidate_relations[relation_id]["members"]
        if member["type"] == "w"
    }
    member_bounds: dict[int, dict[str, Any]] = {}
    member_bounds_error: str | None = None
    if unsupported_member_way_ids:
        try:
            member_handler = _RelationMemberBoundsHandler(unsupported_member_way_ids)
            member_handler.apply_file(str(source_path), locations=True)
            member_bounds = member_handler.bounds
        except Exception as exc:
            member_bounds_error = f"member way locations unavailable: {exc}"

    unsupported_relation_records: list[dict[str, Any]] = []
    for relation_id in sorted(unsupported_relation_ids):
        relation = handler.candidate_relations[relation_id]
        way_evidence = []
        for member in relation["members"]:
            if member["type"] != "w":
                continue
            evidence = member_bounds.get(int(member["ref"]))
            record = {"wayId": int(member["ref"]), "role": member["role"]}
            if evidence is not None:
                bounds = evidence["boundsWgs84"]
                record.update(evidence)
                record["intersectsAcquisitionEnvelope"] = box(*bounds).intersects(filter_bbox_wgs84)
            way_evidence.append(record)
        unsupported_relation_records.append(
            {
                "osmRelationId": relation_id,
                "relationType": relation["tags"].get("type"),
                "reason": (
                    "tagged building relation type is not an area-assembly type; "
                    "it was intentionally excluded from multipolygon area-failure counts"
                ),
                "memberCount": len(relation["members"]),
                "memberWayEvidence": way_evidence,
                "locationEvidenceNote": member_bounds_error
                or "Available member way bounds are evidence only, not a building footprint.",
            }
        )

    accepted_relations = {
        area["sourceId"]
        for area in handler.areas
        if area["sourceType"] == "relation" and area["tags"].get("building") not in {None, "no"}
    }
    relation_member_ways: set[int] = set()
    for relation_id in accepted_relations:
        relation = handler.candidate_relations.get(relation_id, {})
        relation_member_ways.update(
            int(member["ref"]) for member in relation.get("members", []) if member["type"] == "w"
        )

    counts = dict(handler.counts)
    counts.update(
        {
            "excluded_building_no": handler.counts["building_no_ways"]
            + handler.counts["building_no_relations"],
            "excluded_building_part_only": handler.counts["building_part_only_ways"]
            + handler.counts["building_part_only_relations"],
            "relation_member_ways_suppressed": 0,
            "outside_acquisition_buffer": 0,
            "outside_aoi": 0,
            "invalid_geometry": 0,
            "below_minimum_area": 0,
            "relation_area_assembly_failures": len(
                {
                    relation_id
                    for relation_id, relation in handler.candidate_relations.items()
                    if relation["tags"].get("type") in area_relation_types
                    and relation_id not in handler.assembled_building_relations
                }
            ),
            "building_relations_skipped_non_area_type": len(unsupported_relation_ids),
        }
    )
    rejected: list[dict[str, Any]] = list(handler.geometry_errors)
    intermediate_features: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for item in handler.areas:
        source_geom = item["geometryWgs84"]
        source_error = _valid_source_geometry(source_geom)
        if source_error:
            counts["invalid_geometry"] += 1
            rejected.append(
                {
                    "sourceType": item["sourceType"],
                    "sourceId": item["sourceId"],
                    "stage": "source_wgs84",
                    "reason": source_error,
                }
            )
            continue
        projected = _project(source_geom, to_bng)
        projection_error = _valid_source_geometry(projected)
        if projection_error:
            counts["invalid_geometry"] += 1
            rejected.append(
                {
                    "sourceType": item["sourceType"],
                    "sourceId": item["sourceId"],
                    "stage": "projected_bng",
                    "reason": projection_error,
                }
            )
            continue
        if not projected.intersects(buffered_aoi):
            counts["outside_acquisition_buffer"] += 1
            continue
        intermediate_features.append(
            {
                "type": "Feature",
                "id": f"osm-{item['sourceType']}-{item['sourceId']}",
                "properties": {
                    "sourceType": item["sourceType"],
                    "sourceId": item["sourceId"],
                    "tags": item["tags"],
                },
                "geometry": mapping(source_geom),
            }
        )
        if item["sourceType"] == "way" and item["sourceId"] in relation_member_ways:
            counts["relation_member_ways_suppressed"] += 1
            continue
        if not projected.intersects(aoi):
            counts["outside_aoi"] += 1
            continue
        clipped = projected.intersection(aoi)
        clipped_parts = _polygon_parts(clipped)
        if not clipped_parts:
            counts["invalid_geometry"] += 1
            rejected.append(
                {
                    "sourceType": item["sourceType"],
                    "sourceId": item["sourceId"],
                    "stage": "aoi_clip",
                    "reason": f"clipping produced {clipped.geom_type} with no polygon component",
                }
            )
            continue
        local_parts = [
            _to_local_xz(
                polygon,
                aoi_config.center_bng_m[0],
                aoi_config.center_bng_m[1],
            )
            for polygon in clipped_parts
        ]
        try:
            canonical_polygons, signature = _canonical_polygon(local_parts)
        except BuildingImportError as exc:
            counts["invalid_geometry"] += 1
            rejected.append(
                {
                    "sourceType": item["sourceType"],
                    "sourceId": item["sourceId"],
                    "stage": "canonicalize",
                    "reason": str(exc),
                }
            )
            continue
        area_m2 = sum(
            Polygon(polygon["exteriorXZ"], polygon["interiorRingsXZ"]).area
            for polygon in canonical_polygons
        )
        if not math.isfinite(area_m2) or area_m2 < config.minimum_clipped_area_m2:
            counts["below_minimum_area"] += 1
            continue
        height = resolve_building_height(item["tags"], config.height_policy)
        counts["clipped_building_features"] = counts.get("clipped_building_features", 0) + 1
        candidates.append(
            {
                "id": f"osm:{item['sourceType']}:{item['sourceId']}",
                "source": {
                    "dataset": "Geofabrik Devon OpenStreetMap extract",
                    "objectType": item["sourceType"],
                    "osmId": item["sourceId"],
                    "version": item["version"],
                    "timestamp": item["timestamp"],
                },
                "geometry": {"type": "MultiPolygon", "polygons": canonical_polygons},
                "heightM": height.height_m,
                "heightMethod": height.method,
                "heightConfidence": height.confidence,
                "heightProvenance": height.as_dict(),
                "footprintAreaM2": round(area_m2, 3),
                "clippedToAoi": not aoi.covers(projected),
                "qualityFlags": ["clipped_to_aoi"] if not aoi.covers(projected) else [],
                "duplicateReferences": [],
                "tags": _safe_tags(item["tags"]),
                "_signature": signature,
            }
        )

    # Prefer relation areas over member ways and then use stable OSM identity ordering.
    candidates.sort(
        key=lambda item: (
            0 if item["source"]["objectType"] == "relation" else 1,
            item["source"]["osmId"],
        )
    )
    deduplicated: list[dict[str, Any]] = []
    by_signature: dict[tuple[Any, ...], dict[str, Any]] = {}
    duplicate_conflicts: list[dict[str, Any]] = []
    for feature in candidates:
        signature = feature.pop("_signature")
        existing = by_signature.get(signature)
        if existing is None:
            by_signature[signature] = feature
            deduplicated.append(feature)
            continue
        existing["duplicateReferences"].append(feature["id"])
        if existing["tags"] != feature["tags"] or existing["heightM"] != feature["heightM"]:
            duplicate_conflicts.append(
                {"kept": existing["id"], "suppressed": feature["id"], "reason": "tag_conflict"}
            )
            existing["qualityFlags"].append("exact_geometry_duplicate_tag_conflict")
    for feature in deduplicated:
        feature["duplicateReferences"].sort()
        feature["qualityFlags"] = sorted(set(feature["qualityFlags"]))

    if not deduplicated:
        raise BuildingImportError(
            "no valid OSM building footprints at or above the configured clipped-area minimum "
            "intersect the reviewed AOI; no package was written"
        )

    overlaps = _near_overlaps(deduplicated)
    all_components = [
        polygon for feature in deduplicated for polygon in feature["geometry"]["polygons"]
    ]
    height_methods: dict[str, int] = {}
    clamp_counts: dict[str, int] = {}
    for feature in deduplicated:
        height_methods[feature["heightMethod"]] = height_methods.get(feature["heightMethod"], 0) + 1
        clamp = feature["heightProvenance"]["clamp"]
        if clamp:
            clamp_counts[clamp] = clamp_counts.get(clamp, 0) + 1
    counts["clipped_building_features"] = len(candidates)
    counts["exported_buildings"] = len(deduplicated)
    counts["exact_geometry_duplicates_suppressed"] = len(candidates) - len(deduplicated)
    counts["exported_components"] = len(all_components)
    counts["exported_holes"] = sum(len(part["interiorRingsXZ"]) for part in all_components)
    local_area_m2 = sum(feature["footprintAreaM2"] for feature in deduplicated)
    qa = {
        "formatVersion": 1,
        "aoiId": aoi_config.id,
        "selectionStatus": aoi_config.selection_status,
        "coverageStatus": aoi_config.coverage_status,
        "source": source_info,
        "coordinateOperation": {
            "wgs84ToBng": to_bng_info.as_dict(),
            "bngToWgs84": to_wgs_info.as_dict(),
            "axisOrder": "longitude-latitude for geographic input; easting-northing for BNG",
        },
        "acquisitionBufferM": config.acquisition_buffer_m,
        "minimumClippedAreaM2": config.minimum_clipped_area_m2,
        "heightPolicy": {
            "version": 1,
            "levelsToMetres": config.height_policy.levels_to_metres,
            "defaultHeightM": config.height_policy.default_height_m,
            "minimumHeightM": config.height_policy.minimum_height_m,
            "maximumHeightM": config.height_policy.maximum_height_m,
            "precedence": ["height", "building:levels", "configured_default"],
            "taggedHeightConfidence": "tagged_but_unverified",
            "defaultConfidence": "visual_default_estimate",
        },
        "geometryPolicy": {
            "version": 1,
            "acquisitionBufferM": config.acquisition_buffer_m,
            "minimumClippedAreaM2": config.minimum_clipped_area_m2,
            "coordinateQuantizationM": 0.001,
            "exteriorWinding": "counter-clockwise in local XZ coordinates",
            "interiorWinding": "clockwise in local XZ coordinates",
            "invalidGeometryPolicy": "reject without automatic repair",
            "duplicatePolicy": (
                "prefer relation then stable identity; collapse exact canonical geometry"
            ),
            "nearOverlapPolicy": "report; do not merge",
        },
        "counts": counts,
        "quality": {
            "rejectedGeometryCount": len(rejected),
            "candidateGeometryRejectionCount": counts["invalid_geometry"],
            "rejectedGeometrySamples": rejected[:200],
            "relationAreaAssemblyFailures": counts["relation_area_assembly_failures"],
            "unsupportedBuildingRelations": unsupported_relation_records,
            "unsupportedBuildingRelationLocationEvidence": (
                member_bounds_error
                or "Member way bounds are reported when available; they do not assert a footprint."
            ),
            "areaGeometryErrorScope": (
                "libosmium WKB creation errors are observed across the entire Devon source; "
                "when no geometry is returned their AOI location cannot be established."
            ),
            "exactDuplicateConflicts": duplicate_conflicts,
            "nearOverlapCount": len(overlaps),
            "nearOverlapSamples": overlaps[:200],
            "heightMethodCounts": height_methods,
            "heightClampCounts": clamp_counts,
            "taggedHeightsAreUnverified": True,
        },
        "mapComparisonCandidates": _map_comparison_candidates(
            deduplicated,
            aoi_config.center_bng_m[0],
            aoi_config.center_bng_m[1],
            to_wgs,
        ),
        "summary": {
            "aoiAreaM2": aoi_config.width_m * aoi_config.height_m,
            "buildingFootprintAreaM2": round(local_area_m2, 3),
            "footprintAreaPerAoiKm2": round(local_area_m2 / 1_000_000, 6),
            "densityInterpretation": (
                "Mapped OSM coverage only; this is not a completeness estimate."
            ),
            "minimumHeightM": min(feature["heightM"] for feature in deduplicated),
            "maximumHeightM": max(feature["heightM"] for feature in deduplicated),
            "meanHeightM": round(
                sum(feature["heightM"] for feature in deduplicated) / len(deduplicated), 3
            ),
        },
    }
    intermediate = {
        "type": "FeatureCollection",
        "name": "OSM assembled building areas within the 50 m acquisition buffer",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": intermediate_features,
    }
    for item in handler.candidate_relations.values():
        item.clear()
    return BuildingImportResult(deduplicated, intermediate, qa)
