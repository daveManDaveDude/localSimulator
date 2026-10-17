"""Render an atomic north-up PNG from measured AOI DTM samples."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patheffects
from matplotlib.colors import Normalize
from matplotlib.patches import Rectangle

from .terrain_coverage import CoverageResult


def write_terrain_preview(result: CoverageResult, output_path: Path) -> dict[str, Any]:
    """Save a north-up preview with metre axes, AOI bounds and measured coverage."""
    report = result.report
    aoi = report["aoi"]
    coverage = report["coverage"]
    elevation = report["elevation_m"]
    west, south, east, north = aoi["bounds_m"]
    values = np.ma.array(result.elevations_m, mask=~result.valid_mask)
    valid_values = result.elevations_m[result.valid_mask]
    if valid_values.size == 0:
        raise ValueError("cannot render a terrain preview because the AOI has no valid DTM cells")

    minimum = float(np.min(valid_values))
    maximum = float(np.max(valid_values))
    if minimum == maximum:
        padding = max(abs(minimum) * 0.01, 0.5)
        norm = Normalize(vmin=minimum - padding, vmax=maximum + padding)
    else:
        norm = Normalize(vmin=minimum, vmax=maximum)

    cmap = matplotlib.colormaps["terrain"].with_extremes(bad="#d9dde2")
    figure, axis = plt.subplots(figsize=(10, 8))
    figure.subplots_adjust(left=0.12, right=0.86, top=0.88, bottom=0.19)
    figure.patch.set_facecolor("white")
    image = axis.imshow(
        values,
        origin="upper",
        extent=(west, east, south, north),
        interpolation="nearest",
        cmap=cmap,
        norm=norm,
        aspect="equal",
    )
    axis.add_patch(
        Rectangle(
            (west, south),
            east - west,
            north - south,
            fill=False,
            edgecolor="#d62728",
            linewidth=2,
            zorder=4,
            label="AOI boundary",
        )
    )
    center = elevation["center"]
    if center["value_m"] is not None:
        axis.plot(
            center["easting_m"],
            center["northing_m"],
            marker="+",
            color="#111111",
            markersize=12,
            markeredgewidth=2,
            zorder=5,
            label="Configured postcode centroid",
        )
    axis.set_xlabel("Easting (m, EPSG:27700)")
    axis.set_ylabel("Northing (m, EPSG:27700)")
    axis.set_xlim(west, east)
    axis.set_ylim(south, north)
    axis.grid(color="white", linewidth=0.35, alpha=0.5)
    axis.legend(loc="lower left", framealpha=0.9, fontsize=8)
    axis.set_title(
        "Environment Agency LIDAR Composite DTM 1 m (2022)\n"
        f"Measured AOI elevations {minimum:.2f} to {maximum:.2f} m"
    )
    figure.colorbar(
        image,
        ax=axis,
        fraction=0.045,
        pad=0.04,
        label="Elevation (m; publisher Newlyn vertical datum)",
    )

    # A high-contrast scale bar sits opposite the lower-left legend.
    scale_y = south + 55
    scale_x = east - 300
    bar = axis.plot(
        [scale_x, scale_x + 250],
        [scale_y, scale_y],
        color="black",
        linewidth=3,
        zorder=6,
    )[0]
    bar.set_path_effects(
        [patheffects.Stroke(linewidth=6, foreground="white"), patheffects.Normal()]
    )
    axis.plot(
        [scale_x, scale_x],
        [scale_y - 15, scale_y + 15],
        color="black",
        linewidth=2.5,
        zorder=7,
    )
    axis.plot(
        [scale_x + 250, scale_x + 250],
        [scale_y - 15, scale_y + 15],
        color="black",
        linewidth=2.5,
        zorder=7,
    )
    axis.text(
        scale_x + 125,
        scale_y + 17,
        "250 m",
        ha="center",
        va="bottom",
        color="black",
        fontsize=8,
        zorder=5,
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none", "pad": 1},
    )

    center_text = (
        f"Centre sample: {center['value_m']:.3f} m ({center['source_filename']})"
        if center["value_m"] is not None
        else "Centre sample: missing from source data"
    )
    figure.text(
        0.01,
        0.07,
        (
            f"Measured EA raster values. "
            f"Valid cells {coverage['valid_cells']:,}/"
            f"{report['analysis_grid']['cell_count']:,}; "
            f"missing {coverage['missing_cells']:,} ({coverage['missing_fraction']:.3%}). "
            f"{center_text}. Gray cells indicate missing source samples."
        ),
        ha="left",
        va="bottom",
        fontsize=8,
        color="#202124",
    )
    figure.text(
        0.01,
        0.025,
        "Contains public sector information licensed under OGL v3.0. "
        "© Environment Agency copyright and/or database right 2022.",
        ha="left",
        va="bottom",
        fontsize=7,
        color="#30343b",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output_path.stem}.",
            suffix=".png",
            dir=output_path.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
        figure.savefig(
            temporary,
            dpi=160,
            format="png",
            metadata={"Software": "TVW-007 offline terrain preview"},
            facecolor=figure.get_facecolor(),
        )
        os.replace(temporary, output_path)
    finally:
        plt.close(figure)
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    return {
        "path": output_path.as_posix(),
        "width_m": east - west,
        "height_m": north - south,
        "orientation": "north-up",
        "sample_grid": (
            f"{report['analysis_grid']['columns']} columns × "
            f"{report['analysis_grid']['rows']} rows at 1 m"
        ),
        "aoi_boundary_drawn": True,
        "missing_cells_distinct": True,
        "publisher_attribution_drawn": True,
    }
