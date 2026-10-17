"""Known-anchor transformation, axis order, and operation metadata tests."""

from __future__ import annotations

import warnings
from math import hypot
from types import SimpleNamespace

from pyproj import CRS
from pyproj.network import is_network_enabled
from pyproj.transformer import TransformerGroup

from torquay_pipeline.coordinates import (
    _missing_operation_records,
    select_stable_operation,
    transform_bng_to_wgs84,
    transform_wgs84_to_bng,
)


def test_tq1_4hn_transform_matches_provider_centroid_with_reported_accuracy() -> None:
    easting, northing, operation = transform_wgs84_to_bng(-3.536013, 50.477853)

    # Postcodes.io publishes its centroid BNG values rounded to whole metres.
    assert hypot(easting - 291110, northing - 65355) < 2.5
    assert operation.accuracy_m == 2
    assert "OSGB36" in operation.description
    assert operation.name == "EPSG:1314 + EPSG:19916"
    assert operation.uses_grids is False
    assert isinstance(operation.best_available, bool)
    if not operation.best_available:
        missing_grid = operation.preferred_missing_operations[0]["grids"][0]
        assert missing_grid["short_name"] == "uk_os_OSTN15_NTv2_OSGBtoETRS.tif"
        assert missing_grid["available"] is False
    assert not is_network_enabled()


def test_round_trip_preserves_longitude_latitude_axis_order() -> None:
    easting, northing, forward = transform_wgs84_to_bng(-3.536013, 50.477853)
    longitude, latitude, inverse = transform_bng_to_wgs84([easting], [northing])

    # Both operations report 2 m accuracy; round-trip error is expected to be much smaller.
    assert hypot((longitude[0] + 3.536013) * 70_000, (latitude[0] - 50.477853) * 111_000) < 2
    assert forward.accuracy_m == inverse.accuracy_m == 2
    assert "British National Grid" in forward.description
    assert "OSGB36" in inverse.description


def test_pinned_operation_selection_does_not_depend_on_candidate_order() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        group = TransformerGroup(
            CRS.from_epsg(4326), CRS.from_epsg(27700), always_xy=True, allow_ballpark=False
        )
    selected = select_stable_operation(group.transformers)
    reversed_selected = select_stable_operation(reversed(group.transformers))

    assert selected.definition == reversed_selected.definition
    assert selected.accuracy == 2
    assert "OSGB36 to WGS 84 (6)" in selected.description


def test_missing_preferred_operation_and_grid_diagnostics_are_serialized() -> None:
    missing_grid = SimpleNamespace(
        short_name="preferred-grid.tif",
        full_name="",
        available=False,
        url="https://example.invalid/preferred-grid.tif",
    )
    missing_operation = SimpleNamespace(
        name="Preferred operation (1)", accuracy=1.0, grids=[missing_grid]
    )
    diagnostics = _missing_operation_records(
        SimpleNamespace(unavailable_operations=[missing_operation])
    )  # type: ignore[arg-type]

    assert diagnostics == (
        {
            "name": "Preferred operation (1)",
            "reported_accuracy_m": 1.0,
            "grids": [
                {
                    "short_name": "preferred-grid.tif",
                    "full_name": "",
                    "available": False,
                    "url": "https://example.invalid/preferred-grid.tif",
                }
            ],
        },
    )


def test_stable_operation_selection_fails_clearly_when_unavailable() -> None:
    try:
        select_stable_operation([])
    except ValueError as exc:
        assert "pinned non-ballpark EPSG:1314 + EPSG:19916" in str(exc)
    else:
        raise AssertionError("missing pinned operation should fail")


def test_transform_helpers_reject_mismatched_coordinate_lists() -> None:
    try:
        transform_bng_to_wgs84([1, 2], [3])
    except ValueError as exc:
        assert "same number" in str(exc)
    else:
        raise AssertionError("mismatched inputs should fail")


def test_transform_helpers_reject_nonfinite_direct_inputs() -> None:
    try:
        transform_wgs84_to_bng(float("nan"), 50.0)
    except ValueError as exc:
        assert "finite" in str(exc)
    else:
        raise AssertionError("non-finite WGS84 input should fail")

    try:
        transform_bng_to_wgs84([291000], [float("inf")])
    except ValueError as exc:
        assert "finite" in str(exc)
    else:
        raise AssertionError("non-finite BNG input should fail")
