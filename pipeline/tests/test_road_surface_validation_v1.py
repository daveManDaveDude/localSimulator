"""Synthetic exactness tests for the additive Teignmouth validator v1."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from shapely.geometry import Polygon

from torquay_pipeline import road_surface as road
from torquay_pipeline import road_surface_patch as patch
from torquay_pipeline.road_surface_validation_v1 import (
    ValidationContextV1,
    _building_base_change_v1,
    _composite_maximum_under_polygon_v1,
    _maximum_under_building_v1,
    _paired_grid_maxima_under_building_v1,
    _strictly_disjoint,
    composite_earthwork_overlay_report_v1,
)


def _surface():
    accepted = np.asarray(
        [
            [0.0, 0.4, 1.2, 1.7],
            [0.8, 1.3, 2.1, 2.8],
            [1.1, 1.9, 2.6, 3.4],
            [1.8, 2.2, 3.1, 4.0],
        ],
        dtype="<f4",
    )
    bounds = patch.PatchBounds(first_row=0, first_column=0, row_count=3, column_count=3)
    mesh = patch.build_conforming_mesh(bounds, accepted, 6.0, 6.0, 2.0)
    candidate = mesh.base_y.astype("<f4", copy=True)
    candidate[len(candidate) // 2] += np.float32(0.037)
    inputs = SimpleNamespace(
        width_m=6.0,
        depth_m=6.0,
        spacing_m=2.0,
        columns=4,
        rows=4,
        baseline=accepted,
        release_id="synthetic-release",
        source_hashes={"heightfield.f32": {"sha256": "synthetic-source"}},
    )
    return patch.CompositeSurface(mesh, inputs, accepted, candidate)


def _small_patch_surface(*, baseline=None):
    accepted = np.asarray(
        [
            [0.0, 0.4, 1.2, 1.7],
            [0.8, 1.3, 2.1, 2.8],
            [1.1, 1.9, 2.6, 3.4],
            [1.8, 2.2, 3.1, 4.0],
        ],
        dtype="<f4",
    )
    bounds = patch.PatchBounds(first_row=1, first_column=1, row_count=2, column_count=2)
    mesh = patch.build_conforming_mesh(bounds, accepted, 6.0, 6.0, 2.0)
    candidate = mesh.base_y.astype("<f4", copy=True)
    candidate[len(candidate) // 2] += np.float32(0.037)
    inputs = SimpleNamespace(
        width_m=6.0,
        depth_m=6.0,
        spacing_m=2.0,
        columns=4,
        rows=4,
        baseline=accepted.copy() if baseline is None else baseline,
        release_id="synthetic-release",
        source_hashes={"heightfield.f32": {"sha256": "synthetic-source"}},
    )
    return patch.CompositeSurface(mesh, inputs, accepted, candidate)


def test_strict_bbox_rejection_keeps_touching_bounds() -> None:
    assert not _strictly_disjoint((0.0, 0.0, 1.0, 1.0), (1.0, 0.2, 2.0, 0.8))
    assert not _strictly_disjoint((0.0, 0.0, 1.0, 1.0), (0.2, 1.0, 0.8, 2.0))
    assert _strictly_disjoint((0.0, 0.0, 1.0, 1.0), (1.0000001, 0.0, 2.0, 1.0))


def test_cached_polygon_maxima_match_legacy_for_holes_multipart_edges_and_slivers() -> None:
    surface = _surface()
    context = ValidationContextV1(surface, maximum_coarse_entries=5, maximum_face_entries=7)
    feature = {
        "id": "synthetic-multipart",
        "geometry": {
            "polygons": [
                {
                    "exteriorXZ": [
                        [-2.8, -2.7],
                        [-1.1, -2.7],
                        [-1.1, -1.1],
                        [-2.8, -1.1],
                        [-2.8, -2.7],
                    ],
                    "interiorRingsXZ": [
                        [[-2.3, -2.2], [-2.3, -1.8], [-1.8, -1.8], [-1.8, -2.2], [-2.3, -2.2]]
                    ],
                },
                {
                    "exteriorXZ": [
                        [-1.0, -0.75],
                        [0.25, -0.75],
                        [0.25, 0.25],
                        [-1.0, 0.25],
                        [-1.0, -0.75],
                    ],
                    "interiorRingsXZ": [],
                },
                {
                    # The thin polygon crosses the accepted 2 m source breakline.
                    "exteriorXZ": [
                        [-0.00000001, -1.75],
                        [0.00000001, -1.75],
                        [0.00000001, -1.25],
                        [-0.00000001, -1.25],
                        [-0.00000001, -1.75],
                    ],
                    "interiorRingsXZ": [],
                },
                {
                    # This footprint shares the exact local patch/source-grid edge.
                    "exteriorXZ": [[2.0, -1.0], [3.0, -1.0], [3.0, 0.0], [2.0, 0.0], [2.0, -1.0]],
                    "interiorRingsXZ": [],
                },
            ]
        },
    }

    assert _maximum_under_building_v1(
        feature, surface.inputs.baseline, surface.inputs, context
    ) == (
        patch._road_surface._maximum_under_building(
            feature, surface.inputs.baseline, surface.inputs
        )
    )
    for record in feature["geometry"]["polygons"]:
        polygon = Polygon(record["exteriorXZ"], record.get("interiorRingsXZ", []))
        assert _composite_maximum_under_polygon_v1(polygon, surface, context) == (
            patch._composite_maximum_under_polygon(polygon, surface)
        )
    assert len(context.baseline_coarse_polygons) <= 5
    assert len(context.accepted_coarse_polygons) <= 5
    assert len(context.patch_face_polygons) <= 7
    assert len(context.patch_face_bounds) <= 7
    assert context.stats["bboxDisjointRejections"] > 0


def test_unchanged_source_footprints_prove_zero_but_touching_patch_uses_legacy() -> None:
    surface = _small_patch_surface()
    context = ValidationContextV1(surface)
    outside = {
        "id": "outside-patch-multipart-with-hole-and-breakline-sliver",
        "geometry": {
            "polygons": [
                {
                    "exteriorXZ": [
                        [-2.8, -2.8],
                        [-1.5, -2.8],
                        [-1.5, -1.2],
                        [-2.8, -1.2],
                        [-2.8, -2.8],
                    ],
                    "interiorRingsXZ": [
                        [[-2.5, -2.5], [-2.5, -2.0], [-2.0, -2.0], [-2.0, -2.5], [-2.5, -2.5]]
                    ],
                },
                {
                    # The sliver crosses the x=0 source breakline, but lies below
                    # the patch domain in Z.
                    "exteriorXZ": [
                        [-0.00000002, -2.8],
                        [0.00000002, -2.8],
                        [0.00000002, -2.2],
                        [-0.00000002, -2.2],
                        [-0.00000002, -2.8],
                    ],
                    "interiorRingsXZ": [],
                },
            ]
        },
    }

    assert context.baseline_matches_accepted
    assert context.feature_outside_patch(outside)
    assert _building_base_change_v1(outside, surface, context) == 0.0
    assert context.stats["disjointBuildingFastPaths"] == 1

    touching = {
        "id": "patch-boundary-touch",
        "geometry": {
            "polygons": [
                {
                    "exteriorXZ": [
                        [-1.0, -1.8],
                        [-0.4, -1.8],
                        [-0.4, -1.0],
                        [-1.0, -1.0],
                        [-1.0, -1.8],
                    ],
                    "interiorRingsXZ": [],
                }
            ]
        },
    }
    assert not context.feature_outside_patch(touching)
    expected = patch._composite_maximum_under_polygon(
        Polygon(touching["geometry"]["polygons"][0]["exteriorXZ"]), surface
    ) - patch._road_surface._maximum_under_building(
        touching, surface.inputs.baseline, surface.inputs
    )
    assert _building_base_change_v1(touching, surface, context) == expected
    assert context.stats["disjointBuildingFastPaths"] == 1


def test_disjoint_fast_path_requires_identical_accepted_and_baseline_grids() -> None:
    differing_baseline = np.asarray(
        [[0.0, 0.4, 1.2, 1.7], [0.8, 1.3, 2.1, 2.8], [1.1, 1.9, 2.6, 3.4], [1.8, 2.2, 3.1, 4.0]],
        dtype="<f4",
    )
    differing_baseline[0, 0] += np.float32(0.1)
    surface = _small_patch_surface(baseline=differing_baseline)
    context = ValidationContextV1(surface)
    feature = {
        "id": "outside-but-different-source-grid",
        "geometry": {
            "polygons": [
                {
                    "exteriorXZ": [
                        [-2.8, -2.8],
                        [-2.0, -2.8],
                        [-2.0, -2.0],
                        [-2.8, -2.0],
                        [-2.8, -2.8],
                    ],
                    "interiorRingsXZ": [],
                }
            ]
        },
    }
    assert not context.baseline_matches_accepted
    assert context.feature_outside_patch(feature)
    baseline_maximum = patch._road_surface._maximum_under_building(
        feature, surface.inputs.baseline, surface.inputs
    )
    candidate_maximum = max(
        patch._composite_maximum_under_polygon(
            Polygon(item["exteriorXZ"], item.get("interiorRingsXZ", [])), surface
        )
        for item in feature["geometry"]["polygons"]
    )
    paired_baseline, paired_candidate = _paired_grid_maxima_under_building_v1(
        feature, surface, context
    )
    assert (paired_baseline, paired_candidate) == (baseline_maximum, candidate_maximum)
    assert (
        _building_base_change_v1(feature, surface, context) == candidate_maximum - baseline_maximum
    )
    assert context.stats["disjointBuildingFastPaths"] == 0
    assert context.stats["pairedGridBuildings"] == 2


def test_bounded_geometry_cache_evicts_and_admits_new_entries() -> None:
    surface = _small_patch_surface()
    context = ValidationContextV1(surface, maximum_coarse_entries=2)
    context.coarse_polygon("baseline", 0, 0, 0)
    context.coarse_polygon("baseline", 0, 1, 0)
    context.coarse_polygon("baseline", 0, 0, 0)  # refresh first entry
    context.coarse_polygon("baseline", 1, 0, 0)  # evict the second entry
    assert len(context.baseline_coarse_polygons) == 2
    creations_before = context.stats["baselineCoarsePolygonCreations"]
    context.coarse_polygon("baseline", 0, 1, 0)
    assert context.stats["baselineCoarsePolygonCreations"] == creations_before + 1
    assert len(context.baseline_coarse_polygons) == 2


def test_vectorized_grid_sampler_matches_scalar_bitwise_at_edges_and_diagonals() -> None:
    grid = np.asarray(
        [[0.0, 0.4, 1.2, 1.7], [0.8, 1.3, 2.1, 2.8], [1.1, 1.9, 2.6, 3.4], [1.8, 2.2, 3.1, 4.0]],
        dtype="<f4",
    )
    generator = np.random.default_rng(20261023)
    x_values = np.concatenate(
        (generator.uniform(-3.0, 3.0, 1024), np.asarray([-3.0, 3.0, -1.0, 1.0, 0.0, 2.0]))
    )
    z_values = np.concatenate(
        (generator.uniform(-3.0, 3.0, 1024), np.asarray([-3.0, 3.0, 1.0, -1.0, 0.0, -2.0]))
    )
    vectorized = road._sample_grid_many(grid, x_values, z_values, 2.0)
    scalar = np.asarray(
        [
            road._sample_grid(grid, float(x), float(z), 2.0)
            for x, z in zip(x_values, z_values, strict=True)
        ]
    )
    assert np.array_equal(vectorized, scalar)


def test_earthwork_reuses_only_identity_bound_ownership_and_matches_legacy_bytes() -> None:
    surface = _surface()
    context = ValidationContextV1(surface)
    ownership = context.bind_ownership(surface)
    retained_ownership = context.ownership_report
    ownership["passes"] = not ownership["passes"]
    assert context.ownership_report == retained_ownership

    legacy = patch.composite_earthwork_overlay_report(surface)
    optimized = composite_earthwork_overlay_report_v1(surface, context)
    assert patch.serialize_offline_report(optimized) == patch.serialize_offline_report(legacy)

    stale_surface = patch.CompositeSurface(
        surface.mesh,
        surface.inputs,
        surface.accepted_heights,
        surface.patch_heights.copy() + np.float32(0.01),
    )
    with pytest.raises(patch.RoadSurfacePatchError, match="identity does not match"):
        context.require_surface(stale_surface)

    same_count_different_mesh = patch.build_conforming_mesh(
        patch.PatchBounds(first_row=0, first_column=0, row_count=3, column_count=3),
        surface.accepted_heights,
        6.0,
        6.0,
        2.0,
    )
    same_count_different_mesh.vertices_xz[0, 0] += 0.125
    different_surface = patch.CompositeSurface(
        same_count_different_mesh,
        surface.inputs,
        surface.accepted_heights,
        surface.patch_heights,
    )
    assert len(different_surface.mesh.triangles) == len(surface.mesh.triangles)
    with pytest.raises(patch.RoadSurfacePatchError, match="identity does not match"):
        context.bind_ownership(different_surface)
