"""Deterministic WGS84 / British National Grid transforms with network grids disabled."""

from __future__ import annotations

import os
import warnings
from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite
from typing import Any

os.environ["PROJ_NETWORK"] = "OFF"

from pyproj import CRS, Transformer
from pyproj.exceptions import ProjError
from pyproj.network import set_network_enabled
from pyproj.transformer import TransformerGroup

WGS84 = CRS.from_epsg(4326)
BRITISH_NATIONAL_GRID = CRS.from_epsg(27700)

# Pin the published 2 m Helmert fallback (EPSG operation 1314) plus BNG
# projection (EPSG operation 19916), even if a local OSTN grid is installed.
STABLE_OPERATION_CODES = frozenset({"1314", "19916"})
STABLE_OPERATION_ACCURACY_M = 2.0


@dataclass(frozen=True)
class OperationInfo:
    name: str
    description: str
    definition: str
    reported_accuracy_m: float | None
    accuracy_m: float | None
    grid_status: str
    uses_grids: bool
    grids: tuple[dict[str, Any], ...]
    best_available: bool
    preferred_missing_operations: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "definition": self.definition,
            "reported_accuracy_m": self.reported_accuracy_m,
            "accuracy_m": self.accuracy_m,
            "grid_status": self.grid_status,
            "uses_grids": self.uses_grids,
            "grids": list(self.grids),
            "best_available": self.best_available,
            "preferred_missing_operations": list(self.preferred_missing_operations),
        }


def _operation_ids(transformer: Transformer) -> set[str]:
    identifiers: set[str] = set()
    for operation in getattr(transformer, "operations", ()):
        identity = operation.to_json_dict().get("id") or {}
        authority = str(identity.get("authority", "")).upper()
        code = str(identity.get("code", ""))
        if "EPSG" in authority and code:
            identifiers.add(code)
    return identifiers


def select_stable_operation(candidates: Iterable[Transformer]) -> Transformer:
    """Select EPSG:1314 + EPSG:19916 by identity, not candidate list order."""
    matches = [
        candidate
        for candidate in candidates
        if STABLE_OPERATION_CODES.issubset(_operation_ids(candidate))
        and float(candidate.accuracy) == STABLE_OPERATION_ACCURACY_M
        and "ballpark" not in str(candidate.description).lower()
    ]
    if len(matches) != 1:
        raise ValueError(
            "cannot select the pinned non-ballpark EPSG:1314 + EPSG:19916 operation "
            "with reported 2 m accuracy from the available PROJ operations"
        )
    return matches[0]


def _grid_record(grid: Any) -> dict[str, Any]:
    return {
        "short_name": getattr(grid, "short_name", ""),
        "full_name": getattr(grid, "full_name", ""),
        "available": bool(getattr(grid, "available", False)),
        "url": getattr(grid, "url", ""),
    }


def _missing_operation_records(group: TransformerGroup) -> tuple[dict[str, Any], ...]:
    records = []
    for operation in group.unavailable_operations:
        grids = tuple(_grid_record(grid) for grid in getattr(operation, "grids", ()))
        records.append(
            {
                "name": str(operation.name),
                "reported_accuracy_m": float(operation.accuracy)
                if isfinite(float(operation.accuracy)) and operation.accuracy >= 0
                else None,
                "grids": list(grids),
            }
        )
    return tuple(
        sorted(records, key=lambda record: (record["name"], record["reported_accuracy_m"] or 0))
    )


def _operation_info(transformer: Transformer, group: TransformerGroup) -> OperationInfo:
    steps = getattr(transformer, "operations", ()) or (transformer,)
    grids = tuple(_grid_record(grid) for step in steps for grid in getattr(step, "grids", ()))
    uses_grids = bool(grids)
    if not uses_grids:
        grid_status = "selected EPSG:1314 + EPSG:19916 operation uses no grid files"
    elif all(grid["available"] for grid in grids):
        grid_status = "all grid files used by the selected operation are locally available"
    else:
        grid_status = "one or more grid files used by the selected operation are unavailable"
    accuracy = float(transformer.accuracy)
    if not isfinite(accuracy) or accuracy < 0:
        raise ValueError("pinned EPSG:1314 operation did not report a finite accuracy")
    return OperationInfo(
        name="EPSG:1314 + EPSG:19916",
        description=str(transformer.description),
        definition=str(transformer.definition),
        reported_accuracy_m=accuracy,
        accuracy_m=accuracy,
        grid_status=grid_status,
        uses_grids=uses_grids,
        grids=grids,
        best_available=bool(group.best_available),
        preferred_missing_operations=_missing_operation_records(group),
    )


def _group(source: CRS, target: CRS) -> tuple[Transformer, TransformerGroup]:
    set_network_enabled(False)
    try:
        # PROJ warns when its highest-accuracy grid operation is unavailable.
        # That fact is recorded in OperationInfo; suppressing the incidental
        # warning keeps CLI output actionable and deterministic.
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Best transformation is not available")
            group = TransformerGroup(source, target, always_xy=True, allow_ballpark=False)
        return select_stable_operation(group.transformers), group
    except ProjError as exc:
        raise ValueError(
            f"cannot construct pinned EPSG:1314 + EPSG:19916 operation: {exc}"
        ) from exc


def pinned_transformer(source_epsg: int, target_epsg: int) -> tuple[Transformer, OperationInfo]:
    """Return the deterministic non-ballpark project transform used by this pipeline."""
    try:
        source = CRS.from_epsg(source_epsg)
        target = CRS.from_epsg(target_epsg)
        transformer, group = _group(source, target)
        return transformer, _operation_info(transformer, group)
    except ProjError as exc:
        raise ValueError(
            f"cannot construct pinned EPSG:{source_epsg} to EPSG:{target_epsg} operation: {exc}"
        ) from exc


def transform_wgs84_to_bng(longitude: float, latitude: float) -> tuple[float, float, OperationInfo]:
    """Transform longitude/latitude with explicit x/y order and pinned EPSG operations."""
    if not isfinite(longitude) or not isfinite(latitude):
        raise ValueError("WGS84 longitude and latitude must be finite numbers")
    transformer, group = _group(WGS84, BRITISH_NATIONAL_GRID)
    try:
        easting, northing = transformer.transform(longitude, latitude, errcheck=True)
    except ProjError as exc:
        raise ValueError(f"WGS84 to EPSG:27700 transform failed: {exc}") from exc
    if not isfinite(easting) or not isfinite(northing):
        raise ValueError("WGS84 to EPSG:27700 transform returned non-finite coordinates")
    return float(easting), float(northing), _operation_info(transformer, group)


def transform_bng_to_wgs84(
    eastings: list[float], northings: list[float]
) -> tuple[list[float], list[float], OperationInfo]:
    """Transform BNG coordinates to longitude/latitude with pinned EPSG operations."""
    if len(eastings) != len(northings):
        raise ValueError("eastings and northings must have the same number of values")
    if not all(isfinite(value) for value in (*eastings, *northings)):
        raise ValueError("EPSG:27700 eastings and northings must be finite numbers")
    transformer, group = _group(BRITISH_NATIONAL_GRID, WGS84)
    try:
        longitudes, latitudes = transformer.transform(eastings, northings, errcheck=True)
    except ProjError as exc:
        raise ValueError(f"EPSG:27700 to WGS84 transform failed: {exc}") from exc
    if not all(isfinite(value) for value in (*longitudes, *latitudes)):
        raise ValueError("EPSG:27700 to WGS84 transform returned non-finite coordinates")
    return (
        [float(value) for value in longitudes],
        [float(value) for value in latitudes],
        _operation_info(transformer, group),
    )
