"""Synthetic controls for the bounded road-surface display treatment."""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from torquay_pipeline.road_surface import (
    PreviewConfig,
    ReleaseInputs,
    RoadSegment,
    RoadSurfaceError,
    _apply_harm_fallback,
    _canonical_json,
    _fallback_distance_weights,
    _grade_grid,
    _preflight_execution_record,
    _prepare_output_directory,
    _segments_from_payload,
    _terrain_gradient_change_summary,
    guard_output_directory,
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


def test_flat_surface_is_byte_identical_and_no_vertices_change() -> None:
    baseline = _grid()
    preview, report = _grade(baseline, [_road(10, [[-5.0, 0.0], [5.0, 0.0]])])

    assert preview.tobytes() == baseline.tobytes()
    assert report["changedVertexCount"] == 0
    assert report["verticesBeyondAllInfluenceRegionsExact"]


def test_longitudinal_hill_is_retained_while_lateral_slope_is_removed() -> None:
    x = np.linspace(-5.0, 5.0, 11, dtype=np.float32)
    z = np.linspace(-5.0, 5.0, 11, dtype=np.float32)
    baseline = np.asarray(0.1 * x[None, :] + 0.5 * z[:, None], dtype="<f4")
    preview, _ = _grade(baseline, [_road(10, [[-5.0, 0.0], [5.0, 0.0]])])

    # The centerline carries the original longitudinal profile; both road edges
    # now meet at that baseline centerline elevation.
    assert preview[5, :] == pytest.approx(baseline[5, :], abs=1e-6)
    assert preview[4, 2:9] == pytest.approx(baseline[5, 2:9], abs=1e-6)
    assert preview[6, 2:9] == pytest.approx(baseline[5, 2:9], abs=1e-6)
    assert np.diff(preview[5, :]) == pytest.approx(np.diff(baseline[5, :]), abs=1e-6)


def test_smoothstep_shoulder_returns_to_baseline_and_outer_vertices_are_exact() -> None:
    baseline = np.broadcast_to(
        np.linspace(-2.5, 2.5, 11, dtype=np.float32)[:, None], (11, 11)
    ).copy()
    preview, report = _grade(baseline, [_road(10, [[-5.0, 0.0], [5.0, 0.0]])])

    assert preview[5, 5] == pytest.approx(0.0, abs=1e-6)
    assert preview[4, 5] == pytest.approx(0.0, abs=1e-6)
    assert preview[3, 5] == pytest.approx(baseline[3, 5] * 0.5, abs=1e-6)
    assert preview[2, 5] == baseline[2, 5]
    assert preview[1, 5] == baseline[1, 5]
    assert report["verticesBeyondAllInfluenceRegionsExact"]


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

    with pytest.raises(RoadSurfaceError, match="exactly"):
        guard_output_directory(tmp_path, worlds / "torquay-poc-001-2km", [])
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
        lambda *_args: (
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
    assert report["triggeredRegionCount"] == 1
    assert preview[20, 20] == pytest.approx(0.0)
    assert preview[0, 0] == candidate[0, 0]
    assert np.isfinite(preview).all()
    assert report["regions"][0]["postFallbackMaximumAddedGradientMPerM"] < 1.0


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
    assert region["fadeDistanceM"] == 8.0
    assert report["uniqueRetainedCoreAreaEquivalentM2"] == 56.0
    assert report["uniqueAffectedAreaEquivalentM2"] == report["affectedAreaEquivalentM2"]
