"""Known-anchor transformation, axis order, and operation metadata tests."""

from __future__ import annotations

from math import hypot

from pyproj.network import is_network_enabled

from torquay_pipeline.coordinates import transform_bng_to_wgs84, transform_wgs84_to_bng


def test_tq1_4hn_transform_matches_provider_centroid_with_reported_accuracy() -> None:
    easting, northing, operation = transform_wgs84_to_bng(-3.536013, 50.477853)

    # Postcodes.io publishes its centroid BNG values rounded to whole metres.
    assert hypot(easting - 291110, northing - 65355) < 2.5
    assert operation.accuracy_m == 2
    assert "OSGB36" in operation.description
    assert operation.grid_status == "no grid files listed for the operation used"
    assert not is_network_enabled()


def test_round_trip_preserves_longitude_latitude_axis_order() -> None:
    easting, northing, forward = transform_wgs84_to_bng(-3.536013, 50.477853)
    longitude, latitude, inverse = transform_bng_to_wgs84([easting], [northing])

    # Both operations report 2 m accuracy; round-trip error is expected to be much smaller.
    assert hypot((longitude[0] + 3.536013) * 70_000, (latitude[0] - 50.477853) * 111_000) < 2
    assert forward.accuracy_m == inverse.accuracy_m == 2
    assert "British National Grid" in forward.description
    assert "OSGB36" in inverse.description


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
