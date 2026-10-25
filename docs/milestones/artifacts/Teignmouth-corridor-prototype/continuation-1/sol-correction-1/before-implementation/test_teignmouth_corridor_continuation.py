"""Synthetic controls only; these never read the real release or consume a build."""

import json
import runpy
import subprocess
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from shapely.geometry import box

from torquay_pipeline.teignmouth_corridor_continuation import (
    LATERALS,
    barycentric,
    field_height,
    load_continuation_config,
    make_chart,
    ownership_report,
    preflight,
    section_stations,
    section_vectors,
    source_intersections,
    target_section_gates,
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


def test_necessary_preflight_reports_exact_strict_six_metre_witness():
    corridor = fake_corridor(6.0)
    result = preflight(corridor, make_chart(corridor.part))
    assert not result["passes"]
    witness = result["firstViolation"]
    assert witness["stationM"] == pytest.approx(140)
    assert witness["absoluteChangeM"] == pytest.approx(6)
    assert witness["sourceY"] == 0
    assert witness["candidateY"] == 6


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


def synthetic_target_mesh(crossfall_percent=0.0, center_height_m=0.0):
    stations = np.arange(140.0, 155.0001, 0.25)
    lateral = np.arange(-3.0, 3.0001, 0.25)
    xz = np.asarray(
        [[-280.0 + station, -95.0 + offset] for station in stations for offset in lateral],
        dtype="<f4",
    )
    heights = center_height_m + (xz[:, 1].astype(np.float64) + 95.0) * (crossfall_percent / 100.0)
    triangles = []
    width = len(lateral)
    for row in range(len(stations) - 1):
        for column in range(width - 1):
            a = row * width + column
            b, c, d = a + width, a + 1, a + width + 1
            triangles.extend(((a, b, c), (b, d, c)))
    return xz, heights.astype("<f4"), np.asarray(triangles, dtype="<u4")


def test_candidate_local_section_gate_enforces_centerline_deviation_limit():
    corridor = fake_corridor(0.0)
    xz, candidate, triangles = synthetic_target_mesh(center_height_m=2.1)
    result = target_section_gates(corridor, xz, candidate, triangles)
    assert not result["passes"]
    assert result["maximumCenterlineSourceHeightDeviationM"] == pytest.approx(2.1)


def test_candidate_local_section_gate_passes_flat_synthetic_case():
    corridor = fake_corridor(0.0)
    xz, candidate, triangles = synthetic_target_mesh()
    result = target_section_gates(corridor, xz, candidate, triangles)
    assert result["passes"]
    assert result["maximumCrossSlopePercent"] == pytest.approx(0.0)
    assert result["maximumFullWidthSpanM"] == pytest.approx(0.0)


def test_actual_continuation_config_parses_without_loading_geographic_data():
    from pathlib import Path

    config_path = (
        Path(__file__).resolve().parents[2]
        / "config/road-surface-teignmouth-corridor-continuation.json"
    )
    parsed = load_continuation_config(config_path)
    assert parsed.release_id == "616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a"
    assert parsed.output_directory == "data/generated/teignmouth-corridor-continuation"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(output_directory="public/worlds/unsafe"),
        lambda value: value.update(release_id="0" * 64),
        lambda value: value["source"].update(osm_way_id=123),
        lambda value: value["recipe"].update(width_m=7.0),
        lambda value: value["candidate_local_limits"].update(absolute_terrain_change_m_strict=7.0),
        lambda value: value.update(extra_field=True),
    ],
)
def test_continuation_config_rejects_altered_or_malformed_values(tmp_path, mutation):
    import json
    from pathlib import Path

    original = (
        Path(__file__).resolve().parents[2]
        / "config/road-surface-teignmouth-corridor-continuation.json"
    )
    value = json.loads(original.read_text(encoding="utf-8"))
    mutation(value)
    candidate = tmp_path / "bad-config.json"
    candidate.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError):
        load_continuation_config(candidate)


def test_final_float32_mesh_gate_rejects_adversarial_crossfall():
    corridor = fake_corridor(0.0)
    xz, candidate, triangles = synthetic_target_mesh(crossfall_percent=10.0)
    result = target_section_gates(corridor, xz, candidate, triangles)
    assert not result["passes"]
    assert result["surface"] == "serialized final Float32 vertices and triangles"
    assert result["maximumCrossSlopePercent"] == pytest.approx(10.0, abs=1e-4)
    assert result["maximumFullWidthSpanM"] == pytest.approx(0.6, abs=1e-4)


def test_repository_root_import_smoke_does_not_read_gis():
    root = Path(__file__).resolve().parents[2]
    interpreter = root / "pipeline/.venv/Scripts/python.exe"
    command = [
        str(interpreter),
        str(root / "pipeline/scripts/build_teignmouth_corridor_continuation.py"),
        "--import-smoke",
    ]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "no GIS data read" in result.stdout
    assert interpreter.exists()


def test_primary_build_and_telemetry_errors_both_persist(tmp_path):
    root = Path(__file__).resolve().parents[2]
    runner = runpy.run_path(
        str(root / "pipeline/scripts/build_teignmouth_corridor_continuation.py")
    )
    primary_error = {
        "type": "ValueError",
        "message": "synthetic primary build failure",
        "traceback": "synthetic traceback",
    }

    def failed_telemetry():
        raise OSError("synthetic telemetry failure")

    report = runner["finalize_attempt_report"](
        tmp_path,
        {"status": "STOP", "stopReasons": ["synthetic primary build failure"]},
        {"protected.txt": "before-hash"},
        {"protected.txt": "before-hash"},
        primary_error,
        0.0,
        memory_reader=failed_telemetry,
    )
    saved = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    after = json.loads((tmp_path / "preservation-after.json").read_text(encoding="utf-8"))
    assert saved["primaryError"] == primary_error
    assert saved["resources"]["peakWorkingSetStatus"] == "unavailable"
    assert "synthetic telemetry failure" in saved["resources"]["peakWorkingSetError"]
    assert after == {"protected.txt": "before-hash"}
    assert report["primaryError"] == primary_error
