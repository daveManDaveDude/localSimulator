"""Synthetic controls only; these never read the real release or consume a build."""

from types import SimpleNamespace

import numpy as np
import pytest
from shapely.geometry import box

from torquay_pipeline.teignmouth_corridor_continuous import (
    LATERALS,
    barycentric,
    field_height,
    make_chart,
    ownership_report,
    preflight,
    section_stations,
    section_vectors,
    source_intersections,
)
from torquay_pipeline.teignmouth_corridor_prototype import ANCHOR, BOUNDS, Corridor


def test_miter_vectors_preserve_normal_width_at_both_segment_ends():
    part = np.asarray([[0, 0], [120, 0], [200, 30]])
    cumulative, vectors = section_vectors(part)
    assert cumulative[0] == 0
    for index, delta in enumerate(np.diff(part, axis=0)):
        tangent = delta / np.linalg.norm(delta)
        normal = np.asarray([-tangent[1], tangent[0]])
        assert vectors[index] @ normal == pytest.approx(1)
        assert vectors[index + 1] @ normal == pytest.approx(1)


def test_frozen_stations_include_anchor_source_vertices_and_fade_ends():
    stations = section_stations(np.asarray([0, 120.123, 220]))
    for required in (108, 120.123, 140, 155, ANCHOR, 187):
        assert required in stations
    assert np.all(np.diff(stations) > 0)
    assert np.max(np.diff(stations)) <= 0.5


def test_continuous_chart_recovers_every_station_and_shared_edge():
    part = [[0.0, 0.0], [120.0, 0.0], [200.0, 30.0]]
    chart = make_chart(part)
    columns = len(LATERALS)
    center = LATERALS.index(0)
    for index in range(0, len(chart.points), columns):
        field = chart.locate(chart.points[index + center])
        assert field == pytest.approx(chart.fields[index + center], abs=1e-8)
    for row in (0, 10, 30, 100):
        a, b = row * columns + center, (row + 1) * columns + center
        point = (chart.points[a] + chart.points[b]) / 2
        assert chart.locate(point) == pytest.approx((chart.fields[a] + chart.fields[b]) / 2)


def test_chart_rejects_reversals_and_barycentric_degeneracy():
    with pytest.raises(ValueError, match="miter"):
        section_vectors(np.asarray([[0, 0], [200, 0], [0, 0]]))
    with pytest.raises(ValueError, match="degenerate"):
        barycentric(np.asarray([[0.0, 0.0]]), np.zeros((3, 2)))


def test_source_plane_intersections_include_diagonal_crossings():
    first, second = np.asarray([0.25, 0.25]), np.asarray([3.25, 1.25])
    parameters = source_intersections(first, second)
    assert 0 in parameters and 1 in parameters
    assert 0.375 in parameters  # x+z=2 source diagonal
    assert (2 - 0.25) / 3 in parameters  # x=2 source column


def fake_corridor(profile_height):
    part = [[-280.0, -95.0], [-20.0, -95.0]]
    return Corridor(
        SimpleNamespace(baseline=np.zeros((1001, 1001), dtype=np.float32)),
        part,
        np.arange(0.0, 262.0, 2.0),
        np.zeros(131),
        np.full(131, profile_height),
        box(*BOUNDS),
    )


def test_necessary_preflight_reports_exact_strict_five_metre_witness():
    corridor = fake_corridor(5.0)
    result = preflight(corridor, make_chart(corridor.part))
    assert not result["passes"]
    witness = result["firstViolation"]
    assert witness["stationM"] == pytest.approx(140)
    assert witness["absoluteChangeM"] == pytest.approx(5)
    assert witness["sourceY"] == 0
    assert witness["candidateY"] == 5


def test_necessary_preflight_pass_does_not_claim_final_safety():
    corridor = fake_corridor(0.0)
    result = preflight(corridor, make_chart(corridor.part))
    assert result["passes"]
    assert result["testedSamples"] > 100
    assert "necessary only" in result["criterion"]
    assert field_height(corridor, 0, 140, 0) == 0


def test_nearby_off_ground_core_is_excluded_and_conflict_stops():
    corridor = fake_corridor(0)
    corridor.inputs.road_payload = {
        "features": [
            {
                "source": {"osmId": 123},
                "estimatedWidthM": 6,
                "groundAssumption": "explicit_bridge",
                "centerlinePartsXZ": [[[-140, -120], [-140, -70]]],
            }
        ]
    }
    result = ownership_report(corridor, make_chart(corridor.part))
    assert not result["passes"]
    assert result["excludedOffGroundWayIds"] == [123]
    assert not result["conflicts"][0]["groundEligible"]
