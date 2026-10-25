"""Synthetic controls for the independent fixed corridor recipe."""

import math

import numpy as np
import pytest

from torquay_pipeline.teignmouth_corridor_prototype import (
    RADIUS,
    gaussian_profile,
    smoothstep,
    topology_report,
)


def test_constant_profile_and_shape():
    for length in (1, 18, 19, 65):
        actual = gaussian_profile(np.full(length, 12.75))
        assert actual.shape == (length,)
        np.testing.assert_allclose(actual, 12.75, atol=1e-13)


def test_kernel_matches_independent_reflected_sum():
    values = np.arange(71.0) ** 2 / 100.0
    weights = [math.exp(-0.5 * (index / 6.0) ** 2) for index in range(-18, 19)]
    expected = []
    for position in range(len(values)):
        total = 0.0
        for offset, weight in zip(range(-18, 19), weights, strict=True):
            index = position + offset
            if index < 0:
                index = -index
            if index >= len(values):
                index = 2 * len(values) - 2 - index
            total += values[index] * weight
        expected.append(total / sum(weights))
    np.testing.assert_allclose(gaussian_profile(values), expected, atol=1e-13)


def test_short_profile_pads_edge_instead_of_reflecting():
    values = np.asarray([0.0, 10.0])
    weights = np.exp(-0.5 * (np.arange(-RADIUS, RADIUS + 1) / 6.0) ** 2)
    expected = 10.0 * weights[RADIUS + 1 :].sum() / weights.sum()
    assert gaussian_profile(values)[0] == pytest.approx(expected)


@pytest.mark.parametrize("values", [np.asarray([]), np.asarray([np.nan]), np.ones((2, 2))])
def test_invalid_profiles_fail_closed(values):
    with pytest.raises(ValueError):
        gaussian_profile(values)


def test_smooth_fade_retains_endpoints():
    np.testing.assert_array_equal(smoothstep(np.asarray([-1.0, 0.0, 1.0, 2.0])), [0, 0, 1, 1])
    assert smoothstep(np.asarray([0.5]))[0] == 0.5


def test_numpy25_xz_topology_and_hole_rejection():
    # Synthetic flat coarse lattice exercises serialized 2D determinant arithmetic.
    points = np.asarray(
        [(x, z) for z in range(-136, -53, 2) for x in range(-182, -97, 2)], dtype="<f4"
    )
    faces = []
    columns = 43
    for row in range(41):
        for column in range(42):
            first = row * columns + column
            faces.extend(
                (
                    (first, first + columns, first + 1),
                    (first + 1, first + columns, first + columns + 1),
                )
            )
    indices = np.asarray(faces, dtype="<u4")
    report = topology_report(points, indices)
    assert report["passes"]
    assert report["boundaryExactlySource"]
    assert report["upwardNondegenerate"]
    assert not topology_report(points, indices[:-1])["passes"]
