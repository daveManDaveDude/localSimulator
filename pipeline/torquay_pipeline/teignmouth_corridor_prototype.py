"""Independent, offline Teignmouth shared-corridor feasibility experiment.

The source is the pinned 2 m EA-derived display grid, never new survey data.
Only the registered rectangle can change. No rejected solver is imported.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import shapely
from shapely.geometry import LineString, Polygon, box

from .road_surface import _line_point_tangent, _sample_grid, load_config, load_release_inputs

RELEASE_ID = "616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a"
BOUNDS = (-182.0, -136.0, -98.0, -54.0)
START, END, ANCHOR = 140.0, 155.0, 148.15104603556912
SIGMA, STEP, RADIUS = 12.0, 2.0, 18


def gaussian_profile(values: np.ndarray) -> np.ndarray:
    """Independent normalized 3-sigma kernel; reflect, or pad short profiles.

    Matches the documented upstream 2 m / sigma 12 m kernel, without importing
    upstream code. Reflection excludes the endpoint, as NumPy ``reflect`` does.
    """
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("profile must be a finite nonempty vector")
    offsets = np.arange(-RADIUS, RADIUS + 1, dtype=np.float64) * STEP
    weights = np.exp(-0.5 * (offsets / SIGMA) ** 2)
    weights /= weights.sum()
    padded = np.pad(values, RADIUS, mode="reflect" if len(values) > RADIUS else "edge")
    return np.convolve(padded, weights, mode="valid")


def smoothstep(value: np.ndarray) -> np.ndarray:
    t = np.clip(value, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


@dataclass
class Corridor:
    """One fixed recipe over source terrain, suitable for Float32 triangulation."""

    inputs: Any
    part: list[list[float]]
    stations: np.ndarray
    source_profile: np.ndarray
    graded_profile: np.ndarray
    influence: Polygon

    def source(self, points: np.ndarray) -> np.ndarray:
        return np.asarray([_sample_grid(self.inputs.baseline, x, z, 2.0) for x, z in points])

    def heights(self, points: np.ndarray) -> np.ndarray:
        """Flat 6 m carriageway + 1 m shoulder; 1:2-derived 2–12 m blend.

        The 32 m registered longitudinal fade is retained. All vertices incident
        to outside-influence faces are pinned by the mesh builder as well.
        """
        source = self.source(points)
        nearest = np.full(len(points), np.inf)
        station = np.zeros(len(points))
        accumulated = 0.0
        for first, second in zip(self.part, self.part[1:], strict=False):
            a, b = np.asarray(first), np.asarray(second)
            delta = b - a
            length = float(np.linalg.norm(delta))
            if not length:
                continue
            fraction = np.clip((points - a) @ delta / (length * length), 0.0, 1.0)
            distances = np.linalg.norm(points - (a + fraction[:, None] * delta), axis=1)
            # Stable source segment ordering resolves equal-distance ties.
            selected = distances < nearest
            nearest[selected] = distances[selected]
            station[selected] = accumulated + fraction[selected] * length
            accumulated += length
        target = np.interp(station, self.stations, self.graded_profile)
        transition = np.clip(2.0 * np.abs(target - source), 2.0, 12.0)
        lateral = 1.0 - smoothstep((nearest - 4.0) / transition)
        distance_from_window = np.maximum(np.maximum(START - station, station - END), 0.0)
        longitudinal = 1.0 - smoothstep(distance_from_window / 32.0)
        permitted = shapely.contains_xy(self.influence, points[:, 0], points[:, 1])
        return source + (target - source) * lateral * longitudinal * permitted


def load_corridor(root: Path) -> Corridor:
    inputs = load_release_inputs(
        root, load_config(root / "config/road-surface-teignmouth-candidate.json")
    )
    if inputs.release_id != RELEASE_ID:
        raise ValueError("wrong pinned source release")
    feature = next(f for f in inputs.road_payload["features"] if f["source"]["osmId"] == 78455395)
    if feature["estimatedWidthM"] != 6 or feature.get("groundAssumption") != (
        "ground_assumed_from_absent_or_explicit_no_vertical_tags"
    ):
        raise ValueError("target width or ground eligibility changed")
    part = feature["centerlinePartsXZ"][0]
    length = sum(math.dist(a, b) for a, b in zip(part, part[1:], strict=False))
    stations = np.arange(0.0, length, STEP)
    # Keep the exact source endpoint, without calling its shorter final segment 2 m.
    if stations[-1] != length:
        stations = np.append(stations, length)
    points = np.asarray([_line_point_tangent(part, s)[0] for s in stations])
    source = np.asarray([_sample_grid(inputs.baseline, x, z, 2.0) for x, z in points])
    cumulative = np.r_[
        0.0, np.cumsum([math.dist(a, b) for a, b in zip(part, part[1:], strict=False)])
    ]
    target_points = [_line_point_tangent(part, START)[0]]
    target_points.extend(p for p, s in zip(part, cumulative, strict=True) if START < s < END)
    target_points.append(_line_point_tangent(part, END)[0])
    influence = LineString(target_points).buffer(35.0)
    if not box(*BOUNDS).covers(influence):
        raise ValueError("required domain expansion")
    return Corridor(inputs, part, stations, source, gaussian_profile(source), influence)


def build_mesh() -> tuple[np.ndarray, np.ndarray]:
    """0.5 m source-diagonal grid, joined to the unchanged 2 m coarse perimeter.

    Every face stays within an original source triangle. Boundary-cell polygons
    use constrained triangulation with shared collinear half-metre edge nodes;
    the exterior retains only the original two-metre nodes.
    """
    xmin, zmin, xmax, zmax = BOUNDS
    coordinates: dict[tuple[float, float], int] = {}
    triangles: list[list[int]] = []

    def add_triangle(points: list[tuple[float, float]]) -> None:
        ids = []
        for point in points:
            if point not in coordinates:
                coordinates[point] = len(coordinates)
            ids.append(coordinates[point])
        a, b, c = np.asarray(points)
        area = np.linalg.det(np.asarray([b - a, c - a]))
        if area == 0:
            raise ValueError("degenerate construction face")
        triangles.append(ids if area < 0 else [ids[0], ids[2], ids[1]])

    for z in np.arange(zmin, zmax, 2.0):
        for x in np.arange(xmin, xmax, 2.0):
            outer = x == xmin or z == zmin or x == xmax - 2 or z == zmax - 2
            if not outer:
                for dz in np.arange(0.0, 2.0, 0.5):
                    for dx in np.arange(0.0, 2.0, 0.5):
                        a, b = (x + dx, z + dz), (x + dx + 0.5, z + dz)
                        c, d = (x + dx, z + dz + 0.5), (x + dx + 0.5, z + dz + 0.5)
                        add_triangle([a, c, b])
                        add_triangle([b, c, d])
                continue
            a, b, c, d = (x, z), (x + 2, z), (x, z + 2), (x + 2, z + 2)
            for coarse in ([a, c, b], [b, c, d]):
                ring = []
                for first, second in zip(coarse, coarse[1:] + coarse[:1], strict=True):
                    exterior = (first[0] == second[0] and first[0] in (xmin, xmax)) or (
                        first[1] == second[1] and first[1] in (zmin, zmax)
                    )
                    steps = 1 if exterior else 4
                    ring.extend(
                        (
                            first[0] + (second[0] - first[0]) * t / steps,
                            first[1] + (second[1] - first[1]) * t / steps,
                        )
                        for t in range(steps)
                    )
                for face in shapely.constrained_delaunay_triangles(Polygon(ring)).geoms:
                    add_triangle(list(face.exterior.coords)[:-1])
    return np.asarray(list(coordinates), dtype="<f4"), np.asarray(triangles, dtype="<u4")


def topology_report(xz: np.ndarray, triangles: np.ndarray) -> dict[str, Any]:
    """Verify actual serialized X/Z, including full union and exact shared edges."""
    faces = xz[triangles].astype(np.float64)
    first, second = faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 0]
    cross = first[:, 0] * second[:, 1] - first[:, 1] * second[:, 0]
    edges = Counter(
        tuple(sorted((int(t[i]), int(t[(i + 1) % 3])))) for t in triangles for i in range(3)
    )
    boundary = [e for e, n in edges.items() if n == 1]
    expected = set()
    for x in np.arange(-182.0, -98.0, 2.0):
        for z in (-136.0, -54.0):
            expected.add(tuple(sorted(((x, z), (x + 2, z)))))
    for z in np.arange(-136.0, -54.0, 2.0):
        for x in (-182.0, -98.0):
            expected.add(tuple(sorted(((x, z), (x, z + 2)))))
    actual = {tuple(sorted((tuple(xz[a]), tuple(xz[b])))) for a, b in boundary}
    polygons = shapely.polygons(faces)
    union = shapely.union_all(polygons)
    summed = float(np.sum(-cross) * 0.5)
    overlap = summed - union.area
    holes = float(union.symmetric_difference(box(*BOUNDS)).area)
    passes = bool(
        np.isfinite(xz).all()
        and np.all(cross < 0)
        and all(n in (1, 2) for n in edges.values())
        and actual == expected
        and len(xz) - len(edges) + len(triangles) == 1
        and abs(overlap) < 1e-8
        and holes < 1e-8
    )
    return {
        "passes": passes,
        "vertices": len(xz),
        "triangles": len(triangles),
        "boundaryEdges": len(boundary),
        "boundaryExactlySource": actual == expected,
        "overlapAreaM2": overlap,
        "uncoveredOrOutsideAreaM2": holes,
        "upwardNondegenerate": bool(np.all(cross < 0)),
        "eulerCharacteristic": len(xz) - len(edges) + len(triangles),
    }


def diagnostic(root: Path, candidate_directory: Path | None = None) -> dict[str, Any]:
    """Build fixed geometry; stop immediately on topology or global safety failure.

    The optional output contains a geometry-stage candidate only. It cannot be
    served to a browser until subsequent ownership/road/building gates finish.
    """
    corridor = load_corridor(root)
    xz, triangles = build_mesh()
    source = corridor.source(xz)
    heights = corridor.heights(xz).astype("<f4")
    # Pin any face extending outside registered influence, preserving its source plane.
    face_polygons = shapely.polygons(xz[triangles])
    fixed_faces = ~shapely.covers(corridor.influence, face_polygons)
    fixed = np.unique(triangles[fixed_faces])
    heights[fixed] = source[fixed].astype("<f4")
    topology = topology_report(xz, triangles)
    edges = np.unique(
        np.sort(
            np.concatenate((triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]])),
            axis=1,
        ),
        axis=0,
    )
    lengths = np.linalg.norm(xz[edges[:, 1]].astype(float) - xz[edges[:, 0]], axis=1)
    added = (
        np.abs(np.diff(heights[edges].astype(float), axis=1)[:, 0])
        - np.abs(np.diff(source[edges], axis=1)[:, 0])
    ) / lengths
    absolute = np.abs(heights.astype(float) - source)
    worst = int(np.argmax(added))
    safety = {
        "maximumAbsoluteChangeM": float(absolute.max()),
        "absoluteChangeLimitStrictM": 5.0,
        "maximumPositiveAddedGradientMPerM": float(added.max()),
        "addedGradientLimitStrict": 1.0,
        "worstEdgeXZ": xz[edges[worst]].tolist(),
        "worstEdgeSourceY": source[edges[worst]].tolist(),
        "worstEdgeCandidateY": heights[edges[worst]].tolist(),
        "passes": bool(absolute.max() < 5 and added.max() < 1),
    }
    source_grade = np.diff(corridor.source_profile) / np.diff(corridor.stations)
    graded_grade = np.diff(corridor.graded_profile) / np.diff(corridor.stations)
    profile = {
        "stationsM": corridor.stations.tolist(),
        "sourceY": corridor.source_profile.tolist(),
        "smoothedY": corridor.graded_profile.tolist(),
        "heightDifferenceM": (corridor.graded_profile - corridor.source_profile).tolist(),
        "sourceSignedGradeMPerM": source_grade.tolist(),
        "smoothedSignedGradeMPerM": graded_grade.tolist(),
        "signedGradeDifferenceMPerM": (graded_grade - source_grade).tolist(),
        "kernel": {
            "sigmaM": SIGMA,
            "sampleStepM": STEP,
            "radiusSamples": RADIUS,
            "boundary": "reflect excluding end, or edge when n <= radius",
            "endpointFinalIntervalM": float(np.diff(corridor.stations)[-1]),
        },
    }
    files = {
        name: {
            "sha256": record.get("sha256", record.get("readySha256")),
            "byteLength": record.get("byteLength"),
        }
        for name, record in corridor.inputs.source_hashes.items()
    }
    report = {
        "schema": 1,
        "status": "FEASIBLE" if topology["passes"] and safety["passes"] else "STOP",
        "releaseId": RELEASE_ID,
        "sourceInputs": files,
        "recipe": {
            "widthM": 6,
            "shoulderM": 1,
            "slopeHorizontalPerVertical": 2,
            "blendMinM": 2,
            "blendMaxM": 12,
            "longitudinalFadeM": 32,
            "fineSpacingM": 0.5,
            "boundsXZ": list(BOUNDS),
        },
        "topology": topology,
        "globalSafety": safety,
        "profile": profile,
        "bufferBytes": {"xz": xz.nbytes, "y": heights.nbytes, "indices": triangles.nbytes},
        "geometryHashes": {
            "xz": hashlib.sha256(xz.tobytes()).hexdigest(),
            "y": hashlib.sha256(heights.tobytes()).hexdigest(),
            "indices": hashlib.sha256(triangles.tobytes()).hexdigest(),
        },
        "stopReasons": (["invalid topology"] if not topology["passes"] else [])
        + (["global safety ceiling violation"] if not safety["passes"] else []),
    }
    if candidate_directory is not None and report["status"] == "FEASIBLE":
        candidate_directory.mkdir(parents=True, exist_ok=False)
        xyz = np.column_stack((xz[:, 0], heights, xz[:, 1])).astype("<f4")
        (candidate_directory / "terrain-vertices.f32").write_bytes(xyz.tobytes())
        (candidate_directory / "terrain-indices.u32").write_bytes(triangles.tobytes())
        (candidate_directory / "source-heights.f32").write_bytes(source.astype("<f4").tobytes())
    return report
