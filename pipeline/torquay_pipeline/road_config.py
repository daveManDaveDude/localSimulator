"""Strict, editable policy for the local synthetic/OSM road surface derivation."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class RoadConfigError(ValueError):
    """Raised when a road configuration is missing or unsafe."""


@dataclass(frozen=True)
class RoadConfig:
    identifier: str
    source_relative_path: str
    acquisition_buffer_m: float
    coordinate_quantization_m: float
    minimum_ribbon_area_m2: float
    surface_offset_m: float
    widths_m: dict[str, float]
    path_classes: frozenset[str]
    excluded_classes: frozenset[str]
    intermediate_path: str
    package_path: str
    qa_path: str
    preview_path: str

    def validate(self) -> None:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", self.identifier):
            raise RoadConfigError("id must use lowercase letters, digits, and single hyphens")
        for field, value, allow_zero in (
            ("acquisition_buffer_m", self.acquisition_buffer_m, True),
            ("coordinate_quantization_m", self.coordinate_quantization_m, False),
            ("minimum_ribbon_area_m2", self.minimum_ribbon_area_m2, False),
            ("surface_offset_m", self.surface_offset_m, True),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
                or (not allow_zero and value == 0)
            ):
                qualifier = "nonnegative" if allow_zero else "positive"
                raise RoadConfigError(f"{field} must be finite and {qualifier}")
        if not self.widths_m or set(self.path_classes) - set(self.widths_m):
            raise RoadConfigError("path_classes must all have configured widths")
        for highway, width in self.widths_m.items():
            if not isinstance(highway, str) or not highway:
                raise RoadConfigError("widths_m keys must be nonempty highway classes")
            if (
                isinstance(width, bool)
                or not isinstance(width, (int, float))
                or not math.isfinite(width)
                or width <= 0
            ):
                raise RoadConfigError(f"width for {highway!r} must be positive and finite")
        for field, value in (
            ("source.relative_path", self.source_relative_path),
            ("intermediate_path", self.intermediate_path),
            ("package_path", self.package_path),
            ("qa_path", self.qa_path),
            ("preview_path", self.preview_path),
        ):
            path = Path(value)
            if not value or path.is_absolute() or ".." in path.parts:
                raise RoadConfigError(f"{field} must be a safe workspace-relative path")


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RoadConfigError(f"{field} must be a finite JSON number")
    if not math.isfinite(value):
        raise RoadConfigError(f"{field} must be finite")
    return float(value)


def parse_road_config(raw: Any) -> RoadConfig:
    if not isinstance(raw, dict):
        raise RoadConfigError("config must be a JSON object")
    expected = {
        "format_version",
        "id",
        "source",
        "acquisition_buffer_m",
        "coordinate_quantization_m",
        "minimum_ribbon_area_m2",
        "surface_offset_m",
        "widths_m",
        "path_classes",
        "excluded_classes",
        "intermediate_path",
        "package_path",
        "qa_path",
        "preview_path",
    }
    if set(raw) != expected:
        missing = sorted(expected - set(raw))
        unknown = sorted(set(raw) - expected)
        raise RoadConfigError(f"config fields mismatch; missing={missing}, unknown={unknown}")
    if isinstance(raw["format_version"], bool) or raw["format_version"] != 1:
        raise RoadConfigError("format_version must be integer 1")
    source = raw["source"]
    if not isinstance(source, dict) or set(source) != {"relative_path", "manifest_namespace"}:
        raise RoadConfigError("source must contain relative_path and manifest_namespace")
    if source["manifest_namespace"] != "osm":
        raise RoadConfigError("source.manifest_namespace must be 'osm'")
    widths = raw["widths_m"]
    if not isinstance(widths, dict):
        raise RoadConfigError("widths_m must be an object")
    path_classes = raw["path_classes"]
    excluded_classes = raw["excluded_classes"]
    if not isinstance(path_classes, list) or not all(
        isinstance(item, str) for item in path_classes
    ):
        raise RoadConfigError("path_classes must be an array of strings")
    if not isinstance(excluded_classes, list) or not all(
        isinstance(item, str) for item in excluded_classes
    ):
        raise RoadConfigError("excluded_classes must be an array of strings")
    config = RoadConfig(
        identifier=str(raw["id"]),
        source_relative_path=str(source["relative_path"]),
        acquisition_buffer_m=_number(raw["acquisition_buffer_m"], "acquisition_buffer_m"),
        coordinate_quantization_m=_number(
            raw["coordinate_quantization_m"], "coordinate_quantization_m"
        ),
        minimum_ribbon_area_m2=_number(raw["minimum_ribbon_area_m2"], "minimum_ribbon_area_m2"),
        surface_offset_m=_number(raw["surface_offset_m"], "surface_offset_m"),
        widths_m={key: _number(value, f"widths_m.{key}") for key, value in widths.items()},
        path_classes=frozenset(path_classes),
        excluded_classes=frozenset(excluded_classes),
        intermediate_path=str(raw["intermediate_path"]),
        package_path=str(raw["package_path"]),
        qa_path=str(raw["qa_path"]),
        preview_path=str(raw["preview_path"]),
    )
    config.validate()
    return config


def load_road_config(path: Path) -> tuple[RoadConfig, Path, dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RoadConfigError(f"cannot read road config '{path}': {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RoadConfigError(f"road config '{path}' is invalid JSON: {exc}") from exc
    config = parse_road_config(raw)
    return config, path.resolve().parent.parent, raw
