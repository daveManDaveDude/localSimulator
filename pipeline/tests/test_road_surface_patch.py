from __future__ import annotations

import hashlib
import json
import runpy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from shapely.geometry import LineString, Polygon

import torquay_pipeline.road_surface_patch as road_surface_patch_module
from torquay_pipeline.road_surface import RoadSurfaceError, _sample_grid
from torquay_pipeline.road_surface_patch import (
    PATCH_ALGORITHM_VERSION,
    PATCH_FINE_SPACING_M,
    PATCH_OFFLINE_GATE_NAMES,
    PATCH_OUTPUT_FILES,
    PATCH_PACKAGE_TYPE,
    CompositeSurface,
    PatchBounds,
    RoadSurfacePatchError,
    _barycentric_violation,
    _fixed_patch_vertices,
    _patch_triangle_weights,
    _quantize_road_point_for_owners,
    _section_lateral_metrics,
    _shared_float32_owners,
    _triangle_barycentric_weights,
    _triangle_vertex_adjacency,
    _triangles_fully_within_influence,
    _validate_quantized_phase_one,
    assemble_candidate_patch_assets,
    assemble_deterministic_candidate_assets,
    build_conforming_mesh,
    build_local_phase_one_constraints,
    build_topology_study_mesh,
    composite_building_base_report,
    composite_earthwork_overlay_report,
    composite_walk_clearance_report,
    mandatory_corridor_station_union,
    patch_source_triangle_ownership_report,
    patch_topology_report,
    preflight_candidate_publish_paths,
    publish_candidate_patch_assets,
    reclip_affected_road_batches,
    serialize_offline_report,
    solve_local_phase_one,
    validate_candidate_patch_assets,
    validate_offline_candidate,
    validate_terrain_mesh_resources,
    verify_accepted_plane_refinement,
    verify_composite_terrain,
)


def _plane(rows: int, columns: int, spacing_m: float = 2.0) -> np.ndarray:
    row, column = np.mgrid[0:rows, 0:columns]
    return (0.25 * column - 0.125 * row + 3.0).astype(np.float32)


def test_scaled_local_feasibility_handles_near_parallel_rows_and_fixed_unknowns() -> None:
    # Large offsets and differently scaled rows must not turn a feasible system
    # into an infeasibility claim. The third unknown is an exact fixed datum.
    matrix = np.asarray(
        [[1.0, 0.0, 1.0], [-1.0, 0.0, -1.0], [1.0, 0.001, 0.0], [-1.0, -0.001, 0.0]]
    )
    target = np.asarray([1000.0, 0.2, -3.0])
    scales = np.asarray([1e-4, 1e4, 1.0, 100.0])
    result, report = road_surface_patch_module.solve_bounded_local_feasibility(
        matrix * scales[:, None],
        (matrix @ target + 1e-5) * scales,
        np.asarray([999.0, -1.0, -3.0]),
        np.asarray([1001.0, 1.0, -3.0]),
        maximum_iterations=2000,
        maximum_wall_seconds=10.0,
    )
    assert report["status"] == "feasible"
    assert result[2] == -3.0
    assert np.max(matrix @ result - (matrix @ target + 1e-5)) < 1e-6
    assert report.get("infeasibilityCertificate") is None


def test_scaled_local_feasibility_returns_checkable_bounded_certificate() -> None:
    matrix = np.asarray([[1.0, 0.0], [-1.0, 0.0], [0.0, 1.0]])
    limits = np.asarray([0.0, -0.02, 1.0])
    lower, upper = np.asarray([-5.0, -5.0]), np.asarray([5.0, 5.0])
    _result, report = road_surface_patch_module.solve_bounded_local_feasibility(
        matrix,
        limits,
        lower,
        upper,
        maximum_iterations=2000,
        maximum_wall_seconds=10.0,
    )
    certificate = report["infeasibilityCertificate"]
    weights = np.asarray(certificate["nonnegativeRowWeights"])
    combined = matrix.T @ weights
    gap = np.minimum(combined * lower, combined * upper).sum() - limits @ weights
    assert report["status"] == "certified_infeasible"
    assert weights.min() >= 0.0
    assert gap > certificate["roundoffAllowanceM"]
    assert gap == pytest.approx(certificate["contradictionGapM"])


def test_scaled_local_feasibility_never_certifies_a_feasible_thin_interval() -> None:
    matrix = np.asarray([[1.0], [-1.0]])
    values, report = road_surface_patch_module.solve_bounded_local_feasibility(
        matrix,
        np.asarray([0.000001, 0.0]),
        np.asarray([-5.0]),
        np.asarray([5.0]),
        maximum_iterations=500,
        maximum_wall_seconds=10.0,
    )
    assert report["status"] == "feasible"
    assert 0.0 <= values[0] <= 0.000001


def test_sol_escalation_runner_uses_its_own_write_once_evidence_path(tmp_path) -> None:
    runner = runpy.run_path(
        str(Path(__file__).parents[1] / "scripts/run_teignmouth_patch_sol_escalation_offline.py")
    )
    relative = ".codex/evidence/teignmouth-road-surface-sol-escalation"
    assert runner["EVIDENCE_PATH"] == runner["ROOT"] / relative
    evidence = tmp_path / relative
    evidence.mkdir(parents=True)
    marker = evidence / "attempt.json"
    marker.write_bytes(b"preserve")
    preflight = runner["_preflight"]
    preflight.__globals__["EVIDENCE_PATH"] = evidence
    with pytest.raises(RoadSurfacePatchError, match="already exists"):
        preflight(tmp_path)
    assert marker.read_bytes() == b"preserve"


def _mesh_signature(mesh) -> tuple[bytes, bytes, bytes]:
    return (
        mesh.vertices_xz.astype("<f4").tobytes(),
        mesh.base_y.astype("<f4").tobytes(),
        mesh.triangles.astype("<u4").tobytes(),
    )


def test_patch_has_regular_half_metre_interior_and_coarse_perimeter() -> None:
    heights = _plane(15, 15)
    bounds = PatchBounds(first_row=4, first_column=3, row_count=6, column_count=7)

    mesh = build_conforming_mesh(bounds, heights, 28.0, 28.0, 2.0)

    expected_vertices = (
        16 * bounds.coarse_cell_count - 2 * bounds.row_count - 2 * bounds.column_count + 1
    )
    assert mesh.vertices_xz.shape == (expected_vertices, 2)
    assert len(mesh.triangles) < bounds.coarse_cell_count * 32
    assert len(mesh.triangles) > bounds.coarse_cell_count * 2
    interior_cell_count = (bounds.row_count - 2) * (bounds.column_count - 2)
    assert (
        sum(
            len(indices)
            for (row, column, _half), indices in mesh.cell_half_triangles.items()
            if bounds.first_row < row < bounds.last_row - 1
            and bounds.first_column < column < bounds.last_column - 1
        )
        == interior_cell_count * 32
    )
    assert len(mesh.boundary_edges) == 2 * (bounds.row_count + bounds.column_count)
    assert all(count == 2 for count in mesh.edge_counts.values() if count != 1)
    report = patch_topology_report(mesh, 2.0)
    assert report["patchTriangleCount"] == len(mesh.triangles)
    assert report["removedCoarseTriangleCount"] == bounds.coarse_cell_count * 2
    assert report["nonManifoldEdgeCount"] == 0
    assert report["passes"]
    assert report["boundaryEdgesMatch"]
    assert report["boundaryCycleValid"]
    assert report["vertexGraphConnected"]
    assert report["eulerCharacteristic"] == 1
    assert report["areaCoverageValid"]
    assert report["resourceLimitsPass"]
    assert all(np.isfinite(mesh.vertices_xz.astype(np.float32)).ravel())

    keys = np.rint((mesh.vertices_xz + 14.0) / PATCH_FINE_SPACING_M).astype(np.int64)
    boundary_rows = {4 * bounds.first_row, 4 * bounds.last_row}
    boundary_columns = {4 * bounds.first_column, 4 * bounds.last_column}
    for column_key, row_key in keys:
        if row_key in boundary_rows or column_key in boundary_columns:
            assert row_key % 4 == 0 and column_key % 4 == 0


def test_patch_subdivision_reproduces_each_accepted_fixed_triangle_plane() -> None:
    heights = np.zeros((9, 9), dtype=np.float32)
    heights[4, 4] = 2.0
    bounds = PatchBounds(first_row=2, first_column=2, row_count=2, column_count=2)
    mesh = build_conforming_mesh(bounds, heights, 16.0, 16.0, 2.0)

    for triangle in mesh.triangles:
        points = mesh.vertices_xz[triangle]
        center = points.mean(axis=0)
        mesh_height = float(mesh.base_y[triangle].astype(np.float64).mean())
        accepted_height = _sample_grid(heights, float(center[0]), float(center[1]), 2.0)
        assert mesh_height == pytest.approx(accepted_height, abs=2e-7)


def test_patch_face_ownership_preserves_each_source_half_cell_breakline() -> None:
    heights = _plane(21, 21)
    inputs = SimpleNamespace(
        spacing_m=2.0,
        width_m=40.0,
        depth_m=40.0,
        baseline=heights,
        rows=heights.shape[0],
        columns=heights.shape[1],
    )
    mesh = build_conforming_mesh(PatchBounds(7, 7, 6, 6), heights, 40.0, 40.0, 2.0)

    report = patch_source_triangle_ownership_report(mesh, inputs)

    assert report["passes"]
    assert report["patchTriangleCount"] == len(mesh.triangles)
    assert report["sourceHalfCellOwnershipViolationCount"] == 0


@pytest.mark.parametrize("variant", ["flip-05", "road-05", "collar-05"])
def test_study_mesh_variants_have_indexed_complete_source_coverage(variant: str) -> None:
    heights = np.random.default_rng(42).normal(size=(15, 15)).astype(np.float32)
    inputs = SimpleNamespace(
        spacing_m=2.0,
        width_m=28.0,
        depth_m=28.0,
        baseline=heights,
        rows=heights.shape[0],
        columns=heights.shape[1],
    )
    bounds = PatchBounds(first_row=4, first_column=4, row_count=5, column_count=5)
    influence = LineString([(-4.0, -4.0), (-1.0, -4.0)]).buffer(6.0)
    centerline = [(-4.0, -4.0), (-1.0, -4.0)]

    mesh = build_topology_study_mesh(
        bounds,
        heights,
        inputs,
        influence,
        centerline,
        variant=variant,
    )
    ownership = patch_source_triangle_ownership_report(mesh, inputs)
    repeat = build_topology_study_mesh(
        bounds,
        heights,
        inputs,
        influence,
        centerline,
        variant=variant,
    )
    surface = CompositeSurface(mesh, inputs, heights, mesh.base_y.astype("<f4"))

    assert mesh.topology_variant == variant
    assert mesh.triangle_tree is not None
    assert mesh.triangle_geometries is not None
    assert len(mesh.triangle_geometries) == len(mesh.triangles)
    assert ownership["passes"]
    assert ownership["sourceHalfCellOwnershipViolationCount"] == 0
    plane_report = verify_accepted_plane_refinement(
        mesh,
        heights,
        inputs.spacing_m,
        influence=influence,
    )
    assert plane_report["passes"]
    assert plane_report["maximumAcceptedPlaneDeviationM"] <= 0.001
    assert all(mesh.cell_half_triangles.values())
    assert mesh.vertices_xz.astype("<f4").tobytes() == repeat.vertices_xz.astype("<f4").tobytes()
    assert mesh.triangles.tobytes() == repeat.triangles.tobytes()
    for x, z in ((3.0, 3.0), (3.0, -5.0), (-5.0, 3.0)):
        actual, owner = surface.sample(x, z)
        assert owner is not None
        assert actual == pytest.approx(_sample_grid(heights, x, z, 2.0), abs=1e-6)


@pytest.mark.parametrize(
    ("variant", "spacing_m"),
    [("local-025", 0.25), ("local-0125", 0.125)],
)
def test_local_refinement_mesh_is_conforming_and_keeps_source_planes_outside(
    variant: str, spacing_m: float
) -> None:
    heights = np.random.default_rng(81).normal(size=(15, 15)).astype(np.float32)
    inputs = SimpleNamespace(
        spacing_m=2.0,
        width_m=28.0,
        depth_m=28.0,
        baseline=heights,
        rows=heights.shape[0],
        columns=heights.shape[1],
    )
    bounds = PatchBounds(first_row=4, first_column=4, row_count=5, column_count=5)
    influence = LineString([(-4.0, -4.0), (-1.0, -4.0)]).buffer(6.0)
    centerline = [(-4.0, -4.0), (-1.0, -4.0)]

    mesh = build_topology_study_mesh(
        bounds,
        heights,
        inputs,
        influence,
        centerline,
        variant=variant,
        refinement_base_variant="road-05",
    )
    ownership = patch_source_triangle_ownership_report(mesh, inputs)
    plane_report = verify_accepted_plane_refinement(
        mesh,
        heights,
        inputs.spacing_m,
        influence=influence,
    )

    assert mesh.topology_variant == variant
    assert len(mesh.vertices_xz) > bounds.coarse_cell_count * 25
    assert ownership["passes"]
    assert plane_report["passes"]
    assert plane_report["maximumAcceptedPlaneDeviationM"] <= 0.001
    assert spacing_m in (0.25, 0.125)


def test_refinement_mesh_requires_completed_road_aligned_base() -> None:
    heights = np.zeros((15, 15), dtype=np.float32)
    inputs = SimpleNamespace(
        spacing_m=2.0,
        width_m=28.0,
        depth_m=28.0,
        baseline=heights,
        rows=15,
        columns=15,
    )
    bounds = PatchBounds(first_row=4, first_column=4, row_count=5, column_count=5)
    influence = LineString([(-4.0, -4.0), (-1.0, -4.0)]).buffer(6.0)

    with pytest.raises(RoadSurfacePatchError, match="requires a completed"):
        build_topology_study_mesh(
            bounds,
            heights,
            inputs,
            influence,
            [(-4.0, -4.0), (-1.0, -4.0)],
            variant="local-025",
        )


def test_patch_outer_float32_boundary_matches_existing_coarse_grid_bytes() -> None:
    heights = _plane(13, 13)
    bounds = PatchBounds(first_row=3, first_column=4, row_count=4, column_count=3)
    mesh = build_conforming_mesh(bounds, heights, 24.0, 24.0, 2.0)
    boundary_ids = set(int(index) for index in mesh.boundary_edges.ravel())

    assert len(boundary_ids) == (2 * (bounds.row_count + bounds.column_count))
    for vertex_id in boundary_ids:
        x, z = mesh.vertices_xz[vertex_id]
        column = int(round((x + 12.0) / 2.0))
        row = int(round((z + 12.0) / 2.0))
        assert np.float32(mesh.base_y[vertex_id]).tobytes() == heights[row, column].tobytes()
        assert np.float32(x).tobytes() == np.float32(column * 2.0 - 12.0).tobytes()
        assert np.float32(z).tobytes() == np.float32(row * 2.0 - 12.0).tobytes()


def test_patch_topology_and_float32_bytes_repeat_deterministically() -> None:
    heights = _plane(17, 17)
    bounds = PatchBounds(first_row=5, first_column=4, row_count=5, column_count=6)

    first = build_conforming_mesh(bounds, heights, 32.0, 32.0, 2.0)
    second = build_conforming_mesh(bounds, heights, 32.0, 32.0, 2.0)

    assert _mesh_signature(first) == _mesh_signature(second)


@pytest.mark.parametrize(
    "bounds",
    [
        PatchBounds(first_row=0, first_column=0, row_count=0, column_count=1),
        PatchBounds(first_row=0, first_column=0, row_count=81, column_count=1),
        PatchBounds(first_row=-1, first_column=0, row_count=1, column_count=1),
        PatchBounds(first_row=84, first_column=0, row_count=1, column_count=1),
    ],
)
def test_patch_rejects_empty_oversize_or_out_of_grid_bounds(bounds: PatchBounds) -> None:
    with pytest.raises(RoadSurfacePatchError):
        build_conforming_mesh(bounds, _plane(85, 85), 168.0, 168.0, 2.0)


def test_patch_rejects_nonfinite_accepted_base() -> None:
    heights = _plane(8, 8)
    heights[3, 3] = np.nan
    with pytest.raises(RoadSurfacePatchError, match="non-finite"):
        build_conforming_mesh(PatchBounds(2, 2, 2, 2), heights, 14.0, 14.0, 2.0)


def test_local_phase_one_uses_conforming_surface_samples_and_float32_solution() -> None:
    rows = columns = 201
    width = depth = 400.0
    row, column = np.mgrid[0:rows, 0:columns]
    x = column * 2.0 - width / 2
    z = row * 2.0 - depth / 2
    source = (0.1 * x + 0.02 * z).astype(np.float32)
    road_payload = {
        "features": [
            {
                "source": {"osmId": 78455395},
                "centerlinePartsXZ": [[[-100.0, 0.0], [90.0, 0.0]]],
                "estimatedWidthM": 6.0,
            }
        ]
    }
    inputs = SimpleNamespace(
        road_payload=road_payload,
        baseline=source,
        columns=columns,
        rows=rows,
        spacing_m=2.0,
        width_m=width,
        depth_m=depth,
        accepted_preview_qa={
            "gridTreatment": {
                "harmFallback": {
                    "policy": {"alongRoadFadeDistanceM": 1.5},
                    "regions": [
                        {
                            "fadeDistanceM": 1.5,
                            "stationIntervals": [
                                {
                                    "wayId": 78455395,
                                    "partIndex": 0,
                                    "startM": 145.25,
                                    "endM": 146.75,
                                }
                            ],
                        }
                    ],
                }
            }
        },
    )
    bounds = PatchBounds(first_row=90, first_column=110, row_count=40, column_count=40)
    mesh = build_conforming_mesh(bounds, source, width, depth, 2.0)

    constraints, report = build_local_phase_one_constraints(mesh, inputs)
    station_union = mandatory_corridor_station_union(inputs, way_ids=(78455395,))[(78455395, 0)]
    projected, solve = solve_local_phase_one(mesh, inputs, constraints, maximum_iterations=200)

    assert report["maximumStationSpacingM"] <= 1.0
    assert report["acceptedMandatoryStationCountInWindow"] == 18
    assert report["sampleSpacingAcrossWidthM"] == 0.25
    assert {145.25, 146.75}.issubset(station_union)
    constrained_stations = {
        item["label"].get("stationM")
        for item in constraints
        if item["label"].get("kind") == "teignmouth-local-crossfall"
    }
    assert {145.25, 146.75}.issubset(constrained_stations)
    assert solve["converged"]
    assert np.isfinite(projected).all()
    assert (
        max(
            float(
                np.dot(item["coefficients"], projected[item["indices"]].astype(np.float64))
                - item["limitM"]
            )
            for item in constraints
        )
        <= 2e-5
    )


def test_local_phase_one_pins_fixed_vertices_during_each_projection() -> None:
    inputs, mesh = _synthetic_phase_one_inputs_and_mesh()
    influence = LineString(((-100.0, 0.0), (90.0, 0.0))).buffer(20.0)
    fixed = _fixed_patch_vertices(mesh, influence)
    fixed[mesh.boundary_edges.ravel()] = True
    one_fixed_edges = [
        edge for edge in mesh.edge_counts if bool(fixed[edge[0]]) != bool(fixed[edge[1]])
    ]
    assert one_fixed_edges
    fixed_vertex, free_vertex = next(
        (edge[0], edge[1]) if fixed[edge[0]] else (edge[1], edge[0]) for edge in one_fixed_edges
    )
    fixed_base = mesh.base_y.astype(np.float64)
    constraint = {
        "indices": np.asarray([fixed_vertex, free_vertex], dtype=np.int64),
        "coefficients": np.asarray([1.0, -1.0]),
        "limitM": float(fixed_base[fixed_vertex] - fixed_base[free_vertex] - 0.5),
        "label": {"kind": "fixed-projection-byte-regression"},
    }

    candidate, _report = solve_local_phase_one(
        mesh,
        inputs,
        [constraint],
        influence=influence,
        maximum_iterations=20,
    )

    assert candidate[fixed].astype("<f4").tobytes() == mesh.base_y[fixed].astype("<f4").tobytes()


def _synthetic_phase_one_inputs_and_mesh():
    rows = columns = 201
    width = depth = 400.0
    row, column = np.mgrid[0:rows, 0:columns]
    x = column * 2.0 - width / 2
    z = row * 2.0 - depth / 2
    source = (0.1 * x + 0.02 * z).astype(np.float32)
    inputs = SimpleNamespace(
        road_payload={
            "features": [
                {
                    "source": {"osmId": 78455395},
                    "centerlinePartsXZ": [[[-100.0, 0.0], [90.0, 0.0]]],
                    "estimatedWidthM": 6.0,
                }
            ]
        },
        baseline=source,
        columns=columns,
        rows=rows,
        spacing_m=2.0,
        width_m=width,
        depth_m=depth,
    )
    mesh = build_conforming_mesh(
        PatchBounds(first_row=90, first_column=110, row_count=40, column_count=40),
        source,
        width,
        depth,
        2.0,
    )
    return inputs, mesh


def test_mandatory_severe_solver_constraints_reuse_fallback_station_union() -> None:
    inputs, mesh = _synthetic_phase_one_inputs_and_mesh()
    row, column = np.mgrid[0 : inputs.rows, 0 : inputs.columns]
    x = column * inputs.spacing_m - inputs.width_m / 2
    z = row * inputs.spacing_m - inputs.depth_m / 2
    inputs.baseline = (0.05 * x + 0.20 * z).astype(np.float32)
    inputs.accepted_preview_qa = {
        "gridTreatment": {
            "harmFallback": {
                "policy": {"alongRoadFadeDistanceM": 1.5},
                "regions": [
                    {
                        "fadeDistanceM": 1.5,
                        "stationIntervals": [
                            {
                                "wayId": 78455395,
                                "partIndex": 0,
                                "startM": 142.25,
                                "endM": 145.75,
                            }
                        ],
                    }
                ],
            }
        }
    }

    station_union = mandatory_corridor_station_union(inputs, way_ids=(78455395,))[(78455395, 0)]
    constraints, report = build_local_phase_one_constraints(mesh, inputs)
    constrained_severe_stations = {
        item["label"]["stationM"]
        for item in constraints
        if item["label"]["kind"] == "mandatory-severe-corridor-crossfall"
    }

    assert {142.25, 145.75}.issubset(station_union)
    assert {142.25, 145.75}.issubset(constrained_severe_stations)
    assert report["mandatorySevereStationConstraintCountInPatch"] == len(
        constrained_severe_stations
    )
    assert report["mandatorySevereStationCountOutsidePatch"] > 0


def test_local_solver_includes_full_way_centerline_and_signed_grade_constraints() -> None:
    inputs, mesh = _synthetic_phase_one_inputs_and_mesh()
    inputs.road_payload["features"].append(
        {
            "source": {"osmId": 1363931058},
            "centerlinePartsXZ": [[[50.0, -10.0], [50.0, 30.0]]],
            "estimatedWidthM": 6.0,
        }
    )

    constraints, report = build_local_phase_one_constraints(mesh, inputs)

    targeted = [
        item
        for item in constraints
        if item["label"].get("wayId") == 1363931058
        and item["label"]["kind"]
        in {
            "registered-full-way-centerline-envelope",
            "registered-full-way-signed-grade-change",
        }
    ]
    assert targeted
    assert report["registeredFullWayMissingIds"] == [
        way_id
        for way_id in road_surface_patch_module.PROFILE_WAY_IDS
        if way_id not in {78455395, 1363931058}
    ]
    assert report["registeredFullWayConstrainedStationCount"] > 0
    assert all(item["label"].get("stationM", 0.0) >= 0.0 for item in targeted)


def test_outside_influence_triangles_and_patch_perimeter_remain_byte_exact() -> None:
    inputs, mesh = _synthetic_phase_one_inputs_and_mesh()
    influence = LineString(((40.0, 0.0), (55.0, 0.0))).buffer(12.0)
    fixed = _fixed_patch_vertices(mesh, influence)
    constraints, _report = build_local_phase_one_constraints(mesh, inputs)
    source_nodes = np.asarray(
        [_sample_grid(inputs.baseline, x, z, 2.0) for x, z in mesh.vertices_xz]
    )
    edges = np.asarray(list(mesh.edge_counts), dtype=np.int64)
    lengths = np.linalg.norm(mesh.vertices_xz[edges[:, 0]] - mesh.vertices_xz[edges[:, 1]], axis=1)
    edge_limits = np.abs(source_nodes[edges[:, 0]] - source_nodes[edges[:, 1]]) + 0.999 * lengths
    boundary = np.zeros(len(mesh.vertices_xz), dtype=bool)
    boundary[mesh.boundary_edges.ravel()] = True
    fixed |= boundary
    report = _validate_quantized_phase_one(
        mesh,
        mesh.base_y.astype("<f4"),
        source_nodes,
        edges,
        edge_limits,
        constraints,
        fixed,
        mesh.base_y.astype(np.float64),
        influence,
    )

    assert report["passes"]
    assert report["fixedVertexBytesMatch"]
    assert report["outsideInfluenceSurface"]["acceptedFloat32BytesPreserved"]
    assert report["outsideInfluenceSurface"]["outsideInfluenceTriangleCount"] > 0
    assert report["outsideInfluenceSurface"]["outsideInfluenceVerticesFixed"]
    assert not fixed.all()


def test_vectorized_influence_mask_matches_exact_triangle_coverage() -> None:
    _inputs, mesh = _synthetic_phase_one_inputs_and_mesh()
    influence = LineString(((38.0, -4.0), (59.0, 8.0))).buffer(12.0)

    actual = _triangles_fully_within_influence(mesh, influence)
    expected = np.asarray(
        [influence.covers(Polygon(mesh.vertices_xz[triangle])) for triangle in mesh.triangles],
        dtype=bool,
    )

    assert actual.shape == expected.shape
    assert np.array_equal(actual, expected)


def test_quantized_float32_violation_is_rejected_even_when_float64_witness_passes() -> None:
    limit = 1.00000009
    float64_value = 1.00000008
    candidate = np.asarray([float64_value], dtype="<f4")
    assert float64_value <= limit
    assert float(candidate[0]) > limit

    report = _validate_quantized_phase_one(
        None,
        candidate,
        np.asarray([0.0]),
        np.empty((0, 2), dtype=np.int64),
        np.empty(0, dtype=np.float64),
        [
            {
                "indices": np.asarray([0], dtype=np.int64),
                "coefficients": np.asarray([1.0]),
                "limitM": limit,
                "label": {"kind": "quantization-regression"},
            }
        ],
        np.asarray([False]),
        np.asarray([0.0]),
    )

    assert not report["passes"]
    assert report["worstLocalConstraint"]["kind"] == "quantization-regression"
    assert report["maximumLocalHalfspaceViolationM"] > 0


def test_subtolerance_float32_residual_is_reported_against_actual_crossfall_gate() -> None:
    candidate = np.asarray([0.01240006], dtype="<f4")
    constraints = [
        {
            "indices": np.asarray([0], dtype=np.int64),
            "coefficients": np.asarray([1.0]),
            "limitM": 0.0124,
            "label": {
                "kind": "teignmouth-local-crossfall",
                "stationM": 151.0,
                "lateralOffsetStartM": -1.75,
            },
        }
    ]

    report = _validate_quantized_phase_one(
        None,
        candidate,
        np.asarray([0.0]),
        np.empty((0, 2), dtype=np.int64),
        np.empty(0, dtype=np.float64),
        constraints,
        np.asarray([False]),
        np.asarray([0.0]),
    )

    assert report["passes"]
    assert report["maximumLocalHalfspaceViolationM"] > 0.0
    assert report["maximumLocalHalfspaceViolationM"] <= report["solverNumericalToleranceM"]
    assert report["solverLocalHalfspacesWithinTolerance"]
    assert report["maximumActualLocalAcceptanceViolationM"] <= 0.0
    assert report["maximumMeshEdgeAddedGradientExcessM"] == -np.inf


def test_phase_one_reports_infeasible_synthetic_halfspaces_without_accepting_them() -> None:
    inputs, mesh = _synthetic_phase_one_inputs_and_mesh()
    constraints, _report = build_local_phase_one_constraints(mesh, inputs)
    interior = int(np.argmin(np.sum((mesh.vertices_xz - np.asarray([40.0, 0.0])) ** 2, axis=1)))
    constraints.extend(
        [
            {
                "indices": np.asarray([interior]),
                "coefficients": np.asarray([1.0]),
                "limitM": -1.0,
                "label": {"kind": "synthetic-infeasible-upper"},
            },
            {
                "indices": np.asarray([interior]),
                "coefficients": np.asarray([-1.0]),
                "limitM": -1.0,
                "label": {"kind": "synthetic-infeasible-lower"},
            },
        ]
    )

    _candidate, solve = solve_local_phase_one(mesh, inputs, constraints, maximum_iterations=40)

    assert not solve["converged"]
    assert solve["maximumConstraintResidualM"] > 0.4


def test_refined_mesh_reproduces_accepted_piecewise_planes_within_one_millimetre() -> None:
    heights = np.zeros((9, 9), dtype=np.float32)
    heights[4, 4] = 2.0
    bounds = PatchBounds(first_row=2, first_column=2, row_count=4, column_count=4)
    mesh = build_conforming_mesh(bounds, heights, 16.0, 16.0, 2.0)

    report = verify_accepted_plane_refinement(mesh, heights, 2.0)

    assert report["passes"]
    assert report["maximumAcceptedPlaneDeviationM"] <= 0.001
    assert report["method"] == "exact affine extrema at every patch/source-triangle overlay vertex"
    assert report["overlayCount"] >= len(mesh.triangles)
    assert report["testedOverlayVertexCount"] > 0


def test_exact_plane_refinement_detects_intersection_extrema_missed_by_samples() -> None:
    heights = np.zeros((9, 9), dtype=np.float32)
    bounds = PatchBounds(first_row=2, first_column=2, row_count=4, column_count=4)
    mesh = build_conforming_mesh(bounds, heights, 16.0, 16.0, 2.0)
    changed = mesh.base_y.copy()
    changed[0] = np.float32(0.002)
    modified = replace(mesh, base_y=changed)

    report = verify_accepted_plane_refinement(modified, heights, 2.0, fail_closed=False)

    assert report["maximumAcceptedPlaneDeviationM"] > 0.001
    assert not report["passes"]
    assert report["maximumDeviationLocation"] is not None


def test_patch_terrain_resource_limits_accept_boundary_and_reject_overflow() -> None:
    assert validate_terrain_mesh_resources(150_000, 250_000, 8 * 1024 * 1024)["passes"]
    with pytest.raises(RoadSurfacePatchError, match="resource limits"):
        validate_terrain_mesh_resources(150_001, 250_000, 8 * 1024 * 1024)
    with pytest.raises(RoadSurfacePatchError, match="resource limits"):
        validate_terrain_mesh_resources(150_000, 250_001, 8 * 1024 * 1024)
    with pytest.raises(RoadSurfacePatchError, match="resource limits"):
        validate_terrain_mesh_resources(150_000, 250_000, 8 * 1024 * 1024 + 1)


def test_composite_surface_sampling_uses_patch_interior_and_accepted_grid_outside() -> None:
    heights = np.zeros((21, 21), dtype=np.float32)
    inputs = SimpleNamespace(
        baseline=heights.copy(),
        columns=21,
        rows=21,
        spacing_m=2.0,
        width_m=40.0,
        depth_m=40.0,
        road_payload={"features": []},
        buildings={"buildings": []},
    )
    bounds = PatchBounds(first_row=7, first_column=7, row_count=6, column_count=6)
    mesh = build_conforming_mesh(bounds, heights, 40.0, 40.0, 2.0)
    candidate = mesh.base_y.astype("<f4").copy()
    local_vertex = int(np.argmin(np.sum((mesh.vertices_xz - np.asarray([0.0, 0.0])) ** 2, axis=1)))
    candidate[local_vertex] = np.float32(0.25)
    surface = CompositeSurface(mesh, inputs, heights.copy(), candidate)

    interior_height, interior_owner = surface.sample(*mesh.vertices_xz[local_vertex])
    outside_height, outside_owner = surface.sample(-19.0, -19.0)
    many_heights, owners = surface.sample_many(np.asarray([0.0, -19.0]), np.asarray([0.0, -19.0]))

    assert interior_owner is not None
    assert interior_height == pytest.approx(float(candidate[local_vertex]))
    assert outside_height == 0.0 and outside_owner is None
    assert many_heights[1] == 0.0 and owners[1] == -1


def test_interior_fast_sampler_and_collar_fallback_return_containing_faces() -> None:
    heights = np.zeros((21, 21), dtype=np.float32)
    inputs = SimpleNamespace(
        baseline=heights,
        columns=21,
        rows=21,
        spacing_m=2.0,
        width_m=40.0,
        depth_m=40.0,
    )
    bounds = PatchBounds(first_row=7, first_column=7, row_count=6, column_count=6)
    mesh = build_conforming_mesh(bounds, heights, 40.0, 40.0, 2.0)
    candidate = np.linspace(-0.1, 0.1, len(mesh.vertices_xz), dtype="<f4")
    surface = CompositeSurface(mesh, inputs, heights, candidate)
    rng = np.random.default_rng(481)
    points_xz = []
    for row in range(bounds.first_row, bounds.last_row):
        for column in range(bounds.first_column, bounds.last_column):
            for half in (0, 1):
                triangle_ids = mesh.cell_half_triangles[(row, column, half)]
                triangle_id = triangle_ids[len(triangle_ids) // 2]
                triangle = mesh.triangles[triangle_id].astype(np.int64)
                weights = rng.dirichlet(np.ones(3))
                points_xz.append(weights @ mesh.vertices_xz[triangle])

    for x, z in points_xz:
        triangle_id, weights = _patch_triangle_weights(mesh, inputs, float(x), float(z))
        reconstructed = sum(mesh.vertices_xz[index] * weight for index, weight in weights.items())
        assert reconstructed == pytest.approx((x, z), abs=1e-7)
        assert min(weights.values()) >= -1e-8
        sampled, sampled_owner = surface.sample(float(x), float(z))
        assert sampled_owner is not None
        assert sampled == pytest.approx(
            sum(float(candidate[index]) * weight for index, weight in weights.items()),
            abs=1e-7,
        )


def test_local_lateral_metric_detects_a_hidden_interior_slope_spike() -> None:
    values = np.asarray([0.0, 0.0, 0.0201, 0.0], dtype=np.float64)

    metrics = _section_lateral_metrics(values, sample_spacing_m=0.25, total_width_m=0.75)

    assert metrics["endpointCrossfallPercent"] == 0.0
    assert metrics["fullWidthSpanM"] == pytest.approx(0.0201)
    assert metrics["maximumLocalLateralSlopeMPerM"] == pytest.approx(0.0804)
    assert metrics["maximumLocalLateralSlopeMPerM"] * 100 > 5.0


def test_composite_terrain_gate_checks_fixed_boundary_and_global_surface_metrics() -> None:
    heights = np.zeros((21, 21), dtype=np.float32)
    inputs = SimpleNamespace(
        baseline=heights.copy(),
        columns=21,
        rows=21,
        spacing_m=2.0,
        width_m=40.0,
        depth_m=40.0,
    )
    bounds = PatchBounds(first_row=7, first_column=7, row_count=6, column_count=6)
    mesh = build_conforming_mesh(bounds, heights, 40.0, 40.0, 2.0)
    influence = LineString(((0.0, 0.0), (4.0, 0.0))).buffer(5.0)
    surface = CompositeSurface(mesh, inputs, heights.copy(), mesh.base_y.astype("<f4").copy())

    report = verify_composite_terrain(surface, influence)

    assert report["passes"]
    assert report["perimeterXYZFloat32BytesMatch"]
    assert report["outsideInfluenceAcceptedPlanePasses"]
    assert report["maximumAbsoluteChangeFromSourceM"] == 0.0
    assert report["maximumPositiveAddedGradientMPerM"] < 1.0


def test_earthwork_overlay_uses_source_half_cell_ownership_for_exact_extrema() -> None:
    heights = _plane(21, 21)
    inputs = SimpleNamespace(
        baseline=heights.copy(),
        spacing_m=2.0,
        width_m=40.0,
        depth_m=40.0,
    )
    mesh = build_conforming_mesh(PatchBounds(6, 6, 6, 6), heights, 40.0, 40.0, 2.0)
    candidate = (mesh.base_y.astype(np.float64) + 0.75).astype("<f4")
    surface = CompositeSurface(mesh, inputs, heights.copy(), candidate)

    report = composite_earthwork_overlay_report(surface)

    assert report["passes"]
    assert report["overlayFaceCount"] == len(mesh.triangles)
    assert report["sourceTriangleOwnershipPasses"]
    assert report["maximumAbsoluteEarthworkChangeFromSourceM"] == pytest.approx(0.75)
    assert report["maximumFillFromSourceM"] == pytest.approx(0.75)
    assert report["maximumCutFromSourceM"] == pytest.approx(0.75)


def test_complete_composite_building_gate_recomputes_all_footprints(monkeypatch) -> None:
    heights = np.zeros((21, 21), dtype=np.float32)
    required_ids = {
        "osm:way:208684847",
        "osm:way:196536218",
        "osm:way:196536220",
        "osm:way:196536221",
        "osm:way:196536227",
        "osm:way:196536217",
        "osm:way:194444458",
        "osm:way:207341667",
        "osm:way:207341692",
        "osm:way:207341702",
        "osm:way:207341535",
        "osm:way:207341753",
    }
    building_ids = sorted(required_ids) + [
        f"synthetic:{index}" for index in range(3613 - len(required_ids))
    ]
    footprint = {
        "exteriorXZ": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9], [0.1, 0.1]],
        "interiorRingsXZ": [],
    }
    features = [
        {"id": building_id, "geometry": {"polygons": [footprint]}} for building_id in building_ids
    ]
    inputs = SimpleNamespace(
        baseline=heights.copy(),
        columns=21,
        rows=21,
        spacing_m=2.0,
        width_m=40.0,
        depth_m=40.0,
        buildings={"buildings": features},
    )
    mesh = build_conforming_mesh(PatchBounds(6, 6, 6, 6), heights, 40.0, 40.0, 2.0)
    surface = CompositeSurface(mesh, inputs, heights.copy(), mesh.base_y.astype("<f4").copy())
    monkeypatch.setattr(
        "torquay_pipeline.road_surface_patch._maximum_under_building",
        lambda _feature, _baseline, _inputs: 0.0,
    )

    report = composite_building_base_report(surface)

    assert report["passes"]
    assert report["buildingCount"] == 3613
    assert report["completeFootprintsRecomputed"]
    assert report["baseDisplacementP95AbsoluteM"] == 0.0
    assert report["baseDisplacementMaximumAbsoluteM"] == 0.0
    assert report["nearbyBuilding208684847"]["buildingId"] == "osm:way:208684847"
    assert len(report["registeredRiskFootingSections"]) == 12


@pytest.mark.parametrize("flat_height", [-20.0, 8.0, 20.0])
def test_composite_walk_clearance_uses_displayed_surface_at_any_absolute_elevation(
    flat_height: float,
) -> None:
    heights = np.full((21, 21), flat_height, dtype=np.float32)
    inputs = SimpleNamespace(
        baseline=heights.copy(),
        columns=21,
        rows=21,
        spacing_m=2.0,
        width_m=40.0,
        depth_m=40.0,
    )
    mesh = build_conforming_mesh(PatchBounds(7, 7, 6, 6), heights, 40.0, 40.0, 2.0)
    surface = CompositeSurface(mesh, inputs, heights.copy(), mesh.base_y.astype("<f4").copy())
    roads = {
        "passes": True,
        "groups": {
            "vehicular": {"verticesXZ": [[0.0, 0.0]]},
            "cycleway": {"verticesXZ": []},
            "path": {"verticesXZ": []},
        },
    }

    report = composite_walk_clearance_report(surface, roads)

    assert report["passes"]
    assert not report["runtimeBrowserVerified"]
    assert report["roadClearanceCoverageAvailable"]
    assert report["fineCoarseSeamMidpointSampleCount"] == len(mesh.boundary_edges)
    assert report["displaySurfaceOwnerTriangleSampleCount"] > 0
    assert report["groundClearanceRangeM"] == pytest.approx([1.7, 1.7], abs=1e-12)
    assert report["pavementRelativeClearanceRangeM"] == pytest.approx([1.65, 1.65], abs=1e-12)


def test_composite_walk_clearance_fails_closed_without_successful_road_reclip() -> None:
    heights = np.zeros((21, 21), dtype=np.float32)
    inputs = SimpleNamespace(
        baseline=heights.copy(),
        columns=21,
        rows=21,
        spacing_m=2.0,
        width_m=40.0,
        depth_m=40.0,
    )
    mesh = build_conforming_mesh(PatchBounds(7, 7, 6, 6), heights, 40.0, 40.0, 2.0)
    surface = CompositeSurface(mesh, inputs, heights.copy(), mesh.base_y.astype("<f4").copy())
    failed_reclip = {
        "passes": False,
        "groups": {name: {"verticesXZ": []} for name in ("vehicular", "cycleway", "path")},
    }

    report = composite_walk_clearance_report(surface, failed_reclip)

    assert not report["passes"]
    assert not report["roadClearanceCoverageAvailable"]
    assert report["reclippedRoadPathVertexCount"] == 0
    assert "reclip failed" in report["roadClearanceCoverageUnavailableReason"]


def test_road_reclip_preserves_area_and_records_exact_patch_face_ownership() -> None:
    heights = np.zeros((21, 21), dtype=np.float32)
    # Coarse cell (10, 10), half 0 spans local X/Z [0,0] to [2,2].
    road_vertices = [[0.1, 0.1], [0.1, 1.7], [1.7, 0.1]]
    road_batch = {
        "verticesXZ": road_vertices,
        "indices": [[0, 1, 2]],
        "terrainTriangles": [[10, 10, 0]],
    }
    empty_batch = {"verticesXZ": [], "indices": [], "terrainTriangles": []}
    inputs = SimpleNamespace(
        baseline=heights.copy(),
        columns=21,
        rows=21,
        spacing_m=2.0,
        width_m=40.0,
        depth_m=40.0,
        road_payload={
            "surfaceBatches": {
                "vehicular": road_batch,
                "cycleway": empty_batch,
                "path": empty_batch,
            }
        },
    )
    bounds = PatchBounds(first_row=6, first_column=6, row_count=6, column_count=6)
    mesh = build_conforming_mesh(bounds, heights, 40.0, 40.0, 2.0)
    surface = CompositeSurface(mesh, inputs, heights.copy(), mesh.base_y.astype("<f4").copy())

    result = reclip_affected_road_batches(surface)
    batch = result["groups"]["vehicular"]

    assert result["passes"]
    assert batch["affectedSourceFaceCount"] == 1
    assert batch["replacementFaceCount"] > 1
    assert batch["areaDifferenceM2"] <= 1e-8
    assert batch["float32FootprintCoverageErrorM2"] <= 2e-5
    assert abs(batch["float32HorizontalAreaDriftM2"]) <= 2e-5
    assert batch["maximumRoadDrapeErrorM"] <= 0.001
    assert all(0 <= owner < len(mesh.triangles) for owner in batch["terrainTriangles"])
    assert batch["maximumOwnerTriangleBarycentricViolation"] <= 1e-6


def test_road_reclip_handles_both_source_half_orientations_and_float32_ownership() -> None:
    heights = np.zeros((21, 21), dtype=np.float32)
    road_batch = {
        "verticesXZ": [
            [0.1, 0.1],
            [0.1, 1.7],
            [1.7, 0.1],
            [1.8, 1.8],
            [1.8, 0.3],
            [0.3, 1.8],
        ],
        "indices": [[0, 1, 2], [5, 4, 3]],
        "terrainTriangles": [[10, 10, 0], [10, 10, 1]],
    }
    empty_batch = {"verticesXZ": [], "indices": [], "terrainTriangles": []}
    inputs = SimpleNamespace(
        baseline=heights.copy(),
        columns=21,
        rows=21,
        spacing_m=2.0,
        width_m=40.0,
        depth_m=40.0,
        road_payload={
            "surfaceBatches": {
                "vehicular": road_batch,
                "cycleway": empty_batch,
                "path": empty_batch,
            }
        },
    )
    mesh = build_conforming_mesh(PatchBounds(6, 6, 6, 6), heights, 40.0, 40.0, 2.0)
    surface = CompositeSurface(mesh, inputs, heights.copy(), mesh.base_y.astype("<f4").copy())

    result = reclip_affected_road_batches(surface)
    batch = result["groups"]["vehicular"]

    assert result["passes"]
    assert batch["affectedSourceFaceCount"] == 2
    assert batch["areaDifferenceM2"] <= 1e-8
    assert batch["float32FootprintCoverageErrorM2"] <= 2e-5
    assert abs(batch["float32HorizontalAreaDriftM2"]) <= 2e-5
    assert batch["maximumOwnerTriangleBarycentricViolation"] <= 1e-6
    assert all(owner >= 0 for owner in batch["terrainTriangles"])


def test_negative_actual_scale_road_shared_edge_quantization_keeps_one_micro_owner_gate() -> None:
    heights = np.zeros((201, 201), dtype=np.float32)
    mesh = build_conforming_mesh(PatchBounds(30, 46, 6, 6), heights, 400.0, 400.0, 2.0)
    edge_faces, vertex_faces = _triangle_vertex_adjacency(mesh)
    selected = None
    for edge, face_ids in sorted(edge_faces.items()):
        if len(face_ids) != 2:
            continue
        first, second = mesh.vertices_xz[list(edge)]
        midpoint = (first + second) * 0.5
        if not (-111 <= midpoint[0] <= -100 and -142 <= midpoint[1] <= -130):
            continue
        if abs(first[0] - second[0]) < 1e-9 or abs(first[1] - second[1]) < 1e-9:
            continue
        for index in range(1, 1000):
            fraction = index / 1000
            point = first * (1 - fraction) + second * fraction
            exact = (float(point[0]), float(point[1]))
            shared = _shared_float32_owners(mesh, face_ids[0], exact, edge_faces, vertex_faces)
            direct = (float(np.float32(exact[0])), float(np.float32(exact[1])))
            direct_violation = max(
                _barycentric_violation(
                    _triangle_barycentric_weights(
                        mesh.vertices_xz[mesh.triangles[owner].astype(np.int64)], *direct
                    )
                )
                for owner in shared
            )
            if direct_violation > 1e-6:
                selected = (exact, shared, direct_violation)
                break
        if selected is not None:
            break
    assert selected is not None, "fixture must expose Float32 loss of exact shared-edge ownership"
    exact, shared, direct_violation = selected

    repaired, repaired_violation = _quantize_road_point_for_owners(mesh, exact, shared)

    assert exact[0] < 0 and exact[1] < 0
    assert direct_violation > 1e-6
    assert repaired_violation <= 1e-6
    assert repaired != (float(np.float32(exact[0])), float(np.float32(exact[1])))
    assert all(
        _barycentric_violation(
            _triangle_barycentric_weights(
                mesh.vertices_xz[mesh.triangles[owner].astype(np.int64)], *repaired
            )
        )
        <= 1e-6
        for owner in shared
    )


def test_shared_owner_quantization_failure_reports_exact_point_and_triangles() -> None:
    heights = np.zeros((21, 21), dtype=np.float32)
    mesh = build_conforming_mesh(PatchBounds(6, 6, 6, 6), heights, 40.0, 40.0, 2.0)
    distant_owners = (0, len(mesh.triangles) - 1)

    with pytest.raises(RoadSurfacePatchError) as raised:
        _quantize_road_point_for_owners(mesh, (0.1234567, 0.7654321), distant_owners)

    message = str(raised.value)
    assert "pointXZ=[0.1234567, 0.7654321]" in message
    assert "ownerTriangleIds=[0," in message
    assert "triangleVertexIds" in message
    assert "searchUlpRadius=32" in message


def test_negative_actual_scale_road_reclip_reports_post_float32_coverage() -> None:
    heights = np.zeros((201, 201), dtype=np.float32)
    road_batch = {
        "verticesXZ": [[-103.99, -135.99], [-103.9, -134.1], [-102.1, -135.9]],
        "indices": [[0, 1, 2]],
        "terrainTriangles": [[32, 48, 0]],
    }
    empty_batch = {"verticesXZ": [], "indices": [], "terrainTriangles": []}
    inputs = SimpleNamespace(
        baseline=heights.copy(),
        columns=201,
        rows=201,
        spacing_m=2.0,
        width_m=400.0,
        depth_m=400.0,
        road_payload={
            "surfaceBatches": {
                "vehicular": road_batch,
                "cycleway": empty_batch,
                "path": empty_batch,
            }
        },
    )
    mesh = build_conforming_mesh(PatchBounds(30, 46, 6, 6), heights, 400.0, 400.0, 2.0)
    surface = CompositeSurface(mesh, inputs, heights.copy(), mesh.base_y.astype("<f4").copy())

    result = reclip_affected_road_batches(surface)

    assert result["passes"]
    batch = result["groups"]["vehicular"]
    assert batch["maximumOwnerTriangleBarycentricViolation"] <= 1e-6
    assert batch["float32FootprintCoverageErrorM2"] <= 2e-5
    assert abs(batch["float32HorizontalAreaDriftM2"]) <= 2e-5


def test_candidate_asset_assembly_is_deterministic_and_has_exact_owned_files(
    tmp_path, monkeypatch
) -> None:
    heights = np.zeros((21, 21), dtype=np.float32)
    road_batch = {
        "verticesXZ": [[0.1, 0.1], [0.1, 1.7], [1.7, 0.1]],
        "indices": [[0, 1, 2]],
        "terrainTriangles": [[10, 10, 0]],
    }
    empty_batch = {"verticesXZ": [], "indices": [], "terrainTriangles": []}
    inputs = SimpleNamespace(
        baseline=heights.copy(),
        columns=21,
        rows=21,
        spacing_m=2.0,
        width_m=40.0,
        depth_m=40.0,
        origin_e_m=123.0,
        origin_n_m=456.0,
        origin_y_m=7.0,
        release_id="616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a",
        manifest_sha256="1" * 64,
        road_manifest_sha256="2" * 64,
        road_payload_sha256="3" * 64,
        source_hashes={
            "ready.json": {"readySha256": "4" * 64},
            "inventory.json": {"sha256": "5" * 64},
            "heightfield.f32": {"sha256": "6" * 64},
            "buildings/buildings.json": {"sha256": "7" * 64},
        },
        manifest={"heightfield": {"sha256": "6" * 64}},
        road_payload={
            "worldId": "torquay-poc-001",
            "sceneProfile": "current_2km",
            "surfaceBatches": {
                "vehicular": road_batch,
                "cycleway": empty_batch,
                "path": empty_batch,
            },
        },
    )
    mesh = build_conforming_mesh(PatchBounds(6, 6, 6, 6), heights, 40.0, 40.0, 2.0)
    candidate = mesh.base_y.astype("<f4").copy()
    surface = CompositeSurface(mesh, inputs, heights.copy(), candidate)
    clipped = reclip_affected_road_batches(surface)
    candidate_hash = hashlib.sha256(candidate.tobytes(order="C")).hexdigest()
    local_keys = (
        "wayId",
        "partIndex",
        "stationStartM",
        "stationEndM",
        "stationCount",
        "maximumStationSpacingM",
        "lateralSampleSpacingM",
        "maximumLocalLateralSlopePercent",
        "maximumEndpointSpanM",
        "maximumAbsoluteCenterlineDeviationM",
        "maximumAbsoluteSignedGradeChangePercentagePoints",
        "passes",
    )
    report = {
        "passes": True,
        "candidateFloat32Sha256": candidate_hash,
        "gateNames": list(PATCH_OFFLINE_GATE_NAMES),
        "inputBindings": {"passes": True},
        "solverWitness": {"passes": True},
        "float32FinalValidation": {"passes": True},
        "topology": {"passes": True},
        "sourceTriangleOwnership": {"passes": True},
        "earthworkOverlay": {
            "passes": True,
            "maximumAbsoluteEarthworkChangeFromSourceM": 0.0,
            "maximumFillFromSourceM": 0.0,
            "maximumCutFromSourceM": 0.0,
        },
        "acceptedPlaneRefinement": {"passes": True},
        "roadPathReclip": {"passes": True},
        "walkClearance": {"passes": True},
        "localCorridorLongitudinal": {
            "teignmouthLocal": dict.fromkeys(local_keys, 0.0) | {"passes": True},
            "passes": True,
        },
        "compositeTerrain": {
            "maximumAbsoluteChangeFromSourceM": 0.0,
            "maximumFillFromSourceM": 0.0,
            "maximumCutFromSourceM": 0.0,
            "maximumPositiveAddedGradientMPerM": 0.0,
            "maximumOutsideInfluenceAcceptedPlaneDeviationM": 0.0,
            "passes": True,
        },
        "completeBuildingFootprints": {
            "buildingCount": 3613,
            "completeFootprintsRecomputed": True,
            "baseDisplacementP95AbsoluteM": 0.0,
            "baseDisplacementMaximumAbsoluteM": 0.0,
            "registeredBuildingChangesM": {"osm:way:208684847": 0.0},
            "localReviewOver0_50m": [],
            "passes": True,
        },
    }
    report["roadPathReclip"] = clipped

    first, second, deterministic_report = assemble_deterministic_candidate_assets(
        surface, clipped, report
    )

    assert set(first) == set(PATCH_OUTPUT_FILES)
    assert first is not second
    assert first == second
    assert deterministic_report["passes"]
    assert deterministic_report["firstOutputHashes"] == deterministic_report["secondOutputHashes"]
    manifest = json.loads(first["manifest.json"])
    qa = json.loads(first["qa.json"])
    assert manifest["packageType"] == PATCH_PACKAGE_TYPE
    assert manifest["algorithmVersion"] == PATCH_ALGORITHM_VERSION
    assert (
        manifest["assets"]["terrain-vertices.f32"]["sha256"]
        == hashlib.sha256(first["terrain-vertices.f32"]).hexdigest()
    )
    assert qa["candidateFloat32Sha256"] == candidate_hash
    assert len(qa["serializedGeometryWitnessSha256"]) == 64
    assert sum(len(value) for value in first.values()) <= 8 * 1024 * 1024
    asset_report = validate_candidate_patch_assets(first, surface, candidate_hash, clipped)
    assert asset_report["passes"]
    assert asset_report["terrainTriangleCount"] == len(mesh.triangles)
    assert asset_report["roadOwnerCount"] == len(clipped["groups"]["vehicular"]["indices"])

    non_deterministic = dict(second)
    second_qa = json.loads(second["qa.json"])
    second_qa["assemblyMarker"] = "independent-but-different"
    non_deterministic["qa.json"] = serialize_offline_report(second_qa)
    second_manifest = json.loads(second["manifest.json"])
    second_manifest["assets"]["qa.json"].update(
        {
            "byteLength": len(non_deterministic["qa.json"]),
            "sha256": hashlib.sha256(non_deterministic["qa.json"]).hexdigest(),
        }
    )
    non_deterministic["manifest.json"] = serialize_offline_report(second_manifest)
    assert validate_candidate_patch_assets(non_deterministic, surface, candidate_hash, clipped)[
        "passes"
    ]

    for asset_name in PATCH_OUTPUT_FILES - {"manifest.json"}:
        tampered_manifest = json.loads(first["manifest.json"])
        tampered_manifest["assets"][asset_name]["elementCount"] += 1
        tampered = dict(first)
        tampered["manifest.json"] = serialize_offline_report(tampered_manifest)
        tamper_report = validate_candidate_patch_assets(tampered, surface, candidate_hash, clipped)
        assert not tamper_report["passes"]
        assert any(
            f"{asset_name} element-count descriptor mismatch" in failure
            for failure in tamper_report["failures"]
        )

    tampered_geometry = dict(first)
    terrain_vertices = np.frombuffer(first["terrain-vertices.f32"], dtype="<f4").copy()
    terrain_vertices[1] += np.float32(1.0)
    tampered_geometry["terrain-vertices.f32"] = terrain_vertices.astype("<f4").tobytes()
    tampered_manifest = json.loads(first["manifest.json"])
    tampered_manifest["assets"]["terrain-vertices.f32"]["sha256"] = hashlib.sha256(
        tampered_geometry["terrain-vertices.f32"]
    ).hexdigest()
    tampered_qa = json.loads(tampered_geometry["qa.json"])
    tampered_qa["serializedGeometryWitnessSha256"] = (
        road_surface_patch_module.serialized_geometry_witness_sha256(
            tampered_geometry, candidate_hash
        )
    )
    tampered_geometry["qa.json"] = serialize_offline_report(tampered_qa)
    tampered_manifest["assets"]["qa.json"].update(
        {
            "byteLength": len(tampered_geometry["qa.json"]),
            "sha256": hashlib.sha256(tampered_geometry["qa.json"]).hexdigest(),
        }
    )
    tampered_geometry["manifest.json"] = serialize_offline_report(tampered_manifest)
    tampered_witness_report = validate_candidate_patch_assets(
        tampered_geometry, surface, candidate_hash, clipped
    )
    assert not tampered_witness_report["passes"]
    assert any(
        "serialized terrain Y stream does not match external candidate digest" in failure
        for failure in tampered_witness_report["failures"]
    )
    assert any(
        "terrain-vertices.f32 differs from the exact validated surface" in failure
        for failure in tampered_witness_report["failures"]
    )

    for asset_name in (
        "terrain-indices.u32",
        "road-vertices.f32",
        "road-indices.u32",
        "road-terrain-triangles.u32",
    ):
        tampered = dict(first)
        payload = bytearray(tampered[asset_name])
        payload[0] ^= 1
        tampered[asset_name] = bytes(payload)
        qa_document = json.loads(tampered["qa.json"])
        qa_document["serializedGeometryWitnessSha256"] = (
            road_surface_patch_module.serialized_geometry_witness_sha256(tampered, candidate_hash)
        )
        tampered["qa.json"] = serialize_offline_report(qa_document)
        manifest_document = json.loads(tampered["manifest.json"])
        for changed_name in (asset_name, "qa.json"):
            manifest_document["assets"][changed_name].update(
                {
                    "byteLength": len(tampered[changed_name]),
                    "sha256": hashlib.sha256(tampered[changed_name]).hexdigest(),
                }
            )
        tampered["manifest.json"] = serialize_offline_report(manifest_document)
        validation = validate_candidate_patch_assets(tampered, surface, candidate_hash, clipped)
        assert not validation["passes"]
        assert any(
            f"serialized {asset_name} differs from the exact validated surface" in failure
            for failure in validation["failures"]
        )

    (tmp_path / "public/worlds").mkdir(parents=True)
    evidence_root = tmp_path / "docs/milestones/artifacts/Road-surface-treatment"
    evidence_root.mkdir(parents=True)
    monkeypatch.setattr(
        road_surface_patch_module,
        "_protected_hash_snapshot",
        lambda *_args: {"protected:fixture": "f" * 64},
    )
    with pytest.raises(RoadSurfacePatchError, match="not byte-identical"):
        publish_candidate_patch_assets(
            tmp_path,
            surface,
            report,
            first,
            non_deterministic,
            (evidence_root / "build-89.json", evidence_root / "build-90.json"),
        )
    assert not (tmp_path / "public/worlds/torquay-road-surface-teignmouth-candidate").exists()
    assert not (evidence_root / "build-89.json").exists()
    assert not (evidence_root / "build-90.json").exists()
    published = publish_candidate_patch_assets(
        tmp_path,
        surface,
        report,
        first,
        second,
        (evidence_root / "build-91.json", evidence_root / "build-92.json"),
    )
    output = tmp_path / "public/worlds/torquay-road-surface-teignmouth-candidate"
    assert published["passes"]
    assert published["deterministicAssets"]
    assert set(path.name for path in output.iterdir()) == set(PATCH_OUTPUT_FILES)
    assert {
        name: hashlib.sha256((output / name).read_bytes()).hexdigest()
        for name in PATCH_OUTPUT_FILES
    } == published["outputHashes"]
    for record in published["buildRecords"]:
        build_record = json.loads((tmp_path / record).read_bytes())
        assert build_record["offlineGatePasses"] is True
        assert build_record["candidateFloat32Sha256"] == candidate_hash
    build_records = [
        json.loads((tmp_path / record).read_bytes()) for record in published["buildRecords"]
    ]
    assert [record["independentAssembly"] for record in build_records] == [1, 2]
    assert build_records[0]["outputHashes"] == build_records[1]["outputHashes"]

    corrupted = dict(first)
    corrupted["terrain-indices.u32"] += b"\x00\x00\x00\x00"
    rejected = validate_candidate_patch_assets(corrupted, surface, candidate_hash, clipped)
    assert not rejected["passes"]
    assert any("byte-length descriptor mismatch" in failure for failure in rejected["failures"])


def test_candidate_publish_rejects_unsafe_output_aliases_before_writes(tmp_path) -> None:
    (tmp_path / "public/worlds").mkdir(parents=True)
    evidence_root = tmp_path / "docs/milestones/artifacts/Road-surface-treatment"
    evidence_root.mkdir(parents=True)
    records = (evidence_root / "build-31.json", evidence_root / "build-32.json")
    candidate = tmp_path / "public/worlds/torquay-road-surface-teignmouth-candidate"

    for requested in (
        tmp_path / "public/worlds",
        candidate / "nested",
        tmp_path / "public/worlds/../worlds/torquay-road-surface-teignmouth-candidate",
    ):
        with pytest.raises(RoadSurfacePatchError):
            preflight_candidate_publish_paths(tmp_path, requested, records)
    assert not candidate.exists()
    assert not any(path.exists() for path in records)


def test_candidate_publish_rejects_reparse_output_ancestor_before_writes(
    tmp_path, monkeypatch
) -> None:
    (tmp_path / "public/worlds").mkdir(parents=True)
    evidence_root = tmp_path / "docs/milestones/artifacts/Road-surface-treatment"
    evidence_root.mkdir(parents=True)
    candidate = tmp_path / "public/worlds/torquay-road-surface-teignmouth-candidate"
    records = (evidence_root / "build-41.json", evidence_root / "build-42.json")
    is_reparse = road_surface_patch_module._road_surface._is_reparse_point
    worlds = tmp_path / "public/worlds"

    def mark_worlds_as_reparse(path: Path) -> bool:
        return path == worlds or is_reparse(path)

    monkeypatch.setattr(
        road_surface_patch_module._road_surface,
        "_is_reparse_point",
        mark_worlds_as_reparse,
    )
    with pytest.raises(RoadSurfaceError):
        preflight_candidate_publish_paths(tmp_path, candidate, records)
    assert not candidate.exists()
    assert not any(path.exists() for path in records)


@pytest.mark.parametrize("existing_entry", ["owned", "unowned"])
def test_candidate_publish_rejects_existing_output_without_modifying_bytes(
    tmp_path, existing_entry
) -> None:
    candidate = tmp_path / "public/worlds/torquay-road-surface-teignmouth-candidate"
    candidate.mkdir(parents=True)
    filename = next(iter(PATCH_OUTPUT_FILES)) if existing_entry == "owned" else "user.bin"
    existing = candidate / filename
    existing.write_bytes(b"preexisting candidate bytes")
    evidence_root = tmp_path / "docs/milestones/artifacts/Road-surface-treatment"
    evidence_root.mkdir(parents=True)
    records = (evidence_root / "build-51.json", evidence_root / "build-52.json")
    before = hashlib.sha256(existing.read_bytes()).hexdigest()

    with pytest.raises(RoadSurfaceError):
        preflight_candidate_publish_paths(tmp_path, candidate, records)

    assert hashlib.sha256(existing.read_bytes()).hexdigest() == before
    assert not any(path.exists() for path in records)


def test_candidate_publish_rejects_record_collision_and_duplicate_ids_before_writes(
    tmp_path,
) -> None:
    (tmp_path / "public/worlds").mkdir(parents=True)
    evidence_root = tmp_path / "docs/milestones/artifacts/Road-surface-treatment"
    evidence_root.mkdir(parents=True)
    candidate = tmp_path / "public/worlds/torquay-road-surface-teignmouth-candidate"
    collision = evidence_root / "build-61.json"
    collision.write_bytes(b"existing record")
    records = (collision, evidence_root / "build-62.json")

    with pytest.raises(RoadSurfaceError):
        preflight_candidate_publish_paths(tmp_path, candidate, records)
    with pytest.raises(RoadSurfacePatchError, match="distinct"):
        preflight_candidate_publish_paths(tmp_path, candidate, (records[1], records[1]))

    assert collision.read_bytes() == b"existing record"
    assert not (evidence_root / "build-62.json").exists()
    assert not candidate.exists()


def test_candidate_publish_gate_failure_is_no_write(tmp_path) -> None:
    candidate = tmp_path / "public/worlds/torquay-road-surface-teignmouth-candidate"
    evidence_root = tmp_path / "docs/milestones/artifacts/Road-surface-treatment"
    records = (evidence_root / "build-71.json", evidence_root / "build-72.json")
    with pytest.raises(RoadSurfacePatchError, match="every aggregate offline gate"):
        publish_candidate_patch_assets(
            tmp_path,
            None,
            {"passes": False, "gateNames": list(PATCH_OFFLINE_GATE_NAMES)},
            {},
            {},
            records,
        )
    assert not candidate.exists()
    assert not evidence_root.exists()


def test_protected_snapshot_uses_validated_ready_pointer_hash_field(tmp_path, monkeypatch) -> None:
    ready_path = tmp_path / "public/worlds/torquay-poc-001-2km/ready.json"
    ready_path.parent.mkdir(parents=True)
    ready_bytes = b'{"releaseId":"pinned"}\n'
    ready_path.write_bytes(ready_bytes)
    ready_hash = hashlib.sha256(ready_bytes).hexdigest()
    inputs = SimpleNamespace(
        source_hashes={
            "ready.json": {
                "path": ready_path.relative_to(tmp_path).as_posix(),
                "readySha256": ready_hash,
                "inventorySha256": "1" * 64,
            }
        }
    )
    monkeypatch.setattr(road_surface_patch_module, "ACCEPTED_PREVIEW_HASHES", {})
    monkeypatch.setattr(
        road_surface_patch_module._road_surface,
        "_protected_execution_inputs",
        lambda _root: [],
    )

    snapshot = road_surface_patch_module._protected_hash_snapshot(tmp_path, inputs)

    assert snapshot["release:ready.json"] == ready_hash


def test_offline_report_serializer_normalizes_numpy_in_aggregate_structure() -> None:
    aggregate = {
        "passes": True,
        "gateNames": list(PATCH_OFFLINE_GATE_NAMES),
        "candidateFloat32Sha256": "a" * 64,
        **{
            name: {
                "passes": True,
                "diagnostics": {
                    "count": np.int64(index + 1),
                    "values": np.asarray([index, index + 0.5], dtype=np.float64),
                },
            }
            for index, name in enumerate(PATCH_OFFLINE_GATE_NAMES)
        },
    }

    serialized = serialize_offline_report(aggregate)
    decoded = json.loads(serialized)

    assert serialize_offline_report(aggregate) == serialized
    assert decoded["gateNames"] == list(PATCH_OFFLINE_GATE_NAMES)
    assert decoded["solverWitness"]["diagnostics"] == {"count": 2, "values": [1.0, 1.5]}
    assert isinstance(decoded["solverWitness"]["diagnostics"]["count"], int)


def test_offline_gate_aggregates_failures_without_creating_candidate_output(
    monkeypatch, tmp_path
) -> None:
    heights = np.zeros((21, 21), dtype=np.float32)
    mesh = build_conforming_mesh(PatchBounds(6, 6, 6, 6), heights, 40.0, 40.0, 2.0)
    inputs = SimpleNamespace(
        release_id=road_surface_patch_module.CURRENT_RELEASE_ID,
        source_hashes={"heightfield.f32": {"sha256": "6" * 64}},
        manifest={
            "heightfield": {"sha256": "6" * 64},
            "id": "torquay-poc-001",
        },
        road_payload={"worldId": "torquay-poc-001", "sceneProfile": "current_2km"},
        baseline=heights.copy(),
        columns=21,
        rows=21,
        spacing_m=2.0,
        width_m=40.0,
        depth_m=40.0,
    )
    candidate = mesh.base_y.astype("<f4").copy()
    surface = CompositeSurface(mesh, inputs, heights.copy(), candidate)
    candidate_hash = hashlib.sha256(candidate.tobytes(order="C")).hexdigest()

    monkeypatch.setattr(
        road_surface_patch_module,
        "_validate_quantized_phase_one",
        lambda *args, **kwargs: {"passes": True},
    )
    monkeypatch.setattr(
        road_surface_patch_module,
        "patch_topology_report",
        lambda *args, **kwargs: {"passes": True},
    )
    monkeypatch.setattr(
        road_surface_patch_module,
        "patch_source_triangle_ownership_report",
        lambda *args, **kwargs: {
            "passes": True,
            "sourceHalfCellOwnershipViolationCount": 0,
        },
    )
    monkeypatch.setattr(
        road_surface_patch_module,
        "verify_accepted_plane_refinement",
        lambda *args, **kwargs: {"passes": True},
    )
    monkeypatch.setattr(
        road_surface_patch_module,
        "verify_composite_terrain",
        lambda *args, **kwargs: {"passes": False, "reason": "synthetic strict cap breach"},
    )
    monkeypatch.setattr(
        road_surface_patch_module,
        "composite_local_and_corridor_report",
        lambda *args, **kwargs: {"passes": True},
    )
    monkeypatch.setattr(
        road_surface_patch_module,
        "composite_building_base_report",
        lambda *args, **kwargs: {"passes": True},
    )
    monkeypatch.setattr(
        road_surface_patch_module,
        "reclip_affected_road_batches",
        lambda *args, **kwargs: {"passes": True, "groups": {}},
    )
    monkeypatch.setattr(
        road_surface_patch_module,
        "composite_walk_clearance_report",
        lambda *args, **kwargs: {"passes": True, "runtimeBrowserVerified": False},
    )

    def reject_write(*args, **kwargs):
        pytest.fail("offline validation must not write candidate outputs")

    monkeypatch.setattr(Path, "write_bytes", reject_write)
    monkeypatch.setattr(Path, "mkdir", reject_write)

    report = validate_offline_candidate(
        surface,
        Polygon([(-12.0, -12.0), (12.0, -12.0), (12.0, 12.0), (-12.0, 12.0)]),
        [],
        {
            "converged": True,
            "candidateFloat32Sha256": candidate_hash,
            "quantizedValidation": {"passes": True},
            "solverNumericalToleranceM": 2e-5,
        },
        road_surface_patch_module.ACCEPTED_PREVIEW_HASHES,
    )

    assert not report["passes"]
    assert not report["compositeTerrain"]["passes"]
    assert all(report[name]["passes"] for name in report["gateNames"] if name != "compositeTerrain")
    with pytest.raises(RoadSurfacePatchError, match="before all offline gates pass"):
        assemble_candidate_patch_assets(
            surface,
            {"passes": True, "groups": {}},
            report,
        )
    assert not list(tmp_path.iterdir())
