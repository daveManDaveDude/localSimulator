"""Regression tests for the named Teignmouth validation transition v2."""

from __future__ import annotations

import hashlib
from itertools import count

import numpy as np
import pytest
from shapely.geometry import Polygon
from test_road_surface_validation_v1 import _small_patch_surface

from torquay_pipeline import road_surface_patch as patch
from torquay_pipeline.road_surface_validation_v1 import (
    _building_base_change_v1,
    _composite_maximum_under_polygon_v1,
    _maximum_under_building_v1,
)
from torquay_pipeline.road_surface_validation_v2 import (
    ValidationContextV2,
    ValidationDeadlineExceeded,
    _accepted_identity,
    validate_offline_candidate_v2,
)


def test_accepted_identity_binds_shape_dtype_and_canonical_float32_bytes() -> None:
    surface = _small_patch_surface()
    identity = _accepted_identity(surface.accepted_heights)
    assert identity[0] == surface.accepted_heights.shape
    assert identity[1] == surface.accepted_heights.dtype.str
    assert (
        identity[2]
        == hashlib.sha256(
            surface.accepted_heights.astype("<f4", copy=False).tobytes(order="C")
        ).hexdigest()
    )
    assert identity[3] == id(surface.accepted_heights)


def test_accepted_in_place_mutation_invalidates_context_and_rebuilds_equality_decision() -> None:
    surface = _small_patch_surface()
    surface.inputs.baseline = surface.accepted_heights.copy()
    old_context = ValidationContextV2(surface)
    assert old_context.baseline_matches_accepted
    surface.accepted_heights[0, 0] += np.float32(0.32)
    with pytest.raises(patch.RoadSurfacePatchError, match="canonical Float32 bytes changed"):
        old_context.require_surface(surface)
    new_context = ValidationContextV2(surface)
    assert not new_context.baseline_matches_accepted


def test_accepted_in_place_mutation_inside_gate_is_rejected_before_gate_returns() -> None:
    surface = _small_patch_surface()
    context = ValidationContextV2(surface)
    with pytest.raises(patch.RoadSurfacePatchError, match="canonical Float32 bytes changed"):
        with context.gate_scope(surface):
            surface.accepted_heights[0, 0] += np.float32(0.32)
            context.require_surface(surface)


@pytest.mark.parametrize("replacement", ["same", "shape", "dtype"])
def test_accepted_array_replacement_invalidates_context(replacement: str) -> None:
    surface = _small_patch_surface()
    context = ValidationContextV2(surface)
    if replacement == "same":
        replacement_array = surface.accepted_heights.copy()
    elif replacement == "shape":
        replacement_array = surface.accepted_heights.reshape(2, 8)
    else:
        replacement_array = surface.accepted_heights.astype(np.float64)
    object.__setattr__(surface, "accepted_heights", replacement_array)
    with pytest.raises(patch.RoadSurfacePatchError, match="array was replaced"):
        context.require_surface(surface)


def test_review_witness_equal_to_different_transition_matches_legacy_032m_change() -> None:
    accepted = np.full((4, 4), np.float32(1e-16), dtype="<f4")
    bounds = patch.PatchBounds(first_row=1, first_column=1, row_count=2, column_count=2)
    mesh = patch.build_conforming_mesh(bounds, accepted, 6.0, 6.0, 2.0)
    candidate = mesh.base_y.astype("<f4", copy=True)
    inputs = type(_small_patch_surface().inputs)(
        width_m=6.0,
        depth_m=6.0,
        spacing_m=2.0,
        columns=4,
        rows=4,
        baseline=accepted.copy(),
        release_id="synthetic-release",
        source_hashes={"heightfield.f32": {"sha256": "synthetic-source"}},
    )
    surface = patch.CompositeSurface(mesh, inputs, accepted, candidate)
    surface.inputs.baseline = surface.accepted_heights.copy()
    context_before = ValidationContextV2(surface)
    assert context_before.baseline_matches_accepted
    feature = {
        "id": "reviewer-accepted-height-mutation-witness",
        "geometry": {
            "polygons": [
                {
                    "exteriorXZ": [
                        [-3.0, -3.0],
                        [-2.75, -3.0],
                        [-2.75, -2.75],
                        [-3.0, -2.75],
                        [-3.0, -3.0],
                    ],
                    "interiorRingsXZ": [],
                }
            ]
        },
    }
    surface.accepted_heights[0, 0] = np.float32(0.32)
    with pytest.raises(patch.RoadSurfacePatchError, match="canonical Float32 bytes changed"):
        _building_base_change_v1(feature, surface, context_before)

    rebuilt = ValidationContextV2(surface)
    assert not rebuilt.baseline_matches_accepted
    polygon = Polygon(feature["geometry"]["polygons"][0]["exteriorXZ"])
    legacy_delta = _composite_maximum_under_polygon_v1(
        polygon, surface, rebuilt
    ) - _maximum_under_building_v1(feature, surface.inputs.baseline, surface.inputs, rebuilt)
    optimized_delta = _building_base_change_v1(feature, surface, rebuilt)
    assert legacy_delta == 0.3199999928474425
    assert optimized_delta == legacy_delta
    assert optimized_delta != 0.0


def test_validation_cutoff_marks_every_unrun_gate_unavailable() -> None:
    surface = _small_patch_surface()
    context = ValidationContextV2(surface)
    report, _ = validate_offline_candidate_v2(
        surface,
        Polygon(),
        [],
        {"converged": False},
        patch.ACCEPTED_PREVIEW_HASHES,
        context=context,
        validation_deadline_monotonic=5.0,
        clock=lambda: 5.0,
    )
    assert report["passes"] is False
    assert report["validationComplete"] is False
    assert report["validationStatus"] == "incomplete_deadline"
    for gate in patch.PATCH_OFFLINE_GATE_NAMES:
        assert report[gate]["passes"] is False
        assert report[gate]["available"] is False
        assert report[gate]["status"] == "unavailable_deadline"


def test_deadline_during_building_iteration_is_not_a_partial_pass() -> None:
    surface = _small_patch_surface()
    context = ValidationContextV2(surface)
    ticks = count()
    context.validation_deadline_monotonic = 10.0
    context.clock = lambda: 9.0 if next(ticks) == 0 else 10.0
    context.require_surface(surface)
    with pytest.raises(ValidationDeadlineExceeded):
        context.require_surface(surface)
