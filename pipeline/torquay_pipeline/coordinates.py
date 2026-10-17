"""Explicit WGS84 / British National Grid transforms with network grids disabled."""

from __future__ import annotations

import os
from dataclasses import dataclass
from math import isfinite
from typing import Any

os.environ["PROJ_NETWORK"] = "OFF"

from pyproj import CRS, Transformer
from pyproj.exceptions import ProjError
from pyproj.network import set_network_enabled

WGS84 = CRS.from_epsg(4326)
BRITISH_NATIONAL_GRID = CRS.from_epsg(27700)


@dataclass(frozen=True)
class OperationInfo:
    name: str
    description: str
    definition: str
    reported_accuracy_m: float | None
    accuracy_m: float | None
    grid_status: str
    grids: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "definition": self.definition,
            "reported_accuracy_m": self.reported_accuracy_m,
            "accuracy_m": self.accuracy_m,
            "grid_status": self.grid_status,
            "grids": list(self.grids),
        }


def _operation_info(transformer: Transformer) -> OperationInfo:
    try:
        operation = transformer.get_last_used_operation()
    except (AttributeError, NotImplementedError):
        operation = transformer
    if operation is None:
        operation = transformer

    reported_accuracy = float(getattr(operation, "accuracy", -1.0))
    if not isfinite(reported_accuracy):
        reported_accuracy = -1.0
    accuracy = reported_accuracy if reported_accuracy >= 0 else None
    steps = getattr(operation, "operations", ()) or (operation,)
    grids: list[dict[str, Any]] = []
    for step in steps:
        for grid in getattr(step, "grids", ()):
            grids.append(
                {
                    "short_name": getattr(grid, "short_name", ""),
                    "full_name": getattr(grid, "full_name", ""),
                    "available": bool(getattr(grid, "available", False)),
                    "url": getattr(grid, "url", ""),
                }
            )
    if not grids:
        grid_status = "no grid files listed for the operation used"
    elif all(grid["available"] for grid in grids):
        grid_status = "all grid files listed for the operation used are locally available"
    else:
        grid_status = "one or more grid files listed for the operation used are unavailable"

    return OperationInfo(
        name=str(getattr(operation, "name", "unknown")),
        description=str(
            getattr(operation, "description", "")
            or " + ".join(str(getattr(step, "name", "unknown")) for step in steps)
        ),
        definition=str(getattr(operation, "definition", "unknown")),
        reported_accuracy_m=reported_accuracy,
        accuracy_m=accuracy,
        grid_status=grid_status,
        grids=tuple(grids),
    )


def _ensure_network_disabled() -> None:
    set_network_enabled(False)


def transform_wgs84_to_bng(longitude: float, latitude: float) -> tuple[float, float, OperationInfo]:
    """Transform longitude/latitude to BNG metres using explicit x/y axis order."""
    if not isfinite(longitude) or not isfinite(latitude):
        raise ValueError("WGS84 longitude and latitude must be finite numbers")
    _ensure_network_disabled()
    try:
        transformer = Transformer.from_crs(WGS84, BRITISH_NATIONAL_GRID, always_xy=True)
        easting, northing = transformer.transform(longitude, latitude, errcheck=True)
    except ProjError as exc:
        raise ValueError(f"WGS84 to EPSG:27700 transform failed: {exc}") from exc
    if not isfinite(easting) or not isfinite(northing):
        raise ValueError("WGS84 to EPSG:27700 transform returned non-finite coordinates")
    return float(easting), float(northing), _operation_info(transformer)


def transform_bng_to_wgs84(
    eastings: list[float], northings: list[float]
) -> tuple[list[float], list[float], OperationInfo]:
    """Transform lists of BNG points to WGS84 longitude/latitude, in that order."""
    if len(eastings) != len(northings):
        raise ValueError("eastings and northings must have the same number of values")
    if not all(isfinite(value) for value in (*eastings, *northings)):
        raise ValueError("EPSG:27700 eastings and northings must be finite numbers")
    _ensure_network_disabled()
    try:
        transformer = Transformer.from_crs(BRITISH_NATIONAL_GRID, WGS84, always_xy=True)
        longitudes, latitudes = transformer.transform(eastings, northings, errcheck=True)
    except ProjError as exc:
        raise ValueError(f"EPSG:27700 to WGS84 transform failed: {exc}") from exc
    if not all(isfinite(value) for value in (*longitudes, *latitudes)):
        raise ValueError("EPSG:27700 to WGS84 transform returned non-finite coordinates")
    return (
        [float(value) for value in longitudes],
        [float(value) for value in latitudes],
        _operation_info(transformer),
    )
