"""Sole authorized correction: a continuous station/lateral corridor chart.

No nearest-segment assignment, source edits, changed recipe or numerical search.
The necessary earthwork preflight runs inside build 2, before planar assembly.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon, box
from shapely.strtree import STRtree

from .road_surface import _line_point_tangent, _sample_grid
from .road_surface_topology import (
    SourceOverlapIndex,
    affine_surface_overlay_extrema,
    build_constrained_mesh,
)
from .teignmouth_corridor_prototype import (
    ANCHOR,
    BOUNDS,
    END,
    START,
    Corridor,
    load_corridor,
    smoothstep,
    topology_report,
)

LATERALS = (-16.0, -6.0, -4.0, -3.0, 0.0, 3.0, 4.0, 6.0, 16.0)


def section_vectors(part: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Miter/bisector joins; interpolate each vector along its source segment.

    Each endpoint miter has unit projection onto that segment's normal. Linear
    interpolation therefore retains the configured normal road width exactly.
    """
    part = np.asarray(part, dtype=float)
    lengths = np.linalg.norm(np.diff(part, axis=0), axis=1)
    if np.any(lengths <= 0):
        raise ValueError("coincident source centerline vertices")
    tangents = np.diff(part, axis=0) / lengths[:, None]
    normals = np.column_stack((-tangents[:, 1], tangents[:, 0]))
    vectors = np.empty_like(part)
    vectors[0], vectors[-1] = normals[0], normals[-1]
    for index in range(1, len(part) - 1):
        bisector = normals[index - 1] + normals[index]
        denominator = float(bisector @ normals[index])
        if denominator <= 1e-12:
            raise ValueError("undefined or reversing miter join")
        vectors[index] = bisector / denominator
    return np.r_[0.0, np.cumsum(lengths)], vectors


def section_stations(cumulative: np.ndarray) -> np.ndarray:
    """Freeze source vertices, half-metres, target/anchor and exact fade ends."""
    fade_start, fade_end = START - 32.0, END + 32.0
    stations = {fade_start, fade_end, START, END, ANCHOR}
    stations.update(float(s) for s in np.arange(fade_start, fade_end + 0.25, 0.5))
    stations.update(float(s) for s in cumulative if fade_start < s < fade_end)
    return np.asarray(sorted(stations))


def barycentric(points: np.ndarray, triangle: np.ndarray) -> np.ndarray:
    first, second = triangle[1] - triangle[0], triangle[2] - triangle[0]
    determinant = first[0] * second[1] - first[1] * second[0]
    if abs(determinant) < 1e-14:
        raise ValueError("degenerate station/lateral chart triangle")
    relative = points - triangle[0]
    u = (relative[:, 0] * second[1] - relative[:, 1] * second[0]) / determinant
    v = (first[0] * relative[:, 1] - first[1] * relative[:, 0]) / determinant
    return np.column_stack((1 - u - v, u, v))


@dataclass
class Chart:
    stations: np.ndarray
    points: np.ndarray
    fields: np.ndarray
    triangles: np.ndarray
    polygons: np.ndarray
    tree: STRtree

    def locate(self, point: np.ndarray) -> tuple[float, float] | None:
        found = []
        for owner in sorted(self.tree.query(Point(point))):
            triangle = self.triangles[owner]
            weights = barycentric(point[None, :], self.points[triangle])[0]
            if np.min(weights) >= -1e-8:
                found.append(weights @ self.fields[triangle])
        if not found:
            return None
        if np.max(np.ptp(np.asarray(found), axis=0)) > 1e-6:
            raise ValueError("ambiguous overlapping station/lateral ownership")
        return float(found[0][0]), float(found[0][1])


def make_chart(part: list[list[float]]) -> Chart:
    original = np.asarray(part, dtype=float)
    cumulative, vectors = section_vectors(original)
    stations = section_stations(cumulative)
    points, fields = [], []
    for station in stations:
        center = np.asarray(_line_point_tangent(part, float(station))[0])
        vector = np.asarray([np.interp(station, cumulative, vectors[:, axis]) for axis in (0, 1)])
        for lateral in LATERALS:
            points.append(center + lateral * vector)
            fields.append((station, lateral))
    points, fields = np.asarray(points), np.asarray(fields)
    triangles = []
    columns = len(LATERALS)
    for row in range(len(stations) - 1):
        for column in range(columns - 1):
            a = row * columns + column
            b, c, d = a + columns, a + 1, a + columns + 1
            triangles.extend(((a, b, c), (b, d, c)))
    triangles = np.asarray(triangles, dtype="<u4")
    faces = points[triangles]
    first, second = faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 0]
    cross = first[:, 0] * second[:, 1] - first[:, 1] * second[:, 0]
    if not np.isfinite(faces).all() or np.any(cross <= 0):
        raise ValueError("inverted/crossing continuous chart section")
    polygons = shapely.polygons(faces)
    union = shapely.union_all(polygons)
    if abs(float(shapely.area(polygons).sum()) - union.area) > 1e-7:
        raise ValueError("overlapping continuous chart station ownership")
    return Chart(stations, points, fields, triangles, polygons, STRtree(polygons))


def field_height(corridor: Corridor, source: float, station: float, lateral: float) -> float:
    profile = float(np.interp(station, corridor.stations, corridor.graded_profile))
    blend = float(np.clip(2.0 * abs(profile - source), 2.0, 12.0))
    lateral_weight = 1.0 - float(smoothstep(np.asarray([(abs(lateral) - 4.0) / blend]))[0])
    distance = max(START - station, station - END, 0.0)
    longitudinal = 1.0 - float(smoothstep(np.asarray([distance / 32.0]))[0])
    return source + (profile - source) * lateral_weight * longitudinal


def source_intersections(first: np.ndarray, second: np.ndarray) -> list[float]:
    """Parameters at the exact original vertical, horizontal and diagonal planes."""
    result = {0.0, 1.0}
    for direction in (np.asarray([1.0, 0.0]), np.asarray([0.0, 1.0]), np.asarray([1.0, 1.0])):
        a, b = float(first @ direction), float(second @ direction)
        if abs(b - a) <= 1e-14:
            continue
        for value in np.arange(math.ceil(min(a, b) / 2.0) * 2.0, max(a, b) + 1e-10, 2.0):
            t = (value - a) / (b - a)
            if 0 <= t <= 1:
                result.add(float(t))
    return sorted(result)


def preflight(corridor: Corridor, chart: Chart) -> dict[str, Any]:
    """Necessary cut/fill witness, inside this same build and before mesh assembly."""
    tested = 0
    maximum = 0.0
    samples = []
    for point, field in zip(chart.points, chart.fields, strict=True):
        samples.append((float(field[0]), float(field[1]), point, "chart vertex"))
    for triangle in chart.triangles:
        for a, b in (
            (triangle[0], triangle[1]),
            (triangle[1], triangle[2]),
            (triangle[2], triangle[0]),
        ):
            for t in source_intersections(chart.points[a], chart.points[b]):
                point = chart.points[a] * (1 - t) + chart.points[b] * t
                field = chart.fields[a] * (1 - t) + chart.fields[b] * t
                samples.append(
                    (
                        float(field[0]),
                        float(field[1]),
                        point,
                        "chart/source-plane edge intersection",
                    )
                )
    # Original source vertices inside the chart are also overlay intersection vertices.
    for z in np.arange(BOUNDS[1], BOUNDS[3] + 0.1, 2.0):
        for x in np.arange(BOUNDS[0], BOUNDS[2] + 0.1, 2.0):
            point = np.asarray([x, z])
            field = chart.locate(point)
            if field is not None:
                samples.append((*field, point, "source vertex inside chart"))
    cumulative, vectors = section_vectors(np.asarray(corridor.part))
    for station in chart.stations:
        if START <= station <= END:
            center = np.asarray(_line_point_tangent(corridor.part, float(station))[0])
            vector = np.asarray(
                [np.interp(station, cumulative, vectors[:, axis]) for axis in (0, 1)]
            )
            for lateral in np.arange(-3.0, 3.125, 0.25):
                samples.append(
                    (
                        float(station),
                        float(lateral),
                        center + lateral * vector,
                        "required target full-width sample",
                    )
                )
    samples.sort(key=lambda sample: (sample[0], sample[1], sample[3], sample[2][0], sample[2][1]))
    seen = set()
    domain = box(*BOUNDS)
    for station, lateral, point, rule in samples:
        key = tuple(float(value) for value in point)
        if (
            key in seen
            or not domain.covers(Point(point))
            or not corridor.influence.covers(Point(point))
        ):
            continue
        seen.add(key)
        source = _sample_grid(corridor.inputs.baseline, float(point[0]), float(point[1]), 2.0)
        candidate = field_height(corridor, source, station, lateral)
        tested += 1
        difference = abs(candidate - source)
        maximum = max(maximum, difference)
        if not math.isfinite(candidate) or difference >= 5.0:
            return {
                "passes": False,
                "testedSamples": tested,
                "maximumObservedAbsoluteChangeM": maximum,
                "criterion": "strict absolute source-relative earthwork <5 m",
                "firstViolation": {
                    "stationM": station,
                    "lateralM": lateral,
                    "xz": list(key),
                    "sourceY": source,
                    "candidateY": candidate,
                    "absoluteChangeM": difference,
                    "rule": rule,
                },
            }
    return {
        "passes": True,
        "testedSamples": tested,
        "maximumObservedAbsoluteChangeM": maximum,
        "criterion": "necessary only: strict absolute source-relative earthwork <5 m",
    }


def build_corrected(root: Path, evidence: Path) -> dict[str, Any]:
    corridor = load_corridor(root)
    chart = make_chart(corridor.part)
    # Preserve actual chart geometry for independent inspection even on preflight failure.
    chart_assets = {
        "chart-xz.f64": chart.points.astype("<f8").tobytes(),
        "chart-station-lateral.f64": chart.fields.astype("<f8").tobytes(),
        "chart-indices.u32": chart.triangles.tobytes(),
    }
    witnesses = {}
    for name, payload in chart_assets.items():
        (evidence / name).write_bytes(payload)
        witnesses[name] = {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "byteLength": len(payload),
        }
    report = {
        "status": "STOP",
        "algorithm": "continuous-station-lateral-miter-v1",
        "releaseId": corridor.inputs.release_id,
        "sourceHashes": corridor.inputs.source_hashes,
        "profile": {
            "stationsM": corridor.stations.tolist(),
            "sourceY": corridor.source_profile.tolist(),
            "smoothedY": corridor.graded_profile.tolist(),
            "heightDifferenceM": (corridor.graded_profile - corridor.source_profile).tolist(),
            "sourceSignedGradeMPerM": (
                np.diff(corridor.source_profile) / np.diff(corridor.stations)
            ).tolist(),
            "smoothedSignedGradeMPerM": (
                np.diff(corridor.graded_profile) / np.diff(corridor.stations)
            ).tolist(),
        },
        "chart": {
            "sectionStationsM": chart.stations.tolist(),
            "lateralBoundariesM": list(LATERALS),
            "vertices": len(chart.points),
            "triangles": len(chart.triangles),
            "joins": "source miter vectors interpolated along the unchanged source segments",
            "ownership": "continuous barycentric station/lateral fields; no nearest segment",
        },
        "evidenceBuffers": witnesses,
        "fullMeshAssembled": False,
    }
    result = preflight(corridor, chart)
    report["necessaryEarthworkPreflight"] = result
    if not result["passes"]:
        report["stopReasons"] = ["necessary earthwork preflight violates strict <5m ceiling"]
        return report
    ownership = ownership_report(corridor, chart)
    report["ownership"] = ownership
    if not ownership["passes"]:
        report["stopReasons"] = ["unresolved nearby-road/off-ground ownership conflict"]
        return report
    # The fixed chart is noded with unchanged source planes and fine local lines.
    report.update(assemble_corrected(corridor, chart, evidence))
    return report


def assemble_corrected(corridor: Corridor, chart: Chart, evidence: Path) -> dict[str, Any]:
    """Conform all chart/source/shoulder/carriageway and influence boundaries."""
    domain = box(*BOUNDS)
    lines = [LineString(corridor.influence.exterior.coords)]
    unique_edges = set()
    for triangle in chart.triangles:
        for a, b in (
            (triangle[0], triangle[1]),
            (triangle[1], triangle[2]),
            (triangle[2], triangle[0]),
        ):
            unique_edges.add(tuple(sorted((int(a), int(b)))))
    for edge in sorted(unique_edges):
        clipped = LineString(chart.points[list(edge)]).intersection(corridor.influence)
        if clipped.geom_type == "LineString" and clipped.length > 0:
            lines.append(clipped)
        elif clipped.geom_type == "MultiLineString":
            lines.extend(clipped.geoms)
    # Existing source diagonals and coarse controls remain exact outside treatment.
    for x in np.arange(BOUNDS[0], BOUNDS[2] + 0.1, 2.0):
        lines.append(LineString(((x, BOUNDS[1]), (x, BOUNDS[3]))))
    for z in np.arange(BOUNDS[1], BOUNDS[3] + 0.1, 2.0):
        lines.append(LineString(((BOUNDS[0], z), (BOUNDS[2], z))))
    for x in np.arange(BOUNDS[0], BOUNDS[2], 2.0):
        for z in np.arange(BOUNDS[1], BOUNDS[3], 2.0):
            lines.append(LineString(((x, z + 2.0), (x + 2.0, z))))
    # Fine lines end on the inset coarse collar, preserving the original perimeter.
    for x in np.arange(BOUNDS[0] + 2.0, BOUNDS[2] - 1.9, 0.5):
        lines.append(LineString(((x, BOUNDS[1] + 2.0), (x, BOUNDS[3] - 2.0))))
    for z in np.arange(BOUNDS[1] + 2.0, BOUNDS[3] - 1.9, 0.5):
        lines.append(LineString(((BOUNDS[0] + 2.0, z), (BOUNDS[2] - 2.0, z))))
    mesh = build_constrained_mesh(domain, lines)
    xz = mesh.vertices_xz.astype("<f4")
    triangles = mesh.triangles.astype("<u4")
    source = corridor.source(xz)
    candidate = source.copy()
    for index, point in enumerate(xz.astype(float)):
        if corridor.influence.contains(Point(point)):
            field = chart.locate(point)
            if field is not None:
                candidate[index] = field_height(corridor, source[index], *field)
    # Boundary/outside incident faces must retain their original source planes.
    polygons = shapely.polygons(xz[triangles])
    fixed_faces = ~shapely.covers(corridor.influence, polygons)
    fixed = np.unique(triangles[fixed_faces])
    candidate[fixed] = source[fixed]
    candidate = candidate.astype("<f4")
    assets = {
        "failed-xz.f32": xz.tobytes(),
        "failed-source-y.f64": source.astype("<f8").tobytes(),
        "failed-candidate-y.f32": candidate.tobytes(),
        "failed-indices.u32": triangles.tobytes(),
    }
    hashes = {}
    for name, payload in assets.items():
        (evidence / name).write_bytes(payload)
        hashes[name] = {"byteLength": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    edges = np.unique(
        np.sort(
            np.concatenate((triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]])),
            axis=1,
        ),
        axis=0,
    )
    lengths = np.linalg.norm(xz[edges[:, 0]].astype(float) - xz[edges[:, 1]], axis=1)
    added = (
        np.abs(candidate[edges[:, 0]].astype(float) - candidate[edges[:, 1]])
        - np.abs(source[edges[:, 0]] - source[edges[:, 1]])
    ) / lengths
    absolute = np.abs(candidate.astype(float) - source)
    worst = int(np.argmax(added))
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
    overlay = affine_surface_overlay_extrema(mesh, candidate, source_index)
    topology = topology_report(xz, triangles)
    safety = {
        "passes": bool(
            np.isfinite(candidate).all()
            and overlay["maximumAbsoluteChangeFromSourceM"] < 5
            and added.max() < 1
        ),
        "maximumVertexAbsoluteChangeM": float(absolute.max()),
        "maximumAbsoluteChangeM": overlay["maximumAbsoluteChangeFromSourceM"],
        "maximumPositiveAddedGradientMPerM": float(added.max()),
        "worstEdgeXZ": xz[edges[worst]].tolist(),
        "worstEdgeSourceY": source[edges[worst]].tolist(),
        "worstEdgeCandidateY": candidate[edges[worst]].tolist(),
        "sourceOverlay": overlay,
    }
    # Chart cuts reaching the perimeter add seam nodes. Reject instead of concealing them.
    boundary_valid = all(
        np.linalg.norm(xz[a].astype(float) - xz[b]) == 2.0 for a, b in mesh.boundary_edges
    )
    reasons = []
    if not safety["passes"]:
        reasons.append("final global safety ceiling violation")
    if not boundary_valid:
        reasons.append("exact original 2m perimeter not preserved after chart noding")
    if not topology["passes"]:
        reasons.append("final Float32 topology failure")
    return {
        "status": "STOP" if reasons else "GEOMETRY_READY",
        "stopReasons": reasons,
        "fullMeshAssembled": True,
        "finalSafety": safety,
        "finalTopology": topology,
        "boundaryExactlySource": boundary_valid,
        "finalGeometry": {"vertices": len(xz), "triangles": len(triangles), "buffers": hashes},
    }


def ownership_report(corridor: Corridor, chart: Chart) -> dict[str, Any]:
    """Reject any other road core sharing the active target core; never hide a junction.

    An isolated target has unambiguous ownership. A ground or off-ground overlap
    is retained as an explicit conflict requiring a separately reviewed policy.
    """
    core_faces = []
    for triangle in chart.triangles:
        lateral = chart.fields[triangle, 1]
        if np.min(lateral) >= -4 and np.max(lateral) <= 4:
            core_faces.append(Polygon(chart.points[triangle]))
    core = shapely.union_all(core_faces).intersection(corridor.influence).intersection(box(*BOUNDS))
    conflicts = []
    excluded = []
    for feature in corridor.inputs.road_payload["features"]:
        way_id = feature["source"]["osmId"]
        if way_id == 78455395:
            continue
        ground = (
            feature.get("groundAssumption")
            == "ground_assumed_from_absent_or_explicit_no_vertical_tags"
        )
        if not ground:
            excluded.append(way_id)
        for part_index, part in enumerate(feature["centerlinePartsXZ"]):
            if len(part) < 2:
                continue
            ribbon = LineString(part).buffer(
                float(feature["estimatedWidthM"]) / 2.0, cap_style="flat"
            )
            overlap = ribbon.intersection(core)
            if overlap.area > 1e-8:
                conflicts.append(
                    {
                        "wayId": way_id,
                        "partIndex": part_index,
                        "groundEligible": ground,
                        "overlapAreaM2": overlap.area,
                        "overlapWkt": overlap.wkt,
                    }
                )
    return {
        "passes": not conflicts,
        "policy": "isolated target only; all other/off-ground cores protected",
        "excludedOffGroundWayIds": sorted(set(excluded)),
        "conflicts": conflicts,
    }
