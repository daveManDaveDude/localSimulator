"""North-up visual QA map for local OSM-derived road ribbons."""

from __future__ import annotations

import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.patches import PathPatch
from matplotlib.path import Path as PlotPath
from shapely import Geometry
from shapely.geometry import Polygon

from .road_geometry import DISPLAY_GROUPS, _polygon_parts

COLORS = {"vehicular": "#f4b942", "cycleway": "#38b7a3", "path": "#d9e8ff"}
NAMES = {
    "vehicular": "Vehicular street (estimated width)",
    "cycleway": "Cycleway",
    "path": "Path / pedestrian way",
}
NORTH_ARROW_TIP_AXES = (0.965, 0.94)
NORTH_ARROW_TAIL_AXES = (0.965, 0.83)
NORTH_LABEL_AXES = (0.965, 0.965)


def profile_title(qa: dict[str, Any]) -> str:
    """Return an accurate footprint label for the report's terrain profile."""
    if qa.get("sceneProfile") == "current_2km":
        return "2 km current_2km candidate AOI"
    return "1 km historical candidate AOI"


def _patch_for_polygon(polygon: Polygon) -> PathPatch:
    vertices: list[tuple[float, float]] = []
    codes: list[int] = []
    for ring in (polygon.exterior, *polygon.interiors):
        coordinates = list(ring.coords)
        vertices.extend((float(x), float(z)) for x, z in coordinates)
        codes.extend(
            [PlotPath.MOVETO, *([PlotPath.LINETO] * (len(coordinates) - 2)), PlotPath.CLOSEPOLY]
        )
    return PathPatch(PlotPath(vertices, codes), facecolor="#000000", edgecolor="none")


def _raster(terrain_package_path: Path) -> tuple[np.ndarray, dict[str, float]]:
    try:
        manifest = json.loads((terrain_package_path / "manifest.json").read_text(encoding="utf-8"))
        heightfield = manifest["heightfield"]
        extent = manifest["extentM"]
        values = np.fromfile(terrain_package_path / heightfield["path"], dtype="<f4")
        rows, columns = int(heightfield["rows"]), int(heightfield["columns"])
        if values.size != rows * columns:
            raise ValueError("terrain heightfield length differs from the manifest")
        return values.reshape((rows, columns)), {
            "width": float(extent["width"]),
            "depth": float(extent["depth"]),
            "columns": columns,
            "rows": rows,
        }
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"cannot load terrain backdrop for road QA: {exc}") from exc


def render_road_preview(
    display_polygons: dict[str, Geometry],
    features: list[dict[str, Any]],
    qa: dict[str, Any],
    terrain_package_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Render real terrain under the exact AOI-clipped display surfaces."""
    terrain, dimensions = _raster(terrain_package_path)
    width, depth = dimensions["width"], dimensions["depth"]
    fig, ax = plt.subplots(figsize=(12, 12.5), dpi=160)
    image = ax.imshow(
        terrain,
        extent=(-width / 2, width / 2, depth / 2, -depth / 2),
        cmap="terrain",
        interpolation="nearest",
        alpha=0.84,
        zorder=0,
    )
    colorbar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.02)
    colorbar.set_label("Terrain elevation relative to local Newlyn origin (m)")
    for group in DISPLAY_GROUPS:
        geometry = display_polygons.get(group)
        if geometry is None or geometry.is_empty:
            continue
        color = COLORS[group]
        for polygon in _polygon_parts(geometry):
            patch = _patch_for_polygon(polygon)
            patch.set_facecolor(color)
            patch.set_edgecolor("#172332")
            patch.set_linewidth(0.12)
            patch.set_alpha(0.86 if group == "vehicular" else 0.93)
            patch.set_zorder(3 + len(DISPLAY_GROUPS) - DISPLAY_GROUPS.index(group))
            ax.add_patch(patch)

    centerlines: dict[str, list[list[tuple[float, float]]]] = {
        group: [] for group in DISPLAY_GROUPS
    }
    for feature in features:
        group = feature["displayGroup"]
        for part in feature["centerlinePartsXZ"]:
            centerlines[group].append([(float(point[0]), float(point[1])) for point in part])
    for _group, lines in centerlines.items():
        if lines:
            collection = LineCollection(
                lines, colors="#29394c", linewidths=0.22, alpha=0.75, zorder=7
            )
            ax.add_collection(collection)

    half_width, half_depth = width / 2, depth / 2
    ax.plot(
        [-half_width, half_width, half_width, -half_width, -half_width],
        [-half_depth, -half_depth, half_depth, half_depth, -half_depth],
        color="#ef476f",
        linewidth=1.8,
        zorder=9,
    )
    ax.scatter([0], [0], marker="+", s=60, color="white", linewidths=1.8, zorder=10)
    ax.text(
        *NORTH_LABEL_AXES,
        "N",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        weight="bold",
        color="#182332",
    )
    ax.annotate(
        "",
        xy=NORTH_ARROW_TIP_AXES,
        xytext=NORTH_ARROW_TAIL_AXES,
        xycoords="axes fraction",
        textcoords="axes fraction",
        arrowprops={"arrowstyle": "-|>", "color": "#182332", "lw": 1.8},
    )
    ax.set_title(
        "Local OSM highway ribbons on verified EA DTM\n"
        f"{profile_title(qa)} · estimated visual widths · vertical-road tags excluded",
        fontsize=13,
        weight="bold",
    )
    ax.set_xlabel("Local X / easting offset from candidate center (m)")
    ax.set_ylabel("Local Z / northing offset (m) · north is negative Z")
    ax.set_xlim(-half_width - 25, half_width + 25)
    ax.set_ylim(half_depth + 25, -half_depth - 25)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(color="white", linewidth=0.4, alpha=0.3)
    scale_x, scale_z, scale_width = -450.0, 470.0, 100.0
    ax.plot(
        [scale_x, scale_x + scale_width],
        [scale_z, scale_z],
        color="white",
        linewidth=5,
        solid_capstyle="butt",
        zorder=12,
    )
    ax.plot(
        [scale_x, scale_x + scale_width],
        [scale_z, scale_z],
        color="#182332",
        linewidth=1.5,
        solid_capstyle="butt",
        zorder=13,
    )
    ax.plot(
        [scale_x, scale_x],
        [scale_z - 3, scale_z + 3],
        color="#182332",
        linewidth=1.5,
        zorder=13,
    )
    ax.plot(
        [scale_x + scale_width, scale_x + scale_width],
        [scale_z - 3, scale_z + 3],
        color="#182332",
        linewidth=1.5,
        zorder=13,
    )
    ax.text(
        scale_x + scale_width / 2,
        scale_z - 8,
        "100 m",
        ha="center",
        va="bottom",
        fontsize=8,
        color="#182332",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9, "pad": 2},
        zorder=14,
    )
    handles = [
        plt.Line2D([0], [0], color=COLORS[group], linewidth=5, label=NAMES[group])
        for group in DISPLAY_GROUPS
    ]
    handles.append(plt.Line2D([0], [0], color="#ef476f", linewidth=2, label="Exact AOI boundary"))
    fig.subplots_adjust(left=0.11, right=0.89, top=0.89, bottom=0.27)
    fig.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.17),
        ncol=2,
        framealpha=0.95,
        fontsize=8,
    )
    counts = qa.get("counts", {})
    summary = (
        f"Mapped ways {counts.get('uniqueExportedWays', 0):,} · "
        f"ribbon triangles {counts.get('renderTriangleCount', 0):,}\n"
        f"excluded vertical/ambiguous {counts.get('excluded_ground_assumption', 0):,} · "
        f"unknown/excluded class {counts.get('excluded_classes', 0):,}\n"
        "Mapped counts do not prove completeness · selected_pending_coverage / not_checked\n"
        "© OpenStreetMap contributors · Geofabrik GmbH · EA DTM © Environment Agency 2022"
    )
    fig.text(0.5, 0.018, summary, ha="center", va="bottom", fontsize=8)
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=160, facecolor="#f4f5f7")
    plt.close(fig)
    content = buffer.getvalue()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output_path.name}.", suffix=".stage", dir=output_path.parent, delete=False
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, output_path)
    except OSError as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise OSError(f"cannot atomically write road preview '{output_path}': {exc}") from exc
    return {
        "output": str(output_path.resolve()),
        "byteLength": len(content),
        "widthPixels": 1920,
        "heightPixels": 2000,
        "terrainRows": dimensions["rows"],
        "terrainColumns": dimensions["columns"],
        "scaleBarM": int(scale_width),
    }
