"""Tests for the small north-up source-coverage preview contract."""

from pathlib import Path

import numpy as np

from torquay_pipeline.terrain_coverage import CoverageResult
from torquay_pipeline.terrain_preview import write_terrain_preview


def test_preview_records_north_indicator_and_writes_png(tmp_path: Path) -> None:
    result = CoverageResult(
        report={
            "aoi": {"bounds_m": [0.0, 0.0, 4.0, 4.0]},
            "coverage": {"valid_cells": 16, "missing_cells": 0, "missing_fraction": 0.0},
            "elevation_m": {
                "center": {
                    "value_m": 12.0,
                    "source_filename": "synthetic-test.tif",
                    "easting_m": 2.0,
                    "northing_m": 2.0,
                }
            },
            "analysis_grid": {"cell_count": 16, "columns": 4, "rows": 4},
        },
        elevations_m=np.arange(16, dtype=np.float64).reshape((4, 4)),
        valid_mask=np.ones((4, 4), dtype=bool),
    )

    output = tmp_path / "coverage.png"
    metadata = write_terrain_preview(result, output)

    assert metadata["orientation"] == "north-up"
    assert metadata["north_indicator_drawn"] is True
    assert output.is_file() and output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
