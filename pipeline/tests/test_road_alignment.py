"""Independent synthetic controls for road-alignment diagnostics."""

from __future__ import annotations

import numpy as np
import pytest
from shapely.geometry import Polygon, box

from torquay_pipeline.road_alignment import (
    RoadAlignmentError,
    TerrainGrid,
    _coordinate_operation_summary,
    _surface_footprint_comparison,
    _triangle_coverage,
    absolute_grade_percent,
    camera_local_y_for_clearance,
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


def test_camera_clearance_uses_local_ground_y_with_nonzero_origin() -> None:
    local_ground_m = 4.25
    vertical_origin_m = 120.0
    orthometric_ground_m = vertical_origin_m + local_ground_m
    requested_clearance_m = 15.0

    camera_local_y_m = camera_local_y_for_clearance(local_ground_m, requested_clearance_m)

    assert camera_local_y_m == pytest.approx(19.25)
    assert camera_local_y_m - local_ground_m == pytest.approx(requested_clearance_m)
    assert camera_local_y_m != pytest.approx(orthometric_ground_m + requested_clearance_m)


def test_equal_area_translated_surface_has_nonzero_spatial_difference() -> None:
    source = box(0.0, 0.0, 2.0, 3.0)
    published = box(5.0, 0.0, 7.0, 3.0)

    comparison = _surface_footprint_comparison(source, published.area, published)

    assert comparison["sourceVisibleAreaM2"] == pytest.approx(6.0)
    assert comparison["publishedUnionAreaM2"] == pytest.approx(6.0)
    assert comparison["sourcePublishedSymmetricDifferenceAreaM2"] == pytest.approx(12.0)


def test_triangle_coverage_keeps_overlap_sum_separate_from_union() -> None:
    first = Polygon([(0.0, 0.0), (2.0, 0.0), (0.0, 2.0)])
    overlapping = Polygon([(1.0, 0.0), (3.0, 0.0), (1.0, 2.0)])
    gapped = Polygon([(3.0, 0.0), (5.0, 0.0), (3.0, 2.0)])
    window = box(-1.0, -1.0, 6.0, 3.0)

    overlap_sum, overlap_union, overlap_count = _triangle_coverage([first, overlapping], window)
    gap_sum, gap_union, gap_count = _triangle_coverage([first, gapped], window)
    intended_gapped_footprint = box(0.0, 0.0, 5.0, 2.0)
    gap_comparison = _surface_footprint_comparison(intended_gapped_footprint, gap_sum, gap_union)

    assert overlap_count == 2
    assert overlap_sum == pytest.approx(4.0)
    assert overlap_union.area == pytest.approx(3.5)
    assert overlap_sum > overlap_union.area
    assert gap_count == 2
    assert gap_sum == pytest.approx(4.0)
    assert gap_union.area == pytest.approx(4.0)
    assert gap_sum == pytest.approx(gap_union.area)
    assert gap_comparison["sourceVisibleAreaM2"] == pytest.approx(10.0)
    assert gap_comparison["sourcePublishedSymmetricDifferenceAreaM2"] > 0


def test_coordinate_operation_summary_reads_snake_case_manifest_metadata() -> None:
    summary = _coordinate_operation_summary(
        {
            "reported_accuracy_m": 2,
            "grid_status": "selected operation uses no grid files",
            "best_available": False,
            "preferred_missing_operations": [
                {
                    "name": "Preferred operation",
                    "reported_accuracy_m": 1,
                    "grids": [
                        {
                            "short_name": "uk_os_OSTN15_NTv2_OSGBtoETRS.tif",
                            "available": False,
                        }
                    ],
                }
            ],
        }
    )

    assert summary["reportedAccuracyM"] == 2
    assert summary["selectedOperationGridStatus"] == "selected operation uses no grid files"
    assert summary["bestAvailableOperation"] is False
    assert summary["preferredMissingGridNames"] == ["uk_os_OSTN15_NTv2_OSGBtoETRS.tif"]
    assert summary["preferredMissingOperations"] == [
        {
            "name": "Preferred operation",
            "reportedAccuracyM": 1,
            "missingGridNames": ["uk_os_OSTN15_NTv2_OSGBtoETRS.tif"],
        }
    ]
    assert "not best available" in summary["coordinateOperationCaveat"]


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
