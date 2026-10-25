"""Offline local-frame Teignmouth candidate construction and staged gates."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon, box
from shapely.strtree import STRtree

from .road_surface import PreviewConfig, _line_point_tangent, _sample_grid, load_release_inputs
from .road_surface_float32_frame import Float32LocalFrame, encode_indices, triangle_normal_y
from .road_surface_topology import (
    PlanarMesh,
    SourceOverlapIndex,
    TopologyError,
    _plane_coefficients,
    _polygon_parts,
    build_constrained_mesh,
)
from .teignmouth_corridor_continuation import (
    LATERALS,
    Chart,
    field_height,
    make_chart,
    section_stations,
    section_vectors,
)
from .teignmouth_corridor_prototype import (
    ANCHOR,
    END,
    RELEASE_ID,
    START,
    STEP,
    Corridor,
    gaussian_profile,
)

CONFIG_RELATIVE_PATH = Path("config/road-surface-teignmouth-float32.json")
CANDIDATE_OUTPUT = "data/generated/teignmouth-float32-topology"
LIMITS = {
    "absolute_terrain_change_m_strict": 6.5,
    "positive_added_edge_gradient_m_per_m_strict": 1.0,
    "full_width_cross_slope_percent_max": 5.0,
    "full_width_height_span_m_max": 0.30,
    "centerline_source_height_deviation_m_max": 2.0,
    "absolute_longitudinal_grade_percent_max": 10.0,
    "building_p95_displacement_m_max": 0.183,
    "building_max_displacement_m_max": 2.424,
    "newton_legacy_base_displacement_m_max": 0.05,
    "road_drape_error_m_max": 0.001,
    "walk_eye_clearance_m": [1.65, 1.75],
}
EXPECTED_RECIPE = {
    "shoulder_m": 1.0,
    "blend_min_m": 2.0,
    "blend_max_m": 12.0,
    "slope_horizontal_per_vertical": 2.0,
    "gaussian_sigma_m": 12.0,
    "profile_step_m": 2.0,
    "longitudinal_fade_m": 32.0,
    "influence_buffer_m": 35.0,
    "fine_mesh_spacing_m": 0.5,
    "assessment_station_start_m": 140.0,
    "assessment_station_end_m": 155.0,
    "registered_anchor_station_m": 148.15104603556912,
}
EXPECTED_PREVIEW = {
    "transition_distance_factor": 1.0,
    "ambiguity_distance_m": 2.0,
    "ambiguity_height_difference_m": 1.0,
    "maximum_changed_height_m": 10.0,
    "fallback_absolute_change_m": 5.0,
    "fallback_added_gradient_m_per_m": 1.0,
    "fallback_minimum_region_area_m2": 8.0,
    "fallback_fade_distance_m": 32.0,
}
EXPECTED_BOUNDS = (-182.0, -136.0, -98.0, -54.0)


class Float32CandidateError(ValueError):
    """The candidate contract or a required geometry stage is invalid."""


@dataclass(frozen=True)
class CandidateConfig:
    issue_id: str
    release_id: str
    output_directory: str
    frame: Float32LocalFrame
    bounds_global_xz_m: tuple[float, float, float, float]
    recipe: dict[str, Any]
    limits: dict[str, Any]
    preview: PreviewConfig


@dataclass(frozen=True)
class StoredCandidate:
    """Candidate identity is its stored local Float32 vertices and indices."""

    frame: Float32LocalFrame
    local_positions_xyz_f32: np.ndarray
    triangles_u32: np.ndarray
    reconstructed_world_xyz_f64: np.ndarray
    source_y_f32: np.ndarray
    mesh_world64: PlanarMesh
    source_heights_f64: np.ndarray
    gate_reports: dict[str, dict[str, Any]]

    @property
    def candidate_y_f32(self) -> np.ndarray:
        return self.local_positions_xyz_f32[:, 1]


def _same(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and set(actual) == set(expected)
            and all(_same(actual[key], value) for key, value in expected.items())
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(_same(a, e) for a, e in zip(actual, expected, strict=True))
        )
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return (
            isinstance(actual, (int, float)) and not isinstance(actual, bool) and actual == expected
        )
    return type(actual) is type(expected) and actual == expected


GATE_NAMES = (
    "chartSupportCompleteness",
    "requiredTreatmentSupport",
    "treatmentSupportClassification",
    "storedLocalTopology",
    "sourcePerimeterAndPlanes",
    "sourceOverlayAndGradients",
    "actualFloat32Sections",
    "influenceWideRoadOwnership",
    "completeBuildingContact",
    "sharedRoadBuildingWalkSurface",
    "independentDeterministicConfirmation",
)


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _write_gate(evidence: Path | None, name: str, report: dict[str, Any]) -> None:
    if evidence is None:
        return
    state_path = evidence / "gate-state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {key: {"passes": False, "status": "NOT_EVALUATED"} for key in GATE_NAMES}
    state[name] = report
    _write_json(state_path, state)
    _write_json(evidence / "gates" / f"{name}.json", report)


def _write_failure(evidence: Path | None, exc: BaseException) -> None:
    if evidence is None:
        return
    try:
        state = json.loads((evidence / "gate-state.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {key: {"passes": False, "status": "NOT_EVALUATED"} for key in GATE_NAMES}
    for name in GATE_NAMES:
        if state.get(name, {}).get("status") == "NOT_EVALUATED":
            state[name] = {
                "passes": False,
                "status": "UNAVAILABLE_AFTER_FAILURE",
                "reason": f"{type(exc).__name__}: {exc}",
            }
    _write_json(evidence / "gate-state.json", state)
    _write_json(
        evidence / "candidate-failure.json",
        {"errorType": type(exc).__name__, "errorMessage": str(exc)},
    )


def _persist_construction(mesh: PlanarMesh, evidence: Path | None) -> None:
    if evidence is None:
        return
    vertices64 = np.asarray(mesh.vertices_xz, dtype="<f8")
    vertices32 = np.asarray(mesh.vertices_xz, dtype="<f4")
    faces = np.asarray(mesh.triangles, dtype="<u4")
    (evidence / "construction-local-xz.f64").write_bytes(vertices64.tobytes())
    (evidence / "construction-stored-local-xz.f32").write_bytes(vertices32.tobytes())
    (evidence / "construction-indices.u32").write_bytes(encode_indices(faces))
    (evidence / "construction-constraints.u32").write_bytes(
        np.ascontiguousarray(mesh.constraint_edges, dtype="<u4").tobytes()
    )
    (evidence / "construction-boundary.u32").write_bytes(
        np.ascontiguousarray(mesh.boundary_edges, dtype="<u4").tobytes()
    )
    _write_json(
        evidence / "construction-stage.json",
        {
            "status": "COMPLETE",
            "vertices": len(vertices64),
            "triangles": len(faces),
            "constraintEdges": len(mesh.constraint_edges),
            "boundaryEdges": len(mesh.boundary_edges),
            "rawConstructionCoordinatesPersisted": True,
            "storedLocalFloat32CoordinatesPersisted": True,
        },
    )


def _persist_chart(chart: Chart, evidence: Path | None) -> None:
    if evidence is None:
        return
    arrays = {
        "chart-stations.f64": np.asarray(chart.stations, dtype="<f8").tobytes(),
        "chart-points.xz.f64": np.asarray(chart.points, dtype="<f8").tobytes(),
        "chart-fields.station-lateral.f64": np.asarray(chart.fields, dtype="<f8").tobytes(),
        "chart-indices.u32": encode_indices(np.asarray(chart.triangles, dtype="<u4")),
    }
    identities = {}
    for name, content in arrays.items():
        (evidence / name).write_bytes(content)
        identities[name] = {
            "byteLength": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    _write_json(
        evidence / "chart-stage.json",
        {
            "status": "COMPLETE",
            "stationCount": len(chart.stations),
            "pointCount": len(chart.points),
            "triangleCount": len(chart.triangles),
            "chartArrays": identities,
        },
    )


def validate_chart_support(
    corridor: Corridor, chart: Chart
) -> tuple[dict[str, Any], shapely.Geometry]:
    """Prove the frozen station/lateral chart has complete, owned triangular support."""
    reasons = []
    part = np.asarray(corridor.part, dtype=np.float64)
    cumulative, vectors = section_vectors(part)
    expected_stations = section_stations(cumulative)
    expected_fields = np.asarray(
        [(station, lateral) for station in expected_stations for lateral in LATERALS],
        dtype=np.float64,
    )
    expected_points = []
    for station in expected_stations:
        center = np.asarray(_line_point_tangent(corridor.part, float(station))[0])
        vector = np.asarray([np.interp(station, cumulative, vectors[:, axis]) for axis in (0, 1)])
        expected_points.extend(center + lateral * vector for lateral in LATERALS)
    expected_points = np.asarray(expected_points, dtype=np.float64)
    column_count = len(LATERALS)
    expected_triangles = []
    for row in range(len(expected_stations) - 1):
        for column in range(column_count - 1):
            a = row * column_count + column
            b, c, d = a + column_count, a + 1, a + column_count + 1
            expected_triangles.extend(((a, b, c), (b, d, c)))
    expected_triangles = np.asarray(expected_triangles, dtype="<u4")

    if not np.array_equal(np.asarray(chart.stations, dtype=np.float64), expected_stations):
        reasons.append("chart station list does not match frozen 108–187m fade support")
    if not np.array_equal(np.asarray(chart.fields, dtype=np.float64), expected_fields):
        reasons.append("chart station/lateral fields are incomplete or reordered")
    if not np.array_equal(np.asarray(chart.points, dtype=np.float64), expected_points):
        reasons.append("chart geometry does not match the frozen source-normal support")
    if not np.array_equal(np.asarray(chart.triangles, dtype="<u4"), expected_triangles):
        reasons.append("chart triangle ownership does not cover the complete support")

    expected_polygons = shapely.polygons(expected_points[expected_triangles])
    support = shapely.union_all(expected_polygons)
    overlap_area = float(np.sum(shapely.area(expected_polygons)) - support.area)
    if len(chart.polygons) != len(expected_polygons):
        reasons.append("chart polygon count differs from complete expected triangulation")
    else:
        try:
            actual_support = shapely.union_all(chart.polygons)
            if (
                not actual_support.is_valid
                or support.symmetric_difference(actual_support).area > 1e-7
            ):
                reasons.append("chart triangle polygons do not cover the expected support")
        except Exception as exc:
            reasons.append(f"chart polygon union is invalid: {type(exc).__name__}: {exc}")
    if not support.is_valid or support.is_empty or overlap_area > 1e-7:
        reasons.append("expected chart support is invalid, empty or overlapping")

    owner_failures = []
    for index, (point, expected_field) in enumerate(
        zip(expected_points, expected_fields, strict=True)
    ):
        try:
            owned_field = chart.locate(point)
        except Exception as exc:
            owner_failures.append({"index": index, "worldXZ": point.tolist(), "error": str(exc)})
            continue
        if owned_field is None or not np.allclose(owned_field, expected_field, rtol=0.0, atol=1e-6):
            owner_failures.append(
                {
                    "index": index,
                    "worldXZ": point.tolist(),
                    "expectedStationLateral": expected_field.tolist(),
                    "actualStationLateral": None if owned_field is None else list(owned_field),
                }
            )
    if owner_failures:
        reasons.append("one or more expected chart support vertices have no correct triangle owner")

    report = {
        "passes": not reasons,
        "status": "MEASURED_FROZEN_CHART_SUPPORT",
        "stationRangeM": [float(expected_stations[0]), float(expected_stations[-1])],
        "lateralRangeM": [float(LATERALS[0]), float(LATERALS[-1])],
        "expectedStationCount": len(expected_stations),
        "expectedPointCount": len(expected_points),
        "expectedTriangleCount": len(expected_triangles),
        "expectedSupportAreaM2": float(support.area),
        "triangleOverlapAreaM2": overlap_area,
        "ownerFailureCount": len(owner_failures),
        "ownerFailures": owner_failures,
        "reasons": reasons,
    }
    return report, support


def classify_treatment_support(
    point_xz: np.ndarray,
    influence: shapely.Geometry,
    chart_support: shapely.Geometry,
    chart: Chart,
) -> tuple[str, tuple[float, float] | None]:
    """Classify candidate vertices without extrapolating beyond frozen chart support."""
    point = np.asarray(point_xz, dtype=np.float64)
    if point.shape != (2,) or not np.isfinite(point).all():
        raise Float32CandidateError("treatment-support query must be finite world X/Z")
    location = Point(point)
    if not influence.contains(location):
        return "SOURCE_OUTSIDE_INFLUENCE", None
    if not chart_support.covers(location):
        return "SOURCE_INSIDE_INFLUENCE_OUTSIDE_CHART_SUPPORT", None
    field = chart.locate(point)
    if field is None:
        raise Float32CandidateError(
            f"chart support contains {point.tolist()} but no triangle owner is available"
        )
    return "CHART_OWNED", field


def required_treatment_support_report(
    corridor: Corridor, chart: Chart, chart_support: shapely.Geometry
) -> dict[str, Any]:
    """Require complete chart ownership over carriageway and shoulder section samples."""
    cumulative, vectors = section_vectors(np.asarray(corridor.part, dtype=np.float64))
    stations = set(float(value) for value in np.arange(START, END + 1e-9, 0.25))
    stations.update((START, END, ANCHOR))
    stations.update(float(value) for value in corridor.stations if START <= value <= END)
    stations = np.asarray(sorted(stations), dtype=np.float64)
    lateral = np.arange(-4.0, 4.0001, 0.25, dtype=np.float64)
    missing = []
    for station in stations:
        center = np.asarray(_line_point_tangent(corridor.part, float(station))[0])
        normal = np.asarray([np.interp(station, cumulative, vectors[:, axis]) for axis in (0, 1)])
        for offset in lateral:
            point = center + offset * normal
            location = Point(point)
            if not chart_support.covers(location):
                missing.append(
                    {
                        "stationM": float(station),
                        "lateralM": float(offset),
                        "reason": "outside chart support",
                    }
                )
                continue
            try:
                owner = chart.locate(point)
            except Exception as exc:
                owner = None
                reason = f"owner error: {type(exc).__name__}: {exc}"
            else:
                reason = "no chart triangle owner"
            if owner is None:
                missing.append(
                    {"stationM": float(station), "lateralM": float(offset), "reason": reason}
                )
    return {
        "passes": not missing,
        "status": "MEASURED_REQUIRED_TARGET_SUPPORT",
        "stationCount": len(stations),
        "lateralSampleCount": len(lateral),
        "requiredSampleCount": int(len(stations) * len(lateral)),
        "lateralRangeM": [float(lateral[0]), float(lateral[-1])],
        "missingCount": len(missing),
        "missingSamples": missing,
    }


def _section_gates_from_stored_mesh(
    corridor: Corridor, candidate: StoredCandidate
) -> dict[str, Any]:
    """Measure all cross-sections by sampling decoded stored Float32 triangles."""
    cumulative, vectors = section_vectors(np.asarray(corridor.part, dtype=np.float64))
    stations = set(float(value) for value in np.arange(START, END + 1e-9, 0.25))
    stations.update((START, END, ANCHOR))
    stations.update(float(value) for value in corridor.stations if START <= value <= END)
    stations = np.asarray(sorted(stations), dtype=np.float64)
    lateral = np.arange(-3.0, 3.0001, 0.25, dtype=np.float64)
    section_points = []
    for station in stations:
        center = np.asarray(_line_point_tangent(corridor.part, float(station))[0], dtype=np.float64)
        normal = np.asarray(
            [np.interp(station, cumulative, vectors[:, axis]) for axis in (0, 1)],
            dtype=np.float64,
        )
        section_points.extend(center + lateral[:, None] * normal)
    point_array = np.asarray(section_points, dtype=np.float64)
    mesh_heights = sample_stored_triangle_surface(point_array, candidate).reshape(
        len(stations), len(lateral)
    )
    source_heights = corridor.source(point_array).reshape(len(stations), len(lateral))
    slopes = np.abs(np.diff(mesh_heights, axis=1) / np.diff(lateral)[None, :]) * 100.0
    spans = np.ptp(mesh_heights, axis=1)
    center_index = int(np.argmin(np.abs(lateral)))
    center_deviation = np.abs(mesh_heights[:, center_index] - source_heights[:, center_index])
    source_center = np.asarray(
        [
            corridor.source(np.asarray([_line_point_tangent(corridor.part, float(station))[0]]))[0]
            for station in stations
        ],
        dtype=np.float64,
    )
    source_grade = np.diff(source_center) / np.diff(stations)
    candidate_grade = np.diff(mesh_heights[:, center_index]) / np.diff(stations)
    maximum_cross = float(np.max(slopes))
    maximum_span = float(np.max(spans))
    maximum_deviation = float(np.max(center_deviation))
    maximum_grade = float(np.max(np.abs(candidate_grade)) * 100.0)
    return {
        "passes": bool(
            maximum_cross <= LIMITS["full_width_cross_slope_percent_max"]
            and maximum_span <= LIMITS["full_width_height_span_m_max"]
            and maximum_deviation <= LIMITS["centerline_source_height_deviation_m_max"]
            and maximum_grade <= LIMITS["absolute_longitudinal_grade_percent_max"]
        ),
        "status": "MEASURED_STORED_LOCAL_FLOAT32_MESH",
        "surface": "decoded local Float32 positions reconstructed to world Float64",
        "stationsM": stations.tolist(),
        "stationSpacingMaximumM": float(np.max(np.diff(stations))),
        "lateralSpacingM": 0.25,
        "maximumCrossSlopePercent": maximum_cross,
        "maximumFullWidthSpanM": maximum_span,
        "maximumCenterlineSourceHeightDeviationM": maximum_deviation,
        "maximumAbsoluteLongitudinalGradePercent": maximum_grade,
        "limits": {
            key: LIMITS[key]
            for key in (
                "full_width_cross_slope_percent_max",
                "full_width_height_span_m_max",
                "centerline_source_height_deviation_m_max",
                "absolute_longitudinal_grade_percent_max",
            )
        },
        "sourceSignedGradeMPerM": source_grade.tolist(),
        "candidateSignedGradeMPerM": candidate_grade.tolist(),
    }


def load_candidate_config(path: Path) -> CandidateConfig:
    """Strict new schema; never pass this local contract through legacy load_config."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Float32CandidateError(f"cannot read Float32 config: {exc}") from exc
    expected_keys = {
        "schema",
        "issue_id",
        "release_id",
        "source",
        "output_directory",
        "frame",
        "bounds_global_xz_m",
        "recipe",
        "candidate_only_limits",
        "preview_config",
    }
    if not isinstance(raw, dict) or set(raw) != expected_keys:
        raise Float32CandidateError("Float32 candidate config has an invalid exact shape")
    if raw["schema"] != "teignmouth-float32-candidate-config-v1":
        raise Float32CandidateError("Float32 candidate schema mismatch")
    if raw["issue_id"] != "Teignmouth-float32-topology-representation-1":
        raise Float32CandidateError("Float32 candidate issue identity mismatch")
    if raw["release_id"] != RELEASE_ID:
        raise Float32CandidateError("Float32 candidate release mismatch")
    if raw["output_directory"] != CANDIDATE_OUTPUT:
        raise Float32CandidateError("candidate output must stay under ignored data/generated/")
    source = {
        "osm_way_id": 78455395,
        "part_index": 0,
        "estimated_width_m": 6.0,
        "ground_assumption": "ground_assumed_from_absent_or_explicit_no_vertical_tags",
    }
    if not _same(raw["source"], source):
        raise Float32CandidateError("target source identity or estimated width changed")
    frame = Float32LocalFrame.from_metadata(raw["frame"])
    if not _same(raw["bounds_global_xz_m"], list(EXPECTED_BOUNDS)):
        raise Float32CandidateError("candidate domain changed")
    if not _same(raw["recipe"], EXPECTED_RECIPE):
        raise Float32CandidateError("candidate recipe changed")
    if not _same(raw["candidate_only_limits"], LIMITS):
        raise Float32CandidateError("candidate-only or inherited limits changed")
    if not _same(raw["preview_config"], EXPECTED_PREVIEW):
        raise Float32CandidateError("frozen preview values changed")
    preview = PreviewConfig(
        release_id=RELEASE_ID,
        output_directory=CANDIDATE_OUTPUT,
        transition_distance_factor=1.0,
        ambiguity_distance_m=2.0,
        ambiguity_height_difference_m=1.0,
        maximum_changed_height_m=10.0,
        fallback_absolute_change_m=5.0,
        fallback_added_gradient_m_per_m=1.0,
        fallback_minimum_region_area_m2=8.0,
        fallback_fade_distance_m=32.0,
        treatment_variant="teignmouth-circled-segment",
    )
    return CandidateConfig(
        raw["issue_id"],
        RELEASE_ID,
        CANDIDATE_OUTPUT,
        frame,
        EXPECTED_BOUNDS,
        EXPECTED_RECIPE,
        LIMITS,
        preview,
    )


def load_candidate_corridor(root: Path, config: CandidateConfig) -> Corridor:
    inputs = load_release_inputs(root, config.preview)
    if inputs.release_id != RELEASE_ID:
        raise Float32CandidateError("loaded release differs from frozen release")
    feature = next(
        (
            item
            for item in inputs.road_payload["features"]
            if item.get("source", {}).get("osmId") == 78455395
        ),
        None,
    )
    if feature is None or feature.get("estimatedWidthM") != 6.0:
        raise Float32CandidateError("pinned target road/width is unavailable")
    if feature.get("groundAssumption") != "ground_assumed_from_absent_or_explicit_no_vertical_tags":
        raise Float32CandidateError("target road is not source-ground eligible")
    parts = feature.get("centerlinePartsXZ")
    if not isinstance(parts, list) or not parts or len(parts[0]) < 2:
        raise Float32CandidateError("pinned target part is incomplete")
    part = parts[0]
    length = sum(math.dist(a, b) for a, b in zip(part, part[1:], strict=False))
    stations = np.arange(0.0, length, STEP)
    if stations[-1] != length:
        stations = np.append(stations, length)
    profile_points = np.asarray([_line_point_tangent(part, float(s))[0] for s in stations])
    source = np.asarray([_sample_grid(inputs.baseline, x, z, 2.0) for x, z in profile_points])
    cumulative = np.r_[
        0.0, np.cumsum([math.dist(a, b) for a, b in zip(part, part[1:], strict=False)])
    ]
    influence_points = [_line_point_tangent(part, START)[0]]
    influence_points.extend(p for p, s in zip(part, cumulative, strict=True) if START < s < END)
    influence_points.append(_line_point_tangent(part, END)[0])
    influence = LineString(influence_points).buffer(35.0)
    if not box(*EXPECTED_BOUNDS).covers(influence):
        raise Float32CandidateError("fixed influence requires domain expansion")
    return Corridor(inputs, part, stations, source, gaussian_profile(source), influence)


def construct_local_mesh(
    corridor: Corridor, frame: Float32LocalFrame, evidence: Path | None = None
):
    """Translate the full fixed arrangement first, then invoke the unchanged guard."""
    chart = make_chart(corridor.part)
    _persist_chart(chart, evidence)
    lines = [LineString(corridor.influence.exterior.coords)]
    chart_edges = set()
    for face in chart.triangles:
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            chart_edges.add(tuple(sorted((int(a), int(b)))))
    for edge in sorted(chart_edges):
        clipped = LineString(chart.points[list(edge)]).intersection(corridor.influence)
        if clipped.geom_type == "LineString" and clipped.length > 0:
            lines.append(clipped)
        elif clipped.geom_type == "MultiLineString":
            lines.extend(item for item in clipped.geoms if item.length > 0)
    xmin, zmin, xmax, zmax = EXPECTED_BOUNDS
    for x in np.arange(xmin, xmax + 0.1, 2.0):
        lines.append(LineString(((x, zmin), (x, zmax))))
    for z in np.arange(zmin, zmax + 0.1, 2.0):
        lines.append(LineString(((xmin, z), (xmax, z))))
    for x in np.arange(xmin, xmax, 2.0):
        for z in np.arange(zmin, zmax, 2.0):
            lines.append(LineString(((x, z + 2.0), (x + 2.0, z))))
    for x in np.arange(xmin + 2.0, xmax - 1.9, 0.5):
        lines.append(LineString(((x, zmin + 2.0), (x, zmax - 2.0))))
    for z in np.arange(zmin + 2.0, zmax - 1.9, 0.5):
        lines.append(LineString(((xmin + 2.0, z), (xmax - 2.0, z))))
    domain_local = frame.geometry_to_local(box(*EXPECTED_BOUNDS))
    lines_local = [frame.geometry_to_local(line) for line in lines]
    mesh = build_constrained_mesh(domain_local, lines_local)
    _persist_construction(mesh, evidence)
    frame.assert_unique_local_xz(mesh.vertices_xz)
    return mesh, chart


def expected_boundary_world_xz() -> set[tuple[float, float]]:
    xmin, zmin, xmax, zmax = EXPECTED_BOUNDS
    points = set()
    for x in np.arange(xmin, xmax + 0.1, 2.0):
        points.add((float(x), zmin))
        points.add((float(x), zmax))
    for z in np.arange(zmin + 2.0, zmax - 0.1, 2.0):
        points.add((xmin, float(z)))
        points.add((xmax, float(z)))
    return points


def validate_stored_local_mesh(
    local_xz_f32: np.ndarray,
    triangles: np.ndarray,
    domain_local: Polygon,
    constraint_edges: tuple[tuple[int, int], ...],
) -> dict[str, Any]:
    points = np.asarray(local_xz_f32, dtype="<f4")
    faces = np.asarray(triangles, dtype="<u4")
    if points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all():
        raise Float32CandidateError("stored X/Z must be finite N×2 Float32")
    if faces.ndim != 2 or faces.shape[1] != 3 or (faces.size and int(faces.max()) >= len(points)):
        raise Float32CandidateError("triangle indices are malformed or out of range")
    face_points = points[faces].astype(np.float64)
    first, second = face_points[:, 1] - face_points[:, 0], face_points[:, 2] - face_points[:, 0]
    area2 = first[:, 0] * second[:, 1] - first[:, 1] * second[:, 0]
    if not np.isfinite(area2).all() or np.any(area2 >= 0.0):
        raise Float32CandidateError("stored local topology has inverted/degenerate triangles")
    edge_counts: dict[tuple[int, int], int] = {}
    for face in faces:
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edge = tuple(sorted((int(a), int(b))))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
    if any(count not in (1, 2) for count in edge_counts.values()):
        raise Float32CandidateError("stored local topology has nonmanifold/duplicate edges")
    if not set(constraint_edges).issubset(edge_counts):
        raise Float32CandidateError("stored local topology lost constrained edges")
    polygons = shapely.polygons(face_points)
    union = shapely.union_all(polygons)
    overlap = float(np.sum(-area2) * 0.5) - float(union.area)
    coverage = float(union.symmetric_difference(domain_local).area)
    euler = len(points) - len(edge_counts) + len(faces)
    return {
        "passes": euler == 1 and abs(overlap) <= 1e-8 and coverage <= 1e-8,
        "vertices": len(points),
        "triangles": len(faces),
        "edges": len(edge_counts),
        "constraintEdgeCount": len(constraint_edges),
        "missingConstraintEdges": 0,
        "boundaryEdgeCount": sum(count == 1 for count in edge_counts.values()),
        "eulerCharacteristic": euler,
        "overlapAreaM2": overlap,
        "uncoveredOrOutsideAreaM2": coverage,
        "actualStoredLocalFloat32": True,
    }


def road_ownership_scope(corridor: Corridor) -> dict[str, Any]:
    conflicts, off_ground = [], []
    for feature in corridor.inputs.road_payload.get("features", []):
        way_id = feature.get("source", {}).get("osmId")
        if way_id == 78455395:
            continue
        ground = (
            feature.get("groundAssumption")
            == "ground_assumed_from_absent_or_explicit_no_vertical_tags"
        )
        if not ground:
            off_ground.append(way_id)
        for index, part in enumerate(feature.get("centerlinePartsXZ", [])):
            if len(part) < 2:
                continue
            ribbon = LineString(part).buffer(
                float(feature.get("estimatedWidthM", 0.0)) / 2, cap_style="flat"
            )
            overlap = ribbon.intersection(corridor.influence)
            if overlap.area > 1e-8:
                conflicts.append(
                    {
                        "wayId": way_id,
                        "partIndex": index,
                        "groundEligible": ground,
                        "overlapAreaM2": float(overlap.area),
                        "overlapWkt": overlap.wkt,
                    }
                )
    return {
        "passes": not conflicts,
        "status": "MEASURED",
        "scope": "all road ribbons intersecting the complete registered influence",
        "offGroundWayIdsProtected": sorted(set(off_ground)),
        "conflicts": conflicts,
        "roadReclipAndDrapePass": False,
        "reason": "complete road reclip and <=1mm drape QA remain separate gates",
    }


def building_scope(corridor: Corridor) -> dict[str, Any]:
    features = corridor.inputs.buildings.get("buildings")
    if not isinstance(features, list):
        return {
            "passes": False,
            "status": "INVALID_SOURCE",
            "buildingCount": 0,
            "intersectingFootprints": [],
        }
    touched, invalid = [], []
    for feature in features:
        feature_id = feature.get("id") if isinstance(feature, dict) else None
        polygons = (
            feature.get("geometry", {}).get("polygons") if isinstance(feature, dict) else None
        )
        if not isinstance(polygons, list) or not polygons:
            invalid.append(feature_id)
            continue
        pieces = []
        try:
            for record in polygons:
                polygon = Polygon(record["exteriorXZ"], record.get("interiorRingsXZ", []))
                if not polygon.is_valid:
                    raise ValueError("invalid footprint polygon")
                pieces.append(polygon)
        except (KeyError, TypeError, ValueError) as exc:
            invalid.append({"id": feature_id, "error": str(exc)})
            continue
        hits = [poly for poly in pieces if poly.intersects(corridor.influence)]
        if hits:
            touched.append(
                {
                    "id": feature_id,
                    "polygonCount": len(pieces),
                    "intersectingPolygonCount": len(hits),
                    "holesRetained": sum(len(poly.interiors) for poly in hits),
                }
            )
    complete = len(features) == 3613 and not invalid
    return {
        "passes": False,
        "status": "SCOPE_ENUMERATED_CONTACT_NOT_EVALUATED",
        "buildingCount": len(features),
        "completeFootprintSourceValid": complete,
        "intersectingFootprints": touched,
        "invalidFootprints": invalid,
        "registeredRiskBuildingPresent": any(item["id"] == "osm:way:208684847" for item in touched),
        "p95MaximumAndNewtonGatesEvaluated": False,
        "reason": (
            "all complete intersecting footprints are enumerated, but composite contact "
            "metrics remain unevaluated"
        ),
    }


def _serialize_position_buffers(
    frame: Float32LocalFrame,
    construction_local_xz: np.ndarray,
    candidate_y_unrounded: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    """Serialize explicit XYZ positions and measure against the same XYZ baseline."""
    construction_local_xz = np.asarray(construction_local_xz, dtype=np.float64)
    candidate_y_unrounded = np.asarray(candidate_y_unrounded, dtype=np.float64)
    if (
        construction_local_xz.ndim != 2
        or construction_local_xz.shape[1] != 2
        or candidate_y_unrounded.shape != (len(construction_local_xz),)
        or not np.isfinite(construction_local_xz).all()
        or not np.isfinite(candidate_y_unrounded).all()
    ):
        raise Float32CandidateError("construction X/Z and candidate Y buffers are malformed")
    construction_world_xz = frame.local_xz_to_world64(construction_local_xz)
    stored_local_xz = np.asarray(construction_local_xz, dtype="<f4")
    if not np.isfinite(stored_local_xz).all():
        raise Float32CandidateError("local X/Z overflows finite Float32")
    actual_world_xz = frame.local_xz_to_world64(stored_local_xz.astype(np.float64))
    pre_serialization_world_xyz = np.column_stack(
        (
            construction_world_xz[:, 0],
            candidate_y_unrounded,
            construction_world_xz[:, 1],
        )
    )
    actual_pre_storage_xyz = np.column_stack(
        (actual_world_xz[:, 0], candidate_y_unrounded, actual_world_xz[:, 1])
    )
    stored_xyz = frame.store_xyz(actual_pre_storage_xyz)
    if not np.array_equal(stored_xyz[:, (0, 2)], stored_local_xz):
        raise Float32CandidateError("local X/Z bytes changed during XYZ serialization")
    decoded_world_xyz = frame.decode_xyz_to_world64(stored_xyz)
    displacement_xyz = decoded_world_xyz - pre_serialization_world_xyz
    displacement_xz = displacement_xyz[:, (0, 2)]
    report = {
        "coordinateOrder": "X,Y,Z",
        "preSerializationCoordinates": (
            "original construction world X/Z and unrounded candidate Y, ordered X,Y,Z"
        ),
        "serializedCoordinates": (
            "decoded stored local Float32 XYZ reconstructed in world Float64, ordered X,Y,Z"
        ),
        "maximumAbsoluteDisplacementByAxisM": np.max(np.abs(displacement_xyz), axis=0).tolist(),
        "maximumHorizontalDisplacementByAxisM": np.max(np.abs(displacement_xz), axis=0).tolist(),
        "maximumVerticalDisplacementM": float(np.max(np.abs(displacement_xyz[:, 1]))),
        "maximumEuclideanDisplacementM": float(np.max(np.linalg.norm(displacement_xyz, axis=1))),
    }
    return stored_xyz, decoded_world_xyz, construction_world_xz, report


def _candidate_affine_surface_overlay_extrema(
    mesh: PlanarMesh,
    candidate_heights: np.ndarray,
    source_index: SourceOverlapIndex,
    *,
    clip_geometry=None,
    area_tolerance_m2: float = 1e-12,
) -> dict[str, Any]:
    """Measure prototype-local affine overlays without filtering tiny fragments.

    Clipping keeps the historical association: face/source intersection first,
    then the optional clip geometry. Coverage is checked from the positive
    fragments and their union; pairwise source intersections distinguish real
    overlap from a floating-point sum-minus-union residue.
    """
    values = np.asarray(candidate_heights, dtype=np.float64)
    if values.shape != (len(mesh.vertices_xz),) or not np.isfinite(values).all():
        raise TopologyError("candidate heights do not match the finite topology vertex buffer")
    if source_index.heights is None:
        raise TopologyError("overlay extrema require source heights in the overlap index")
    if not math.isfinite(area_tolerance_m2) or area_tolerance_m2 < 0.0:
        raise TopologyError("overlay area tolerance must be finite and nonnegative")

    def validate_geometry(geometry, label: str) -> None:
        coordinates = shapely.get_coordinates(geometry)
        measures = (float(geometry.area), float(geometry.length))
        bounds = () if geometry.is_empty else tuple(float(value) for value in geometry.bounds)
        if (
            not geometry.is_valid
            or not np.isfinite(coordinates).all()
            or not all(math.isfinite(value) for value in measures + bounds)
        ):
            raise TopologyError(f"overlay has invalid or nonfinite geometry at {label}")

    if clip_geometry is not None:
        validate_geometry(clip_geometry, "clip input")

    source_planes = []
    for index, source_id in enumerate(source_index.source_ids):
        source_xz = np.asarray(source_index.vertices_xz[index], dtype=np.float64)
        source_y = np.asarray(source_index.heights[index], dtype=np.float64)
        plane = _plane_coefficients(source_xz, source_y)
        if not np.isfinite(plane).all():
            raise TopologyError(f"source triangle {source_id} plane is nonfinite")
        source_planes.append(plane)

    max_fill = -math.inf
    min_cut = math.inf
    first_difference = None
    minimum_signed = None
    maximum_signed = None
    minimum_absolute = None
    maximum_absolute = None
    overlay_count = 0
    tested_vertices = 0
    empty_face_count = 0
    assessed_area_parts = []
    covered_area_parts = []
    union_area_parts = []
    gap_area_parts = []
    excess_area_parts = []
    sum_minus_union_parts = []
    pairwise_overlap_area_parts = []
    pairwise_overlap_pair_count = 0
    positive_fragment_count = 0
    zero_area_contact_count = 0
    zero_area_contact_witnesses = []

    def remember_contact(source_id: int, geometry) -> None:
        nonlocal zero_area_contact_count
        if geometry.is_empty:
            return
        zero_area_contact_count += 1
        if len(zero_area_contact_witnesses) < 8:
            zero_area_contact_witnesses.append(
                {
                    "sourceTriangleId": source_id,
                    "geometryType": geometry.geom_type,
                    "wkt": geometry.wkt,
                }
            )

    for face_id, face_ids in enumerate(mesh.triangles):
        patch_ids = np.asarray(face_ids, dtype=np.int64)
        patch_xz = np.asarray(mesh.vertices_xz[patch_ids], dtype=np.float64)
        patch_y = values[patch_ids]
        patch_polygon = Polygon(patch_xz)
        validate_geometry(patch_polygon, f"patch face {face_id}")
        if patch_polygon.is_empty or float(patch_polygon.area) <= 0.0:
            raise TopologyError(f"patch face {face_id} is empty or degenerate")
        patch_plane = _plane_coefficients(patch_xz, patch_y)
        if not np.isfinite(patch_plane).all():
            raise TopologyError(f"patch face {face_id} plane is nonfinite")
        assessed = (
            patch_polygon if clip_geometry is None else patch_polygon.intersection(clip_geometry)
        )
        validate_geometry(assessed, f"assessed region for face {face_id}")
        expected_area = float(assessed.area)
        if expected_area < 0.0:
            raise TopologyError(f"assessed region for face {face_id} has negative area")
        candidate_indices = sorted(
            int(index) for index in source_index.tree.query(patch_polygon, predicate="intersects")
        )

        if expected_area == 0.0:
            empty_face_count += 1
            for source_at in candidate_indices:
                contact = patch_polygon.intersection(source_index.geometries[source_at])
                if clip_geometry is not None and not contact.is_empty:
                    contact = contact.intersection(clip_geometry)
                validate_geometry(contact, f"zero-area contact face {face_id}")
                if float(contact.area) == 0.0:
                    remember_contact(source_index.source_ids[source_at], contact)
            continue

        assessed_area_parts.append(expected_area)
        fragment_polygons: list[tuple[int, Any, float]] = []
        for source_at in candidate_indices:
            source_id = source_index.source_ids[source_at]
            clipped = patch_polygon.intersection(source_index.geometries[source_at])
            if clip_geometry is not None and not clipped.is_empty:
                clipped = clipped.intersection(clip_geometry)
            validate_geometry(clipped, f"face {face_id} source {source_id} clipped fragment")
            clipped_area = float(clipped.area)
            if clipped_area == 0.0:
                remember_contact(source_id, clipped)
                continue
            for polygon in _polygon_parts(clipped):
                polygon_area = float(polygon.area)
                if not math.isfinite(polygon_area) or polygon_area <= 0.0:
                    if not math.isfinite(polygon_area):
                        raise TopologyError(
                            f"face {face_id} source {source_id} polygon area is nonfinite"
                        )
                    continue
                fragment_polygons.append((source_at, polygon, polygon_area))

        fragment_areas = [item[2] for item in fragment_polygons]
        covered_area = math.fsum(fragment_areas)
        if not math.isfinite(covered_area):
            raise TopologyError(f"face {face_id} positive-fragment area sum is nonfinite")
        if not fragment_polygons:
            raise TopologyError(
                "positive assessed region has no positive-area source coverage: "
                f"face={face_id}, expectedArea={expected_area:.17g}, "
                f"zeroAreaContactCount={zero_area_contact_count}"
            )
        positive_union = shapely.union_all([item[1] for item in fragment_polygons])
        validate_geometry(positive_union, f"face {face_id} positive-fragment union")
        gap = assessed.difference(positive_union)
        excess = positive_union.difference(assessed)
        symmetric_difference = positive_union.symmetric_difference(assessed)
        validate_geometry(gap, f"face {face_id} coverage gap")
        validate_geometry(excess, f"face {face_id} coverage excess")
        validate_geometry(symmetric_difference, f"face {face_id} coverage symmetric difference")
        union_area = float(positive_union.area)
        gap_area = float(gap.area)
        excess_area = float(excess.area)
        sum_minus_union = covered_area - union_area
        if not all(
            math.isfinite(value) for value in (union_area, gap_area, excess_area, sum_minus_union)
        ):
            raise TopologyError(f"face {face_id} coverage area summaries are nonfinite")

        pairwise_overlaps = []
        candidate_ids_for_partition = [
            source_at
            for source_at in candidate_indices
            if source_index.geometries[source_at].intersects(assessed)
        ]
        for first_offset, first_at in enumerate(candidate_ids_for_partition):
            first = source_index.geometries[first_at]
            for second_at in candidate_ids_for_partition[first_offset + 1 :]:
                second = source_index.geometries[second_at]
                if not first.intersects(second):
                    continue
                pair_overlap = first.intersection(second)
                if not pair_overlap.is_empty:
                    pair_overlap = pair_overlap.intersection(assessed)
                validate_geometry(pair_overlap, f"face {face_id} source-pair intersection")
                pair_area = float(pair_overlap.area)
                if pair_area > 0.0:
                    pairwise_overlaps.append(
                        {
                            "sourceTriangleIds": [
                                source_index.source_ids[first_at],
                                source_index.source_ids[second_at],
                            ],
                            "areaM2": pair_area,
                            "wkt": pair_overlap.wkt,
                        }
                    )
        pairwise_overlap_area = math.fsum(item["areaM2"] for item in pairwise_overlaps)
        tolerance = max(area_tolerance_m2, expected_area * 1e-10)
        coverage_residual = covered_area - expected_area
        if not math.isfinite(pairwise_overlap_area) or not math.isfinite(coverage_residual):
            raise TopologyError(f"face {face_id} coverage residual is nonfinite")
        if (
            abs(coverage_residual) > tolerance
            or gap_area > tolerance
            or excess_area > tolerance
            or pairwise_overlap_area > tolerance
        ):
            details = {
                "faceId": face_id,
                "expectedAreaM2": expected_area,
                "coveredAreaM2": covered_area,
                "coverageResidualM2": coverage_residual,
                "toleranceM2": tolerance,
                "gapAreaM2": gap_area,
                "gapWkt": gap.wkt,
                "excessAreaM2": excess_area,
                "excessWkt": excess.wkt,
                "pairwiseSourceOverlapAreaM2": pairwise_overlap_area,
                "pairwiseSourceOverlaps": pairwise_overlaps,
                "sumMinusUnionResidualM2": sum_minus_union,
                "partitionVerifiedHint": source_index.partition_verified,
            }
            raise TopologyError(
                "source overlay coverage or positive-area source overlap failed: "
                + json.dumps(details, sort_keys=True, allow_nan=False)
            )

        covered_area_parts.append(covered_area)
        positive_fragment_count += len(fragment_polygons)
        union_area_parts.append(union_area)
        gap_area_parts.append(gap_area)
        excess_area_parts.append(excess_area)
        sum_minus_union_parts.append(sum_minus_union)
        pairwise_overlap_area_parts.append(pairwise_overlap_area)
        pairwise_overlap_pair_count += len(pairwise_overlaps)
        overlay_count += 1

        for source_at, polygon, _polygon_area in fragment_polygons:
            source_plane = source_planes[source_at]
            rings = [polygon.exterior, *polygon.interiors]
            for ring in rings:
                for x, z in list(ring.coords)[:-1]:
                    candidate_y = float(patch_plane[0] * x + patch_plane[1] * z + patch_plane[2])
                    baseline_y = float(source_plane[0] * x + source_plane[1] * z + source_plane[2])
                    delta = candidate_y - baseline_y
                    if not all(math.isfinite(value) for value in (candidate_y, baseline_y, delta)):
                        raise TopologyError(
                            f"face {face_id} source {source_index.source_ids[source_at]} "
                            "has a nonfinite overlay plane witness"
                        )
                    witness = {
                        "patchFaceId": face_id,
                        "sourceTriangleId": source_index.source_ids[source_at],
                        "localXZ": [float(x), float(z)],
                        "candidateY": candidate_y,
                        "sourceY": baseline_y,
                        "signedDifferenceM": delta,
                        "absoluteDifferenceM": abs(delta),
                    }
                    if first_difference is None:
                        first_difference = witness
                    if minimum_signed is None or delta < minimum_signed["signedDifferenceM"]:
                        minimum_signed = witness
                    if maximum_signed is None or delta > maximum_signed["signedDifferenceM"]:
                        maximum_signed = witness
                    if (
                        minimum_absolute is None
                        or abs(delta) < minimum_absolute["absoluteDifferenceM"]
                    ):
                        minimum_absolute = witness
                    if (
                        maximum_absolute is None
                        or abs(delta) > maximum_absolute["absoluteDifferenceM"]
                    ):
                        maximum_absolute = witness
                    max_fill = max(max_fill, delta)
                    min_cut = min(min_cut, delta)
                    tested_vertices += 1

    if tested_vertices == 0:
        if overlay_count != 0:
            raise TopologyError("positive source overlay produced no finite plane extrema")
        return {
            "overlayFaceCount": 0,
            "testedIntersectionVertexCount": 0,
            "maximumFillFromSourceM": None,
            "maximumCutFromSourceM": None,
            "maximumAbsoluteChangeFromSourceM": None,
            "maximumFillLocation": None,
            "maximumCutLocation": None,
            "firstDifferenceWitness": None,
            "minimumSignedDifferenceWitness": None,
            "maximumSignedDifferenceWitness": None,
            "minimumAbsoluteDifferenceWitness": None,
            "maximumAbsoluteDifferenceWitness": None,
            "emptyAssessedRegion": True,
            "emptyAssessedFaceCount": empty_face_count,
            "zeroAreaContactCount": zero_area_contact_count,
            "zeroAreaContactWitnesses": zero_area_contact_witnesses,
            "assessedAreaM2": 0.0,
            "positiveFragmentCount": 0,
            "coveredAreaM2": 0.0,
            "positiveFragmentUnionAreaM2": 0.0,
            "coverageGapAreaM2": 0.0,
            "coverageExcessAreaM2": 0.0,
            "summedAreaMinusUnionResidualM2": 0.0,
            "pairwiseSourceOverlapAreaM2": 0.0,
            "pairwiseSourceOverlapPairCount": 0,
            "areaToleranceM2": area_tolerance_m2,
            "clipOperationOrder": "face.intersection(source_triangle).intersection(clip_geometry)",
        }
    if not all(math.isfinite(value) for value in (max_fill, min_cut)):
        raise TopologyError("source overlay produced nonfinite intersection extrema")
    return {
        "overlayFaceCount": overlay_count,
        "testedIntersectionVertexCount": tested_vertices,
        "maximumFillFromSourceM": max_fill,
        "maximumCutFromSourceM": min_cut,
        "maximumAbsoluteChangeFromSourceM": max(abs(max_fill), abs(min_cut)),
        "maximumFillLocation": maximum_signed,
        "maximumCutLocation": minimum_signed,
        "firstDifferenceWitness": first_difference,
        "minimumSignedDifferenceWitness": minimum_signed,
        "maximumSignedDifferenceWitness": maximum_signed,
        "minimumAbsoluteDifferenceWitness": minimum_absolute,
        "maximumAbsoluteDifferenceWitness": maximum_absolute,
        "emptyAssessedRegion": False,
        "positiveFragmentCount": positive_fragment_count,
        "emptyAssessedFaceCount": empty_face_count,
        "zeroAreaContactCount": zero_area_contact_count,
        "zeroAreaContactWitnesses": zero_area_contact_witnesses,
        "assessedAreaM2": math.fsum(assessed_area_parts),
        "coveredAreaM2": math.fsum(covered_area_parts),
        "positiveFragmentUnionAreaM2": math.fsum(union_area_parts),
        "coverageGapAreaM2": math.fsum(gap_area_parts),
        "coverageExcessAreaM2": math.fsum(excess_area_parts),
        "summedAreaMinusUnionResidualM2": math.fsum(sum_minus_union_parts),
        "pairwiseSourceOverlapAreaM2": math.fsum(pairwise_overlap_area_parts),
        "pairwiseSourceOverlapPairCount": pairwise_overlap_pair_count,
        "areaToleranceM2": area_tolerance_m2,
        "clipOperationOrder": "face.intersection(source_triangle).intersection(clip_geometry)",
    }


def _serialize_candidate(
    corridor: Corridor, frame: Float32LocalFrame, mesh, chart: Chart, evidence: Path | None
) -> StoredCandidate:
    gates = {name: {"passes": False, "status": "NOT_EVALUATED"} for name in GATE_NAMES}
    if evidence is not None:
        _write_json(evidence / "gate-state.json", gates)
    chart_support_gate, chart_support = validate_chart_support(corridor, chart)
    gates["chartSupportCompleteness"] = chart_support_gate
    _write_gate(evidence, "chartSupportCompleteness", chart_support_gate)
    if not chart_support_gate["passes"]:
        raise Float32CandidateError(
            "frozen chart support is incomplete: " + "; ".join(chart_support_gate["reasons"])
        )
    required_support = required_treatment_support_report(corridor, chart, chart_support)
    gates["requiredTreatmentSupport"] = required_support
    _write_gate(evidence, "requiredTreatmentSupport", required_support)
    if not required_support["passes"]:
        raise Float32CandidateError(
            f"required carriageway/shoulder chart support is missing at "
            f"{required_support['missingCount']} samples"
        )
    construction_local_xz = np.asarray(mesh.vertices_xz, dtype=np.float64)
    local_xz = np.asarray(mesh.vertices_xz, dtype="<f4")
    world_xz = frame.local_xz_to_world64(local_xz.astype(np.float64))
    source_y = corridor.source(world_xz)
    candidate_y = source_y.copy()
    support_counts = {
        "SOURCE_OUTSIDE_INFLUENCE": 0,
        "SOURCE_INSIDE_INFLUENCE_OUTSIDE_CHART_SUPPORT": 0,
        "CHART_OWNED": 0,
    }
    support_witnesses = []
    owner_failures = []
    for index, point in enumerate(world_xz):
        try:
            status, field = classify_treatment_support(
                point, corridor.influence, chart_support, chart
            )
        except Float32CandidateError as exc:
            owner_failures.append(
                {"vertexIndex": index, "worldXZ": point.tolist(), "error": str(exc)}
            )
            continue
        support_counts[status] += 1
        if status == "SOURCE_INSIDE_INFLUENCE_OUTSIDE_CHART_SUPPORT":
            if len(support_witnesses) < 8:
                support_witnesses.append(
                    {
                        "vertexIndex": index,
                        "worldXZ": point.tolist(),
                        "sourceHeightM": float(source_y[index]),
                        "candidateHeightM": float(candidate_y[index]),
                        "sourceDeltaM": float(candidate_y[index] - source_y[index]),
                    }
                )
        elif status == "CHART_OWNED":
            candidate_y[index] = field_height(corridor, source_y[index], *field)
    support_classification = {
        "passes": not owner_failures,
        "status": "MEASURED_TREATMENT_SUPPORT_CLASSIFICATION",
        "sourceOutsideInfluenceVertexCount": support_counts["SOURCE_OUTSIDE_INFLUENCE"],
        "sourceInsideInfluenceOutsideChartSupportVertexCount": support_counts[
            "SOURCE_INSIDE_INFLUENCE_OUTSIDE_CHART_SUPPORT"
        ],
        "chartOwnedVertexCount": support_counts["CHART_OWNED"],
        "outsideChartSupportSourceWitnesses": support_witnesses,
        "outsideChartSupportSourceDeltaM": [item["sourceDeltaM"] for item in support_witnesses],
        "missingOwnerCount": len(owner_failures),
        "missingOwners": owner_failures,
        "missingSupportInsideExpectedChartIsHardFailure": True,
    }
    gates["treatmentSupportClassification"] = support_classification
    _write_gate(evidence, "treatmentSupportClassification", support_classification)
    if owner_failures:
        raise Float32CandidateError(
            f"{len(owner_failures)} candidate vertices inside chart support have no triangle owner"
        )
    influence_local = frame.geometry_to_local(corridor.influence)
    local_faces = shapely.polygons(local_xz[np.asarray(mesh.triangles, dtype=np.uint32)])
    outside_faces = ~shapely.covers(influence_local, local_faces)
    fixed = np.unique(np.asarray(mesh.triangles, dtype=np.uint32)[outside_faces])
    candidate_y[fixed] = source_y[fixed]
    source_y_f32 = np.asarray(source_y, dtype="<f4")
    stored_xyz, world_xyz, construction_world_xz, serialization_report = (
        _serialize_position_buffers(frame, construction_local_xz, candidate_y)
    )
    candidate_y_f32 = stored_xyz[:, 1]
    faces = np.asarray(mesh.triangles, dtype="<u4")
    if evidence is not None:
        (evidence / "construction-world-xz.f64").write_bytes(
            np.asarray(construction_world_xz, dtype="<f8").tobytes()
        )
        (evidence / "pre-serialization-world-positions.xyz.f64").write_bytes(
            np.column_stack((construction_world_xz[:, 0], candidate_y, construction_world_xz[:, 1]))
            .astype("<f8")
            .tobytes()
        )
        (evidence / "serialized-local-positions.xyz.f32").write_bytes(stored_xyz.tobytes())
        (evidence / "serialized-world-positions.xyz.f64").write_bytes(
            np.asarray(world_xyz, dtype="<f8").tobytes()
        )
        (evidence / "serialized-source-y.f32").write_bytes(source_y_f32.tobytes())
        (evidence / "serialized-candidate-y.f32").write_bytes(candidate_y_f32.tobytes())
        (evidence / "serialized-indices.u32").write_bytes(encode_indices(faces))
        _write_json(
            evidence / "serialization-stage.json",
            {"status": "COMPLETE", **serialization_report},
        )
    if np.any(triangle_normal_y(stored_xyz, faces) <= 0.0):
        raise Float32CandidateError("actual stored Float32 mesh has inverted/degenerate 3D faces")
    local_domain = frame.geometry_to_local(box(*EXPECTED_BOUNDS))
    topology = validate_stored_local_mesh(local_xz, faces, local_domain, mesh.constraint_edges)
    frame.assert_unique_local_xz(local_xz.astype(np.float64))
    gates["storedLocalTopology"] = topology
    _write_gate(evidence, "storedLocalTopology", topology)
    world_mesh = PlanarMesh(
        world_xyz[:, (0, 2)].copy(), faces, mesh.boundary_edges, mesh.constraint_edges
    )
    expected_boundary = expected_boundary_world_xz()
    boundary_vertices = sorted({v for edge in mesh.boundary_edges for v in edge})
    actual_boundary = {(float(world_xyz[i, 0]), float(world_xyz[i, 2])) for i in boundary_vertices}
    boundary_xz = actual_boundary == expected_boundary
    boundary_y = bool(
        np.array_equal(candidate_y_f32[boundary_vertices], source_y_f32[boundary_vertices])
    )
    source_index = SourceOverlapIndex.from_grid(
        corridor.inputs.baseline,
        width_m=2000.0,
        depth_m=2000.0,
        spacing_m=2.0,
        first_row=432,
        last_row=473,
        first_column=409,
        last_column=451,
    )
    outside_geometry = box(*EXPECTED_BOUNDS).difference(corridor.influence)
    outside_overlay = _candidate_affine_surface_overlay_extrema(
        world_mesh, candidate_y_f32, source_index, clip_geometry=outside_geometry
    )
    outside_planes = outside_overlay["emptyAssessedRegion"] or (
        outside_overlay["maximumAbsoluteChangeFromSourceM"] == 0.0
    )
    outside_support_geometry = corridor.influence.difference(chart_support)
    outside_support_overlay = _candidate_affine_surface_overlay_extrema(
        world_mesh,
        candidate_y_f32,
        source_index,
        clip_geometry=outside_support_geometry,
    )
    outside_support_planes = outside_support_overlay["emptyAssessedRegion"] or (
        outside_support_overlay["maximumAbsoluteChangeFromSourceM"] == 0.0
    )
    perimeter_gate = {
        "passes": boundary_xz and boundary_y and outside_planes and outside_support_planes,
        "decodedBoundaryXZExactlySource": boundary_xz,
        "originalFloat32BoundaryYExactlyPreserved": boundary_y,
        "outsideInfluenceSourcePlanesPreserved": outside_planes,
        "outsideInfluenceOverlayEmptyIsVacuous": outside_overlay["emptyAssessedRegion"],
        "outsideSourcePlaneOverlay": outside_overlay,
        "outsideSourcePlaneRequiresExactZeroResidual": True,
        "insideInfluenceOutsideChartSupportSourcePlanesPreserved": outside_support_planes,
        "outsideChartSupportOverlayEmptyIsVacuous": outside_support_overlay["emptyAssessedRegion"],
        "insideInfluenceOutsideChartSupportOverlay": outside_support_overlay,
        "outsideChartSupportSourcePlaneRequiresExactZeroResidual": True,
        "expectedBoundaryVertices": len(expected_boundary),
        "actualBoundaryVertices": len(actual_boundary),
        "serializationDisplacement": serialization_report,
    }
    gates["sourcePerimeterAndPlanes"] = perimeter_gate
    _write_gate(evidence, "sourcePerimeterAndPlanes", perimeter_gate)
    overlay = _candidate_affine_surface_overlay_extrema(world_mesh, candidate_y_f32, source_index)
    edge_ids = np.unique(
        np.sort(np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]])), axis=1),
        axis=0,
    )
    edge_lengths = np.linalg.norm(
        world_xyz[edge_ids[:, 0]][:, (0, 2)] - world_xyz[edge_ids[:, 1]][:, (0, 2)], axis=1
    )
    source_delta = np.abs(source_y[edge_ids[:, 0]] - source_y[edge_ids[:, 1]])
    candidate_delta = np.abs(
        candidate_y_f32[edge_ids[:, 0]].astype(np.float64)
        - candidate_y_f32[edge_ids[:, 1]].astype(np.float64)
    )
    added = (candidate_delta - source_delta) / edge_lengths
    safety = {
        "passes": not overlay["emptyAssessedRegion"]
        and overlay["maximumAbsoluteChangeFromSourceM"] is not None
        and overlay["maximumAbsoluteChangeFromSourceM"] < LIMITS["absolute_terrain_change_m_strict"]
        and float(np.max(added)) < LIMITS["positive_added_edge_gradient_m_per_m_strict"],
        "maximumAbsoluteChangeFromSourceM": overlay["maximumAbsoluteChangeFromSourceM"],
        "maximumPositiveAddedGradientMPerM": float(np.max(added)),
        "sourceTriangleOverlayExtrema": overlay,
        "finalEdgeCount": len(edge_ids),
        "limits": {"absoluteTerrainChangeMStrict": 6.5, "positiveAddedGradientMPerMStrict": 1.0},
    }
    gates["sourceOverlayAndGradients"] = safety
    _write_gate(evidence, "sourceOverlayAndGradients", safety)
    candidate = StoredCandidate(
        frame, stored_xyz, faces, world_xyz, source_y_f32, world_mesh, source_y, gates
    )
    sections = _section_gates_from_stored_mesh(corridor, candidate)
    gates["actualFloat32Sections"] = sections
    _write_gate(evidence, "actualFloat32Sections", sections)
    road_gate = road_ownership_scope(corridor)
    gates["influenceWideRoadOwnership"] = road_gate
    _write_gate(evidence, "influenceWideRoadOwnership", road_gate)
    building_gate = building_scope(corridor)
    gates["completeBuildingContact"] = building_gate
    _write_gate(evidence, "completeBuildingContact", building_gate)
    gates["sharedRoadBuildingWalkSurface"] = {
        "passes": False,
        "status": "NOT_EVALUATED",
        "reason": (
            "shared runtime sampler, re-clipped roads, building contact and walking "
            "clearance are not implemented"
        ),
    }
    _write_gate(evidence, "sharedRoadBuildingWalkSurface", gates["sharedRoadBuildingWalkSurface"])
    gates["independentDeterministicConfirmation"] = {
        "passes": False,
        "status": "NOT_RUN",
        "reason": "requires a separate reserved confirmation build after all other gates pass",
    }
    _write_gate(
        evidence,
        "independentDeterministicConfirmation",
        gates["independentDeterministicConfirmation"],
    )
    candidate = StoredCandidate(
        frame, stored_xyz, faces, world_xyz, source_y_f32, world_mesh, source_y, gates
    )
    if evidence is not None:
        persist_candidate_buffers(candidate, evidence)
    return candidate


def assemble_candidate(
    corridor: Corridor, frame: Float32LocalFrame, mesh, chart: Chart, evidence: Path | None = None
) -> StoredCandidate:
    try:
        return _serialize_candidate(corridor, frame, mesh, chart, evidence)
    except Exception as exc:
        try:
            _write_failure(evidence, exc)
        except Exception as evidence_error:
            exc.add_note(
                "failure evidence persistence also failed: "
                f"{type(evidence_error).__name__}: {evidence_error}"
            )
        raise


def evaluate_gates(candidate: StoredCandidate) -> dict[str, Any]:
    gates = candidate.gate_reports
    required = list(gates.values())
    passes = all(bool(gate.get("passes")) for gate in required)
    return {
        "passes": passes,
        "gateCount": len(required),
        "passedCount": sum(bool(gate.get("passes")) for gate in required),
        "allOfflineGates": gates,
        "candidateEligibleForServing": False,
        "candidateEligibleForRuntimeOutput": False,
        "fallback": {
            "mode": "unchanged source surface",
            "candidateUsed": False,
            "notice": "experimental Float32 candidate unavailable; source surface remains active",
        },
    }


def persist_candidate_buffers(candidate: StoredCandidate, evidence: Path) -> dict[str, Any]:
    assets = {
        "candidate-local-positions.xyz.f32": candidate.local_positions_xyz_f32.astype(
            "<f4"
        ).tobytes(),
        "candidate-indices.u32": encode_indices(candidate.triangles_u32),
        "candidate-source-y.f32": candidate.source_y_f32.astype("<f4").tobytes(),
    }
    records = {}
    for name, payload in assets.items():
        (evidence / name).write_bytes(payload)
        records[name] = {"byteLength": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    return records


def candidate_runtime_manifest(
    candidate: StoredCandidate, config: CandidateConfig
) -> dict[str, Any]:
    return {
        "schema": "teignmouth-float32-candidate-v1",
        "issueId": config.issue_id,
        "releaseId": config.release_id,
        "frame": candidate.frame.to_metadata(),
        "positions": {
            "path": "candidate-local-positions.xyz.f32",
            "format": "Float32 little-endian XYZ",
            "positionCount": len(candidate.local_positions_xyz_f32),
            "indicesPath": "candidate-indices.u32",
            "triangleCount": len(candidate.triangles_u32),
            "identitySpace": "local Float32 bytes",
        },
        "candidateOnlyLimits": config.limits,
        "gates": evaluate_gates(candidate),
    }


def candidate_fallback(candidate_present: bool, frame_valid: bool) -> dict[str, Any]:
    usable = bool(candidate_present and frame_valid)
    return {
        "candidateUsed": usable,
        "surface": "float32-local-candidate" if usable else "unchanged-source",
        "notice": None
        if usable
        else "experimental candidate unavailable; unchanged source surface is active",
    }


def sample_stored_triangle_surface(
    query_world_xz: np.ndarray, candidate: StoredCandidate
) -> np.ndarray:
    """CPU QA samples the decoded Float64 world surface, never global Float32 vertices."""
    query = np.asarray(query_world_xz, dtype=np.float64)
    if query.ndim != 2 or query.shape[1] != 2 or not np.isfinite(query).all():
        raise Float32CandidateError("surface query must be a finite N×2 world X/Z array")
    vertices, triangles = candidate.reconstructed_world_xyz_f64, candidate.triangles_u32
    polys = shapely.polygons(vertices[triangles][:, :, (0, 2)])
    tree = STRtree(polys)
    heights = []
    for point in query:
        found = []
        for owner in sorted(tree.query(Point(point))):
            face = vertices[triangles[int(owner)]]
            xz = face[:, (0, 2)]
            first, second = xz[1] - xz[0], xz[2] - xz[0]
            det = first[0] * second[1] - first[1] * second[0]
            if abs(det) <= 1e-18:
                raise Float32CandidateError("decoded CPU surface contains a degenerate triangle")
            relative = point - xz[0]
            u = (relative[0] * second[1] - relative[1] * second[0]) / det
            v = (first[0] * relative[1] - first[1] * relative[0]) / det
            weights = np.asarray([1.0 - u - v, u, v])
            if np.min(weights) >= -1e-8:
                found.append(float(weights @ face[:, 1]))
        if not found:
            raise Float32CandidateError(f"decoded mesh does not cover {point.tolist()}")
        if max(found) - min(found) > 1e-6:
            raise Float32CandidateError("decoded mesh has inconsistent shared-edge ownership")
        heights.append(found[0])
    return np.asarray(heights, dtype=np.float64)
