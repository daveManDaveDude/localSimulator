"""Deterministic north-up building QA map generated from exported footprints."""

from __future__ import annotations

import io
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as PolygonPatch
from matplotlib.patches import Rectangle
from shapely.geometry import Polygon

OSM_ATTRIBUTION = (
    "© OpenStreetMap contributors · Open Database License 1.0 · "
    "https://www.openstreetmap.org/copyright · Geofabrik Devon extract"
)


def render_building_preview(
    buildings: list[dict[str, Any]], qa: dict[str, Any], *, title: str = "OSM building footprint QA"
) -> bytes:
    """Render local XZ footprints with north plotted upward and an exact AOI frame."""
    figure, axis = plt.subplots(figsize=(11, 10))
    figure.subplots_adjust(left=0.11, right=0.98, bottom=0.16, top=0.94)
    figure.patch.set_facecolor("#f7f8fa")
    axis.set_facecolor("#f7f8fa")
    methods = {
        "osm_height": "Tagged height (unverified)",
        "estimated_levels": "Estimated from levels",
        "estimated_default": "Visual default estimate",
    }
    colors = {
        "osm_height": "#4477aa",
        "estimated_levels": "#66a61e",
        "estimated_default": "#e6ab02",
    }
    label_items: dict[str, tuple[float, float, str, float]] = {}
    for building in buildings:
        fill = colors[building["heightMethod"]]
        for component in building["geometry"]["polygons"]:
            exterior = [(float(x), -float(z)) for x, z in component["exteriorXZ"]]
            axis.add_patch(
                PolygonPatch(
                    exterior,
                    closed=True,
                    facecolor=fill,
                    edgecolor="#26313c",
                    linewidth=0.35,
                    alpha=0.83,
                    zorder=2,
                )
            )
            for hole in component["interiorRingsXZ"]:
                northing_up = [(float(x), -float(z)) for x, z in hole]
                axis.add_patch(
                    PolygonPatch(
                        northing_up,
                        closed=True,
                        facecolor="#f7f8fa",
                        edgecolor="#26313c",
                        linewidth=0.3,
                        zorder=3,
                    )
                )
            polygon = Polygon(exterior)
            if polygon.area > 100:
                point = polygon.representative_point()
                object_id = str(building["id"]).replace("osm:", "")
                northing = float(point.y)
                quadrant = ("N" if northing >= 0 else "S") + ("W" if point.x < 0 else "E")
                current = label_items.get(quadrant)
                if current is None or polygon.area > current[3]:
                    label_items[quadrant] = (
                        float(point.x),
                        northing,
                        object_id,
                        float(polygon.area),
                    )

    axis.add_patch(
        Rectangle(
            (-500, -500), 1000, 1000, fill=False, edgecolor="#c51b29", linewidth=1.8, zorder=5
        )
    )
    for quadrant, (x, y, object_id, _area) in sorted(label_items.items()):
        axis.annotate(
            f"{quadrant} · {object_id}",
            xy=(x, y),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=7,
            color="#15202b",
            bbox={"facecolor": "white", "edgecolor": "#46525e", "alpha": 0.9, "pad": 2},
            zorder=8,
        )
    axis.scatter(
        [0], [0], marker="+", s=85, linewidths=1.7, color="#222", zorder=7, label="AOI centre"
    )
    axis.annotate(
        "N",
        xy=(0.95, 0.94),
        xytext=(0.95, 0.86),
        xycoords="axes fraction",
        textcoords="axes fraction",
        arrowprops={"arrowstyle": "-|>", "color": "#202a33", "lw": 1.4},
        ha="center",
        va="bottom",
        fontsize=10,
        weight="bold",
        zorder=8,
    )
    axis.set_xlim(-560, 560)
    axis.set_ylim(-560, 560)
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("Local easting from AOI centre (m)")
    axis.set_ylabel("Northing from AOI centre (m)")
    axis.set_xticks(range(-500, 501, 100))
    axis.set_yticks(range(-500, 501, 100))
    axis.grid(color="#aeb6bf", linewidth=0.35, alpha=0.4, zorder=0)
    axis.set_title(title, loc="left", fontsize=13, weight="bold", pad=12)

    methods_count = qa.get("quality", {}).get("heightMethodCounts", {})
    summary = qa.get("summary", {})
    counts = qa.get("counts", {})
    legend_lines = [
        f"Buildings exported: {counts.get('exported_buildings', len(buildings))}",
        f"Footprint area: {summary.get('buildingFootprintAreaM2', 0):,.1f} m²",
        f"Mapped density: {summary.get('footprintAreaPerAoiKm2', 0):,.4f} km²/km²",
        f"Multipolygon assembly failures: {counts.get('relation_area_assembly_failures', 0)}",
        f"Non-area relations skipped: {counts.get('building_relations_skipped_non_area_type', 0)}",
        "Mapped OSM coverage only; not a completeness estimate.",
        "Red outline: exact 1,000 m AOI boundary.",
    ]
    for method, label in methods.items():
        legend_lines.append(f"{label}: {methods_count.get(method, 0)}")
    axis.text(
        0.015,
        0.985,
        "\n".join(legend_lines),
        transform=axis.transAxes,
        ha="left",
        va="top",
        fontsize=8,
        bbox={"facecolor": "white", "edgecolor": "#b8c1ca", "alpha": 0.93, "pad": 6},
        zorder=9,
    )
    axis.plot(
        [-450, -350], [-525, -525], color="#15202b", linewidth=2.2, solid_capstyle="butt", zorder=8
    )
    axis.plot([-450, -450], [-530, -520], color="#15202b", linewidth=1.2, zorder=8)
    axis.plot([-350, -350], [-530, -520], color="#15202b", linewidth=1.2, zorder=8)
    axis.text(-400, -542, "100 m", ha="center", va="top", fontsize=8, color="#15202b", zorder=8)
    figure.text(0.01, 0.025, OSM_ATTRIBUTION, fontsize=7, color="#30343b")
    buffer = io.BytesIO()
    figure.savefig(
        buffer,
        dpi=170,
        format="png",
        metadata={"Software": "TVW-009 deterministic building preview"},
        facecolor=figure.get_facecolor(),
    )
    plt.close(figure)
    return buffer.getvalue()
