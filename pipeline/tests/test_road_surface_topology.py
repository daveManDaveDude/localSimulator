from __future__ import annotations

import math

import numpy as np
import pytest
from shapely.geometry import LineString, Polygon, box

from torquay_pipeline.road_surface_topology import (
    SourceOverlapIndex,
    TopologyError,
    affine_surface_overlay_extrema,
    alternate_internal_diagonals,
    build_constrained_mesh,
    graded_collar_constraints,
    localized_grid_constraints,
    localized_refinement_zone,
    mesh_face_polygon,
    road_aligned_constraints,
    source_overlap_provenance,
)


def _edge(mesh, first: tuple[float, float], second: tuple[float, float]) -> tuple[int, int]:
    keys = {tuple(point): index for index, point in enumerate(mesh.vertices_xz)}
    return tuple(sorted((keys[first], keys[second])))


def test_noded_constraint_arrangement_preserves_crossing_edges_and_is_deterministic() -> None:
    domain = box(-4.0, -2.0, 4.0, 2.0)
    constraints = [
        LineString([(-4.0, -1.0), (4.0, -1.0)]),
        LineString([(0.0, -2.0), (0.0, 2.0)]),
        LineString([(-4.0, 2.0), (4.0, -2.0)]),
    ]

    first = build_constrained_mesh(domain, constraints)
    second = build_constrained_mesh(domain, constraints)

    assert first.vertices_xz.astype("<f4").tobytes() == second.vertices_xz.astype("<f4").tobytes()
    assert first.triangles.tobytes() == second.triangles.tobytes()
    points = {tuple(float(value) for value in point) for point in first.vertices_xz}
    assert points >= {(0.0, -1.0), (0.0, 0.0), (2.0, -1.0)}
    assert _edge(first, (-4.0, -1.0), (0.0, -1.0)) in first.constraint_edges
    assert _edge(first, (0.0, -1.0), (2.0, -1.0)) in first.constraint_edges
    assert _edge(first, (2.0, -1.0), (4.0, -1.0)) in first.constraint_edges
    assert _edge(first, (0.0, -2.0), (0.0, -1.0)) in first.constraint_edges
    assert _edge(first, (0.0, -1.0), (0.0, 0.0)) in first.constraint_edges
    assert _edge(first, (0.0, 0.0), (0.0, 2.0)) in first.constraint_edges
    assert math.isclose(
        math.fsum(mesh_face_polygon(first, index).area for index in range(len(first.triangles))),
        domain.area,
        rel_tol=0.0,
        abs_tol=1e-10,
    )


def test_constraint_arrangement_handles_hole_and_near_collinear_lines() -> None:
    domain = Polygon(
        [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
        holes=[[(4.0, 4.0), (4.0, 6.0), (6.0, 6.0), (6.0, 4.0)]],
    )
    mesh = build_constrained_mesh(
        domain,
        [
            LineString([(0.0, 4.0), (4.0, 4.0), (8.0, 4.00001), (10.0, 4.0)]),
            LineString([(0.0, 7.0), (10.0, 7.000001)]),
        ],
    )
    total_area = math.fsum(
        mesh_face_polygon(mesh, face_id).area for face_id in range(len(mesh.triangles))
    )
    assert math.isclose(total_area, domain.area, rel_tol=0.0, abs_tol=1e-9)
    assert not any(
        mesh_face_polygon(mesh, face_id).covers(box(4.5, 4.5, 5.5, 5.5))
        for face_id in range(len(mesh.triangles))
    )


def test_dangling_internal_constraint_is_rejected_instead_of_silently_dropped() -> None:
    with pytest.raises(TopologyError, match="noded constraint arrangement"):
        build_constrained_mesh(box(0.0, 0.0, 10.0, 10.0), [LineString([(2.0, 5.0), (8.0, 5.0)])])


def test_distinct_vertices_that_collapse_in_float32_are_rejected() -> None:
    domain = box(0.0, 0.0, 2.0, 2.0)
    with pytest.raises(TopologyError, match="Float32|zero-area"):
        build_constrained_mesh(
            domain,
            [
                LineString([(1.0, 0.0), (1.0, 2.0)]),
                LineString([(1.0 + 1e-8, 0.0), (1.0 + 1e-8, 2.0)]),
            ],
        )


def test_patch_face_records_multiple_source_triangle_overlaps_and_full_coverage() -> None:
    domain = box(-1.0, -1.0, 1.0, 1.0)
    mesh = build_constrained_mesh(domain, [])
    source_index = SourceOverlapIndex.create(
        [
            [(-1.0, -1.0), (0.0, -1.0), (-1.0, 1.0)],
            [(0.0, -1.0), (0.0, 1.0), (-1.0, 1.0)],
            [(0.0, -1.0), (1.0, -1.0), (1.0, 1.0)],
            [(0.0, -1.0), (1.0, 1.0), (0.0, 1.0)],
        ],
        [42, 8, 7, 12],
    )

    provenance = source_overlap_provenance(mesh, source_index)

    assert len(provenance) == len(mesh.triangles) == 2
    assert all(
        [row.source_id for row in face] == sorted(row.source_id for row in face)
        for face in provenance
    )
    for face_id, rows in enumerate(provenance):
        assert math.isclose(
            math.fsum(row.intersection_area_m2 for row in rows),
            mesh_face_polygon(mesh, face_id).area,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    assert any(len(face) >= 2 for face in provenance)


def test_overlay_extrema_reproduce_a_source_plane_across_multiple_source_faces() -> None:
    domain = box(-1.0, -1.0, 1.0, 1.0)
    mesh = build_constrained_mesh(domain, [])
    source_triangles = [
        [(-1.0, -1.0), (0.0, -1.0), (-1.0, 1.0)],
        [(0.0, -1.0), (0.0, 1.0), (-1.0, 1.0)],
        [(0.0, -1.0), (1.0, -1.0), (1.0, 1.0)],
        [(0.0, -1.0), (1.0, 1.0), (0.0, 1.0)],
    ]

    def plane(x: float, z: float) -> float:
        return 2.0 * x - 3.0 * z + 5.0

    source_heights = [[plane(x, z) for x, z in triangle] for triangle in source_triangles]
    index = SourceOverlapIndex.create(source_triangles, [4, 2, 9, 1], source_heights)
    candidate_heights = [plane(x, z) for x, z in mesh.vertices_xz]

    report = affine_surface_overlay_extrema(mesh, candidate_heights, index)

    assert report["overlayFaceCount"] > len(mesh.triangles)
    assert report["testedIntersectionVertexCount"] > 0
    assert report["maximumAbsoluteChangeFromSourceM"] < 1e-12
    assert abs(float(index.sample_height(9, 0.75, 0.25)) - plane(0.75, 0.25)) < 1e-12


def test_grid_source_overlap_index_uses_the_pinned_cell_diagonal_and_plane() -> None:
    # One 2 m cell with independent piecewise planes on its original diagonal.
    grid = np.asarray([[0.0, 2.0], [4.0, 10.0]], dtype=np.float64)
    index = SourceOverlapIndex.from_grid(
        grid,
        width_m=2.0,
        depth_m=2.0,
        spacing_m=2.0,
        first_row=0,
        last_row=1,
        first_column=0,
        last_column=1,
    )
    assert index.source_ids == (0, 1)
    assert index.sample_height(0, -0.5, -0.5) == pytest.approx(1.5)
    assert index.sample_height(1, 0.5, 0.5) == pytest.approx(6.5)


def test_source_overlap_refuses_a_gap_or_overlapping_source_provenance() -> None:
    index = SourceOverlapIndex.create(
        [[(0.0, 0.0), (2.0, 0.0), (0.0, 2.0)]],
        [1],
    )
    with pytest.raises(TopologyError, match="not fully covered"):
        index.overlaps(box(0.5, 0.5, 1.5, 1.5))

    overlap_index = SourceOverlapIndex.create(
        [
            [(0.0, 0.0), (2.0, 0.0), (0.0, 2.0)],
            [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0)],
        ],
        [1, 2],
    )
    with pytest.raises(TopologyError, match="not fully covered"):
        overlap_index.overlaps(box(0.5, 0.5, 1.5, 1.5))


def test_invalid_or_nonfinite_source_triangles_are_rejected() -> None:
    with pytest.raises(TopologyError, match="invalid triangle"):
        SourceOverlapIndex.create([[(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]], [1])
    with pytest.raises((TopologyError, ValueError)):
        SourceOverlapIndex.create([[(0.0, 0.0), (1.0, 0.0), (float("nan"), 1.0)]], [1])


def test_alternate_diagonal_trial_changes_only_influence_connectivity() -> None:
    domain = box(-2.0, -2.0, 2.0, 2.0)
    original = build_constrained_mesh(
        domain,
        [
            LineString([(-1, -2), (-1, 2)]),
            LineString([(1, -2), (1, 2)]),
            LineString([(-2, -1), (2, -1)]),
            LineString([(-2, 0), (2, 0)]),
            LineString([(-2, 1), (2, 1)]),
        ],
    )
    influence = box(-1.0, -1.0, 1.0, 1.0)

    flipped, count = alternate_internal_diagonals(original, influence)

    assert count >= 1
    assert (
        flipped.vertices_xz.astype("<f4").tobytes() == original.vertices_xz.astype("<f4").tobytes()
    )
    assert flipped.boundary_edges == original.boundary_edges
    assert set(original.constraint_edges).issubset(set(flipped.constraint_edges))
    assert flipped.triangles.tobytes() != original.triangles.tobytes()
    assert math.fsum(
        mesh_face_polygon(flipped, index).area for index in range(len(flipped.triangles))
    ) == pytest.approx(domain.area)
    original_faces = {tuple(sorted(map(int, face))) for face in original.triangles}
    flipped_faces = {tuple(sorted(map(int, face))) for face in flipped.triangles}
    fixed_faces = {
        tuple(sorted(map(int, face)))
        for face in original.triangles
        if not influence.covers(Polygon(original.vertices_xz[face]))
    }
    assert fixed_faces.issubset(flipped_faces)
    assert all(
        influence.covers(Polygon(flipped.vertices_xz[list(face)]))
        for face in flipped_faces - original_faces
    )


def test_road_aligned_bend_normals_are_noded_and_preserve_ribbon_edges() -> None:
    domain = box(-5.0, -5.0, 5.0, 5.0)
    centerline = [(-3.0, 0.0), (0.0, 0.0), (0.0, 3.0)]
    constraints = road_aligned_constraints(
        centerline,
        width_m=2.0,
        station_spacing_m=0.5,
        lateral_spacing_m=0.5,
        domain=domain,
    )
    mesh = build_constrained_mesh(domain, constraints)

    assert len(constraints) > 20
    assert len(mesh.constraint_edges) >= len(constraints)
    assert math.fsum(
        mesh_face_polygon(mesh, index).area for index in range(len(mesh.triangles))
    ) == pytest.approx(domain.area)
    assert all(count in (1, 2) for count in _edge_counts(mesh).values())


def test_graded_collar_and_local_refinement_are_nested_and_bounded() -> None:
    centerline = [(-2.0, -1.0), (0.0, 0.0), (2.0, -1.0)]
    influence = box(-8.0, -8.0, 8.0, 8.0)
    collar_lines = graded_collar_constraints(centerline, width_m=2.0, domain=influence)
    zone = localized_refinement_zone(
        centerline,
        width_m=2.0,
        source_cell_spacing_m=2.0,
        influence=influence,
    )

    assert len(collar_lines) == 3
    assert [line.length for line in collar_lines] == sorted(line.length for line in collar_lines)
    assert zone.covers(LineString(centerline).buffer(3.0, cap_style="flat", join_style="mitre"))
    assert influence.covers(zone)
    with pytest.raises(TopologyError, match="increasing"):
        graded_collar_constraints(centerline, width_m=2.0, collar_steps_m=(1.0, 0.5))


def test_localized_grid_constraints_are_deterministic_and_clipped_to_zone() -> None:
    zone = Polygon(
        [(0, 0), (3, 0), (3, 3), (0, 3)],
        holes=[[(1, 1), (2, 1), (2, 2), (1, 2)]],
    )

    first = localized_grid_constraints(zone, 0.25)
    second = localized_grid_constraints(zone, 0.25)

    assert first == second
    assert first
    assert all(zone.covers(line) for line in first)
    assert all(line.length > 0 for line in first)


def _edge_counts(mesh) -> dict[tuple[int, int], int]:
    counts: dict[tuple[int, int], int] = {}
    for triangle in mesh.triangles:
        for first, second in (
            (int(triangle[0]), int(triangle[1])),
            (int(triangle[1]), int(triangle[2])),
            (int(triangle[2]), int(triangle[0])),
        ):
            key = tuple(sorted((first, second)))
            counts[key] = counts.get(key, 0) + 1
    return counts
