from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from shapely import from_wkt, union_all
from shapely.geometry import Polygon, box

from torquay_pipeline.road_surface_float32_frame import Float32LocalFrame
from torquay_pipeline.road_surface_topology import PlanarMesh, SourceOverlapIndex, TopologyError
from torquay_pipeline.teignmouth_corridor_continuation import field_height, make_chart
from torquay_pipeline.teignmouth_corridor_prototype import Corridor
from torquay_pipeline.teignmouth_float32_candidate import (
    Float32CandidateError,
    StoredCandidate,
    _candidate_affine_surface_overlay_extrema,
    _section_gates_from_stored_mesh,
    _serialize_position_buffers,
    _write_failure,
    _write_gate,
    candidate_fallback,
    classify_treatment_support,
    required_treatment_support_report,
    sample_stored_triangle_surface,
    validate_chart_support,
    validate_stored_local_mesh,
)


def test_stored_topology_checks_actual_float32_triangles_and_constraints() -> None:
    points = np.asarray([[0, 0], [0, 1], [1, 0], [1, 1]], dtype="<f4")
    faces = np.asarray([[0, 1, 2], [1, 3, 2]], dtype="<u4")
    result = validate_stored_local_mesh(
        points,
        faces,
        box(0, 0, 1, 1),
        ((0, 1), (1, 2)),
    )
    assert result["passes"] is True
    assert result["actualStoredLocalFloat32"] is True
    with pytest.raises(Float32CandidateError, match="lost constrained edges"):
        validate_stored_local_mesh(points, faces, box(0, 0, 1, 1), ((0, 3),))


def test_stored_topology_rejects_float32_collapse_and_inverted_faces() -> None:
    points = np.asarray([[0, 0], [1, 0], [0, 1]], dtype="<f4")
    inverted = np.asarray([[0, 1, 2]], dtype="<u4")
    with pytest.raises(Float32CandidateError, match="inverted/degenerate"):
        validate_stored_local_mesh(points, inverted, box(0, 0, 1, 1), ())
    collapsed = np.asarray([[0, 0], [1, 0], [0, 1]], dtype="<f4")
    collapsed[2] = collapsed[1]
    with pytest.raises(Float32CandidateError, match="inverted/degenerate"):
        validate_stored_local_mesh(
            collapsed, np.asarray([[0, 1, 2]], dtype="<u4"), box(0, 0, 1, 1), ()
        )


def test_decoded_world_float64_sampler_and_truthful_fallback() -> None:
    frame = Float32LocalFrame()
    local_xyz = np.asarray([[-1, 3, -1], [1, 3, -1], [-1, 5, 1]], dtype="<f4")
    world_xyz = frame.decode_xyz_to_world64(local_xyz)
    candidate = StoredCandidate(
        frame=frame,
        local_positions_xyz_f32=local_xyz,
        triangles_u32=np.asarray([[0, 2, 1]], dtype="<u4"),
        reconstructed_world_xyz_f64=world_xyz,
        source_y_f32=np.asarray([3, 3, 5], dtype="<f4"),
        mesh_world64=None,
        source_heights_f64=np.asarray([3, 3, 5], dtype=np.float64),
        gate_reports={},
    )
    query = np.asarray([[-140.5, -94.5]], dtype=np.float64)
    sampled = sample_stored_triangle_surface(query, candidate)
    assert sampled.shape == (1,)
    assert sampled[0] == pytest.approx(4.5)
    assert candidate_fallback(True, False) == {
        "candidateUsed": False,
        "surface": "unchanged-source",
        "notice": "experimental candidate unavailable; unchanged source surface is active",
    }


def test_section_gate_uses_stored_mesh_and_rejects_mesh_slope_recipe_misses() -> None:
    frame = Float32LocalFrame()
    x_values = np.arange(139.0, 156.0001, 0.25)
    z_values = np.arange(-4.0, 4.0001, 0.25)
    world_x, world_z = np.meshgrid(x_values, z_values)
    world = np.column_stack((world_x.ravel(), (0.06 * world_z).ravel(), world_z.ravel()))
    local = frame.store_xyz(world)
    world_decoded = frame.decode_xyz_to_world64(local)
    width, height = len(x_values), len(z_values)
    faces = []
    for row in range(height - 1):
        for column in range(width - 1):
            lower = row * width + column
            upper = lower + width
            faces.extend(((lower, lower + 1, upper), (lower + 1, upper + 1, upper)))
    candidate = StoredCandidate(
        frame,
        local,
        np.asarray(faces, dtype="<u4"),
        world_decoded,
        local[:, 1].copy(),
        mesh_world64=None,
        source_heights_f64=np.zeros(len(local)),
        gate_reports={},
    )
    corridor = Corridor(
        inputs=None,
        part=[[0.0, 0.0], [200.0, 0.0]],
        stations=np.asarray([0.0, 200.0]),
        source_profile=np.zeros(2),
        graded_profile=np.zeros(2),
        influence=box(130.0, -10.0, 160.0, 10.0),
    )
    corridor.source = lambda points: np.zeros(len(points), dtype=np.float64)
    report = _section_gates_from_stored_mesh(corridor, candidate)
    assert 0.0 <= 5.0  # ideal flat recipe passes the cross-slope limit
    assert report["surface"] == "decoded local Float32 positions reconstructed to world Float64"
    assert report["maximumCrossSlopePercent"] == pytest.approx(6.0)
    assert report["passes"] is False


def test_known_global_collision_pair_samples_separately_in_stored_local_frame() -> None:
    frame = Float32LocalFrame()
    first_x = -164.2316811012587
    second_x = -164.23167542853238
    z = -85.5
    from torquay_pipeline.road_surface_topology import _float32_bytes

    assert _float32_bytes(first_x, z) == _float32_bytes(second_x, z)
    world_vertices = np.asarray(
        [
            [first_x, 1.0, z],
            [first_x - 3e-5, 1.0, z],
            [first_x, 1.0, z + 3e-5],
            [second_x, 3.0, z],
            [second_x + 3e-5, 3.0, z],
            [second_x, 3.0, z - 3e-5],
        ],
        dtype=np.float64,
    )
    stored = frame.store_xyz(world_vertices)
    decoded = frame.decode_xyz_to_world64(stored)
    candidate = StoredCandidate(
        frame,
        stored,
        np.asarray([[0, 1, 2], [3, 4, 5]], dtype="<u4"),
        decoded,
        stored[:, 1].copy(),
        mesh_world64=None,
        source_heights_f64=world_vertices[:, 1],
        gate_reports={},
    )
    queries = np.asarray(
        [
            np.mean(decoded[[0, 1, 2]][:, (0, 2)], axis=0),
            np.mean(decoded[[3, 4, 5]][:, (0, 2)], axis=0),
        ]
    )
    sampled = sample_stored_triangle_surface(queries, candidate)
    assert sampled == pytest.approx([1.0, 3.0])


def test_candidate_serialization_uses_xyz_order_and_reports_axis_errors() -> None:
    frame = Float32LocalFrame()
    construction_local_xz = np.asarray(
        [[24.123456789, 0.333333333], [-23.876543211, -0.666666667]],
        dtype=np.float64,
    )
    candidate_y = np.asarray([7.123456789, -1.234567891], dtype=np.float64)
    stored, decoded, construction_world_xz, report = _serialize_position_buffers(
        frame, construction_local_xz, candidate_y
    )
    expected_local = np.asarray(construction_local_xz, dtype="<f4")
    expected_world = np.column_stack(
        (
            frame.origin_xyz_m[0] + expected_local[:, 0].astype(np.float64),
            candidate_y.astype("<f4").astype(np.float64),
            frame.origin_xyz_m[2] + expected_local[:, 1].astype(np.float64),
        )
    )
    pre_serialization_world = np.column_stack(
        (construction_world_xz[:, 0], candidate_y, construction_world_xz[:, 1])
    )
    actual_delta = decoded - pre_serialization_world
    assert np.array_equal(stored[:, (0, 2)], expected_local)
    assert np.array_equal(decoded, expected_world)
    assert report["coordinateOrder"] == "X,Y,Z"
    assert report["maximumAbsoluteDisplacementByAxisM"] == pytest.approx(
        np.max(np.abs(actual_delta), axis=0).tolist()
    )
    assert report["maximumHorizontalDisplacementByAxisM"] == pytest.approx(
        np.max(np.abs(actual_delta[:, (0, 2)]), axis=0).tolist()
    )
    assert report["maximumVerticalDisplacementM"] == pytest.approx(
        float(np.max(np.abs(actual_delta[:, 1])))
    )
    assert report["maximumHorizontalDisplacementByAxisM"][0] > 0.0
    assert report["maximumVerticalDisplacementM"] > 0.0


def test_completed_gate_survives_later_typed_failure(tmp_path) -> None:
    from torquay_pipeline.teignmouth_float32_candidate import GATE_NAMES

    initial = {name: {"passes": False, "status": "NOT_EVALUATED"} for name in GATE_NAMES}
    (tmp_path / "gate-state.json").write_text(json.dumps(initial), encoding="utf-8")
    _write_gate(
        tmp_path,
        "storedLocalTopology",
        {"passes": True, "status": "MEASURED", "vertexCount": 3},
    )
    _write_failure(tmp_path, RuntimeError("synthetic later-stage error"))
    state = json.loads((tmp_path / "gate-state.json").read_text(encoding="utf-8"))
    failure = json.loads((tmp_path / "candidate-failure.json").read_text(encoding="utf-8"))
    assert state["storedLocalTopology"]["passes"] is True
    assert state["actualFloat32Sections"]["status"] == "UNAVAILABLE_AFTER_FAILURE"
    assert failure == {
        "errorType": "RuntimeError",
        "errorMessage": "synthetic later-stage error",
    }


def test_runner_limit_and_failed_output_archive_are_bounded(tmp_path) -> None:
    runner_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "build_teignmouth_float32_candidate.py"
    )
    spec = importlib.util.spec_from_file_location("float32_candidate_runner_test", runner_path)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runner
    sys.path.insert(0, str(runner_path.parent))
    spec.loader.exec_module(runner)
    assert runner.MAX_BUILD_SECONDS == 180.0
    with pytest.raises(SystemExit) as direct_worker:
        runner.main(["--worker-internal"])
    assert direct_worker.value.code == 2
    output = tmp_path / "generated"
    evidence = tmp_path / "correction-1-build-1"
    output.mkdir()
    evidence.mkdir()
    marker = output / "partial.bin"
    marker.write_bytes(b"preserve")
    archived = runner._archive_partial_output(output, evidence)
    assert archived == str(evidence / "partial-candidate-output")
    assert not output.exists()
    assert (Path(archived) / marker.name).read_bytes() == b"preserve"


def test_worker_logical_and_handled_launch_failures_exit_nonzero(tmp_path) -> None:
    runner_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "build_teignmouth_float32_candidate.py"
    )
    spec = importlib.util.spec_from_file_location("float32_candidate_worker_exit_test", runner_path)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runner
    sys.path.insert(0, str(runner_path.parent))
    spec.loader.exec_module(runner)
    logical = subprocess.run(
        [
            sys.executable,
            "-c",
            "import runpy,sys; runpy.run_path(sys.argv[1])['_propagate_worker_result'](2)",
            str(runner_path),
        ],
        cwd=runner_path.parents[1],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert logical.returncode == 2
    assert runner._select_runner_exit("BLOCKED_EXCEPTION", False, True, 2, 2) == 2
    assert runner._select_runner_exit("PASS", False, True, 0, 0) == 0

    evidence = tmp_path / "worker-launch-evidence"
    evidence.mkdir()
    handled = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import runpy,sys; from pathlib import Path; "
                "runpy.run_path(sys.argv[1])['_worker_entry']("
                "Path(sys.argv[2]),Path(sys.argv[3]),{},{},1)"
            ),
            str(runner_path),
            str(tmp_path / "unused-output"),
            str(evidence),
        ],
        cwd=runner_path.parents[1],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert handled.returncode == 2
    result = json.loads((evidence / "worker-process-result.json").read_text(encoding="utf-8"))
    report = json.loads((evidence / "build-report.json").read_text(encoding="utf-8"))
    assert result["logicalWorkerReturnCode"] == 2
    assert report["candidateEligibleForServing"] is False


def _synthetic_support_corridor() -> Corridor:
    return Corridor(
        inputs=None,
        part=[[0.0, 0.0], [200.0, 0.0]],
        stations=np.asarray([0.0, 200.0]),
        source_profile=np.zeros(2),
        graded_profile=np.full(2, 6.0),
        influence=box(-100.0, -100.0, 300.0, 100.0),
    )


def test_chart_support_is_complete_and_corruption_fails() -> None:
    corridor = _synthetic_support_corridor()
    chart = make_chart(corridor.part)
    report, support = validate_chart_support(corridor, chart)
    assert report["passes"] is True
    assert report["stationRangeM"] == [108.0, 187.0]
    assert report["lateralRangeM"] == [-16.0, 16.0]
    assert support.is_valid
    assert required_treatment_support_report(corridor, chart, support)["passes"] is True

    chart.triangles = chart.triangles[:-1].copy()
    corrupted, _ = validate_chart_support(corridor, chart)
    assert corrupted["passes"] is False
    assert "triangle ownership" in " ".join(corrupted["reasons"])


def test_broad_influence_outside_chart_support_uses_source_height() -> None:
    corridor = _synthetic_support_corridor()
    chart = make_chart(corridor.part)
    report, support = validate_chart_support(corridor, chart)
    assert report["passes"] is True
    point = np.asarray([100.0, 25.0])
    kind, field = classify_treatment_support(point, corridor.influence, support, chart)
    assert kind == "SOURCE_INSIDE_INFLUENCE_OUTSIDE_CHART_SUPPORT"
    assert field is None
    source_height = 42.0
    candidate_height = (
        source_height if kind != "CHART_OWNED" else field_height(corridor, source_height, *field)
    )
    assert candidate_height == source_height


def test_missing_chart_owner_and_required_target_support_fail(monkeypatch) -> None:
    corridor = _synthetic_support_corridor()
    chart = make_chart(corridor.part)
    report, support = validate_chart_support(corridor, chart)
    assert report["passes"] is True
    monkeypatch.setattr(chart, "locate", lambda _point: None)
    with pytest.raises(Float32CandidateError, match="no triangle owner"):
        classify_treatment_support(np.asarray([140.0, 0.0]), corridor.influence, support, chart)
    required = required_treatment_support_report(corridor, chart, box(100.0, -1.0, 110.0, 1.0))
    assert required["passes"] is False
    assert required["missingCount"] > 0


def test_treatment_is_zero_at_frozen_chart_edges_and_active_just_inside() -> None:
    corridor = _synthetic_support_corridor()
    for station in (108.0, 187.0):
        for lateral in (-16.0, 16.0):
            assert field_height(corridor, 0.0, station, lateral) == pytest.approx(0.0)
    assert field_height(corridor, 0.0, 140.0, 16.0) == pytest.approx(0.0)
    assert field_height(corridor, 0.0, 140.0, 15.99) > 0.0
    assert field_height(corridor, 0.0, 108.01, 0.0) > 0.0
    assert field_height(corridor, 0.0, 186.99, 0.0) > 0.0


def _saved_overlay_face_fixture() -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / "teignmouth_overlay_face_19669.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_saved_face_retains_both_sub_tolerance_fragments_and_nonzero_extrema() -> None:
    fixture = _saved_overlay_face_fixture()
    face_xz = np.asarray(fixture["coordinatesXZ"], dtype=np.float64)
    candidate_y = np.asarray(fixture["candidateHeightsY"], dtype=np.float64)
    triangles = [item["coordinatesXZ"] for item in fixture["sourceTriangles"]]
    source_y = [item["heightsY"] for item in fixture["sourceTriangles"]]
    source_ids = [item["sourceTriangleId"] for item in fixture["sourceTriangles"]]
    face = Polygon(face_xz)
    clip = from_wkt(fixture["clipWkt"])
    production_fragments = [
        face.intersection(Polygon(triangle)).intersection(clip) for triangle in triangles
    ]
    fragment_areas = [float(fragment.area) for fragment in production_fragments]
    assert fixture["areaToleranceM2"] == 1e-12
    assert len(fragment_areas) == 2
    assert all(0.0 < area <= 1e-12 for area in fragment_areas)
    covered_area = math.fsum(fragment_areas)
    assert covered_area > 1e-12  # The old per-fragment filter discarded all coverage.
    assert abs(covered_area - fixture["expectedClipAreaM2"]) <= fixture["areaToleranceM2"]
    expected_clip = from_wkt(fixture["expectedOutsideClip"]["wkt"])
    assert (
        face.intersection(clip).symmetric_difference(expected_clip).area
        <= fixture["areaToleranceM2"]
    )
    source = SourceOverlapIndex.create(triangles, source_ids, source_y, partition_verified=True)
    mesh = PlanarMesh(
        face_xz,
        np.asarray([[0, 1, 2]], dtype="<u4"),
        (),
        (),
    )
    report = _candidate_affine_surface_overlay_extrema(
        mesh,
        candidate_y,
        source,
        clip_geometry=clip,
        area_tolerance_m2=fixture["areaToleranceM2"],
    )
    assert report["emptyAssessedRegion"] is False
    assert report["overlayFaceCount"] == 1
    assert report["positiveFragmentCount"] == 2
    assert report["coveredAreaM2"] == covered_area
    assert (
        abs(report["assessedAreaM2"] - fixture["expectedClipAreaM2"]) <= fixture["areaToleranceM2"]
    )
    assert abs(report["coveredAreaM2"] - report["assessedAreaM2"]) <= fixture["areaToleranceM2"]
    assert report["testedIntersectionVertexCount"] == fixture["expectedPlaneWitnessCount"]
    assert report["maximumAbsoluteChangeFromSourceM"] > 0.0
    assert report["minimumAbsoluteDifferenceWitness"]["absoluteDifferenceM"] == pytest.approx(
        fixture["expectedAbsolutePlaneDifferenceRangeM"][0], abs=1e-12
    )
    assert report["maximumAbsoluteDifferenceWitness"]["absoluteDifferenceM"] == pytest.approx(
        fixture["expectedAbsolutePlaneDifferenceRangeM"][1], abs=1e-12
    )
    for key in ("minimumAbsoluteDifferenceWitness", "maximumAbsoluteDifferenceWitness"):
        witness = report[key]
        source_at = source_ids.index(witness["sourceTriangleId"])
        assert tuple(witness["localXZ"]) in production_fragments[source_at].exterior.coords
    assert report["pairwiseSourceOverlapAreaM2"] == 0.0
    assert abs(report["summedAreaMinusUnionResidualM2"]) <= fixture["areaToleranceM2"]
    assert (
        report["clipOperationOrder"]
        == "face.intersection(source_triangle).intersection(clip_geometry)"
    )


def test_saved_face_clipping_association_sensitivity_stays_within_tolerance() -> None:
    fixture = _saved_overlay_face_fixture()
    face = Polygon(fixture["coordinatesXZ"])
    clip = from_wkt(fixture["clipWkt"])
    source_triangles = [Polygon(item["coordinatesXZ"]) for item in fixture["sourceTriangles"]]
    production = [face.intersection(source).intersection(clip) for source in source_triangles]
    alternative = [face.intersection(clip).intersection(source) for source in source_triangles]
    production_union = union_all(production)
    alternative_union = union_all(alternative)
    symmetric_difference_area = float(production_union.symmetric_difference(alternative_union).area)
    union_area_difference = abs(float(production_union.area) - float(alternative_union.area))

    source_index = SourceOverlapIndex.create(
        [item["coordinatesXZ"] for item in fixture["sourceTriangles"]],
        [item["sourceTriangleId"] for item in fixture["sourceTriangles"]],
        [item["heightsY"] for item in fixture["sourceTriangles"]],
        partition_verified=True,
    )
    local_report = _candidate_affine_surface_overlay_extrema(
        PlanarMesh(
            np.asarray(fixture["coordinatesXZ"], dtype=np.float64),
            np.asarray([[0, 1, 2]], dtype="<u4"),
            (),
            (),
        ),
        np.asarray(fixture["candidateHeightsY"], dtype=np.float64),
        source_index,
        clip_geometry=clip,
        area_tolerance_m2=fixture["areaToleranceM2"],
    )
    assert union_area_difference <= fixture["areaToleranceM2"]
    assert symmetric_difference_area <= fixture["areaToleranceM2"]
    assert local_report["clipOperationOrder"] == (
        "face.intersection(source_triangle).intersection(clip_geometry)"
    )
    assert local_report["testedIntersectionVertexCount"] == fixture["expectedPlaneWitnessCount"]
    assert local_report["maximumAbsoluteChangeFromSourceM"] > 0.0


def test_local_overlay_ordinary_complete_coverage_reports_signed_extrema() -> None:
    triangle = np.asarray([[0.0, 0.0], [2.0, 0.0], [0.0, 2.0]])
    mesh = PlanarMesh(triangle, np.asarray([[0, 1, 2]], dtype="<u4"), (), ())
    source = SourceOverlapIndex.create([triangle], [42], [[1.0, 1.0, 1.0]], partition_verified=True)
    report = _candidate_affine_surface_overlay_extrema(mesh, np.asarray([2.0, 4.0, 6.0]), source)
    assert report["emptyAssessedRegion"] is False
    assert report["maximumFillFromSourceM"] == pytest.approx(5.0)
    assert report["maximumCutFromSourceM"] == pytest.approx(1.0)
    assert report["maximumAbsoluteChangeFromSourceM"] == pytest.approx(5.0)
    assert report["minimumSignedDifferenceWitness"]["sourceTriangleId"] == 42
    assert report["maximumAbsoluteDifferenceWitness"]["localXZ"] == pytest.approx([0.0, 2.0])
    assert report["coverageGapAreaM2"] == 0.0
    assert report["coverageExcessAreaM2"] == 0.0


def test_local_overlay_evaluates_hole_ring_vertices() -> None:
    triangle = np.asarray([[0.0, 0.0], [4.0, 0.0], [0.0, 4.0]])
    clip_with_hole = Polygon(
        triangle,
        holes=[[(0.5, 0.5), (1.0, 0.5), (0.5, 1.0), (0.5, 0.5)]],
    )
    mesh = PlanarMesh(triangle, np.asarray([[0, 1, 2]], dtype="<u4"), (), ())
    source = SourceOverlapIndex.create([triangle], [51], [[0.0, 0.0, 0.0]], partition_verified=True)
    report = _candidate_affine_surface_overlay_extrema(
        mesh, np.asarray([0.0, 2.0, 4.0]), source, clip_geometry=clip_with_hole
    )
    assert report["testedIntersectionVertexCount"] == 6
    assert report["minimumSignedDifferenceWitness"]["localXZ"] == pytest.approx([0.0, 0.0])
    assert report["maximumSignedDifferenceWitness"]["localXZ"] == pytest.approx([0.0, 4.0])


def test_local_overlay_empty_clip_and_zero_area_contact_are_explicit() -> None:
    triangle = np.asarray([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    mesh = PlanarMesh(triangle, np.asarray([[0, 1, 2]], dtype="<u4"), (), ())
    source = SourceOverlapIndex.create([triangle], [7], [[0.0, 0.0, 0.0]], partition_verified=True)
    heights = np.zeros(3, dtype=np.float64)
    empty = _candidate_affine_surface_overlay_extrema(
        mesh, heights, source, clip_geometry=Polygon()
    )
    contact = _candidate_affine_surface_overlay_extrema(
        mesh, heights, source, clip_geometry=box(1.0, 0.0, 2.0, 1.0)
    )
    assert empty["emptyAssessedRegion"] is True
    assert empty["maximumAbsoluteChangeFromSourceM"] is None
    assert empty["testedIntersectionVertexCount"] == 0
    assert contact["emptyAssessedRegion"] is True
    assert contact["zeroAreaContactCount"] > 0
    assert contact["maximumFillFromSourceM"] is None


def test_local_overlay_empty_face_is_skipped_but_positive_face_is_measured() -> None:
    points = np.asarray([[0, 0], [1, 0], [0, 1], [2, 0], [3, 0], [2, 1]], dtype=np.float64)
    faces = np.asarray([[0, 1, 2], [3, 4, 5]], dtype="<u4")
    first = points[[0, 1, 2]]
    second = points[[3, 4, 5]]
    source = SourceOverlapIndex.create(
        [first, second], [10, 20], [[0, 0, 0], [0, 0, 0]], partition_verified=True
    )
    report = _candidate_affine_surface_overlay_extrema(
        PlanarMesh(points, faces, (), ()),
        np.zeros(len(points), dtype=np.float64),
        source,
        clip_geometry=box(-0.1, -0.1, 1.1, 1.1),
    )
    assert report["emptyAssessedRegion"] is False
    assert report["emptyAssessedFaceCount"] == 1
    assert report["overlayFaceCount"] == 1
    assert report["testedIntersectionVertexCount"] == 3


def test_local_overlay_positive_expected_region_without_coverage_fails() -> None:
    face = np.asarray([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    source_triangle = np.asarray([[2.0, 2.0], [3.0, 2.0], [2.0, 3.0]])
    source = SourceOverlapIndex.create(
        [source_triangle], [99], [[0.0, 0.0, 0.0]], partition_verified=True
    )
    with pytest.raises(
        TopologyError,
        match="positive assessed region has no positive-area source coverage",
    ):
        _candidate_affine_surface_overlay_extrema(
            PlanarMesh(face, np.asarray([[0, 1, 2]], dtype="<u4"), (), ()),
            np.zeros(3),
            source,
        )


def test_local_overlay_rejects_partial_gap_without_overlap_for_verified_partition() -> None:
    face = np.asarray([[0.0, 0.0], [2.0, 0.0], [0.0, 2.0]])
    half = np.asarray([[0.0, 0.0], [2.0, 0.0], [0.0, 1.0]])
    source = SourceOverlapIndex.create([half], [100], [[0, 0, 0]], partition_verified=True)
    with pytest.raises(
        TopologyError,
        match="source overlay coverage or positive-area source overlap failed",
    ) as error:
        _candidate_affine_surface_overlay_extrema(
            PlanarMesh(face, np.asarray([[0, 1, 2]], dtype="<u4"), (), ()),
            np.zeros(3),
            source,
        )
    details = json.loads(str(error.value).split("failed: ", 1)[1])
    assert details["partitionVerifiedHint"] is True
    assert details["expectedAreaM2"] == 2.0
    assert details["coveredAreaM2"] == 1.0
    assert details["gapAreaM2"] == 1.0
    assert from_wkt(details["gapWkt"]).equals(Polygon(face).difference(Polygon(half)))
    assert details["excessAreaM2"] == 0.0
    assert details["pairwiseSourceOverlapAreaM2"] == 0.0
    assert details["pairwiseSourceOverlaps"] == []


def test_local_overlay_rejects_real_overlap_without_gap_for_verified_partition() -> None:
    face = np.asarray([[0.0, 0.0], [2.0, 0.0], [0.0, 2.0]])
    half = np.asarray([[0.0, 0.0], [2.0, 0.0], [0.0, 1.0]])
    source = SourceOverlapIndex.create(
        [face, half], [100, 101], [[0, 0, 0], [0, 0, 0]], partition_verified=True
    )
    with pytest.raises(
        TopologyError,
        match="source overlay coverage or positive-area source overlap failed",
    ) as error:
        _candidate_affine_surface_overlay_extrema(
            PlanarMesh(face, np.asarray([[0, 1, 2]], dtype="<u4"), (), ()),
            np.zeros(3),
            source,
        )
    details = json.loads(str(error.value).split("failed: ", 1)[1])
    assert details["partitionVerifiedHint"] is True
    assert details["expectedAreaM2"] == 2.0
    assert details["coveredAreaM2"] == 3.0
    assert details["gapAreaM2"] == 0.0
    assert from_wkt(details["gapWkt"]).is_empty
    assert details["excessAreaM2"] == 0.0
    assert details["pairwiseSourceOverlapAreaM2"] == 1.0
    assert len(details["pairwiseSourceOverlaps"]) == 1
    overlap = details["pairwiseSourceOverlaps"][0]
    assert overlap["sourceTriangleIds"] == [100, 101]
    assert overlap["areaM2"] == 1.0
    assert from_wkt(overlap["wkt"]).equals(Polygon(half))


def test_local_overlay_rejects_equal_gap_and_real_overlap_even_for_verified_partition() -> None:
    face = np.asarray([[0.0, 0.0], [2.0, 0.0], [0.0, 2.0]])
    half = np.asarray([[0.0, 0.0], [2.0, 0.0], [0.0, 1.0]])
    source = SourceOverlapIndex.create(
        [half, half], [100, 101], [[0, 0, 0], [0, 0, 0]], partition_verified=True
    )
    with pytest.raises(
        TopologyError,
        match="source overlay coverage or positive-area source overlap failed",
    ) as error:
        _candidate_affine_surface_overlay_extrema(
            PlanarMesh(face, np.asarray([[0, 1, 2]], dtype="<u4"), (), ()),
            np.zeros(3),
            source,
        )
    assert '"gapAreaM2": 1.0' in str(error.value)
    assert '"pairwiseSourceOverlapAreaM2": 1.0' in str(error.value)
    assert '"sourceTriangleIds": [100, 101]' in str(error.value)


def test_candidate_uses_prototype_local_overlay_for_all_three_assessments() -> None:
    source = (
        Path(__file__).parents[1] / "torquay_pipeline" / "teignmouth_float32_candidate.py"
    ).read_text(encoding="utf-8")
    assert source.count("affine_surface_overlay_extrema(") == 4
    assert source.count("_candidate_affine_surface_overlay_extrema(") == 4
