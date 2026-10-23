"""Synthetic controls for the bounded road-surface display treatment."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
import pytest

from torquay_pipeline.road_surface import (
    PreviewConfig,
    ReleaseInputs,
    RoadSegment,
    RoadSurfaceError,
    _active_triangle_vertex_weights,
    _apply_harm_fallback,
    _apply_station_harm_fallback,
    _canonical_json,
    _carriageway_triangle_owners,
    _fallback_distance_weights,
    _grade_grid,
    _preflight_execution_record,
    _prepare_output_directory,
    _project_grid_edge_constraints,
    _road_part_topology,
    _sample_grid,
    _segments_from_payload,
    _severe_station_crossfall_constraints,
    _teignmouth_section_metrics,
    _teignmouth_section_samples,
    _terrain_gradient_change_summary,
    _topology_node_distances,
    _topology_station_distances,
    _transition_for_station,
    guard_output_directory,
    load_config,
)


def _config(**overrides: float) -> PreviewConfig:
    values: dict[str, float | str] = {
        "release_id": "a" * 64,
        "output_directory": "public/worlds/torquay-road-surface-preview",
        "transition_distance_factor": 1.0,
        "ambiguity_distance_m": 2.0,
        "ambiguity_height_difference_m": 1.0,
        "maximum_changed_height_m": 10.0,
        "fallback_absolute_change_m": 5.0,
        "fallback_added_gradient_m_per_m": 1.0,
        "fallback_minimum_region_area_m2": 8.0,
        "fallback_fade_distance_m": 8.0,
    }
    values.update(overrides)
    return PreviewConfig(**values)  # type: ignore[arg-type]


def _feature(way_id: int, parts: list[list[list[float]]], width: float = 2.0) -> dict:
    return {
        "id": f"way/{way_id}",
        "displayGroup": "vehicular",
        "groundAssumption": "ground_assumed_from_absent_or_explicit_no_vertical_tags",
        "estimatedWidthM": width,
        "source": {"osmId": way_id},
        "sourceTags": {"name": f"Test road {way_id}"},
        "centerlinePartsXZ": parts,
    }


def _road(way_id: int, points: list[list[float]], width: float = 2.0) -> dict:
    return _feature(way_id, [points], width)


def _grid() -> np.ndarray:
    return np.zeros((11, 11), dtype="<f4")


def _grade(baseline: np.ndarray, features: list[dict], config: PreviewConfig | None = None):
    segments = _segments_from_payload({"features": features}, 1.0, 1.0)
    return _grade_grid(baseline, segments, 1.0, 10.0, 10.0, config or _config())


def test_connected_part_harm_uses_shared_endpoint_retention_weights() -> None:
    segments = _segments_from_payload(
        {
            "features": [
                _road(100, [[0.0, 0.0], [10.0, 0.0]]),
                _road(101, [[10.0, 0.0], [20.0, 0.0]]),
                _road(102, [[20.0, 0.0], [30.0, 0.0]]),
                _road(103, [[30.2, 0.0], [40.2, 0.0]]),
            ]
        },
        1.0,
        1.0,
    )
    topology = _road_part_topology(segments)
    seeds = {(100, 0): [(9.0, 10.0)]}
    node_distances = _topology_node_distances(topology, seeds)

    first_end = _topology_station_distances(
        topology, node_distances, (100, 0), np.asarray([10.0]), seeds
    )[0]
    second_start = _topology_station_distances(
        topology, node_distances, (101, 0), np.asarray([0.0]), seeds
    )[0]
    second_end = _topology_station_distances(
        topology, node_distances, (101, 0), np.asarray([10.0]), seeds
    )[0]
    third_start = _topology_station_distances(
        topology, node_distances, (102, 0), np.asarray([0.0]), seeds
    )[0]
    third_interior = _topology_station_distances(
        topology, node_distances, (102, 0), np.asarray([5.0]), seeds
    )[0]
    disconnected_start = _topology_station_distances(
        topology, node_distances, (103, 0), np.asarray([0.0]), seeds
    )[0]

    assert first_end == second_start == pytest.approx(0.0)
    assert second_end == third_start == pytest.approx(10.0)
    assert third_interior == pytest.approx(15.0)
    assert math.isinf(disconnected_start)


def test_flat_surface_is_byte_identical_and_no_vertices_change() -> None:
    baseline = _grid()
    preview, report = _grade(baseline, [_road(10, [[-5.0, 0.0], [5.0, 0.0]])])

    assert preview.tobytes() == baseline.tobytes()
    assert report["changedVertexCount"] == 0
    assert report["verticesBeyondAllInfluenceRegionsExact"]


def test_longitudinal_hill_is_retained_while_lateral_slope_is_removed() -> None:
    x = np.linspace(-5.0, 5.0, 11, dtype=np.float32)
    z = np.linspace(-5.0, 5.0, 11, dtype=np.float32)
    baseline = np.asarray(0.1 * x[None, :] + 0.4 * z[:, None], dtype="<f4")
    preview, _ = _grade(baseline, [_road(10, [[-5.0, 0.0], [5.0, 0.0]])])

    # The centerline carries the original longitudinal profile; both road edges
    # now meet at that baseline centerline elevation.
    assert preview[5, :] == pytest.approx(baseline[5, :], abs=1e-6)
    assert preview[4, 2:9] == pytest.approx(baseline[5, 2:9], abs=1e-6)
    assert preview[6, 2:9] == pytest.approx(baseline[5, 2:9], abs=1e-6)
    assert np.diff(preview[5, :]) == pytest.approx(np.diff(baseline[5, :]), abs=1e-6)


def test_final_surface_projection_keeps_pinned_control_and_caps_added_edge_gradient() -> None:
    baseline = np.zeros((5, 5), dtype="<f4")
    candidate = baseline.copy()
    candidate[2, 2] = 4.0
    adjustable = np.ones_like(baseline, dtype=bool)
    pinned = np.zeros_like(adjustable)
    pinned[2, 2] = True

    projected, report = _project_grid_edge_constraints(
        baseline,
        candidate,
        1.0,
        adjustable,
        pinned,
        candidate,
    )

    assert projected[2, 2] == pytest.approx(4.0)
    assert np.max(np.abs(np.diff(projected.astype(np.float64), axis=0))) <= 0.9991
    assert np.max(np.abs(np.diff(projected.astype(np.float64), axis=1))) <= 0.9991
    assert np.max(np.abs(projected)) < 5.0
    assert report["maximumFloat32ConstraintResidualM"] <= 5e-5


def test_final_surface_projection_rejects_incompatible_pinned_controls() -> None:
    baseline = np.zeros((3, 3), dtype="<f4")
    candidate = baseline.copy()
    pinned = np.zeros_like(baseline, dtype=bool)
    pinned[1, 1] = pinned[1, 2] = True
    pinned_values = baseline.copy()
    pinned_values[1, 1] = 0.0
    pinned_values[1, 2] = 2.0

    with pytest.raises(RoadSurfaceError, match="pinned samples violate"):
        _project_grid_edge_constraints(
            baseline,
            candidate,
            1.0,
            np.ones_like(pinned),
            pinned,
            pinned_values,
        )


def test_final_surface_projection_enforces_sparse_lateral_crossfall_constraint() -> None:
    baseline = np.zeros((3, 3), dtype="<f4")
    candidate = baseline.copy()
    candidate.flat[0] = 1.0
    adjustable = np.ones_like(baseline, dtype=bool)
    pinned = np.zeros_like(adjustable)
    constraint = {
        "indices": np.asarray([0, 1], dtype=np.int64),
        "coefficients": np.asarray([1.0, -1.0], dtype=np.float64),
        "limitM": 0.5,
        "label": {
            "wayId": 30480989,
            "partIndex": 0,
            "stationM": 12.0,
            "direction": "right-minus-left",
        },
    }

    projected, report = _project_grid_edge_constraints(
        baseline,
        candidate,
        1.0,
        adjustable,
        pinned,
        baseline,
        linear_constraints=[constraint],
    )

    assert abs(float(projected.flat[0] - projected.flat[1])) <= 0.50005
    assert report["linearConstraintCount"] == 1
    assert report["maximumLinearConstraintViolationM"] <= 5e-5


def test_final_surface_projection_names_fixed_lateral_constraint_conflict() -> None:
    baseline = np.zeros((2, 2), dtype="<f4")
    pinned = np.ones_like(baseline, dtype=bool)
    pinned_values = baseline.copy()
    pinned_values.flat[0] = 0.9
    constraint = {
        "indices": np.asarray([0, 1], dtype=np.int64),
        "coefficients": np.asarray([1.0, -1.0], dtype=np.float64),
        "limitM": 0.5,
        "label": {
            "wayId": 30480989,
            "partIndex": 0,
            "stationM": 12.0,
            "direction": "right-minus-left",
        },
    }

    with pytest.raises(RoadSurfaceError, match='stationM":12.0.*wayId":30480989'):
        _project_grid_edge_constraints(
            baseline,
            baseline,
            1.0,
            np.ones_like(pinned),
            pinned,
            pinned_values,
            linear_constraints=[constraint],
        )


def test_renderer_triangle_weights_match_display_sampler() -> None:
    heights = np.arange(9, dtype="<f4").reshape((3, 3))

    for x, z in ((-0.25, -0.25), (0.25, 0.25)):
        weights = _active_triangle_vertex_weights(heights, x, z, 1.0)
        weighted = sum(float(heights.flat[index]) * weight for index, weight in weights)
        assert sum(weight for _index, weight in weights) == pytest.approx(1.0)
        assert weighted == pytest.approx(_sample_grid(heights, x, z, 1.0))


def test_severe_station_constraints_cover_all_required_sampled_stations() -> None:
    z_values = np.arange(-2.0, 3.0, dtype=np.float32)
    baseline = np.broadcast_to((0.2 * z_values[:, None]), (5, 5)).astype("<f4").copy()
    roads = {
        "features": [
            _road(way_id, [[-1.0, 0.0], [1.0, 0.0]], width=2.0)
            for way_id in (30480989, 78455388, 78455395)
        ]
    }
    inputs = ReleaseInputs(
        release_root=Path("unused"),
        release_id="a" * 64,
        ready_sha256="1" * 64,
        inventory_sha256="2" * 64,
        manifest={"heightfield": {"sha256": "3" * 64}},
        manifest_sha256="4" * 64,
        road_manifest={},
        road_manifest_sha256="5" * 64,
        road_payload=roads,
        road_payload_sha256="6" * 64,
        baseline=baseline,
        columns=5,
        rows=5,
        spacing_m=1.0,
        width_m=4.0,
        depth_m=4.0,
        origin_e_m=0.0,
        origin_n_m=0.0,
        origin_y_m=0.0,
        buildings={"buildings": []},
        source_hashes={},
    )

    constraints, report = _severe_station_crossfall_constraints(
        inputs, baseline, 1.0, {"regions": []}
    )

    assert report["stationCountsByWay"] == {
        "30480989": 3,
        "78455388": 3,
        "78455395": 3,
    }
    assert report["inequalityCount"] == 18
    assert all(
        item["label"]["baselineCrossfallPercent"] == pytest.approx(20.0)
        for item in constraints[::2]
    )
    assert all(
        item["label"]["maximumPreviewCrossfallPercent"] == pytest.approx(10.0)
        for item in constraints[::2]
    )
    assert {item["wayId"] for item in report["baselineWorstStations"]} == {
        30480989,
        78455388,
        78455395,
    }


def test_smoothstep_shoulder_returns_to_baseline_and_outer_vertices_are_exact() -> None:
    baseline = np.broadcast_to(
        np.linspace(-0.5, 0.5, 11, dtype=np.float32)[:, None], (11, 11)
    ).copy()
    preview, report = _grade(baseline, [_road(10, [[-5.0, 0.0], [5.0, 0.0]])])

    assert preview[5, 5] == pytest.approx(0.0, abs=1e-6)
    assert preview[4, 5] == pytest.approx(0.0, abs=1e-6)
    assert preview[3, 5] == pytest.approx(baseline[3, 5] * 0.5, abs=1e-6)
    assert preview[2, 5] == baseline[2, 5]
    assert preview[1, 5] == baseline[1, 5]
    assert report["verticesBeyondAllInfluenceRegionsExact"]


def test_expanded_shoulder_uses_the_full_32m_projection_support() -> None:
    coordinates = np.arange(-40.0, 41.0, dtype=np.float32)
    baseline = np.broadcast_to(0.1 * coordinates[:, None], (81, 81)).copy()
    segments = _segments_from_payload(
        {"features": [_road(10, [[-40.0, 0.0], [40.0, 0.0]], width=6.0)]},
        1.0,
        1.0,
    )
    preview, _report = _grade_grid(
        baseline,
        segments,
        1.0,
        80.0,
        80.0,
        _config(),
        {(10, 0): [(0.0, 80.0)]},
    )

    # At 20 m from the centerline the 32 m shoulder is still active and follows
    # the same smoothstep as its target. The previous influence-radius clip
    # returned the source value here, truncating the widened transition.
    distance = 20.0
    half_width = 3.0
    transition = 32.0
    position = (distance - half_width) / transition
    weight = 1.0 - (3 * position**2 - 2 * position**3)
    row_at_20m = int(distance + 40)
    assert preview[row_at_20m, 40] == pytest.approx(
        baseline[row_at_20m, 40] * (1.0 - weight), abs=1e-6
    )
    # The transition reaches unchanged source ground exactly at the 32 m cap.
    row_at_35m = int(half_width + transition + 40)
    assert preview[row_at_35m, 40] == baseline[row_at_35m, 40]


def test_gradient_change_reports_new_slope_increases_separately_from_removed_slopes() -> None:
    baseline = np.zeros((3, 3), dtype="<f4")
    preview = baseline.copy()
    preview[1:, 2] = 2.0

    report = _terrain_gradient_change_summary(baseline, preview, 1.0, 2.0, 2.0)

    assert report["maximumPositiveIncreaseMPerM"] == pytest.approx(2.0)
    assert report["maximumPositiveIncreaseEdge"]["baselineMagnitudeMPerM"] == pytest.approx(0.0)
    assert report["maximumPositiveIncreaseEdge"]["previewMagnitudeMPerM"] == pytest.approx(2.0)
    regions = report["significantPositiveIncreaseRegions"]
    assert report["significantIncreaseThresholdMPerM"] == pytest.approx(1.0)
    assert len(regions) == 1
    assert regions[0]["edgeCount"] == 3
    assert regions[0]["maximumEdge"]["previewMagnitudeMPerM"] == pytest.approx(2.0)


def test_ambiguous_parallel_roads_keep_original_ground_without_averaging() -> None:
    values = np.broadcast_to(
        2.0 * np.linspace(-5.0, 5.0, 11, dtype=np.float32)[:, None], (11, 11)
    ).copy()
    features = [
        _road(11, [[-5.0, -1.0], [5.0, -1.0]]),
        _road(12, [[-5.0, 1.0], [5.0, 1.0]]),
    ]

    preview, report = _grade(values, features)

    assert preview[5, 5] == values[5, 5]
    assert report["ambiguousGridVertexCountRetainedAtOriginalGround"] > 0
    assert report["ambiguousConnectedRegions"]
    assert all(
        region["effect"].startswith("retain original")
        for region in report["ambiguousConnectedRegions"]
    )


def test_every_vertex_in_an_intersected_carriageway_triangle_keeps_core_ownership() -> None:
    baseline = np.zeros((11, 11), dtype="<f4")
    segments = _segments_from_payload(
        {"features": [_road(40, [[-4.0, -1.0], [4.0, 1.0]], width=2.0)]}, 1.0, 1.0
    )

    owners, is_core, _conflicts = _carriageway_triangle_owners(
        baseline, segments, 1.0, 10.0, 10.0, 1.0
    )

    supported = owners >= 0
    assert supported.any()
    assert np.all(is_core[supported])
    # The oblique ribbon intersects triangles that contain vertices outside its
    # half-width; those vertices still participate in renderer sampling.
    outside_half_width = False
    for row, column in np.argwhere(supported):
        segment = segments[int(owners[row, column])]
        x, z = float(column - 5), float(row - 5)
        amount = np.clip(
            ((x - segment.first_x) * segment.dx + (z - segment.first_z) * segment.dz)
            / segment.length_squared,
            0.0,
            1.0,
        )
        distance = math.hypot(
            x - (segment.first_x + amount * segment.dx),
            z - (segment.first_z + amount * segment.dz),
        )
        outside_half_width |= distance > segment.width_m / 2 + 1e-9
    assert outside_half_width


def test_chained_adjacent_core_conflicts_use_only_snapshot_segment_owners() -> None:
    def narrow_road(way_id: int, z: float) -> dict:
        feature = _road(way_id, [[-5.0, z], [5.0, z]], width=0.2)
        return feature

    baseline = np.broadcast_to(
        (np.arange(13, dtype=np.float32) - 6.0)[:, None] * 2.0, (13, 13)
    ).copy()
    segments = _segments_from_payload(
        {"features": [narrow_road(101, -2.0), narrow_road(102, 0.0), narrow_road(103, 2.0)]},
        1.0,
        1.0,
    )

    _owners, _is_core, conflicts = _carriageway_triangle_owners(
        baseline, segments, 1.0, 12.0, 12.0, 1.0
    )

    way_pairs = {tuple(item["ways"]) for item in conflicts}
    assert (101, 102) in way_pairs
    assert (102, 103) in way_pairs
    assert way_pairs <= {(101, 102), (102, 103)}
    for item in conflicts:
        for way_id, segment_index in item["segmentByWay"].items():
            assert segment_index >= 0
            assert segments[segment_index].way_id == way_id


@pytest.mark.parametrize(
    "features",
    [
        [
            _road(20, [[-5.0, 0.0], [5.0, 0.0]]),
            _road(21, [[0.0, -5.0], [0.0, 5.0]]),
        ],
        [_road(22, [[-5.0, -2.0], [0.0, 0.0], [5.0, -2.0]])],
        [_road(23, [[-5.0, -5.0], [-5.0, 5.0]])],
    ],
)
def test_junction_curved_and_aoi_edge_cases_are_finite_and_deterministic(
    features: list[dict],
) -> None:
    baseline = np.asarray(
        np.linspace(-1.0, 1.0, 11, dtype=np.float32)[:, None]
        + np.linspace(-1.0, 1.0, 11, dtype=np.float32)[None, :],
        dtype="<f4",
    )
    first, first_report = _grade(baseline, features)
    second, second_report = _grade(baseline, features)

    assert np.isfinite(first).all()
    assert first.tobytes() == second.tobytes()
    assert _canonical_json(first_report) == _canonical_json(second_report)
    assert (
        hashlib.sha256(first.tobytes()).hexdigest() == hashlib.sha256(second.tobytes()).hexdigest()
    )


def test_segment_selection_excludes_non_ground_and_non_vehicular_features() -> None:
    road = _road(30, [[-5.0, 0.0], [5.0, 0.0]])
    bridge = {**_road(31, [[-5.0, 1.0], [5.0, 1.0]]), "groundAssumption": "bridge"}
    path = {**_road(32, [[-5.0, 2.0], [5.0, 2.0]]), "displayGroup": "path"}

    segments = _segments_from_payload({"features": [road, bridge, path]}, 1.0, 1.0)

    assert {segment.way_id for segment in segments} == {30}


def test_output_guard_accepts_only_exact_owned_directory_and_rejects_overlap(tmp_path) -> None:
    worlds = tmp_path / "public/worlds"
    worlds.mkdir(parents=True)
    output = worlds / "torquay-road-surface-preview"
    accepted = guard_output_directory(tmp_path, output, [worlds / "torquay-poc-001-2km"])
    assert accepted == output
    candidate = worlds / "torquay-road-surface-teignmouth-candidate"
    assert guard_output_directory(tmp_path, candidate, [output]) == candidate

    with pytest.raises(RoadSurfaceError, match="exactly"):
        guard_output_directory(tmp_path, worlds / "torquay-poc-001-2km", [])
    with pytest.raises(RoadSurfaceError, match="exact allowlisted"):
        guard_output_directory(
            tmp_path, worlds / "torquay-road-surface-teignmouth-candidate-copy", []
        )
    with pytest.raises(RoadSurfaceError, match="overlaps protected"):
        guard_output_directory(tmp_path, output, [worlds])

    output.mkdir()
    (output / "unowned-backup.json").write_text("keep", encoding="utf-8")
    with pytest.raises(RoadSurfaceError, match="unowned or unsafe"):
        guard_output_directory(tmp_path, output, [])


def test_absent_output_directory_is_created_after_guard_and_repeated_prepare_is_safe(
    tmp_path,
) -> None:
    worlds = tmp_path / "public/worlds"
    worlds.mkdir(parents=True)
    output = worlds / "torquay-road-surface-preview"

    prepared = _prepare_output_directory(tmp_path, output, [worlds / "source"])
    assert prepared == output
    assert output.is_dir()
    marker = output / "manifest.json"
    marker.write_bytes(b"owned derivative marker")
    before = marker.read_bytes()

    assert _prepare_output_directory(tmp_path, output, [worlds / "source"]) == output
    assert marker.read_bytes() == before
    backup = output / "unrelated-backup.bin"
    backup.write_bytes(b"preserve me")
    with pytest.raises(RoadSurfaceError, match="unowned or unsafe"):
        _prepare_output_directory(tmp_path, output, [])
    assert backup.read_bytes() == b"preserve me"

    candidate_output = worlds / "torquay-road-surface-teignmouth-candidate"
    candidate_prepared = _prepare_output_directory(
        tmp_path, candidate_output, [output, worlds / "source"]
    )
    assert candidate_prepared == candidate_output
    assert candidate_output.is_dir()


def test_builder_creates_absent_approved_output_then_repeats_deterministically(
    tmp_path, monkeypatch
) -> None:
    import torquay_pipeline.road_surface as road_surface

    project_root = tmp_path
    (project_root / "public/worlds").mkdir(parents=True)
    (project_root / "docs/milestones/artifacts/Road-surface-treatment").mkdir(parents=True)
    baseline = np.zeros((3, 3), dtype="<f4")
    baseline_hash = hashlib.sha256(baseline.tobytes()).hexdigest()
    inputs = ReleaseInputs(
        release_root=project_root / "unused-release",
        release_id="a" * 64,
        ready_sha256="1" * 64,
        inventory_sha256="2" * 64,
        manifest={"heightfield": {"sha256": baseline_hash}},
        manifest_sha256="3" * 64,
        road_manifest={},
        road_manifest_sha256="4" * 64,
        road_payload={"features": []},
        road_payload_sha256="5" * 64,
        baseline=baseline,
        columns=3,
        rows=3,
        spacing_m=1.0,
        width_m=2.0,
        depth_m=2.0,
        origin_e_m=0.0,
        origin_n_m=0.0,
        origin_y_m=0.0,
        buildings={"buildings": []},
        source_hashes={"ready.json": {"readySha256": "1" * 64}},
    )
    monkeypatch.setattr(road_surface, "load_release_inputs", lambda *_args: inputs)
    monkeypatch.setattr(
        road_surface,
        "_segments_from_payload",
        lambda *_args: [RoadSegment(("way/1", 0, 0), 1, "road", 2.0, -1, 0, 2, 0, 4, 3)],
    )
    monkeypatch.setattr(
        road_surface,
        "_grade_grid",
        lambda *_args, **_kwargs: (
            baseline.copy(),
            {
                "changedVertexCount": 0,
                "ambiguousGridVertexCountRetainedAtOriginalGround": 0,
                "harmFallback": {"regions": []},
            },
        ),
    )
    monkeypatch.setattr(road_surface, "_source_raster_paths", lambda *_args: ([], []))
    monkeypatch.setattr(road_surface, "_profiles", lambda *_args: [])
    monkeypatch.setattr(
        road_surface,
        "_building_base_report",
        lambda *_args: {"individualChangesM": []},
    )
    monkeypatch.setattr(road_surface, "_browser_contexts", lambda *_args: [])
    monkeypatch.setattr(road_surface, "_map_contexts", lambda *_args: [])
    monkeypatch.setattr(
        road_surface,
        "_registered_terrain_sections",
        lambda *_args: {"sections": [], "footings": []},
    )

    output = project_root / "public/worlds/torquay-road-surface-preview"
    record = project_root / "docs/milestones/artifacts/Road-surface-treatment/build-10.json"
    first = road_surface.build_preview(project_root, _config(), record)
    assert output.is_dir()
    assert record.is_file()
    first_bytes = {path.name: path.read_bytes() for path in output.iterdir()}
    second = road_surface.build_preview(project_root, _config())
    second_bytes = {path.name: path.read_bytes() for path in output.iterdir()}
    assert first["outputHashes"] == second["outputHashes"]
    assert first_bytes == second_bytes


def test_teignmouth_config_is_bound_to_its_exact_candidate_output(tmp_path: Path) -> None:
    import json

    project_root = Path(__file__).resolve().parents[2]
    accepted = load_config(project_root / "config/road-surface-preview.json")
    candidate_path = project_root / "config/road-surface-teignmouth-candidate.json"
    candidate = load_config(candidate_path)
    assert accepted.treatment_variant == "accepted-preview"
    assert accepted.output_directory == "public/worlds/torquay-road-surface-preview"
    assert candidate.treatment_variant == "teignmouth-circled-segment"
    assert candidate.output_directory == "public/worlds/torquay-road-surface-teignmouth-candidate"

    raw = json.loads(candidate_path.read_text(encoding="utf-8"))
    raw["output_directory"] = "public/worlds/torquay-road-surface-preview"
    invalid = tmp_path / "invalid-teignmouth-config.json"
    invalid.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(RoadSurfaceError, match="exact pinned output policy"):
        load_config(invalid)


def test_teignmouth_registered_full_width_constraints_include_source_vertices_and_anchor() -> None:
    baseline = np.zeros((301, 301), dtype="<f4")
    z = np.arange(301, dtype=np.float32) * 2.0 - 300.0
    baseline[:] = (z[:, None] * 0.6).astype("<f4")
    inputs = ReleaseInputs(
        release_root=Path("unused"),
        release_id="a" * 64,
        ready_sha256="1" * 64,
        inventory_sha256="2" * 64,
        manifest={},
        manifest_sha256="3" * 64,
        road_manifest={},
        road_manifest_sha256="4" * 64,
        road_payload={
            "features": [
                {
                    "source": {"osmId": 78455395},
                    "estimatedWidthM": 6.0,
                    "centerlinePartsXZ": [[[-200.0, 0.0], [-55.5, 0.0], [200.0, 0.0]]],
                }
            ]
        },
        road_payload_sha256="5" * 64,
        baseline=baseline,
        columns=301,
        rows=301,
        spacing_m=2.0,
        width_m=600.0,
        depth_m=600.0,
        origin_e_m=0.0,
        origin_n_m=0.0,
        origin_y_m=0.0,
        buildings={"buildings": []},
        source_hashes={},
    )

    constraints, report = _teignmouth_section_samples(inputs, baseline, 2.0)
    assert report["stationStartM"] == 140.0
    assert report["stationEndM"] == 155.0
    assert report["maximumStationSpacingM"] <= 1.0
    assert report["sampleSpacingAcrossWidthM"] == 0.25
    assert report["samplesPerSection"] == 25
    assert report["constraintCount"] == len(constraints)
    assert report["constraintCount"] < report["stationCount"] * 48
    stations = {section["stationM"] for section in report["baselineSections"]}
    assert 144.5 in stations  # Exact source vertex station.
    assert 148.15104603556912 in stations  # Registered worst section.
    assert (
        max(
            item["baselineMaximumAbsoluteLateralSlopePercent"]
            for item in report["baselineSections"]
        )
        > 5
    )

    flat = np.zeros_like(baseline)
    metrics = _teignmouth_section_metrics(inputs, baseline, flat, 2.0)
    assert metrics["allStationsPass"]
    assert metrics["maximumObservedAbsoluteLateralSlopePercent"] == 0
    assert metrics["maximumObservedEndpointSpanM"] == 0
    assert metrics["maximumCenterlineDeviationM"] == 0


def test_teignmouth_candidate_shoulder_uses_bounded_smooth_existing_transition() -> None:
    segment = RoadSegment(
        sort_key=("way/78455395", 0, 0),
        way_id=78455395,
        name="Teignmouth Road",
        width_m=6.0,
        first_x=0.0,
        first_z=0.0,
        dx=10.0,
        dz=0.0,
        length_squared=100.0,
        influence_m=9.0,
    )
    config = _config(fallback_fade_distance_m=32.0)
    intervals = {(78455395, 0): [(140.0, 155.0)]}
    assert _transition_for_station(segment, 148.0, 2.0, config, intervals) == 32.0
    assert _transition_for_station(segment, 187.0, 2.0, config, intervals) == 6.0
    middle = _transition_for_station(segment, 171.0, 2.0, config, intervals)
    assert 6.0 < middle < 32.0


@pytest.mark.parametrize(
    "destination",
    [
        "AGENTS.md",
        "docs/milestones/artifacts/Road-surface-treatment",
        "docs/milestones/artifacts/Road-surface-treatment/../Road-alignment/build-10.json",
        "docs/milestones/artifacts/Road-surface-treatment/subdir/../build-10.json",
        "docs/milestones/artifacts/Road-surface-treatment/../../../../AGENTS.md",
    ],
)
def test_record_preflight_rejects_unsafe_destinations_without_touching_protected_bytes(
    tmp_path, monkeypatch, destination
) -> None:
    import torquay_pipeline.road_surface as road_surface

    evidence = tmp_path / "docs/milestones/artifacts/Road-surface-treatment"
    evidence.mkdir(parents=True)
    (tmp_path / "public/worlds/torquay-road-surface-preview").mkdir(parents=True)
    protected = tmp_path / "AGENTS.md"
    protected.write_bytes(b"project protection marker")
    output_files = [
        tmp_path / "public/worlds/torquay-road-surface-preview" / name
        for name in ("manifest.json", "heightfield.f32", "qa.json")
    ]
    for path in output_files:
        path.write_bytes((path.name + " original bytes").encode())
    before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest() for path in [protected, *output_files]
    }
    monkeypatch.setattr(
        road_surface,
        "load_release_inputs",
        lambda *_args, **_kwargs: pytest.fail("unsafe record path reached release loading"),
    )

    with pytest.raises(RoadSurfaceError):
        road_surface.build_preview(tmp_path, _config(), tmp_path / destination)

    after = {
        path: hashlib.sha256(path.read_bytes()).hexdigest() for path in [protected, *output_files]
    }
    assert after == before


def test_record_preflight_rejects_existing_issue_destination_without_overwrite(
    tmp_path, monkeypatch
) -> None:
    import torquay_pipeline.road_surface as road_surface

    evidence = tmp_path / "docs/milestones/artifacts/Road-surface-treatment"
    evidence.mkdir(parents=True)
    output = tmp_path / "public/worlds/torquay-road-surface-preview"
    output.mkdir(parents=True)
    protected = evidence / "build-10.json"
    protected.write_bytes(b"existing build record")
    derivative = output / "heightfield.f32"
    derivative.write_bytes(b"existing derivative bytes")
    before = {
        protected: hashlib.sha256(protected.read_bytes()).hexdigest(),
        derivative: hashlib.sha256(derivative.read_bytes()).hexdigest(),
    }
    monkeypatch.setattr(
        road_surface,
        "load_release_inputs",
        lambda *_args, **_kwargs: pytest.fail("existing record reached release loading"),
    )

    with pytest.raises(RoadSurfaceError, match="already exists"):
        road_surface.build_preview(tmp_path, _config(), protected)

    assert {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in before} == before


def test_record_preflight_rejects_symlink_or_junction_alias(tmp_path) -> None:
    evidence = tmp_path / "docs/milestones/artifacts/Road-surface-treatment"
    evidence.mkdir(parents=True)
    alias = evidence / "alias"
    try:
        alias.symlink_to(tmp_path, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"this Windows account cannot create a directory symlink: {exc}")

    with pytest.raises(RoadSurfaceError, match="symlink or junction"):
        _preflight_execution_record(tmp_path, alias / "build-10.json")


def test_fallback_uses_zero_ended_smoothstep_and_keeps_the_outer_candidate_exact() -> None:
    min_row, min_column, weights = _fallback_distance_weights([(8, 8)], 17, 17, 1.0, 4.0)
    assert weights[8 - min_row, 8 - min_column] == pytest.approx(0.0)
    assert weights[8 - min_row, 10 - min_column] == pytest.approx(0.5)
    assert weights[8 - min_row, 12 - min_column] == pytest.approx(1.0)

    baseline = np.zeros((41, 41), dtype="<f4")
    candidate = baseline.copy()
    candidate[18:23, 18:23] = 8.0
    preview, report = _apply_harm_fallback(
        baseline,
        candidate,
        [],
        1.0,
        40.0,
        40.0,
        _config(fallback_fade_distance_m=8.0),
        np.zeros_like(baseline, dtype=np.int64),
    )
    assert report["triggeredRegionCount"] == 2
    assert {trigger for region in report["regions"] for trigger in region["harmTriggers"]} == {
        "absolute local cut/fill threshold",
        "connected added-gradient threshold and minimum area",
    }
    assert preview[20, 20] == pytest.approx(0.0)
    assert preview[0, 0] == candidate[0, 0]
    assert np.isfinite(preview).all()
    assert report["regions"][0]["postFallbackMaximumAddedGradientMPerM"] < 1.0
    assert report["regions"][0]["fadeDistanceM"] == 8.0
    assert report["uniqueRetainedCoreAreaEquivalentM2"] >= 25.0
    assert report["uniqueAffectedAreaEquivalentM2"] <= report["affectedAreaEquivalentM2"]


def test_fallback_catches_minimum_two_vertex_added_gradient_component() -> None:
    baseline = np.zeros((41, 41), dtype="<f4")
    adjacent_pattern = np.tile(np.asarray([0.0, 2.8], dtype="<f4"), 7)
    baseline[19, 10:24] = adjacent_pattern
    baseline[21, 10:24] = adjacent_pattern
    baseline[20, 24] = 2.8
    candidate = baseline.copy()
    candidate[20, 10:24] = adjacent_pattern

    preview, report = _apply_harm_fallback(
        baseline,
        candidate,
        [],
        2.0,
        80.0,
        80.0,
        _config(fallback_fade_distance_m=8.0),
        np.zeros_like(baseline, dtype=np.int64),
    )

    assert report["triggeredRegionCount"] == 1
    region = report["regions"][0]
    assert region["coreAreaEquivalentM2"] == 56.0
    assert "connected added-gradient threshold and minimum area" in region["harmTriggers"]
    assert np.all(preview[20, 10:24] == baseline[20, 10:24])
    assert region["postFallbackMaximumAddedGradientMPerM"] < 1.0


def test_harm_fade_touching_carriageway_core_uses_core_aware_ramp() -> None:
    baseline = np.broadcast_to(
        (np.arange(21, dtype=np.float32) - 10.0)[:, None] * 0.2, (21, 21)
    ).copy()
    candidate = baseline.copy()
    candidate[8:13, :] = 0.0
    candidate[14, 8:13] += 6.0
    segments = _segments_from_payload(
        {"features": [_road(44, [[-10.0, 0.0], [10.0, 0.0]], width=2.0)]}, 1.0, 1.0
    )
    nearest_way = np.full((21, 21), 44, dtype=np.int64)
    nearest_segment = np.zeros((21, 21), dtype=np.int32)
    nearest_station = np.broadcast_to(np.arange(21, dtype=np.float64), (21, 21)).copy()
    nearest_distance = np.broadcast_to(
        np.abs(np.arange(21, dtype=np.float64) - 10.0)[:, None], (21, 21)
    ).copy()
    triangle_owner = np.full((21, 21), -1, dtype=np.int32)
    triangle_owner[8:13, :] = 0
    triangle_owner_is_core = triangle_owner >= 0

    preview, report = _apply_station_harm_fallback(
        baseline,
        candidate,
        segments,
        1.0,
        2.0,
        20.0,
        _config(fallback_fade_distance_m=8.0),
        nearest_way,
        nearest_segment,
        nearest_station,
        nearest_distance,
        [],
        triangle_owner,
        triangle_owner_is_core,
    )

    assert preview[8:13, :] == pytest.approx(candidate[8:13, :])
    assert preview[14, 8:13] == pytest.approx(baseline[14, 8:13])
    assert report["maximumChangeAfterFallbackM"] < 5.0
    assert report["maximumAddedGradientAfterFallbackMPerM"] < 1.0
    assert report["regions"]
    for region in report["regions"]:
        assert region["fallbackMode"] == "core-aware spatial source-retention ramp"
        assert region["componentIntersectsTriangleCoreSupport"] is False
        assert region["harmFadeEnvelopeIntersectsTriangleCoreSupport"] is True
        assert region["sourceRetentionRamp"]["start"] == (
            "0 at immutable triangle-support vertices"
        )
        assert region["sourceRetentionRamp"]["seed"] == (
            "1 at the harmful component before strict surface-gradient validation"
        )


def test_core_intersecting_cut_fill_harm_rejects_its_connected_section() -> None:
    baseline = np.zeros((21, 21), dtype="<f4")
    candidate = baseline.copy()
    candidate[10:15, 10] = 6.0
    segments = _segments_from_payload(
        {"features": [_road(44, [[-10.0, 0.0], [10.0, 0.0]], width=2.0)]}, 1.0, 1.0
    )
    nearest_way = np.full((21, 21), 44, dtype=np.int64)
    nearest_segment = np.zeros((21, 21), dtype=np.int32)
    nearest_station = np.broadcast_to(np.arange(21, dtype=np.float64), (21, 21)).copy()
    nearest_distance = np.broadcast_to(
        np.abs(np.arange(21, dtype=np.float64) - 10.0)[:, None], (21, 21)
    ).copy()
    triangle_owner = np.full((21, 21), -1, dtype=np.int32)
    triangle_owner[8:13, :] = 0
    triangle_owner_is_core = triangle_owner >= 0

    preview, report = _apply_station_harm_fallback(
        baseline,
        candidate,
        segments,
        1.0,
        2.0,
        20.0,
        _config(fallback_fade_distance_m=8.0),
        nearest_way,
        nearest_segment,
        nearest_station,
        nearest_distance,
        [],
        triangle_owner,
        triangle_owner_is_core,
    )

    region = next(
        region
        for region in report["regions"]
        if "absolute local cut/fill threshold" in region["harmTriggers"]
    )
    assert region["coreCutFillConnectedSectionFallback"] is True
    assert region["componentIntersectsTriangleCoreSupport"] is True
    assert region["fallbackMode"] == "connected-section source retention for core cut/fill harm"
    assert all(
        interval["fallbackScope"]
        == "full road section because candidate harm reaches carriageway core"
        for interval in region["stationIntervals"]
    )
    assert preview[10:15, 10] == pytest.approx(baseline[10:15, 10])
    assert report["maximumChangeAfterFallbackM"] < 5.0
    assert report["maximumAddedGradientAfterFallbackMPerM"] < 1.0
