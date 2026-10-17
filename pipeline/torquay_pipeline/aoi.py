"""Derive a pending-coverage candidate AOI and deterministic RFC 7946 outputs."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .config import AoiConfig
from .coordinates import transform_bng_to_wgs84, transform_wgs84_to_bng


def signed_ring_area(ring: list[list[float]]) -> float:
    """Return the signed area of a lon/lat ring; positive is counter-clockwise."""
    return (
        sum(
            ring[index][0] * ring[index + 1][1] - ring[index + 1][0] * ring[index][1]
            for index in range(len(ring) - 1)
        )
        / 2
    )


def _operation_report(info: Any) -> dict[str, Any]:
    return info.as_dict()


def generate_selection(config: AoiConfig) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Build deterministic JSON, GeoJSON, and Markdown from a validated config."""
    center_e, center_n, forward_operation = transform_wgs84_to_bng(
        config.anchor.longitude, config.anchor.latitude
    )
    west = center_e - config.width_m / 2
    east = center_e + config.width_m / 2
    south = center_n - config.height_m / 2
    north = center_n + config.height_m / 2

    # SW → SE → NE → NW produces a counter-clockwise exterior ring in projected space.
    projected_ring = [
        [west, south],
        [east, south],
        [east, north],
        [west, north],
        [west, south],
    ]
    longitudes, latitudes, inverse_operation = transform_bng_to_wgs84(
        [point[0] for point in projected_ring], [point[1] for point in projected_ring]
    )
    ring = [
        [longitude, latitude] for longitude, latitude in zip(longitudes, latitudes, strict=True)
    ]
    if ring[0] != ring[-1]:
        ring[-1] = ring[0].copy()
    if signed_ring_area(ring) < 0:
        ring = list(reversed(ring))

    anchor = {
        "postcode": config.anchor.postcode,
        "coordinates": {
            "crs": "EPSG:4326",
            "longitude": config.anchor.longitude,
            "latitude": config.anchor.latitude,
        },
        "coordinate_meaning": config.anchor.coordinate_meaning,
        "quality": config.anchor.quality,
        "source_name": config.anchor.source_name,
        "source_url": config.anchor.source_url,
        "source_license": config.anchor.source_license,
        "retrieved_date": config.anchor.retrieved_date,
    }
    selection = {
        "format_version": config.format_version,
        "id": config.id,
        "name": config.name,
        "selection_status": config.selection_status,
        "coverage_status": config.coverage_status,
        "coverage_note": "EA DTM and OSM/OS feature coverage have not been checked in TVW-006.",
        "anchor": anchor,
        "source_crs": "EPSG:4326",
        "target_crs": config.crs,
        "world_units": config.world_units,
        "aoi": {
            "center_easting_m": center_e,
            "center_northing_m": center_n,
            "bbox_m": [west, south, east, north],
            "width_m": config.width_m,
            "height_m": config.height_m,
            "corner_coordinates_wgs84": ring[:-1],
        },
        "transformations": {
            "network_grids_enabled": False,
            "wgs84_to_bng": _operation_report(forward_operation),
            "bng_to_wgs84": _operation_report(inverse_operation),
        },
    }
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": f"{config.id}-aoi",
                "properties": {
                    "name": f"{config.name} — candidate square",
                    "selection_status": config.selection_status,
                    "coverage_status": config.coverage_status,
                    "projected_crs": config.crs,
                    "width_m": config.width_m,
                    "height_m": config.height_m,
                },
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            },
            {
                "type": "Feature",
                "id": f"{config.id}-anchor",
                "properties": {
                    "name": f"{config.anchor.postcode} postcode centroid (candidate anchor)",
                    "selection_status": config.selection_status,
                    "source_name": config.anchor.source_name,
                    "coordinate_meaning": config.anchor.coordinate_meaning,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [config.anchor.longitude, config.anchor.latitude],
                },
            },
        ],
    }
    markdown = render_selection_markdown(selection)
    return selection, geojson, markdown


def render_selection_markdown(selection: dict[str, Any]) -> str:
    anchor = selection["anchor"]
    aoi = selection["aoi"]
    transformations = selection["transformations"]
    forward = transformations["wgs84_to_bng"]
    inverse = transformations["bng_to_wgs84"]
    west, south, east, north = aoi["bbox_m"]

    def accuracy_text(operation: dict[str, Any]) -> str:
        accuracy = operation["accuracy_m"]
        return f"{accuracy:.3f} m" if accuracy is not None else "not published by PROJ"

    def grid_text(operation: dict[str, Any]) -> str:
        if operation["grids"]:
            return "; ".join(
                f"{grid['short_name'] or grid['full_name']} "
                f"(available={str(grid['available']).lower()})"
                for grid in operation["grids"]
            )
        return operation["grid_status"]

    centroid_text = (
        f"- WGS84 centroid: longitude `{anchor['coordinates']['longitude']:.6f}`, "
        f"latitude `{anchor['coordinates']['latitude']:.6f}`"
    )
    provider_text = (
        f"- Provider: [{anchor['source_name']}]({anchor['source_url']}) "
        f"(quality {anchor['quality']}); retrieved {anchor['retrieved_date']}"
    )
    center_text = (
        f"- Projected centre: `{aoi['center_easting_m']:.3f} m E, "
        f"{aoi['center_northing_m']:.3f} m N` ({selection['target_crs']})"
    )
    bounds_text = (
        f"- Bounds `[west, south, east, north]`: "
        f"`[{west:.3f}, {south:.3f}, {east:.3f}, {north:.3f}] m`"
    )
    lines = [
        "# AOI selection candidate",
        "",
        f"**Status:** `{selection['selection_status']}`<br>",
        f"**Coverage:** `{selection['coverage_status']}` — {selection['coverage_note']}",
        "",
        "## Anchor provenance",
        "",
        f"- Postcode: **{anchor['postcode']}**",
        centroid_text,
        f"- Meaning: {anchor['coordinate_meaning']}",
        provider_text,
        f"- Licence: {anchor['source_license']}",
        "",
        "## Candidate square",
        "",
        center_text,
        bounds_text,
        f"- Dimensions: `{aoi['width_m']:.1f} m × {aoi['height_m']:.1f} m`",
        "- This is a derived postcode-centred candidate. It is not coverage-approved or frozen.",
        "",
        "## Transformation evidence",
        "",
        (
            "PROJ network access was disabled. These records describe the operations actually used "
            "for the forward centre transform and inverse corner transform."
        ),
        "",
        f"- WGS84 → BNG operation: `{forward['name']}` — {forward['description']}",
        f"  - Reported accuracy: {accuracy_text(forward)}; grids: {grid_text(forward)}.",
        f"- BNG → WGS84 operation: `{inverse['name']}` — {inverse['description']}",
        f"  - Reported accuracy: {accuracy_text(inverse)}; grids: {grid_text(inverse)}.",
        "",
        "## Map context and limits",
        "",
        (
            "An independent OpenStreetMap view centred on the postcode showed Wrights Lane, "
            "Haslam Road, Chatto Way and Charito Road in a built-up inland context "
            "(viewed 2026-10-17, zoom 18). This check confirms map context only. EA DTM coverage, "
            "OSM/OS feature counts and local data availability have not been checked; those remain "
            "TVW-007 work."
        ),
        "",
        (
            "Map: [OpenStreetMap view](https://www.openstreetmap.org/?mlat=50.477853&mlon=-3.536013"
            "#map=18/50.477853/-3.536013). © OpenStreetMap contributors, "
            "[ODbL](https://www.openstreetmap.org/copyright). The saved screenshot is a dated "
            "map-context reference, not source geometry."
        ),
        "Provider reference: [Postcodes.io API documentation](https://postcodes.io/docs/).",
        "Coordinate reference: [pyproj Transformer documentation](https://pyproj4.github.io/pyproj/stable/api/transformer.html).",
        (
            "Saved map context: [TVW-006 postcode screenshot]"
            "(milestones/screenshots/TVW-006-postcode-context.png)."
        ),
        "",
        (
            "To regenerate after changing only the configured anchor or AOI parameters from "
            "PowerShell, run `.\\.venv\\Scripts\\python.exe -m torquay_pipeline.cli "
            "select-aoi --config ..\\config\\aoi.torquay.json --output-dir ..\\docs` "
            "from `pipeline/`."
        ),
        "",
    ]
    return "\n".join(lines)


def _encode_json(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def atomic_write_outputs(outputs: dict[Path, bytes]) -> None:
    """Stage all content beside its destination, then atomically replace each file."""
    staged: list[tuple[Path, Path]] = []
    try:
        for destination, content in outputs.items():
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{destination.name}.",
                suffix=".tmp",
                dir=destination.parent,
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            staged.append((temporary, destination))
        for temporary, destination in staged:
            os.replace(temporary, destination)
    finally:
        for temporary, _destination in staged:
            temporary.unlink(missing_ok=True)


def write_selection(
    output_dir: Path,
    selection: dict[str, Any],
    geojson: dict[str, Any],
    markdown: str,
    config_path: Path | None = None,
) -> None:
    outputs = {
        output_dir / "aoi-selection.json": _encode_json(selection),
        output_dir / "aoi-selection.geojson": _encode_json(geojson),
        output_dir / "aoi-selection.md": markdown.encode("utf-8"),
    }
    if config_path is not None:
        raw_config = json.loads(config_path.read_text(encoding="utf-8"))
        raw_config["aoi"]["center_bng_m"] = [
            selection["aoi"]["center_easting_m"],
            selection["aoi"]["center_northing_m"],
        ]
        raw_config["aoi"]["bbox_m"] = selection["aoi"]["bbox_m"]
        outputs[config_path] = _encode_json(raw_config)
    atomic_write_outputs(outputs)
