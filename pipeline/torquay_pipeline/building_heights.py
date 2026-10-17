"""Explicit, testable OSM building-height parsing and fallback policy."""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import isfinite
from typing import Any

_METRIC = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(m|metres?|meters?)?\s*$", re.IGNORECASE)
_FEET = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(ft|feet|foot)\s*$", re.IGNORECASE)
_INCHES = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(in|inch|inches)\s*$", re.IGNORECASE)
_FEET_INCHES = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(?:ft|feet|foot|')\s*"
    r"(?:(\d+(?:\.\d+)?)\s*(?:in|inches|inch|\"))?\s*$",
    re.IGNORECASE,
)
_LEVELS = re.compile(r"^[1-9]\d*$")


@dataclass(frozen=True)
class HeightPolicy:
    levels_to_metres: float = 3.0
    default_height_m: float = 8.0
    minimum_height_m: float = 1.0
    maximum_height_m: float = 150.0

    def validate(self) -> None:
        values = (
            self.levels_to_metres,
            self.default_height_m,
            self.minimum_height_m,
            self.maximum_height_m,
        )
        if not all(isfinite(value) and value > 0 for value in values):
            raise ValueError("building height policy values must be finite and positive")
        if self.minimum_height_m > self.maximum_height_m:
            raise ValueError("minimum building height cannot exceed maximum building height")


@dataclass(frozen=True)
class HeightResult:
    height_m: float
    method: str
    confidence: str
    raw_height: str | None
    parsed_height_m: float | None
    parsed_unit: str | None
    raw_levels: str | None
    clamp: str | None
    fallback_reason: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "heightM": self.height_m,
            "method": self.method,
            "confidence": self.confidence,
            "rawHeight": self.raw_height,
            "parsedHeightM": self.parsed_height_m,
            "parsedUnit": self.parsed_unit,
            "rawLevels": self.raw_levels,
            "clamp": self.clamp,
            "fallbackReason": self.fallback_reason,
        }


def _positive_number(value: str) -> float | None:
    try:
        number = float(value)
    except ValueError:
        return None
    return number if isfinite(number) and number > 0 else None


def parse_height(value: str) -> tuple[float, str] | None:
    """Parse a single positive metric/feet/inches value; reject ranges and ambiguity."""
    for pattern, factor, unit in (
        (_METRIC, 1.0, "metres"),
        (_FEET, 0.3048, "feet"),
        (_INCHES, 0.0254, "inches"),
    ):
        match = pattern.fullmatch(value)
        if match:
            number = _positive_number(match.group(1))
            return (number * factor, unit) if number is not None else None
    match = _FEET_INCHES.fullmatch(value)
    if match:
        feet = _positive_number(match.group(1))
        inches = float(match.group(2) or 0)
        if feet is not None and isfinite(inches) and 0 <= inches < 12:
            return feet * 0.3048 + inches * 0.0254, "feet_inches"
        return None
    return None


def _clamp(height_m: float, policy: HeightPolicy) -> tuple[float, str | None]:
    bounded = min(max(height_m, policy.minimum_height_m), policy.maximum_height_m)
    if bounded == height_m:
        return bounded, None
    return bounded, "clamped_low" if height_m < policy.minimum_height_m else "clamped_high"


def resolve_building_height(tags: dict[str, str], policy: HeightPolicy) -> HeightResult:
    """Resolve usable `height`, then integer levels, then the configured visual default."""
    policy.validate()
    raw_height = tags.get("height")
    raw_levels = tags.get("building:levels")
    parsed_height: float | None = None
    parsed_unit: str | None = None
    failure: str | None = None

    if raw_height is not None:
        parsed = parse_height(raw_height)
        if parsed is not None:
            parsed_height, parsed_unit = parsed
            height, clamp = _clamp(parsed_height, policy)
            return HeightResult(
                height,
                "osm_height",
                "tagged_but_unverified",
                raw_height,
                parsed_height,
                parsed_unit,
                raw_levels,
                clamp,
                None,
            )
        failure = "height tag is nonpositive, malformed, nonfinite, or ambiguous"

    if raw_levels is not None:
        if _LEVELS.fullmatch(raw_levels.strip()):
            try:
                parsed_levels = int(raw_levels)
            except (ValueError, OverflowError):
                parsed_levels = 0
            if parsed_levels > 0:
                if parsed_levels > policy.maximum_height_m / policy.levels_to_metres:
                    candidate = policy.maximum_height_m + policy.levels_to_metres
                else:
                    candidate = parsed_levels * policy.levels_to_metres
            else:
                candidate = 0.0
            if isfinite(candidate) and candidate > 0:
                height, clamp = _clamp(candidate, policy)
                return HeightResult(
                    height,
                    "estimated_levels",
                    "estimated_from_tagged_levels",
                    raw_height,
                    parsed_height,
                    parsed_unit,
                    raw_levels,
                    clamp,
                    failure,
                )
        failure = (failure + "; " if failure else "") + (
            "building:levels must be a positive integer"
        )

    height, clamp = _clamp(policy.default_height_m, policy)
    return HeightResult(
        height,
        "estimated_default",
        "visual_default_estimate",
        raw_height,
        parsed_height,
        parsed_unit,
        raw_levels,
        clamp,
        failure or "no usable height or building:levels tag",
    )
