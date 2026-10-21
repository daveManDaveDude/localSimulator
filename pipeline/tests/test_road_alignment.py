"""Independent synthetic controls for road-alignment diagnostics."""

from __future__ import annotations

import numpy as np
import pytest

from torquay_pipeline.road_alignment import (
    RoadAlignmentError,
    TerrainGrid,
    absolute_grade_percent,
    coordinate_delta_summary,
    cross_grade_percent,
    guard_output_directory,
    inspect_face,
)


def _grid(values: np.ndarray, spacing: float, origin_y: float = 0.0) -> TerrainGrid:
    rows, columns = values.shape
    return TerrainGrid(
        heights=values.astype("<f4"),
        columns=columns,
        rows=rows,
        spacing_m=spacing,
        width_m=(columns - 1) * spacing,
        depth_m=(rows - 1) * spacing,
        origin_e_m=291_000.0,
        origin_n_m=65_000.0,
        origin_y_m=origin_y,
    )


def test_translated_centerline_delta_is_measured_without_registration_fit() -> None:
    source = [(0.0, 0.0), (20.0, 10.0), (40.0, 20.0)]
    shifted = [(x + 3.0, z - 4.0) for x, z in source]

    result = coordinate_delta_summary(source, shifted)

    assert result["maximumAbsoluteAxisDeltaM"] == 4.0
    assert result["maximumEuclideanDeltaM"] == 5.0
    with pytest.raises(RoadAlignmentError, match="matching non-empty"):
        coordinate_delta_summary(source, shifted[:-1])


def test_sloped_synthetic_terrain_produces_expected_longitudinal_grade() -> None:
    # Ten percent eastward slope: height rises 0.5 m over each 5 m terrain cell.
    values = np.tile(np.array([-0.5, 0.0, 0.5], dtype=np.float32), (3, 1))
    grid = _grid(values, spacing=5.0, origin_y=12.0)
    stations = [0.0, 2.0, 4.0, 6.0, 8.0]
    positions = [(-4.0 + station, 0.0) for station in stations]
    elevations = [grid.sample_relative(x, z) for x, z in positions]

    grades = absolute_grade_percent(stations, elevations)

    assert grades == pytest.approx([10.0] * 4)
    assert [grid.sample_absolute(x, z) for x, z in positions] == pytest.approx(
        [11.6, 11.8, 12.0, 12.2, 12.4]
    )


def test_steep_cross_section_is_reported_as_terrain_crossfall() -> None:
    # A 1:1 synthetic cross-slope yields 4 m over a 4 m estimated ribbon.
    values = np.repeat(np.array([-5.0, 0.0, 5.0], dtype=np.float32)[:, None], 3, axis=1)
    grid = _grid(values, spacing=5.0)

    first = grid.sample_absolute(0.0, -2.0)
    second = grid.sample_absolute(0.0, 2.0)

    assert first == pytest.approx(-2.0)
    assert second == pytest.approx(2.0)
    assert cross_grade_percent(first, second, 4.0) == pytest.approx(100.0)


def test_exact_fixed_triangle_face_conforms_and_diagonal_crossing_is_detected() -> None:
    # The NW/SW/NE half of this cell is flat; the SE corner is intentionally raised.
    grid = _grid(np.array([[0.0, 0.0], [0.0, 12.0]], dtype=np.float32), spacing=2.0)
    conforming = [(-1.0, -1.0), (-1.0, 1.0), (1.0, -1.0)]
    crossing = [(-0.8, -0.8), (-0.8, 0.8), (0.8, 0.8)]

    exact = inspect_face(conforming, row=0, column=0, triangle=0, grid=grid)
    invalid = inspect_face(crossing, row=0, column=0, triangle=0, grid=grid)

    assert exact["containedInDouble"] is True
    assert exact["containedInFloat32"] is True
    assert abs(exact["doubleCentroidResidualM"]) < 1e-12
    assert abs(exact["float32CentroidResidualM"]) < 1e-6
    assert invalid["containedInDouble"] is False
    assert invalid["containedInFloat32"] is False


def test_output_guard_rejects_input_alias_and_unowned_existing_files(tmp_path) -> None:
    protected = tmp_path / "data" / "sentinel.json"
    protected.parent.mkdir()
    protected.write_text("protected", encoding="utf-8")

    with pytest.raises(RoadAlignmentError, match="exactly"):
        guard_output_directory(tmp_path, protected.parent)
    assert protected.read_text(encoding="utf-8") == "protected"

    output = tmp_path / "docs/milestones/artifacts/Road-alignment"
    output.mkdir(parents=True)
    sentinel = output / "unowned.txt"
    sentinel.write_text("leave in place", encoding="utf-8")
    with pytest.raises(RoadAlignmentError, match="unowned or unsafe"):
        guard_output_directory(tmp_path, output)
    assert sentinel.read_text(encoding="utf-8") == "leave in place"
    assert protected.read_text(encoding="utf-8") == "protected"
