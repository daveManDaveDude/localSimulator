"""Build a bounded, source-bound visual terrain derivative for a road preview.

The derivative never changes the EA heightfield or road source geometry. It
uses the pinned current release's configured ground-assumed vehicle centerlines
to produce a separate display grid for the comparison route.
"""

from __future__ import annotations

import hashlib
import heapq
import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from pyproj import Transformer
from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)

from .road_alignment import CURRENT_RELEASE_ID, sha256_file
from .terrain_export import _sample_bilinear_mosaic

ALGORITHM_VERSION = "road-surface-preview-1.0.0"
OUTPUT_FILES = frozenset({"manifest.json", "heightfield.f32", "qa.json"})
RUNTIME_FILES = (
    "buildings/buildings.json",
    "buildings/manifest.json",
    "buildings/qa.json",
    "heightfield.f32",
    "manifest.json",
    "qa.json",
    "roads/manifest.json",
    "roads/qa.json",
    "roads/roads.json",
    "scene-qa.json",
)
MAX_PROFILE_STATION_SPACING_M = 5.0
SPATIAL_TILE_M = 16.0
ROAD_SURFACE_OFFSET_M = 0.05
SIGNIFICANT_ADDED_GRADIENT_THRESHOLD_M_PER_M = 1.0
PROFILE_WAY_IDS = (78455388, 78455395, 30480989, 1363931058, 30482119, 30482121, 46348326)
FALLBACK_MIN_CONNECTED_AREA_M2 = 8.0


class RoadSurfaceError(ValueError):
    """Raised when inputs, output safety, or the preview geometry are invalid."""


@dataclass(frozen=True)
class PreviewConfig:
    release_id: str
    output_directory: str
    transition_distance_factor: float
    ambiguity_distance_m: float
    ambiguity_height_difference_m: float
    maximum_changed_height_m: float
    fallback_absolute_change_m: float
    fallback_added_gradient_m_per_m: float
    fallback_minimum_region_area_m2: float
    fallback_fade_distance_m: float


@dataclass(frozen=True)
class RoadSegment:
    sort_key: tuple[str, int, int]
    way_id: int
    name: str
    width_m: float
    first_x: float
    first_z: float
    dx: float
    dz: float
    length_squared: float
    influence_m: float

    @property
    def length_m(self) -> float:
        return math.sqrt(self.length_squared)


@dataclass(frozen=True)
class Projection:
    segment_index: int
    way_id: int
    distance_m: float
    x: float
    z: float
    target_y: float
    width_m: float
    part_index: int
    segment_index_in_part: int


@dataclass(frozen=True)
class ReleaseInputs:
    release_root: Path
    release_id: str
    ready_sha256: str
    inventory_sha256: str
    manifest: dict[str, Any]
    manifest_sha256: str
    road_manifest: dict[str, Any]
    road_manifest_sha256: str
    road_payload: dict[str, Any]
    road_payload_sha256: str
    baseline: np.ndarray
    columns: int
    rows: int
    spacing_m: float
    width_m: float
    depth_m: float
    origin_e_m: float
    origin_n_m: float
    origin_y_m: float
    buildings: dict[str, Any]
    source_hashes: dict[str, dict[str, Any]]


def load_config(path: Path) -> PreviewConfig:
    """Load the exact accepted config shape and reject altered release/output roots."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RoadSurfaceError(f"cannot read preview config '{path}': {exc}") from exc
    expected = {
        "format_version",
        "release_id",
        "output_directory",
        "transition_distance_factor",
        "ambiguity_distance_m",
        "ambiguity_height_difference_m",
        "maximum_changed_height_m",
        "fallback_absolute_change_m",
        "fallback_added_gradient_m_per_m",
        "fallback_minimum_region_area_m2",
        "fallback_fade_distance_m",
    }
    if not isinstance(raw, dict) or set(raw) != expected:
        raise RoadSurfaceError("preview config has an invalid object shape")
    if (
        raw["format_version"] != 1
        or raw["release_id"] != CURRENT_RELEASE_ID
        or raw["output_directory"] != "public/worlds/torquay-road-surface-preview"
        or raw["transition_distance_factor"] != 1.0
    ):
        raise RoadSurfaceError("preview config does not match the accepted pinned output policy")
    for name in (
        "ambiguity_distance_m",
        "ambiguity_height_difference_m",
        "maximum_changed_height_m",
        "fallback_absolute_change_m",
        "fallback_added_gradient_m_per_m",
        "fallback_minimum_region_area_m2",
        "fallback_fade_distance_m",
    ):
        value = raw[name]
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value <= 0
        ):
            raise RoadSurfaceError(f"preview config {name} must be positive and finite")
    return PreviewConfig(
        release_id=raw["release_id"],
        output_directory=raw["output_directory"],
        transition_distance_factor=float(raw["transition_distance_factor"]),
        ambiguity_distance_m=float(raw["ambiguity_distance_m"]),
        ambiguity_height_difference_m=float(raw["ambiguity_height_difference_m"]),
        maximum_changed_height_m=float(raw["maximum_changed_height_m"]),
        fallback_absolute_change_m=float(raw["fallback_absolute_change_m"]),
        fallback_added_gradient_m_per_m=float(raw["fallback_added_gradient_m_per_m"]),
        fallback_minimum_region_area_m2=float(raw["fallback_minimum_region_area_m2"]),
        fallback_fade_distance_m=float(raw["fallback_fade_distance_m"]),
    )


def _json_object(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        contents = path.read_bytes()
        value = json.loads(contents.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoadSurfaceError(f"cannot read JSON input '{path}': {exc}") from exc
    if not isinstance(value, dict):
        raise RoadSurfaceError(f"JSON input '{path}' must be an object")
    return value, contents


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _is_reparse_point(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction()) if callable(is_junction) else False


def _assert_no_reparse_components(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    cursor = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        cursor = cursor / component
        if _is_reparse_point(cursor):
            raise RoadSurfaceError(f"path crosses a symlink or junction: '{cursor}'")


def _paths_overlap(first: Path, second: Path) -> bool:
    a = os.path.normcase(str(first.resolve(strict=False)))
    b = os.path.normcase(str(second.resolve(strict=False)))
    try:
        return os.path.commonpath([a, b]) in (a, b)
    except ValueError:
        return False


def guard_output_directory(project_root: Path, requested: Path, protected: list[Path]) -> Path:
    """Guard the exact owned derivative directory before creating or replacing files."""
    project_root = project_root.resolve()
    expected = project_root / "public/worlds/torquay-road-surface-preview"
    candidate = requested if requested.is_absolute() else project_root / requested
    _assert_no_reparse_components(candidate)
    resolved = candidate.resolve(strict=False)
    if os.path.normcase(str(resolved)) != os.path.normcase(str(expected)):
        raise RoadSurfaceError(
            "output directory must be exactly public/worlds/torquay-road-surface-preview"
        )
    _assert_no_reparse_components(project_root / "public/worlds")
    _assert_no_reparse_components(resolved)
    for source in protected:
        if _paths_overlap(resolved, source):
            raise RoadSurfaceError(f"output directory overlaps protected input '{source}'")
    if resolved.exists() and not resolved.is_dir():
        raise RoadSurfaceError("output directory exists but is not a directory")
    if resolved.is_dir():
        for child in resolved.iterdir():
            if child.name not in OUTPUT_FILES or child.is_dir() or _is_reparse_point(child):
                raise RoadSurfaceError(
                    f"output directory contains an unowned or unsafe entry: '{child.name}'"
                )
    return resolved


def _protected_execution_inputs(project_root: Path) -> list[Path]:
    """Files and source roots an execution record must never be able to replace."""
    return [
        project_root / "AGENTS.md",
        project_root / ".codex/torquay-plan-implementation.md",
        project_root / "docs/project-plan.md",
        project_root / "docs/asset-contract.md",
        project_root / "docs/milestones/Road-alignment.md",
        project_root / "docs/milestones/Road-surface-treatment-spec.md",
        project_root / "config/road-surface-preview.json",
        project_root / "scripts/build-road-surface-preview.py",
        project_root / "pipeline/torquay_pipeline/road_surface.py",
        project_root / "data/source-manifest.json",
        project_root / "data/raw/ea_dtm",
        project_root / "public/worlds/torquay-poc-001-2km",
        project_root / "public/worlds/torquay-poc-001",
    ]


def _preflight_execution_record(project_root: Path, requested: Path | None) -> Path | None:
    """Validate an absent, direct-child record path before doing any build work."""
    if requested is None:
        return None
    evidence_root = project_root / "docs/milestones/artifacts/Road-surface-treatment"
    if not evidence_root.is_dir():
        raise RoadSurfaceError("the dedicated Road-surface-treatment evidence directory is missing")
    _assert_no_reparse_components(evidence_root)
    canonical_root = evidence_root.resolve(strict=True)
    candidate = requested if requested.is_absolute() else project_root / requested
    if ".." in candidate.parts:
        raise RoadSurfaceError("execution record path cannot use parent-directory aliases")
    _assert_no_reparse_components(candidate.parent)
    if _is_reparse_point(candidate):
        raise RoadSurfaceError("execution record destination cannot be a symlink or junction")
    canonical_candidate = candidate.resolve(strict=False)
    if (
        canonical_candidate == canonical_root
        or canonical_candidate.parent != canonical_root
        or os.path.normcase(candidate.name) != candidate.name.casefold()
        or not candidate.name.startswith("build-")
        or not candidate.name.endswith(".json")
        or not candidate.name[6:-5].isdigit()
    ):
        raise RoadSurfaceError(
            "execution record must be a direct build-N.json child of the dedicated "
            "Road-surface-treatment evidence directory"
        )
    if os.path.normcase(str(canonical_candidate.parent)) != os.path.normcase(str(canonical_root)):
        raise RoadSurfaceError("execution record destination is not canonically contained")
    for protected in _protected_execution_inputs(project_root):
        if _paths_overlap(canonical_candidate, protected):
            raise RoadSurfaceError(f"execution record overlaps protected input '{protected}'")
    if candidate.exists() or candidate.is_symlink() or _is_reparse_point(candidate):
        raise RoadSurfaceError(
            "execution record destination already exists; refusing to overwrite it"
        )
    return canonical_candidate


def _prepare_output_directory(project_root: Path, requested: Path, protected: list[Path]) -> Path:
    """Create only the exact missing ignored derivative directory and recheck it."""
    output = guard_output_directory(project_root, requested, protected)
    if not output.exists():
        parent = output.parent
        _assert_no_reparse_components(parent)
        if not parent.is_dir():
            raise RoadSurfaceError("approved derivative output parent does not exist")
        try:
            output.mkdir(exist_ok=False)
        except FileExistsError as exc:
            raise RoadSurfaceError("approved derivative output appeared during creation") from exc
        _assert_no_reparse_components(output)
    return guard_output_directory(project_root, output, protected)


def _validate_inventory(
    project_root: Path, release_id: str
) -> tuple[Path, dict[str, Any], dict[str, dict[str, Any]], dict[str, str]]:
    world_root = project_root / "public/worlds/torquay-poc-001-2km"
    ready_path = world_root / "ready.json"
    ready, ready_bytes = _json_object(ready_path)
    if ready.get("releaseId") != release_id:
        raise RoadSurfaceError("ready.json does not select the accepted pinned current_2km release")
    release_root = world_root / "releases" / release_id
    inventory_path = release_root / "inventory.json"
    inventory, inventory_bytes = _json_object(inventory_path)
    inventory_hash = hashlib.sha256(inventory_bytes).hexdigest()
    if (
        ready.get("inventorySha256") != inventory_hash
        or ready.get("inventoryByteLength") != len(inventory_bytes)
        or inventory.get("releaseId") != release_id
        or inventory.get("worldId") != "torquay-poc-001"
        or inventory.get("sceneProfile") != "current_2km"
    ):
        raise RoadSurfaceError("ready pointer or inventory does not bind the pinned release")
    files_value = inventory.get("files")
    if not isinstance(files_value, list) or len(files_value) != len(RUNTIME_FILES):
        raise RoadSurfaceError("pinned release inventory has the wrong runtime file count")
    descriptors: dict[str, dict[str, Any]] = {}
    for item in files_value:
        if not isinstance(item, dict) or set(item) != {"path", "byteLength", "sha256"}:
            raise RoadSurfaceError("pinned release inventory contains a malformed file record")
        path = item.get("path")
        if path not in RUNTIME_FILES or path in descriptors:
            raise RoadSurfaceError("pinned release inventory contains an unowned or duplicate path")
        if not isinstance(item.get("byteLength"), int) or item["byteLength"] <= 0:
            raise RoadSurfaceError(f"pinned release byte length is invalid for '{path}'")
        if not isinstance(item.get("sha256"), str) or len(item["sha256"]) != 64:
            raise RoadSurfaceError(f"pinned release SHA-256 is invalid for '{path}'")
        descriptors[path] = item
    if tuple(descriptors) != RUNTIME_FILES:
        raise RoadSurfaceError("pinned release inventory file order is not deterministic")
    release_body = {
        key: inventory[key] for key in ("formatVersion", "worldId", "sceneProfile", "files")
    }
    derived_release_id = hashlib.sha256(_canonical_json(release_body)).hexdigest()
    if derived_release_id != release_id:
        raise RoadSurfaceError(
            "pinned release inventory body does not hash to the selected release ID"
        )
    ready_hash = hashlib.sha256(ready_bytes).hexdigest()
    return (
        release_root,
        inventory,
        descriptors,
        {
            "readySha256": ready_hash,
            "inventorySha256": inventory_hash,
            "inventoryByteLength": str(len(inventory_bytes)),
        },
    )


def _hash_bound_file(
    path: Path, descriptor: dict[str, Any], label: str
) -> tuple[bytes, dict[str, Any]]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise RoadSurfaceError(f"cannot read pinned {label} '{path}': {exc}") from exc
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != descriptor["byteLength"] or digest != descriptor["sha256"]:
        raise RoadSurfaceError(f"pinned {label} does not match its release inventory record")
    return data, {"path": path.as_posix(), "byteLength": len(data), "sha256": digest}


def load_release_inputs(project_root: Path, config: PreviewConfig) -> ReleaseInputs:
    """Validate and read only the pinned current release's geometry and terrain."""
    release_root, _inventory, descriptors, pointer = _validate_inventory(
        project_root, config.release_id
    )
    required = (
        "manifest.json",
        "heightfield.f32",
        "roads/manifest.json",
        "roads/roads.json",
        "buildings/buildings.json",
    )
    input_bytes: dict[str, bytes] = {}
    input_records: dict[str, dict[str, Any]] = {}
    for relative in required:
        data, record = _hash_bound_file(release_root / relative, descriptors[relative], relative)
        input_bytes[relative] = data
        input_records[relative] = record
    try:
        manifest = json.loads(input_bytes["manifest.json"].decode("utf-8"))
        road_manifest = json.loads(input_bytes["roads/manifest.json"].decode("utf-8"))
        road_payload = json.loads(input_bytes["roads/roads.json"].decode("utf-8"))
        buildings = json.loads(input_bytes["buildings/buildings.json"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoadSurfaceError(f"pinned release JSON is invalid: {exc}") from exc
    if not all(
        isinstance(value, dict) for value in (manifest, road_manifest, road_payload, buildings)
    ):
        raise RoadSurfaceError("pinned release packages must be JSON objects")
    heightfield = manifest.get("heightfield")
    extent = manifest.get("extentM")
    origin = manifest.get("origin")
    if (
        manifest.get("sceneProfile") != "current_2km"
        or manifest.get("worldType") != "real"
        or manifest.get("id") != "torquay-poc-001"
        or not isinstance(heightfield, dict)
        or not isinstance(extent, dict)
        or not isinstance(origin, dict)
        or heightfield.get("path") != "heightfield.f32"
        or heightfield.get("columns") != 1001
        or heightfield.get("rows") != 1001
        or heightfield.get("spacingM") != 2.0
        or extent.get("width") != 2000.0
        or extent.get("depth") != 2000.0
        or heightfield.get("sha256") != input_records["heightfield.f32"]["sha256"]
    ):
        raise RoadSurfaceError(
            "pinned terrain manifest does not match the accepted current_2km grid"
        )
    expected_road_identity = road_manifest.get("terrainIdentity")
    if (
        road_manifest.get("sceneProfile") != "current_2km"
        or road_manifest.get("worldId") != manifest["id"]
        or not isinstance(expected_road_identity, dict)
        or expected_road_identity.get("manifestSha256") != input_records["manifest.json"]["sha256"]
        or expected_road_identity.get("heightfieldSha256")
        != input_records["heightfield.f32"]["sha256"]
        or road_payload.get("worldId") != manifest["id"]
        or road_payload.get("sceneProfile") != "current_2km"
    ):
        raise RoadSurfaceError("published road package is not bound to the pinned terrain identity")
    heights = np.frombuffer(input_bytes["heightfield.f32"], dtype="<f4")
    if heights.size != 1001 * 1001 or not np.isfinite(heights).all():
        raise RoadSurfaceError("pinned terrain heightfield is malformed")
    baseline = heights.reshape(1001, 1001).copy()
    return ReleaseInputs(
        release_root=release_root,
        release_id=config.release_id,
        ready_sha256=pointer["readySha256"],
        inventory_sha256=pointer["inventorySha256"],
        manifest=manifest,
        manifest_sha256=input_records["manifest.json"]["sha256"],
        road_manifest=road_manifest,
        road_manifest_sha256=input_records["roads/manifest.json"]["sha256"],
        road_payload=road_payload,
        road_payload_sha256=input_records["roads/roads.json"]["sha256"],
        baseline=baseline,
        columns=1001,
        rows=1001,
        spacing_m=2.0,
        width_m=2000.0,
        depth_m=2000.0,
        origin_e_m=float(origin["eastingM"]),
        origin_n_m=float(origin["northingM"]),
        origin_y_m=float(origin["elevationM"]),
        buildings=buildings,
        source_hashes={
            **input_records,
            "ready.json": {"path": "public/worlds/torquay-poc-001-2km/ready.json", **pointer},
            "inventory.json": {
                "path": (release_root / "inventory.json").as_posix(),
                "byteLength": int(pointer["inventoryByteLength"]),
                "sha256": pointer["inventorySha256"],
            },
        },
    )


def _sample_grid(heights: np.ndarray, x: float, z: float, spacing_m: float) -> float:
    rows, columns = heights.shape
    width = (columns - 1) * spacing_m
    depth = (rows - 1) * spacing_m
    half_width, half_depth = width / 2, depth / 2
    if (
        not math.isfinite(x)
        or not math.isfinite(z)
        or not (-half_width <= x <= half_width and -half_depth <= z <= half_depth)
    ):
        raise RoadSurfaceError(f"terrain sample ({x}, {z}) falls outside the grid")
    gx, gz = (x + half_width) / spacing_m, (z + half_depth) / spacing_m
    column, row = min(math.floor(gx), columns - 2), min(math.floor(gz), rows - 2)
    u, v = gx - column, gz - row
    a, b = float(heights[row, column]), float(heights[row, column + 1])
    c, d = float(heights[row + 1, column]), float(heights[row + 1, column + 1])
    if u + v <= 1:
        return a + (b - a) * u + (c - a) * v
    return d + (c - d) * (1 - u) + (b - d) * (1 - v)


def _segments_from_payload(
    payload: dict[str, Any], transition_factor: float, spacing_m: float
) -> list[RoadSegment]:
    features = payload.get("features")
    if not isinstance(features, list):
        raise RoadSurfaceError("pinned roads payload has no feature array")
    segments: list[RoadSegment] = []
    for feature in features:
        if not isinstance(feature, dict) or feature.get("displayGroup") != "vehicular":
            continue
        if (
            feature.get("groundAssumption")
            != "ground_assumed_from_absent_or_explicit_no_vertical_tags"
        ):
            continue
        width = feature.get("estimatedWidthM")
        source = feature.get("source")
        parts = feature.get("centerlinePartsXZ")
        if (
            not isinstance(width, (int, float))
            or isinstance(width, bool)
            or not math.isfinite(width)
            or width <= 0
            or not isinstance(source, dict)
            or not isinstance(source.get("osmId"), int)
            or not isinstance(parts, list)
        ):
            raise RoadSurfaceError(
                "eligible published road feature has invalid width, identity, or centerline"
            )
        way_id = int(source["osmId"])
        stable_id = str(feature.get("id", f"way/{way_id}"))
        name = str(feature.get("sourceTags", {}).get("name", way_id))
        half_width = float(width) / 2
        transition = max(float(width), 2 * spacing_m) * transition_factor
        influence = half_width + transition
        for part_index, part in enumerate(parts):
            if not isinstance(part, list):
                raise RoadSurfaceError(f"way {way_id} centerline part is malformed")
            for segment_index, (first, second) in enumerate(zip(part, part[1:], strict=False)):
                if (
                    not isinstance(first, list)
                    or not isinstance(second, list)
                    or len(first) != 2
                    or len(second) != 2
                ):
                    raise RoadSurfaceError(f"way {way_id} contains a malformed centerline vertex")
                x0, z0 = float(first[0]), float(first[1])
                x1, z1 = float(second[0]), float(second[1])
                if not all(math.isfinite(value) for value in (x0, z0, x1, z1)):
                    raise RoadSurfaceError(
                        f"way {way_id} contains non-finite centerline coordinates"
                    )
                dx, dz = x1 - x0, z1 - z0
                length_squared = dx * dx + dz * dz
                if length_squared <= 1e-12:
                    continue
                segments.append(
                    RoadSegment(
                        sort_key=(stable_id, part_index, segment_index),
                        way_id=way_id,
                        name=name,
                        width_m=float(width),
                        first_x=x0,
                        first_z=z0,
                        dx=dx,
                        dz=dz,
                        length_squared=length_squared,
                        influence_m=influence,
                    )
                )
    return sorted(segments, key=lambda item: item.sort_key)


def _project(
    segment_index: int,
    segment: RoadSegment,
    x: float,
    z: float,
    baseline: np.ndarray,
    spacing_m: float,
) -> Projection:
    amount = max(
        0.0,
        min(
            1.0,
            ((x - segment.first_x) * segment.dx + (z - segment.first_z) * segment.dz)
            / segment.length_squared,
        ),
    )
    projected_x = segment.first_x + segment.dx * amount
    projected_z = segment.first_z + segment.dz * amount
    distance = math.hypot(projected_x - x, projected_z - z)
    return Projection(
        segment_index=segment_index,
        way_id=segment.way_id,
        distance_m=distance,
        x=projected_x,
        z=projected_z,
        target_y=_sample_grid(baseline, projected_x, projected_z, spacing_m),
        width_m=segment.width_m,
        part_index=segment.sort_key[1],
        segment_index_in_part=segment.sort_key[2],
    )


def _projection_key(
    projection: Projection, segments: list[RoadSegment]
) -> tuple[float, str, int, int]:
    segment = segments[projection.segment_index]
    return (
        projection.distance_m,
        segment.sort_key[0],
        projection.part_index,
        projection.segment_index_in_part,
    )


def _blend_weight(distance: float, half_width: float, transition: float) -> float:
    if distance <= half_width:
        return 1.0
    if distance >= half_width + transition:
        return 0.0
    position = (distance - half_width) / transition
    return 1 - (3 * position * position - 2 * position * position * position)


def _grid_tile_range(tile_index: int, spacing_m: float, half_extent: float, count: int) -> range:
    lower = math.ceil((tile_index * SPATIAL_TILE_M + half_extent) / spacing_m)
    upper_exclusive = math.ceil(((tile_index + 1) * SPATIAL_TILE_M + half_extent) / spacing_m)
    return range(max(0, lower), min(count, upper_exclusive))


def _mask_components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    """Return deterministic 8-connected components for a sparse grid mask."""
    rows, columns = mask.shape
    remaining = set(int(value) for value in np.flatnonzero(mask))
    components: list[list[tuple[int, int]]] = []
    while remaining:
        first = min(remaining)
        remaining.remove(first)
        stack = [first]
        component = []
        while stack:
            index = stack.pop()
            row, column = divmod(index, columns)
            component.append((row, column))
            for delta_row in (-1, 0, 1):
                for delta_column in (-1, 0, 1):
                    if delta_row == 0 and delta_column == 0:
                        continue
                    neighbor_row = row + delta_row
                    neighbor_column = column + delta_column
                    if 0 <= neighbor_row < rows and 0 <= neighbor_column < columns:
                        neighbor = neighbor_row * columns + neighbor_column
                        if neighbor in remaining:
                            remaining.remove(neighbor)
                            stack.append(neighbor)
        components.append(sorted(component))
    return components


def _connected_fallback_regions(
    baseline: np.ndarray,
    candidate: np.ndarray,
    spacing_m: float,
    config: PreviewConfig,
    width_m: float,
    depth_m: float,
) -> list[dict[str, Any]]:
    """Select only connected local components meeting the documented harm heuristic."""
    baseline_x = np.abs(np.diff(baseline.astype(np.float64), axis=1)) / spacing_m
    candidate_x = np.abs(np.diff(candidate.astype(np.float64), axis=1)) / spacing_m
    baseline_z = np.abs(np.diff(baseline.astype(np.float64), axis=0)) / spacing_m
    candidate_z = np.abs(np.diff(candidate.astype(np.float64), axis=0)) / spacing_m
    added_x = np.maximum(candidate_x - baseline_x, 0.0)
    added_z = np.maximum(candidate_z - baseline_z, 0.0)
    seed_mask = np.abs(candidate.astype(np.float64) - baseline.astype(np.float64)) >= (
        config.fallback_absolute_change_m
    )
    steep_x = added_x >= config.fallback_added_gradient_m_per_m
    steep_z = added_z >= config.fallback_added_gradient_m_per_m
    seed_mask[:, :-1] |= steep_x
    seed_mask[:, 1:] |= steep_x
    seed_mask[:-1, :] |= steep_z
    seed_mask[1:, :] |= steep_z
    components = _mask_components(seed_mask)
    half_width, half_depth = width_m / 2, depth_m / 2
    delta = candidate.astype(np.float64) - baseline.astype(np.float64)
    output = []
    for component in components:
        vertex_mask = np.zeros(seed_mask.shape, dtype=bool)
        rows = np.asarray([point[0] for point in component], dtype=np.intp)
        columns = np.asarray([point[1] for point in component], dtype=np.intp)
        vertex_mask[rows, columns] = True
        cell_area = len(component) * spacing_m * spacing_m
        x_edges = vertex_mask[:, :-1] | vertex_mask[:, 1:]
        z_edges = vertex_mask[:-1, :] | vertex_mask[1:, :]
        maximum_added_gradient = max(
            float(np.max(added_x[x_edges])) if np.any(x_edges) else 0.0,
            float(np.max(added_z[z_edges])) if np.any(z_edges) else 0.0,
        )
        maximum_change = float(np.max(np.abs(delta[vertex_mask])))
        cut_fill_trigger = maximum_change >= config.fallback_absolute_change_m
        gradient_trigger = (
            maximum_added_gradient >= config.fallback_added_gradient_m_per_m
            and cell_area >= config.fallback_minimum_region_area_m2
        )
        if not (cut_fill_trigger or gradient_trigger):
            continue
        maximum_index = int(np.argmax(np.abs(delta[vertex_mask])))
        maximum_row = int(rows[maximum_index])
        maximum_column = int(columns[maximum_index])
        if maximum_change < config.fallback_absolute_change_m:
            if np.any(x_edges) and float(np.max(added_x[x_edges])) >= maximum_added_gradient:
                local_index = np.argmax(np.where(x_edges, added_x, -1.0))
                edge_row, edge_column = np.unravel_index(local_index, added_x.shape)
                maximum_row, maximum_column = int(edge_row), int(edge_column)
            else:
                local_index = np.argmax(np.where(z_edges, added_z, -1.0))
                edge_row, edge_column = np.unravel_index(local_index, added_z.shape)
                maximum_row, maximum_column = int(edge_row), int(edge_column)
        x_max = float(np.max(np.where(x_edges, added_x, -1.0))) if np.any(x_edges) else -1.0
        z_max = float(np.max(np.where(z_edges, added_z, -1.0))) if np.any(z_edges) else -1.0
        if x_max >= z_max and x_max >= 0.0:
            edge_row, edge_column = np.unravel_index(
                int(np.argmax(np.where(x_edges, added_x, -1.0))), added_x.shape
            )
            edge_axis = "x"
            edge_first = [
                float(edge_column * spacing_m - half_width),
                float(edge_row * spacing_m - half_depth),
            ]
            edge_second = [edge_first[0] + spacing_m, edge_first[1]]
            edge_baseline = float(baseline_x[edge_row, edge_column])
            edge_candidate = float(candidate_x[edge_row, edge_column])
            edge_increase = float(added_x[edge_row, edge_column])
        elif z_max >= 0.0:
            edge_row, edge_column = np.unravel_index(
                int(np.argmax(np.where(z_edges, added_z, -1.0))), added_z.shape
            )
            edge_axis = "z"
            edge_first = [
                float(edge_column * spacing_m - half_width),
                float(edge_row * spacing_m - half_depth),
            ]
            edge_second = [edge_first[0], edge_first[1] + spacing_m]
            edge_baseline = float(baseline_z[edge_row, edge_column])
            edge_candidate = float(candidate_z[edge_row, edge_column])
            edge_increase = float(added_z[edge_row, edge_column])
        else:
            edge_axis, edge_first, edge_second = None, None, None
            edge_baseline, edge_candidate, edge_increase = 0.0, 0.0, 0.0
        output.append(
            {
                "corePoints": component,
                "coreVertexCount": len(component),
                "coreAreaEquivalentM2": cell_area,
                "coreLocalBoundsXZ": [
                    float(np.min(columns) * spacing_m - half_width),
                    float(np.min(rows) * spacing_m - half_depth),
                    float(np.max(columns) * spacing_m - half_width),
                    float(np.max(rows) * spacing_m - half_depth),
                ],
                "maximumCandidateAbsoluteChangeM": maximum_change,
                "maximumCandidateChangeLocalXZ": [
                    float(maximum_column * spacing_m - half_width),
                    float(maximum_row * spacing_m - half_depth),
                ],
                "maximumCandidateAddedGradientMPerM": maximum_added_gradient,
                "maximumCandidateAddedGradientEdge": {
                    "axis": edge_axis,
                    "firstLocalXZ": edge_first,
                    "secondLocalXZ": edge_second,
                    "baselineMagnitudeMPerM": edge_baseline,
                    "candidateMagnitudeMPerM": edge_candidate,
                    "addedMagnitudeMPerM": edge_increase,
                },
                "harmTriggers": [
                    trigger
                    for trigger, active in (
                        ("absolute local cut/fill threshold", cut_fill_trigger),
                        ("connected added-gradient threshold and minimum area", gradient_trigger),
                    )
                    if active
                ],
            }
        )
    return output


def _fallback_distance_weights(
    component: list[tuple[int, int]],
    rows: int,
    columns: int,
    spacing_m: float,
    fade_distance_m: float,
) -> tuple[int, int, np.ndarray]:
    """Build zero-ended smoothstep weights from a core using an 8-neighbour metric."""
    fade_cells = math.ceil(fade_distance_m / spacing_m)
    min_row = max(0, min(row for row, _column in component) - fade_cells)
    max_row = min(rows - 1, max(row for row, _column in component) + fade_cells)
    min_column = max(0, min(column for _row, column in component) - fade_cells)
    max_column = min(columns - 1, max(column for _row, column in component) + fade_cells)
    local_distances = np.full(
        (max_row - min_row + 1, max_column - min_column + 1), np.inf, dtype=np.float64
    )
    queue: list[tuple[float, int, int]] = []
    for row, column in component:
        local_row, local_column = row - min_row, column - min_column
        local_distances[local_row, local_column] = 0.0
        heapq.heappush(queue, (0.0, local_row, local_column))
    neighbours = tuple(
        (delta_row, delta_column, spacing_m * math.hypot(delta_row, delta_column))
        for delta_row in (-1, 0, 1)
        for delta_column in (-1, 0, 1)
        if delta_row or delta_column
    )
    while queue:
        distance, row, column = heapq.heappop(queue)
        if distance > fade_distance_m or distance != local_distances[row, column]:
            continue
        for delta_row, delta_column, edge_length in neighbours:
            next_row, next_column = row + delta_row, column + delta_column
            if not (0 <= next_row < local_distances.shape[0]):
                continue
            if not (0 <= next_column < local_distances.shape[1]):
                continue
            next_distance = distance + edge_length
            if next_distance > fade_distance_m:
                continue
            if next_distance < local_distances[next_row, next_column]:
                local_distances[next_row, next_column] = next_distance
                heapq.heappush(queue, (next_distance, next_row, next_column))
    position = np.clip(local_distances / fade_distance_m, 0.0, 1.0)
    weights = (3 * position * position - 2 * position * position * position).astype(np.float32)
    weights[~np.isfinite(local_distances)] = 1.0
    return min_row, min_column, weights


def _apply_harm_fallback(
    baseline: np.ndarray,
    candidate: np.ndarray,
    segments: list[RoadSegment],
    spacing_m: float,
    width_m: float,
    depth_m: float,
    config: PreviewConfig,
    nearest_way_grid: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Restore only measured harmful connected regions, fading smoothly to candidate."""
    rows, columns = baseline.shape
    candidate_float = candidate.astype(np.float64)
    baseline_float = baseline.astype(np.float64)
    scale = np.ones((rows, columns), dtype=np.float32)
    regions = _connected_fallback_regions(baseline, candidate, spacing_m, config, width_m, depth_m)
    for region in regions:
        component = region.pop("corePoints")
        region["nearestRoadWayIds"] = sorted(
            {
                int(nearest_way_grid[row, column])
                for row, column in component
                if nearest_way_grid[row, column] > 0
            }
        )
        min_row, min_column, local_weights = _fallback_distance_weights(
            component, rows, columns, spacing_m, config.fallback_fade_distance_m
        )
        max_row = min_row + local_weights.shape[0]
        max_column = min_column + local_weights.shape[1]
        window = scale[min_row:max_row, min_column:max_column]
        scale[min_row:max_row, min_column:max_column] = np.minimum(window, local_weights)
        core_count = len(component)
        faded_count = int(np.count_nonzero((local_weights > 0.0) & (local_weights < 1.0)))
        affected_count = int(np.count_nonzero(local_weights < 1.0))
        region["coreLocalBoundsXZ"] = region.pop("coreLocalBoundsXZ")
        region["coreVertexCount"] = core_count
        region["coreAreaEquivalentM2"] = core_count * spacing_m * spacing_m
        region["fadedVertexCount"] = faded_count
        region["fadedAreaEquivalentM2"] = faded_count * spacing_m * spacing_m
        region["affectedAreaEquivalentM2"] = affected_count * spacing_m * spacing_m
        region["fadeDistanceM"] = config.fallback_fade_distance_m
        region["fadeBlend"] = "cubic smoothstep with zero slope at the core and outer edge"
        region["effect"] = "retain source ground in the connected core and fade outward"
        region["componentMask"] = (min_row, min_column, local_weights < 1.0)

    output = (
        baseline_float + scale.astype(np.float64) * (candidate_float - baseline_float)
    ).astype("<f4")
    if not np.isfinite(output).all():
        raise RoadSurfaceError("harm fallback produced a non-finite display height")
    for region in regions:
        min_row, min_column, local_mask = region.pop("componentMask")
        max_row = min_row + local_mask.shape[0]
        max_column = min_column + local_mask.shape[1]
        local_preview = output[min_row:max_row, min_column:max_column].astype(np.float64)
        local_baseline = baseline_float[min_row:max_row, min_column:max_column]
        horizontal_preview = np.abs(np.diff(local_preview, axis=1)) / spacing_m
        horizontal_baseline = np.abs(np.diff(local_baseline, axis=1)) / spacing_m
        vertical_preview = np.abs(np.diff(local_preview, axis=0)) / spacing_m
        vertical_baseline = np.abs(np.diff(local_baseline, axis=0)) / spacing_m
        horizontal_mask = local_mask[:, :-1] | local_mask[:, 1:]
        vertical_mask = local_mask[:-1, :] | local_mask[1:, :]
        added_values = np.concatenate(
            (
                np.maximum(horizontal_preview - horizontal_baseline, 0.0)[horizontal_mask],
                np.maximum(vertical_preview - vertical_baseline, 0.0)[vertical_mask],
            )
        )
        preview_values = np.concatenate(
            (horizontal_preview[horizontal_mask], vertical_preview[vertical_mask])
        )
        baseline_values = np.concatenate(
            (horizontal_baseline[horizontal_mask], vertical_baseline[vertical_mask])
        )
        region["postFallbackMaximumAddedGradientMPerM"] = (
            float(np.max(added_values)) if added_values.size else 0.0
        )
        region["postFallbackMaximumPreviewGradientMPerM"] = (
            float(np.max(preview_values)) if preview_values.size else 0.0
        )
        region["postFallbackMaximumBaselineGradientMPerM"] = (
            float(np.max(baseline_values)) if baseline_values.size else 0.0
        )
        region["postFallbackMaximumAbsoluteChangeM"] = float(
            np.max(np.abs(local_preview[local_mask] - local_baseline[local_mask]))
        )
    return output, {
        "policy": {
            "maximumAbsoluteLocalChangeM": config.fallback_absolute_change_m,
            "minimumNewGradientIncreaseMPerM": config.fallback_added_gradient_m_per_m,
            "minimumConnectedRegionAreaM2": config.fallback_minimum_region_area_m2,
            "fadeDistanceM": config.fallback_fade_distance_m,
            "interpretation": (
                "preview safety heuristic only; regions qualify by the absolute local cut/fill "
                "threshold or by the added-gradient threshold over the minimum connected area"
            ),
        },
        "triggeredRegionCount": len(regions),
        "retainedCoreAreaEquivalentM2": float(
            sum(region["coreAreaEquivalentM2"] for region in regions)
        ),
        "fadedAreaEquivalentM2": float(sum(region["fadedAreaEquivalentM2"] for region in regions)),
        "affectedAreaEquivalentM2": float(
            sum(region["affectedAreaEquivalentM2"] for region in regions)
        ),
        "uniqueRetainedCoreAreaEquivalentM2": float(np.count_nonzero(scale == 0.0) * spacing_m**2),
        "uniqueFadedAreaEquivalentM2": float(
            np.count_nonzero((scale > 0.0) & (scale < 1.0)) * spacing_m**2
        ),
        "uniqueAffectedAreaEquivalentM2": float(np.count_nonzero(scale < 1.0) * spacing_m**2),
        "regions": regions,
    }


def _grade_grid(
    baseline: np.ndarray,
    segments: list[RoadSegment],
    spacing_m: float,
    width_m: float,
    depth_m: float,
    config: PreviewConfig,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Apply nearest-road anchored cross sections and retain ground in conflicts."""
    rows, columns = baseline.shape
    half_width, half_depth = width_m / 2, depth_m / 2
    tiles: dict[tuple[int, int], list[int]] = {}
    for segment_index, segment in enumerate(segments):
        radius = segment.influence_m + config.ambiguity_distance_m
        min_tx = math.floor(
            (min(segment.first_x, segment.first_x + segment.dx) - radius) / SPATIAL_TILE_M
        )
        max_tx = math.floor(
            (max(segment.first_x, segment.first_x + segment.dx) + radius) / SPATIAL_TILE_M
        )
        min_tz = math.floor(
            (min(segment.first_z, segment.first_z + segment.dz) - radius) / SPATIAL_TILE_M
        )
        max_tz = math.floor(
            (max(segment.first_z, segment.first_z + segment.dz) + radius) / SPATIAL_TILE_M
        )
        for tile_z in range(min_tz, max_tz + 1):
            for tile_x in range(min_tx, max_tx + 1):
                tiles.setdefault((tile_x, tile_z), []).append(segment_index)

    output = baseline.astype("<f4", copy=True)
    ambiguous: dict[int, dict[str, Any]] = {}
    influence_mask = np.zeros((rows, columns), dtype=bool)
    transition_mask = np.zeros((rows, columns), dtype=bool)
    candidate_vertex_count = 0
    affected_segment_ids: set[int] = set()
    nearest_way_grid = np.zeros((rows, columns), dtype=np.int64)
    for tile_x, tile_z in sorted(tiles, key=lambda key: (key[1], key[0])):
        candidates = sorted(set(tiles[(tile_x, tile_z)]))
        for row in _grid_tile_range(tile_z, spacing_m, half_depth, rows):
            z = row * spacing_m - half_depth
            if math.floor(z / SPATIAL_TILE_M) != tile_z:
                continue
            for column in _grid_tile_range(tile_x, spacing_m, half_width, columns):
                x = column * spacing_m - half_width
                if math.floor(x / SPATIAL_TILE_M) != tile_x:
                    continue
                active_projections: list[Projection] = []
                ambiguity_projections: list[Projection] = []
                for segment_index in candidates:
                    segment = segments[segment_index]
                    projection = _project(segment_index, segment, x, z, baseline, spacing_m)
                    if (
                        projection.distance_m
                        <= segment.influence_m + config.ambiguity_distance_m + 1e-9
                    ):
                        ambiguity_projections.append(projection)
                        if projection.distance_m <= segment.influence_m + 1e-9:
                            active_projections.append(projection)
                if not active_projections:
                    continue
                vertex_index = row * columns + column
                influence_mask[row, column] = True
                candidate_vertex_count += 1
                by_way: dict[int, Projection] = {}
                for projection in active_projections:
                    current = by_way.get(projection.way_id)
                    if current is None or _projection_key(projection, segments) < _projection_key(
                        current, segments
                    ):
                        by_way[projection.way_id] = projection
                nearest = min(by_way.values(), key=lambda item: _projection_key(item, segments))
                nearest_way_grid[row, column] = nearest.way_id
                ambiguity_by_way: dict[int, Projection] = {}
                for projection in ambiguity_projections:
                    current = ambiguity_by_way.get(projection.way_id)
                    if current is None or _projection_key(projection, segments) < _projection_key(
                        current, segments
                    ):
                        ambiguity_by_way[projection.way_id] = projection
                competitors = sorted(
                    (item for way_id, item in ambiguity_by_way.items() if way_id != nearest.way_id),
                    key=lambda item: _projection_key(item, segments),
                )
                conflict = next(
                    (
                        item
                        for item in competitors
                        if abs(item.distance_m - nearest.distance_m) <= config.ambiguity_distance_m
                        and abs(item.target_y - nearest.target_y)
                        >= config.ambiguity_height_difference_m
                    ),
                    None,
                )
                if conflict is not None:
                    ambiguous[vertex_index] = {
                        "row": row,
                        "column": column,
                        "ways": sorted({nearest.way_id, conflict.way_id}),
                        "heightDifferenceM": abs(nearest.target_y - conflict.target_y),
                        "retentionRadiusM": max(
                            segments[nearest.segment_index].width_m / 2,
                            segments[conflict.segment_index].width_m / 2,
                        )
                        + spacing_m,
                        "fadeDistanceM": max(
                            segments[nearest.segment_index].width_m,
                            segments[conflict.segment_index].width_m,
                            2 * spacing_m,
                        ),
                    }
                    affected_segment_ids.update((nearest.segment_index, conflict.segment_index))
                    continue
                segment = segments[nearest.segment_index]
                half_road = segment.width_m / 2
                transition = max(segment.width_m, 2 * spacing_m) * config.transition_distance_factor
                if half_road < nearest.distance_m < half_road + transition:
                    transition_mask[row, column] = True
                weight = _blend_weight(nearest.distance_m, half_road, transition)
                if weight <= 0:
                    continue
                base_y = float(baseline[row, column])
                graded_y = base_y + weight * (nearest.target_y - base_y)
                if not math.isfinite(graded_y) or not math.isfinite(float(np.float32(graded_y))):
                    raise RoadSurfaceError("grading produced a non-finite visual height")
                if abs(graded_y - base_y) > config.maximum_changed_height_m:
                    raise RoadSurfaceError(
                        "grading exceeds configured local height change "
                        f"at row {row}, column {column}"
                    )
                output[row, column] = np.float32(graded_y)
    affected_mask = np.zeros((rows, columns), dtype=bool)
    fully_retained_mask = np.zeros((rows, columns), dtype=bool)
    fade_scale = np.ones((rows, columns), dtype=np.float32)
    affected_ambiguities: dict[int, dict[str, Any]] = {}
    for seed in ambiguous.values():
        center_row, center_column = seed["row"], seed["column"]
        core_radius = seed["retentionRadiusM"]
        fade_distance = seed["fadeDistanceM"]
        radius = core_radius + fade_distance
        cells = math.ceil(radius / spacing_m)
        for row in range(max(0, center_row - cells), min(rows, center_row + cells + 1)):
            for column in range(
                max(0, center_column - cells), min(columns, center_column + cells + 1)
            ):
                x_distance = (column - center_column) * spacing_m
                z_distance = (row - center_row) * spacing_m
                distance = math.hypot(x_distance, z_distance)
                if distance > radius:
                    continue
                vertex_index = row * columns + column
                if distance <= core_radius:
                    weight = 0.0
                    fully_retained_mask[row, column] = True
                else:
                    position = (distance - core_radius) / fade_distance
                    weight = 3 * position * position - 2 * position * position * position
                if weight >= 1.0:
                    continue
                fade_scale[row, column] = min(fade_scale[row, column], weight)
                affected_mask[row, column] = True
                record = affected_ambiguities.setdefault(
                    vertex_index,
                    {
                        "row": row,
                        "column": column,
                        "ways": [],
                        "heightDifferenceM": 0.0,
                        "core": False,
                        "fadeWeight": 1.0,
                    },
                )
                record["ways"] = sorted(set(record["ways"]) | set(seed["ways"]))
                record["heightDifferenceM"] = max(
                    record["heightDifferenceM"], seed["heightDifferenceM"]
                )
                record["core"] = record["core"] or distance <= core_radius
                record["fadeWeight"] = min(record["fadeWeight"], weight)
    original_output = output.astype(np.float64)
    baseline_float64 = baseline.astype(np.float64)
    output[affected_mask] = (
        baseline_float64[affected_mask]
        + fade_scale[affected_mask].astype(np.float64)
        * (original_output[affected_mask] - baseline_float64[affected_mask])
    ).astype("<f4")
    candidate_before_harm_fallback = output.copy()
    output, harm_fallback = _apply_harm_fallback(
        baseline,
        output,
        segments,
        spacing_m,
        width_m,
        depth_m,
        config,
        nearest_way_grid,
    )
    if not np.isfinite(output).all():
        raise RoadSurfaceError("graded display grid contains non-finite values")
    regions = _ambiguity_regions(affected_ambiguities, rows, columns, spacing_m, width_m, depth_m)
    changed = output != baseline
    delta = output.astype(np.float64) - baseline.astype(np.float64)
    delta_abs = np.abs(delta[changed])
    gradient_x = np.diff(delta, axis=1) / spacing_m
    gradient_z = np.diff(delta, axis=0) / spacing_m
    transition_gradient = np.concatenate((np.abs(gradient_x).ravel(), np.abs(gradient_z).ravel()))
    transition_edges_x = transition_mask[:, 1:] | transition_mask[:, :-1]
    transition_edges_z = transition_mask[1:, :] | transition_mask[:-1, :]
    transition_only_gradients = np.concatenate(
        (np.abs(gradient_x[transition_edges_x]), np.abs(gradient_z[transition_edges_z]))
    )
    maximum_change_gradient = _maximum_edge_gradient(delta, spacing_m, width_m, depth_m)
    candidate_delta = candidate_before_harm_fallback.astype(np.float64) - baseline_float64
    candidate_gradient_change = _terrain_gradient_change_summary(
        baseline_float64,
        candidate_before_harm_fallback.astype(np.float64),
        spacing_m,
        width_m,
        depth_m,
    )
    candidate_fill_index = int(np.argmax(candidate_delta))
    candidate_cut_index = int(np.argmin(candidate_delta))
    candidate_fill_row, candidate_fill_column = divmod(candidate_fill_index, columns)
    candidate_cut_row, candidate_cut_column = divmod(candidate_cut_index, columns)
    original_terrain_gradient = _terrain_gradient_summary(
        baseline.astype(np.float64), spacing_m, width_m, depth_m
    )
    preview_terrain_gradient = _terrain_gradient_summary(
        output.astype(np.float64), spacing_m, width_m, depth_m
    )
    terrain_gradient_change = _terrain_gradient_change_summary(
        baseline.astype(np.float64), output.astype(np.float64), spacing_m, width_m, depth_m
    )
    report = {
        "eligibleGroundAssumedVehicularSegmentCount": len(segments),
        "candidateGridVertexCount": candidate_vertex_count,
        "changedVertexCount": int(changed.sum()),
        "changedVertexEquivalentAreaM2": float(changed.sum() * spacing_m * spacing_m),
        "unchangedOuterVerticesExact": bool(np.array_equal(output[~changed], baseline[~changed])),
        "verticesBeyondAllInfluenceRegionsExact": bool(
            np.array_equal(output[~influence_mask], baseline[~influence_mask])
        ),
        "verticesBeyondAllInfluenceRegionCount": int((~influence_mask).sum()),
        "signedCutFill": {
            "cutMaximumM": float(max(0.0, float(np.max(-delta)))) if delta.size else 0.0,
            "fillMaximumM": float(max(0.0, float(np.max(delta)))) if delta.size else 0.0,
            "absoluteChangePercentilesM": {
                "p50": float(np.percentile(delta_abs, 50)) if delta_abs.size else 0.0,
                "p95": float(np.percentile(delta_abs, 95)) if delta_abs.size else 0.0,
                "p99": float(np.percentile(delta_abs, 99)) if delta_abs.size else 0.0,
                "maximum": float(np.max(delta_abs)) if delta_abs.size else 0.0,
            },
        },
        "transitionGradientOfDisplayChange": {
            "maximumMPerM": float(np.max(transition_gradient)) if transition_gradient.size else 0.0,
            "p95MPerM": float(np.percentile(transition_gradient, 95))
            if transition_gradient.size
            else 0.0,
            "maximumWithinShoulderMPerM": float(np.max(transition_only_gradients))
            if transition_only_gradients.size
            else 0.0,
            "p95WithinShoulderMPerM": float(np.percentile(transition_only_gradients, 95))
            if transition_only_gradients.size
            else 0.0,
        },
        "maximumAdjacentDisplayChangeGradient": maximum_change_gradient,
        "terrainGradient": {
            "baseline": original_terrain_gradient,
            "preview": preview_terrain_gradient,
        },
        "terrainGradientChange": terrain_gradient_change,
        "nearestProjectionSelection": (
            "minimum horizontal distance; stable way identity, part index, "
            "then segment index tie break"
        ),
        "ambiguitySeedVertexCount": len(ambiguous),
        "ambiguousGridVertexCountRetainedAtOriginalGround": int(fully_retained_mask.sum()),
        "ambiguityExcludedAreaEquivalentM2": float(
            fully_retained_mask.sum() * spacing_m * spacing_m
        ),
        "ambiguityFadeVertexCount": int((affected_mask & ~fully_retained_mask).sum()),
        "ambiguityFadeAreaEquivalentM2": float(
            (affected_mask & ~fully_retained_mask).sum() * spacing_m * spacing_m
        ),
        "ambiguityAffectedAreaEquivalentM2": float(affected_mask.sum() * spacing_m * spacing_m),
        "ambiguousConnectedRegions": regions,
        "waysAffectedByAmbiguity": sorted(
            {way for segment_id in affected_segment_ids for way in (segments[segment_id].way_id,)}
        ),
        "candidateBeforeHarmFallback": {
            "fillMaximumM": float(max(0.0, float(np.max(candidate_delta)))),
            "cutMaximumM": float(max(0.0, float(np.max(-candidate_delta)))),
            "fillMaximumLocalXZ": [
                float(candidate_fill_column * spacing_m - half_width),
                float(candidate_fill_row * spacing_m - half_depth),
            ],
            "cutMaximumLocalXZ": [
                float(candidate_cut_column * spacing_m - half_width),
                float(candidate_cut_row * spacing_m - half_depth),
            ],
            "maximumAbsoluteChangeM": float(np.max(np.abs(candidate_delta))),
            "maximumPositiveAddedGradientMPerM": candidate_gradient_change[
                "maximumPositiveIncreaseMPerM"
            ],
            "maximumPositiveAddedGradientEdge": candidate_gradient_change[
                "maximumPositiveIncreaseEdge"
            ],
        },
        "harmFallback": harm_fallback,
    }
    return output, report


def _maximum_edge_gradient(
    delta: np.ndarray, spacing_m: float, width_m: float, depth_m: float
) -> dict[str, Any]:
    gradient_x = np.abs(np.diff(delta, axis=1)) / spacing_m
    gradient_z = np.abs(np.diff(delta, axis=0)) / spacing_m
    max_x = float(np.max(gradient_x)) if gradient_x.size else 0.0
    max_z = float(np.max(gradient_z)) if gradient_z.size else 0.0
    if max_x >= max_z:
        row, column = np.unravel_index(int(np.argmax(gradient_x)), gradient_x.shape)
        first = float(delta[row, column])
        second = float(delta[row, column + 1])
        axis = "x"
        first_local = [column * spacing_m - width_m / 2, row * spacing_m - depth_m / 2]
        second_local = [first_local[0] + spacing_m, first_local[1]]
        value = max_x
    else:
        row, column = np.unravel_index(int(np.argmax(gradient_z)), gradient_z.shape)
        first = float(delta[row, column])
        second = float(delta[row + 1, column])
        axis = "z"
        first_local = [column * spacing_m - width_m / 2, row * spacing_m - depth_m / 2]
        second_local = [first_local[0], first_local[1] + spacing_m]
        value = max_z
    return {
        "magnitudeMPerM": value,
        "axis": axis,
        "firstLocalXZ": first_local,
        "secondLocalXZ": second_local,
        "firstValueM": first,
        "secondValueM": second,
    }


def _terrain_gradient_summary(
    heights: np.ndarray, spacing_m: float, width_m: float, depth_m: float
) -> dict[str, Any]:
    gradient_x = np.abs(np.diff(heights, axis=1)) / spacing_m
    gradient_z = np.abs(np.diff(heights, axis=0)) / spacing_m
    values = np.concatenate((gradient_x.ravel(), gradient_z.ravel()))
    maximum = _maximum_edge_gradient(heights, spacing_m, width_m, depth_m)
    return {
        "maximumAbsoluteEdgeGradientMPerM": maximum["magnitudeMPerM"],
        "p95AbsoluteEdgeGradientMPerM": float(np.percentile(values, 95)) if values.size else 0.0,
        "maximumEdge": maximum,
    }


def _terrain_gradient_change_summary(
    baseline: np.ndarray,
    preview: np.ndarray,
    spacing_m: float,
    width_m: float,
    depth_m: float,
) -> dict[str, Any]:
    baseline_x = np.abs(np.diff(baseline, axis=1)) / spacing_m
    preview_x = np.abs(np.diff(preview, axis=1)) / spacing_m
    baseline_z = np.abs(np.diff(baseline, axis=0)) / spacing_m
    preview_z = np.abs(np.diff(preview, axis=0)) / spacing_m
    signed_changes = (preview_x - baseline_x, preview_z - baseline_z)
    absolute_changes = tuple(np.abs(change) for change in signed_changes)

    def edge_for_max(arrays: tuple[np.ndarray, np.ndarray], positive_only: bool) -> dict[str, Any]:
        selected = tuple(np.maximum(array, 0) if positive_only else array for array in arrays)
        lengths = tuple(array.size for array in selected)
        combined = np.concatenate(tuple(array.ravel() for array in selected))
        index = int(np.argmax(combined))
        axis_index = 0 if index < lengths[0] else 1
        row, column = np.unravel_index(
            index - (0 if axis_index == 0 else lengths[0]), selected[axis_index].shape
        )
        axis = "x" if axis_index == 0 else "z"
        local_x = column * spacing_m - width_m / 2
        local_z = row * spacing_m - depth_m / 2
        return {
            "magnitudeMPerM": float(combined[index]),
            "axis": axis,
            "firstLocalXZ": [local_x, local_z],
            "secondLocalXZ": [local_x + spacing_m, local_z]
            if axis == "x"
            else [local_x, local_z + spacing_m],
            "baselineMagnitudeMPerM": float(
                (baseline_x if axis == "x" else baseline_z)[row, column]
            ),
            "previewMagnitudeMPerM": float((preview_x if axis == "x" else preview_z)[row, column]),
        }

    positive = edge_for_max(signed_changes, positive_only=True)
    absolute = edge_for_max(absolute_changes, positive_only=False)
    significant_regions = _significant_gradient_increase_regions(
        signed_changes,
        baseline_x,
        preview_x,
        baseline_z,
        preview_z,
        spacing_m,
        width_m,
        depth_m,
    )
    return {
        "significantIncreaseThresholdMPerM": SIGNIFICANT_ADDED_GRADIENT_THRESHOLD_M_PER_M,
        "significantPositiveIncreaseRegions": significant_regions,
        "maximumPositiveIncreaseMPerM": positive["magnitudeMPerM"],
        "maximumPositiveIncreaseEdge": positive,
        "maximumAbsoluteChangeMPerM": absolute["magnitudeMPerM"],
        "maximumAbsoluteChangeEdge": absolute,
    }


def _significant_gradient_increase_regions(
    changes: tuple[np.ndarray, np.ndarray],
    baseline_x: np.ndarray,
    preview_x: np.ndarray,
    baseline_z: np.ndarray,
    preview_z: np.ndarray,
    spacing_m: float,
    width_m: float,
    depth_m: float,
) -> list[dict[str, Any]]:
    """Group newly steepened grid edges for QA; this threshold never changes grading."""
    edges: list[tuple[int, int, int, int, str, float, float, float]] = []
    edges_by_cell: dict[tuple[int, int], list[int]] = {}
    edge_cells: list[tuple[int, int]] = []

    for axis_index, change in enumerate(changes):
        baseline = baseline_x if axis_index == 0 else baseline_z
        preview = preview_x if axis_index == 0 else preview_z
        axis = "x" if axis_index == 0 else "z"
        for row, column in zip(
            *np.nonzero(change >= SIGNIFICANT_ADDED_GRADIENT_THRESHOLD_M_PER_M), strict=True
        ):
            if axis == "x":
                first_row, first_column = int(row), int(column)
                second_row, second_column = int(row), int(column) + 1
            else:
                first_row, first_column = int(row), int(column)
                second_row, second_column = int(row) + 1, int(column)
            edge_index = len(edges)
            edge_cell = (
                math.floor((first_row + second_row) / 2),
                math.floor((first_column + second_column) / 2),
            )
            edge_cells.append(edge_cell)
            edges_by_cell.setdefault(edge_cell, []).append(edge_index)
            edges.append(
                (
                    first_row,
                    first_column,
                    second_row,
                    second_column,
                    axis,
                    float(change[row, column]),
                    float(baseline[row, column]),
                    float(preview[row, column]),
                )
            )

    remaining = set(range(len(edges)))
    regions = []
    half_width, half_depth = width_m / 2, depth_m / 2
    while remaining:
        first = min(remaining)
        remaining.remove(first)
        stack = [first]
        component = []
        while stack:
            edge_index = stack.pop()
            component.append(edge_index)
            edge_row, edge_column = edge_cells[edge_index]
            for delta_row in (-1, 0, 1):
                for delta_column in (-1, 0, 1):
                    for neighbor in edges_by_cell.get(
                        (edge_row + delta_row, edge_column + delta_column), []
                    ):
                        if neighbor in remaining:
                            remaining.remove(neighbor)
                            stack.append(neighbor)
        component_edges = [edges[index] for index in component]
        vertices = {(edge[0], edge[1]) for edge in component_edges} | {
            (edge[2], edge[3]) for edge in component_edges
        }
        maximum = max(component_edges, key=lambda edge: edge[5])
        vertex_rows = [point[0] for point in vertices]
        vertex_columns = [point[1] for point in vertices]
        first_local_x = maximum[1] * spacing_m - half_width
        first_local_z = maximum[0] * spacing_m - half_depth
        regions.append(
            {
                "edgeCount": len(component_edges),
                "vertexCount": len(vertices),
                "affectedAreaEquivalentM2": len(vertices) * spacing_m * spacing_m,
                "localBoundsXZ": [
                    min(vertex_columns) * spacing_m - half_width,
                    min(vertex_rows) * spacing_m - half_depth,
                    max(vertex_columns) * spacing_m - half_width,
                    max(vertex_rows) * spacing_m - half_depth,
                ],
                "maximumPositiveIncreaseMPerM": maximum[5],
                "maximumEdge": {
                    "axis": maximum[4],
                    "firstLocalXZ": [first_local_x, first_local_z],
                    "secondLocalXZ": [first_local_x + spacing_m, first_local_z]
                    if maximum[4] == "x"
                    else [first_local_x, first_local_z + spacing_m],
                    "baselineMagnitudeMPerM": maximum[6],
                    "previewMagnitudeMPerM": maximum[7],
                },
            }
        )
    return sorted(
        regions,
        key=lambda region: (
            -region["affectedAreaEquivalentM2"],
            region["localBoundsXZ"][1],
            region["localBoundsXZ"][0],
        ),
    )


def _ambiguity_regions(
    points: dict[int, dict[str, Any]],
    rows: int,
    columns: int,
    spacing_m: float,
    width_m: float,
    depth_m: float,
) -> list[dict[str, Any]]:
    remaining = set(points)
    regions = []
    while remaining:
        first = min(remaining)
        stack = [first]
        remaining.remove(first)
        component = []
        while stack:
            index = stack.pop()
            component.append(points[index])
            row, column = divmod(index, columns)
            for dz in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    neighbor_row, neighbor_column = row + dz, column + dx
                    if 0 <= neighbor_row < rows and 0 <= neighbor_column < columns:
                        neighbor = neighbor_row * columns + neighbor_column
                    else:
                        continue
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        stack.append(neighbor)
        component_rows = [item["row"] for item in component]
        component_columns = [item["column"] for item in component]
        half_width, half_depth = width_m / 2, depth_m / 2
        regions.append(
            {
                "vertexCount": len(component),
                "fullyRetainedVertexCount": sum(
                    bool(item.get("core", False)) for item in component
                ),
                "fadedVertexCount": sum(not bool(item.get("core", False)) for item in component),
                "localBoundsXZ": [
                    min(component_columns) * spacing_m - half_width,
                    min(component_rows) * spacing_m - half_depth,
                    max(component_columns) * spacing_m - half_width,
                    max(component_rows) * spacing_m - half_depth,
                ],
                "wayIds": sorted({way for item in component for way in item["ways"]}),
                "maximumCandidateAnchorDifferenceM": max(
                    item["heightDifferenceM"] for item in component
                ),
                "affectedAreaEquivalentM2": len(component) * spacing_m * spacing_m,
                "fullyRetainedAreaEquivalentM2": sum(
                    bool(item.get("core", False)) for item in component
                )
                * spacing_m
                * spacing_m,
                "minimumTreatmentBlendWeight": min(
                    item.get("fadeWeight", 0.0) for item in component
                ),
                "effect": (
                    "retain original baseline ground in the core and smoothly fade "
                    "treatment around it"
                ),
            }
        )
    return regions


def _line_point_tangent(
    part: list[list[float]], station_m: float
) -> tuple[tuple[float, float], tuple[float, float]]:
    lengths = [math.dist(a, b) for a, b in zip(part, part[1:], strict=False)]
    total = sum(lengths)
    if total <= 0:
        raise RoadSurfaceError("road centerline part has no positive length")
    station = min(max(station_m, 0.0), total)
    accumulated = 0.0
    for index, (first, second) in enumerate(zip(part, part[1:], strict=False)):
        length = lengths[index]
        if length <= 0:
            continue
        if station <= accumulated + length or index == len(lengths) - 1:
            ratio = (station - accumulated) / length
            dx, dz = second[0] - first[0], second[1] - first[1]
            return ((first[0] + dx * ratio, first[1] + dz * ratio), (dx / length, dz / length))
        accumulated += length
    raise RoadSurfaceError("cannot project a station onto the road centerline")


def _grade_percent(stations: list[float], elevations: list[float]) -> list[float]:
    return [
        abs(second - first) / (s1 - s0) * 100
        for s0, s1, first, second in zip(
            stations, stations[1:], elevations, elevations[1:], strict=False
        )
    ]


def _cross_percent(first: float, second: float, width_m: float) -> float:
    return abs(first - second) / width_m * 100


def _source_raster_paths(project_root: Path) -> tuple[list[Path], list[dict[str, Any]]]:
    manifest_path = project_root / "data/source-manifest.json"
    try:
        source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RoadSurfaceError(f"cannot read verified EA source manifest: {exc}") from exc
    sources = source_manifest.get("sources") if isinstance(source_manifest, dict) else None
    if not isinstance(sources, list) or not sources:
        raise RoadSurfaceError("EA source manifest does not list the original raster inputs")
    paths, hashes = [], []
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("raster_relative_path"), str):
            raise RoadSurfaceError("EA source manifest contains an invalid raster record")
        path = project_root / "data/raw/ea_dtm" / source["raster_relative_path"]
        expected = source.get("raster")
        if not isinstance(expected, dict):
            raise RoadSurfaceError("EA source manifest lacks raster checksum metadata")
        actual_hash = sha256_file(path)
        if actual_hash != expected.get("sha256") or path.stat().st_size != expected.get(
            "size_bytes"
        ):
            raise RoadSurfaceError(
                f"original EA raster input does not match the local source manifest: '{path}'"
            )
        paths.append(path)
        hashes.append(
            {
                "path": path.relative_to(project_root).as_posix(),
                "byteLength": path.stat().st_size,
                "sha256": actual_hash,
            }
        )
    return paths, hashes


def _sample_source_raster(
    paths: list[Path], inputs: ReleaseInputs, positions: list[tuple[float, float]]
) -> list[float]:
    eastings = np.asarray([inputs.origin_e_m + x for x, _z in positions], dtype=np.float64).reshape(
        1, -1
    )
    northings = np.asarray(
        [inputs.origin_n_m - z for _x, z in positions], dtype=np.float64
    ).reshape(1, -1)
    try:
        values = _sample_bilinear_mosaic(paths, eastings, northings)
    except Exception as exc:
        raise RoadSurfaceError(f"cannot sample the verified original EA 1 m DTM: {exc}") from exc
    if not np.isfinite(values).all():
        raise RoadSurfaceError("source DTM sampling produced a non-finite value")
    return [float(value) for value in values.ravel()]


def _profile_feature(
    feature: dict[str, Any], inputs: ReleaseInputs, preview: np.ndarray, raster_paths: list[Path]
) -> dict[str, Any]:
    width = float(feature["estimatedWidthM"])
    parts_output = []
    all_baseline_cross, all_preview_cross, all_source_cross = [], [], []
    baseline_grades, preview_grades, source_grades = [], [], []
    max_centerline_deviation = 0.0
    station_records = 0
    for part_index, raw_part in enumerate(feature["centerlinePartsXZ"]):
        part = [[float(point[0]), float(point[1])] for point in raw_part]
        lengths = [math.dist(a, b) for a, b in zip(part, part[1:], strict=False)]
        total_length = sum(lengths)
        if total_length <= 0:
            continue
        interval_count = max(1, math.ceil(total_length / MAX_PROFILE_STATION_SPACING_M))
        spacing = total_length / interval_count
        centers = [
            _line_point_tangent(part, index * spacing) for index in range(interval_count + 1)
        ]
        positions = [point for point, _tangent in centers]
        source_values = _sample_source_raster(raster_paths, inputs, positions)
        baseline_values = [
            _sample_grid(inputs.baseline, *point, inputs.spacing_m) for point in positions
        ]
        preview_values = [_sample_grid(preview, *point, inputs.spacing_m) for point in positions]
        stations = [index * spacing for index in range(interval_count + 1)]
        baseline_grades.extend(_grade_percent(stations, baseline_values))
        preview_grades.extend(_grade_percent(stations, preview_values))
        source_grades.extend(_grade_percent(stations, source_values))
        center_samples = []
        for index, ((x, z), _tangent) in enumerate(centers):
            deviation = preview_values[index] - baseline_values[index]
            max_centerline_deviation = max(max_centerline_deviation, abs(deviation))
            station_records += 1
            center_samples.append(
                {
                    "stationM": stations[index],
                    "localXZ": [x, z],
                    "tangentXZ": list(_tangent),
                    "baselineLocalM": baseline_values[index],
                    "previewLocalM": preview_values[index],
                    "sourceEAOrthoM": source_values[index],
                    "previewMinusBaselineM": deviation,
                }
            )
        cross_samples = []
        cross_definitions = []
        cross_positions: list[tuple[float, float]] = []
        for index in range(interval_count):
            station = (index + 0.5) * spacing
            (center_x, center_z), tangent = _line_point_tangent(part, station)
            normal_x, normal_z = -tangent[1], tangent[0]
            left = (center_x + normal_x * width / 2, center_z + normal_z * width / 2)
            right = (center_x - normal_x * width / 2, center_z - normal_z * width / 2)
            if any(
                abs(point[0]) > inputs.width_m / 2 or abs(point[1]) > inputs.depth_m / 2
                for point in (left, right)
            ):
                continue
            cross_positions.extend((left, right))
            cross_definitions.append((station, (center_x, center_z), tangent, left, right))
        source_cross_values = _sample_source_raster(raster_paths, inputs, cross_positions)
        for sample_index, (station, (center_x, center_z), tangent, left, right) in enumerate(
            cross_definitions
        ):
            baseline_pair = [
                _sample_grid(inputs.baseline, *point, inputs.spacing_m) for point in (left, right)
            ]
            preview_pair = [
                _sample_grid(preview, *point, inputs.spacing_m) for point in (left, right)
            ]
            source_pair = source_cross_values[sample_index * 2 : sample_index * 2 + 2]
            baseline_grade = _cross_percent(*baseline_pair, width)
            preview_grade = _cross_percent(*preview_pair, width)
            source_grade = _cross_percent(*source_pair, width)
            all_baseline_cross.append(baseline_grade)
            all_preview_cross.append(preview_grade)
            all_source_cross.append(source_grade)
            cross_samples.append(
                {
                    "stationM": station,
                    "centerLocalXZ": [center_x, center_z],
                    "tangentXZ": list(tangent),
                    "oppositeLocalXZ": [list(left), list(right)],
                    "baselineLocalM": baseline_pair,
                    "previewLocalM": preview_pair,
                    "sourceEAOrthoM": source_pair,
                    "baselineAbsoluteCrossfallPercent": baseline_grade,
                    "previewAbsoluteCrossfallPercent": preview_grade,
                    "sourceEAAbsoluteCrossfallPercent": source_grade,
                }
            )
        parts_output.append(
            {
                "partIndex": part_index,
                "lengthM": total_length,
                "intervalCount": interval_count,
                "maximumStationSpacingM": spacing,
                "longitudinalSamples": center_samples,
                "crossfallSamples": cross_samples,
            }
        )

    def summary(values: list[float]) -> dict[str, float | None]:
        return {
            "medianAbsolutePercent": float(np.median(values)) if values else None,
            "maximumAbsolutePercent": float(max(values)) if values else None,
        }

    return {
        "wayId": int(feature["source"]["osmId"]),
        "name": feature.get("sourceTags", {}).get("name"),
        "displayGroup": feature.get("displayGroup"),
        "groundAssumption": feature.get("groundAssumption"),
        "configuredWidthM": width,
        "widthMethod": feature.get("widthMethod"),
        "centerlineGeometryUnchanged": True,
        "stationSampleCount": station_records,
        "longitudinalGradePercent": {
            "baseline": summary(baseline_grades),
            "preview": summary(preview_grades),
            "sourceEA1mDTM": summary(source_grades),
        },
        "crossfallPercent": {
            "baseline": summary(all_baseline_cross),
            "preview": summary(all_preview_cross),
            "sourceEA1mDTM": summary(all_source_cross),
        },
        "maximumPreviewCenterlineDeviationFromBaselineM": max_centerline_deviation,
        "parts": parts_output,
    }


def _maximum_under_building(
    feature: dict[str, Any], heights: np.ndarray, inputs: ReleaseInputs
) -> float:
    maximum = float("-inf")
    for polygon_record in feature["geometry"]["polygons"]:
        exterior = polygon_record["exteriorXZ"]
        holes = polygon_record.get("interiorRingsXZ", [])
        polygon = Polygon(exterior, holes)
        if polygon.is_empty or not polygon.is_valid:
            raise RoadSurfaceError(f"building {feature.get('id')} has invalid footprint geometry")
        min_x, min_z, max_x, max_z = polygon.bounds
        first_column = max(0, math.floor((min_x + inputs.width_m / 2) / inputs.spacing_m))
        last_column = min(
            inputs.columns - 2, math.floor((max_x + inputs.width_m / 2) / inputs.spacing_m)
        )
        first_row = max(0, math.floor((min_z + inputs.depth_m / 2) / inputs.spacing_m))
        last_row = min(inputs.rows - 2, math.floor((max_z + inputs.depth_m / 2) / inputs.spacing_m))
        for row in range(first_row, last_row + 1):
            z0 = row * inputs.spacing_m - inputs.depth_m / 2
            z1 = z0 + inputs.spacing_m
            for column in range(first_column, last_column + 1):
                x0 = column * inputs.spacing_m - inputs.width_m / 2
                x1 = x0 + inputs.spacing_m
                triangles = (
                    Polygon(((x0, z0), (x0, z1), (x1, z0))),
                    Polygon(((x1, z0), (x0, z1), (x1, z1))),
                )
                for triangle in triangles:
                    overlap = polygon.intersection(triangle)
                    if overlap.is_empty:
                        continue
                    for x, z in _geometry_points(overlap):
                        maximum = max(maximum, _sample_grid(heights, x, z, inputs.spacing_m))
    if not math.isfinite(maximum):
        raise RoadSurfaceError(f"building {feature.get('id')} has no samples under its footprint")
    return maximum


def _geometry_points(geometry: Any) -> list[tuple[float, float]]:
    if isinstance(geometry, Point):
        return [(float(geometry.x), float(geometry.y))]
    if isinstance(geometry, (LineString, MultiPoint)):
        return (
            [(float(x), float(y)) for x, y, *_rest in geometry.coords]
            if isinstance(geometry, LineString)
            else [(float(point.x), float(point.y)) for point in geometry.geoms]
        )
    if isinstance(geometry, (Polygon, MultiPolygon, MultiLineString, GeometryCollection)):
        result: list[tuple[float, float]] = []
        for part in getattr(geometry, "geoms", [geometry]):
            if isinstance(part, Polygon):
                result.extend((float(x), float(y)) for x, y, *_rest in part.exterior.coords)
                for ring in part.interiors:
                    result.extend((float(x), float(y)) for x, y, *_rest in ring.coords)
            else:
                result.extend(_geometry_points(part))
        return result
    return []


def _building_base_report(inputs: ReleaseInputs, preview: np.ndarray) -> dict[str, Any]:
    features = inputs.buildings.get("buildings")
    if not isinstance(features, list):
        raise RoadSurfaceError("pinned building payload has no feature list")
    changes = []
    for feature in features:
        if not isinstance(feature, dict):
            raise RoadSurfaceError("pinned building payload contains a malformed feature")
        baseline_base = _maximum_under_building(feature, inputs.baseline, inputs)
        preview_base = _maximum_under_building(feature, preview, inputs)
        changes.append(preview_base - baseline_base)
    values = np.asarray(changes, dtype=np.float64)
    return {
        "buildingCount": len(changes),
        "changedBuildingBaseCount": int(np.count_nonzero(values)),
        "basePolicy": (
            "highest sampled display terrain under each complete footprint plus "
            "unchanged building height; visual convention only"
        ),
        "wallBaseBurialM": 0.02,
        "signedPreviewMinusBaselineBaseM": {
            "minimum": float(np.min(values)) if values.size else 0.0,
            "p50": float(np.percentile(values, 50)) if values.size else 0.0,
            "p95Absolute": float(np.percentile(np.abs(values), 95)) if values.size else 0.0,
            "maximum": float(np.max(values)) if values.size else 0.0,
            "maximumAbsolute": float(np.max(np.abs(values))) if values.size else 0.0,
        },
        "individualChangesM": [
            {"id": feature["id"], "previewMinusBaselineM": float(change)}
            for feature, change in zip(features, values, strict=True)
        ],
    }


def _annotate_fallback_buildings(
    inputs: ReleaseInputs, grid_report: dict[str, Any], building_report: dict[str, Any]
) -> None:
    """Attach nearby source building IDs and observed footing shifts to each region."""
    changes = {
        item["id"]: item["previewMinusBaselineM"] for item in building_report["individualChangesM"]
    }
    features = inputs.buildings.get("buildings", [])
    for region in grid_report["harmFallback"]["regions"]:
        min_x, min_z, max_x, max_z = region["coreLocalBoundsXZ"]
        core = Polygon(
            (
                (min_x, min_z),
                (max_x, min_z),
                (max_x, max_z),
                (min_x, max_z),
            )
        )
        candidates = []
        for feature in features:
            polygons = feature.get("geometry", {}).get("polygons", [])
            distances = []
            for record in polygons:
                footprint = Polygon(record["exteriorXZ"], record.get("interiorRingsXZ", []))
                distances.append(core.distance(footprint))
            distance = min(distances, default=math.inf)
            if distance <= 16.0:
                candidates.append((distance, str(feature["id"])))
        candidates.sort()
        nearest = candidates[:8]
        region["nearbyBuildingIds"] = [building_id for _distance, building_id in nearest]
        region["nearbyBuildingBaseChangesM"] = [
            {
                "id": building_id,
                "previewMinusBaselineM": float(changes[building_id]),
            }
            for building_id in region["nearbyBuildingIds"]
            if building_id in changes
        ]
        region["nearestBuildingDistanceM"] = nearest[0][0] if nearest else None


def _nearest_eligible_road_context(
    inputs: ReleaseInputs, point: tuple[float, float] | list[float]
) -> dict[str, Any]:
    candidates = []
    px, pz = float(point[0]), float(point[1])
    for feature in inputs.road_payload["features"]:
        if (
            feature.get("displayGroup") != "vehicular"
            or feature.get("groundAssumption")
            != "ground_assumed_from_absent_or_explicit_no_vertical_tags"
        ):
            continue
        way_id = int(feature["source"]["osmId"])
        for part_index, part in enumerate(feature.get("centerlinePartsXZ", [])):
            station_base = 0.0
            for segment_index, (first, second) in enumerate(zip(part, part[1:], strict=False)):
                dx, dz = float(second[0] - first[0]), float(second[1] - first[1])
                length_squared = dx * dx + dz * dz
                if length_squared <= 1e-12:
                    continue
                length = math.sqrt(length_squared)
                amount = max(
                    0.0,
                    min(1.0, ((px - first[0]) * dx + (pz - first[1]) * dz) / length_squared),
                )
                x, z = float(first[0] + amount * dx), float(first[1] + amount * dz)
                candidates.append(
                    (
                        math.hypot(x - px, z - pz),
                        str(feature["id"]),
                        part_index,
                        segment_index,
                        way_id,
                        station_base + amount * length,
                        [x, z],
                        [dx / length, dz / length],
                        feature.get("sourceTags", {}).get("name"),
                    )
                )
                station_base += length
    if not candidates:
        raise RoadSurfaceError("harm-region context has no eligible ground-assumed road")
    distance, feature_id, part_index, segment_index, way_id, station, projected, tangent, name = (
        min(candidates)
    )
    return {
        "featureId": feature_id,
        "wayId": way_id,
        "name": name,
        "partIndex": part_index,
        "segmentIndex": segment_index,
        "stationM": station,
        "distanceM": distance,
        "centerlineProjectionLocalXZ": projected,
        "tangentXZ": tangent,
    }


def _registered_terrain_sections(
    inputs: ReleaseInputs,
    preview: np.ndarray,
    grid_report: dict[str, Any],
) -> dict[str, Any]:
    regions = grid_report["harmFallback"]["regions"]
    if not regions:
        return {
            "verticalDatum": "package-local display-grid metres",
            "sections": [],
            "footings": [],
            "affectedRegions": [],
        }
    buildings_by_id = {feature["id"]: feature for feature in inputs.buildings.get("buildings", [])}

    def inside_grid(x: float, z: float) -> bool:
        return abs(x) <= inputs.width_m / 2 and abs(z) <= inputs.depth_m / 2

    def region_detail(region: dict[str, Any], index: int) -> dict[str, Any]:
        road_context = _nearest_eligible_road_context(
            inputs, region["maximumCandidateChangeLocalXZ"]
        )
        tangent_x, tangent_z = road_context["tangentXZ"]
        normal_x, normal_z = -tangent_z, tangent_x
        center_x, center_z = road_context["centerlineProjectionLocalXZ"]
        road_samples = []
        for offset in range(-20, 21):
            x = center_x + normal_x * offset
            z = center_z + normal_z * offset
            if not inside_grid(x, z):
                continue
            road_samples.append(
                {
                    "offsetFromCenterlineM": float(offset),
                    "localXZ": [float(x), float(z)],
                    "baselineLocalM": _sample_grid(inputs.baseline, x, z, inputs.spacing_m),
                    "previewLocalM": _sample_grid(preview, x, z, inputs.spacing_m),
                }
            )
        edge = region["maximumCandidateAddedGradientEdge"]
        bank_samples = []
        requested_bank_sample_count = 0
        if edge["firstLocalXZ"] is not None:
            first_x, first_z = edge["firstLocalXZ"]
            second_x, second_z = edge["secondLocalXZ"]
            middle_x, middle_z = (first_x + second_x) / 2, (first_z + second_z) / 2
            direction = (1.0, 0.0) if edge["axis"] == "x" else (0.0, 1.0)
            for offset in range(-16, 17):
                requested_bank_sample_count += 1
                x = middle_x + direction[0] * offset
                z = middle_z + direction[1] * offset
                if not inside_grid(x, z):
                    continue
                bank_samples.append(
                    {
                        "offsetFromCandidateBankEdgeM": float(offset),
                        "localXZ": [float(x), float(z)],
                        "baselineLocalM": _sample_grid(inputs.baseline, x, z, inputs.spacing_m),
                        "previewLocalM": _sample_grid(preview, x, z, inputs.spacing_m),
                    }
                )
        footings = []
        for building_id in region["nearbyBuildingIds"]:
            feature = buildings_by_id.get(building_id)
            if feature is None:
                continue
            polygons = [
                Polygon(record["exteriorXZ"], record.get("interiorRingsXZ", []))
                for record in feature.get("geometry", {}).get("polygons", [])
            ]
            if not polygons:
                continue
            min_x = min(polygon.bounds[0] for polygon in polygons)
            min_z = min(polygon.bounds[1] for polygon in polygons)
            max_x = max(polygon.bounds[2] for polygon in polygons)
            max_z = max(polygon.bounds[3] for polygon in polygons)
            footing_z = (min_z + max_z) / 2
            footing_samples = []
            for x in range(math.ceil(min_x), math.floor(max_x) + 1):
                point = Point(float(x), footing_z)
                if not inside_grid(float(x), footing_z) or not any(
                    polygon.covers(point) for polygon in polygons
                ):
                    continue
                footing_samples.append(
                    {
                        "localXZ": [float(x), float(footing_z)],
                        "baselineLocalM": _sample_grid(
                            inputs.baseline, x, footing_z, inputs.spacing_m
                        ),
                        "previewLocalM": _sample_grid(preview, x, footing_z, inputs.spacing_m),
                    }
                )
            footings.append(
                {
                    "buildingId": building_id,
                    "sourceFootprintBoundsXZ": [min_x, min_z, max_x, max_z],
                    "crossSectionAxis": "local X through footprint-bounds midpoint Z",
                    "samples": footing_samples,
                }
            )
        return {
            "id": f"harm-region-{index:02d}",
            "coreLocalBoundsXZ": region["coreLocalBoundsXZ"],
            "maximumCandidateChangeLocalXZ": region["maximumCandidateChangeLocalXZ"],
            "maximumCandidateAbsoluteChangeM": region["maximumCandidateAbsoluteChangeM"],
            "maximumCandidateAddedGradientMPerM": region["maximumCandidateAddedGradientMPerM"],
            "maximumCandidateAddedGradientEdge": edge,
            "postFallbackMaximumAbsoluteChangeM": region["postFallbackMaximumAbsoluteChangeM"],
            "postFallbackMaximumAddedGradientMPerM": region[
                "postFallbackMaximumAddedGradientMPerM"
            ],
            "nearbyRoadWayIds": region["nearestRoadWayIds"],
            "nearbyBuildingBaseChangesM": region["nearbyBuildingBaseChangesM"],
            "roadContext": road_context,
            "sections": [
                {
                    "id": "road-cross-section",
                    "method": (
                        "1 m samples perpendicular to the nearest source centerline, ±20 m; "
                        "out-of-grid samples omitted"
                    ),
                    "requestedSampleCount": 41,
                    "omittedOutOfGridSampleCount": 41 - len(road_samples),
                    "maximumAbsolutePreviewMinusBaselineM": max(
                        (
                            abs(sample["previewLocalM"] - sample["baselineLocalM"])
                            for sample in road_samples
                        ),
                        default=0.0,
                    ),
                    "samples": road_samples,
                },
                {
                    "id": "candidate-bank-cross-section",
                    "method": (
                        "1 m samples along the candidate terrain-gradient axis, ±16 m; "
                        "out-of-grid samples omitted"
                    ),
                    "requestedSampleCount": requested_bank_sample_count,
                    "omittedOutOfGridSampleCount": requested_bank_sample_count - len(bank_samples),
                    "maximumAbsolutePreviewMinusBaselineM": max(
                        (
                            abs(sample["previewLocalM"] - sample["baselineLocalM"])
                            for sample in bank_samples
                        ),
                        default=0.0,
                    ),
                    "samples": bank_samples,
                },
            ],
            "footings": footings,
        }

    region_details = [region_detail(item, index + 1) for index, item in enumerate(regions)]
    selected_index = max(
        range(len(regions)),
        key=lambda index: regions[index]["maximumCandidateAbsoluteChangeM"],
    )
    region = regions[selected_index]
    selected = region_details[selected_index]
    selected_sections = selected["sections"]
    return {
        "verticalDatum": (
            "package-local display-grid metres relative to the original terrain origin; "
            "orthometric EA source heights are reported separately"
        ),
        "selectedHarmRegion": {
            "coreLocalBoundsXZ": region["coreLocalBoundsXZ"],
            "maximumCandidateChangeLocalXZ": region["maximumCandidateChangeLocalXZ"],
            "maximumCandidateAbsoluteChangeM": region["maximumCandidateAbsoluteChangeM"],
            "roadContext": selected["roadContext"],
        },
        "sections": [
            {**selected_sections[0], "id": "maximum-fill-road-cross-section"},
            {**selected_sections[1], "id": "maximum-added-bank-cross-section"},
        ],
        "footings": selected["footings"],
        "affectedRegions": region_details,
    }


def _browser_contexts(
    inputs: ReleaseInputs,
    profiles: list[dict[str, Any]],
    grid_report: dict[str, Any],
) -> list[dict[str, Any]]:
    profile_by_id = {profile["wayId"]: profile for profile in profiles}
    output = []
    severe = profile_by_id.get(30480989)
    if severe:
        samples = [sample for part in severe["parts"] for sample in part["crossfallSamples"]]
        maximum = max(samples, key=lambda sample: sample["baselineAbsoluteCrossfallPercent"])
        output.append(
            {
                "id": "parkfield-severe",
                "wayIds": [30480989],
                "anchorLocalXZ": maximum["centerLocalXZ"],
                "stationM": maximum["stationM"],
                "tangentXZ": maximum["tangentXZ"],
                "selection": (
                    "maximum baseline same-station crossfall sample on Parkfield way 30480989"
                ),
            }
        )
    harm_regions = grid_report.get("harmFallback", {}).get("regions", [])
    if harm_regions:
        harm_region = max(harm_regions, key=lambda item: item["maximumCandidateAbsoluteChangeM"])
        harm_point = harm_region["maximumCandidateChangeLocalXZ"]
        harm_road = _nearest_eligible_road_context(inputs, harm_point)
        output.append(
            {
                "id": "newton-high-fill"
                if harm_road["wayId"] == 46348326
                else "maximum-local-harm",
                "wayIds": sorted(set(harm_region["nearestRoadWayIds"]) | {harm_road["wayId"]}),
                "buildingIds": harm_region["nearbyBuildingIds"],
                "anchorLocalXZ": harm_point,
                "tangentXZ": harm_road["tangentXZ"],
                "stationM": harm_road["stationM"],
                "centerlineProjectionLocalXZ": harm_road["centerlineProjectionLocalXZ"],
                "distanceToCenterlineM": harm_road["distanceM"],
                "candidateMaximumAbsoluteChangeM": harm_region["maximumCandidateAbsoluteChangeM"],
                "candidateMaximumAddedGradientEdge": harm_region[
                    "maximumCandidateAddedGradientEdge"
                ],
                "selection": (
                    "largest connected region meeting the generic preview harm heuristic; "
                    "registered at its maximum candidate cut/fill coordinate"
                ),
            }
        )
    gradient_edge = grid_report["terrainGradientChange"]["maximumPositiveIncreaseEdge"]
    gradient_point = gradient_edge["firstLocalXZ"]
    gradient_candidates = []
    for feature in inputs.road_payload["features"]:
        if (
            feature.get("displayGroup") != "vehicular"
            or feature.get("groundAssumption")
            != "ground_assumed_from_absent_or_explicit_no_vertical_tags"
        ):
            continue
        way_id = feature.get("source", {}).get("osmId")
        for part_index, part in enumerate(feature.get("centerlinePartsXZ", [])):
            station_base = 0.0
            for segment_index, (first, second) in enumerate(zip(part, part[1:], strict=False)):
                dx, dz = second[0] - first[0], second[1] - first[1]
                length = math.hypot(dx, dz)
                if length <= 1e-12:
                    continue
                amount = max(
                    0.0,
                    min(
                        1.0,
                        ((gradient_point[0] - first[0]) * dx + (gradient_point[1] - first[1]) * dz)
                        / (length * length),
                    ),
                )
                projected_x = first[0] + amount * dx
                projected_z = first[1] + amount * dz
                distance = math.hypot(
                    projected_x - gradient_point[0], projected_z - gradient_point[1]
                )
                gradient_candidates.append(
                    (
                        distance,
                        str(feature["id"]),
                        part_index,
                        segment_index,
                        way_id,
                        station_base + amount * length,
                        [dx / length, dz / length],
                        [projected_x, projected_z],
                    )
                )
                station_base += length
    if not gradient_candidates:
        raise RoadSurfaceError("maximum added-gradient edge has no eligible road context")
    (
        gradient_distance,
        _stable,
        gradient_part,
        gradient_segment,
        gradient_way,
        gradient_station,
        gradient_tangent,
        gradient_centerline,
    ) = min(gradient_candidates)
    output.append(
        {
            "id": "maximum-added-gradient",
            "wayIds": [gradient_way],
            "anchorLocalXZ": gradient_point,
            "tangentXZ": gradient_tangent,
            "stationM": gradient_station,
            "partIndex": gradient_part,
            "segmentIndex": gradient_segment,
            "distanceToCenterlineM": gradient_distance,
            "centerlineProjectionLocalXZ": gradient_centerline,
            "selection": (
                "nearest eligible published centerline projection to the maximum "
                "positive derivative gradient-change edge"
            ),
        }
    )
    gradient_regions = [
        region
        for region in grid_report.get("harmFallback", {}).get("regions", [])
        if "connected added-gradient threshold and minimum area" in region["harmTriggers"]
    ]
    gradient_regions.sort(
        key=lambda region: (
            -region["maximumCandidateAddedGradientMPerM"],
            region["coreLocalBoundsXZ"],
        )
    )
    for index, region in enumerate(gradient_regions, start=1):
        anchor = region["maximumCandidateChangeLocalXZ"]
        road_context = _nearest_eligible_road_context(inputs, anchor)
        output.append(
            {
                "id": f"harm-gradient-region-{index:02d}",
                "wayIds": sorted(set(region["nearestRoadWayIds"]) | {road_context["wayId"]}),
                "buildingIds": region["nearbyBuildingIds"],
                "anchorLocalXZ": anchor,
                "tangentXZ": road_context["tangentXZ"],
                "stationM": road_context["stationM"],
                "centerlineProjectionLocalXZ": road_context["centerlineProjectionLocalXZ"],
                "distanceToCenterlineM": road_context["distanceM"],
                "candidateMaximumAddedGradientMPerM": region["maximumCandidateAddedGradientMPerM"],
                "candidateMaximumAddedGradientEdge": region["maximumCandidateAddedGradientEdge"],
                "coreLocalBoundsXZ": region["coreLocalBoundsXZ"],
                "selection": (
                    "connected candidate added-gradient region retained under the generic "
                    "preview safety heuristic; ranked by candidate added gradient"
                ),
            }
        )
    choices = (
        ("pennys-teignmouth", [-244.518, -58.794], [78455388, 78455395]),
        ("arthington-control", [-511.744, 207.096], [30482119, 30482121]),
        (
            "cricketfield-junction",
            [-307.96, -28.828],
            [23595196, 686711262, 689028452, 24806641, 30480035],
        ),
    )
    features = inputs.road_payload["features"]
    for context_id, anchor, way_ids in choices:
        candidates = []
        for feature in features:
            way_id = feature.get("source", {}).get("osmId")
            if way_id not in way_ids:
                continue
            for part_index, part in enumerate(feature.get("centerlinePartsXZ", [])):
                for segment_index, (first, second) in enumerate(zip(part, part[1:], strict=False)):
                    dx, dz = second[0] - first[0], second[1] - first[1]
                    length2 = dx * dx + dz * dz
                    if length2 <= 1e-12:
                        continue
                    amount = max(
                        0.0,
                        min(
                            1.0,
                            ((anchor[0] - first[0]) * dx + (anchor[1] - first[1]) * dz) / length2,
                        ),
                    )
                    x, z = first[0] + amount * dx, first[1] + amount * dz
                    distance = math.hypot(x - anchor[0], z - anchor[1])
                    candidates.append(
                        (
                            distance,
                            str(feature["id"]),
                            part_index,
                            segment_index,
                            x,
                            z,
                            dx / math.sqrt(length2),
                            dz / math.sqrt(length2),
                            way_id,
                            feature.get("sourceTags", {}).get("name"),
                        )
                    )
        if not candidates:
            raise RoadSurfaceError(f"browser evidence context '{context_id}' has no candidate road")
        distance, _stable, part_index, segment_index, x, z, tangent_x, tangent_z, way_id, name = (
            min(candidates)
        )
        output.append(
            {
                "id": context_id,
                "wayIds": list(way_ids),
                "queryAnchorLocalXZ": anchor,
                "anchorLocalXZ": [x, z],
                "distanceToContextAnchorM": distance,
                "wayId": way_id,
                "name": name,
                "partIndex": part_index,
                "segmentIndex": segment_index,
                "tangentXZ": [tangent_x, tangent_z],
                "selection": (
                    "nearest existing published centerline projection to registered "
                    "local context point"
                ),
            }
        )
    for context in _map_contexts(inputs):
        nearest = context["nearestRoads"][0]
        output.append(
            {
                "id": context["id"],
                "wayIds": [road["wayId"] for road in context["nearestRoads"]],
                "queryAnchorLocalXZ": context["localXZ"],
                "anchorLocalXZ": nearest["centerlineProjectionLocalXZ"],
                "distanceToContextAnchorM": nearest["distanceM"],
                "wayId": nearest["wayId"],
                "name": nearest["name"],
                "tangentXZ": nearest["tangentXZ"],
                "selection": (
                    "pinned-operation conversion of registered WGS84 map context "
                    "point; nearest published centerline is reported separately"
                ),
            }
        )
    return output


def _map_contexts(inputs: ReleaseInputs) -> list[dict[str, Any]]:
    coordinate = inputs.road_manifest.get("coordinateOperation", {}).get("wgs84ToBng", {})
    definition = coordinate.get("definition")
    if (
        not isinstance(definition, str)
        or coordinate.get("reported_accuracy_m") != 2.0
        or coordinate.get("uses_grids") is not False
    ):
        raise RoadSurfaceError(
            "pinned road manifest does not contain the accepted WGS84-to-BNG operation"
        )
    transformer = Transformer.from_pipeline(definition)
    anchors = (
        ("user-map-context-1", 50.4783696, -3.5383277, (78455388,)),
        ("user-map-context-2", 50.4777531, -3.5375891, (1363931058, 30480989)),
    )
    output = []
    for context_id, latitude, longitude, way_ids in anchors:
        easting, northing = transformer.transform(longitude, latitude, errcheck=True)
        local = [float(easting) - inputs.origin_e_m, inputs.origin_n_m - float(northing)]
        roads = []
        for feature in inputs.road_payload["features"]:
            way_id = feature.get("source", {}).get("osmId")
            if way_id not in way_ids:
                continue
            for part_index, part in enumerate(feature.get("centerlinePartsXZ", [])):
                for segment_index, (first, second) in enumerate(zip(part, part[1:], strict=False)):
                    dx, dz = second[0] - first[0], second[1] - first[1]
                    length2 = dx * dx + dz * dz
                    if length2 <= 1e-12:
                        continue
                    amount = max(
                        0.0,
                        min(
                            1.0, ((local[0] - first[0]) * dx + (local[1] - first[1]) * dz) / length2
                        ),
                    )
                    x, z = first[0] + amount * dx, first[1] + amount * dz
                    distance = math.hypot(x - local[0], z - local[1])
                    length = math.sqrt(length2)
                    roads.append(
                        {
                            "distanceM": distance,
                            "wayId": way_id,
                            "name": feature.get("sourceTags", {}).get("name"),
                            "partIndex": part_index,
                            "segmentIndex": segment_index,
                            "centerlineProjectionLocalXZ": [x, z],
                            "tangentXZ": [dx / length, dz / length],
                        }
                    )
        roads.sort(
            key=lambda road: (
                road["distanceM"],
                road["wayId"],
                road["partIndex"],
                road["segmentIndex"],
            )
        )
        closest_by_way: dict[int, dict[str, Any]] = {}
        for road in roads:
            closest_by_way.setdefault(road["wayId"], road)
        roads = sorted(
            closest_by_way.values(),
            key=lambda road: (
                road["distanceM"],
                road["wayId"],
                road["partIndex"],
                road["segmentIndex"],
            ),
        )
        if not roads:
            raise RoadSurfaceError(
                f"WGS84 context point '{context_id}' has no requested candidate centerline"
            )
        output.append(
            {
                "id": context_id,
                "wgs84LatLon": [latitude, longitude],
                "localXZ": local,
                "coordinateOperation": coordinate.get("name"),
                "reportedAccuracyM": coordinate["reported_accuracy_m"],
                "preferredOSTN15GridAvailable": False,
                "nearestRoads": roads,
                "interpretation": "context only; not an exact road-surface control",
            }
        )
    return output


def _profiles(
    inputs: ReleaseInputs, preview: np.ndarray, raster_paths: list[Path]
) -> list[dict[str, Any]]:
    features = inputs.road_payload["features"]
    by_id = {int(feature["source"]["osmId"]): feature for feature in features}
    output = []
    missing = []
    for way_id in PROFILE_WAY_IDS:
        feature = by_id.get(way_id)
        if feature is None:
            missing.append(way_id)
            continue
        output.append(_profile_feature(feature, inputs, preview, raster_paths))
    if missing:
        raise RoadSurfaceError(f"mandatory source-backed profile ways are missing: {missing}")
    return output


def _safe_float(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _safe_float(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_float(item) for item in value]
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def _atomic_write(output_directory: Path, files: dict[str, bytes]) -> None:
    staged: dict[Path, Path] = {}
    try:
        for filename, content in sorted(files.items()):
            if filename not in OUTPUT_FILES:
                raise RoadSurfaceError(f"refusing an unowned derivative output '{filename}'")
            target = output_directory / filename
            with tempfile.NamedTemporaryFile(
                prefix=f".road-surface-preview-{filename}.",
                suffix=".tmp",
                dir=output_directory,
                delete=False,
            ) as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
                staged[target] = Path(stream.name)
        for target, stage in staged.items():
            os.replace(stage, target)
    finally:
        for stage in staged.values():
            stage.unlink(missing_ok=True)


def build_preview(
    project_root: Path, config: PreviewConfig, execution_record: Path | None = None
) -> dict[str, Any]:
    """Generate a deterministic derivative and QA bound to one pinned release."""
    project_root = project_root.resolve()
    execution_record_path = _preflight_execution_record(project_root, execution_record)
    release_root = project_root / "public/worlds/torquay-poc-001-2km/releases" / config.release_id
    output_directory = guard_output_directory(
        project_root,
        project_root / config.output_directory,
        [project_root / "public/worlds/torquay-poc-001-2km", release_root],
    )
    inputs = load_release_inputs(project_root, config)
    segments = _segments_from_payload(
        inputs.road_payload, config.transition_distance_factor, inputs.spacing_m
    )
    if not segments:
        raise RoadSurfaceError(
            "the pinned release has no eligible ground-assumed vehicular centerlines"
        )
    preview, grid_report = _grade_grid(
        inputs.baseline, segments, inputs.spacing_m, inputs.width_m, inputs.depth_m, config
    )
    raster_paths, raster_hashes = _source_raster_paths(project_root)
    profile_records = _profiles(inputs, preview, raster_paths)
    buildings = _building_base_report(inputs, preview)
    _annotate_fallback_buildings(inputs, grid_report, buildings)
    contexts = _browser_contexts(inputs, profile_records, grid_report)
    terrain_sections = _registered_terrain_sections(inputs, preview, grid_report)
    map_contexts = _map_contexts(inputs)
    baseline_bytes = inputs.baseline.astype("<f4", copy=False).tobytes(order="C")
    derivative_bytes = preview.astype("<f4", copy=False).tobytes(order="C")
    derivative_hash = hashlib.sha256(derivative_bytes).hexdigest()
    baseline_hash = hashlib.sha256(baseline_bytes).hexdigest()
    expected_height_hash = inputs.manifest["heightfield"]["sha256"]
    if baseline_hash != expected_height_hash:
        raise RoadSurfaceError(
            "baseline heightfield read-back hash changed during preview generation"
        )
    qa = {
        "formatVersion": 1,
        "issue": "Road-surface treatment preview; visual approximation only; not TVW-016",
        "algorithmVersion": ALGORITHM_VERSION,
        "source": {
            "releaseId": inputs.release_id,
            "readySha256": inputs.ready_sha256,
            "inventorySha256": inputs.inventory_sha256,
            "terrainManifestSha256": inputs.manifest_sha256,
            "terrainHeightfieldSha256": expected_height_hash,
            "roadManifestSha256": inputs.road_manifest_sha256,
            "roadPayloadSha256": inputs.road_payload_sha256,
        },
        "sourceMetadata": {
            "worldId": "torquay-poc-001",
            "sceneProfile": "current_2km",
            "roadFeatureCount": len(inputs.road_payload.get("features", [])),
            "rasterComparisonInputs": raster_hashes,
        },
        "derivative": {
            "path": "heightfield.f32",
            "byteLength": len(derivative_bytes),
            "sha256": derivative_hash,
            "grid": {
                "columns": inputs.columns,
                "rows": inputs.rows,
                "spacingM": inputs.spacing_m,
                "widthM": inputs.width_m,
                "depthM": inputs.depth_m,
                "rowOrder": "north-to-south",
                "byteOrder": "little-endian",
                "encoding": "float32",
                "valueMeaning": "visual world Y relative to original terrain origin elevation",
            },
        },
        "policy": {
            "target": (
                "zero imposed lateral crossfall, anchored to unchanged baseline terrain "
                "sampled at the nearest eligible existing centerline projection"
            ),
            "longitudinalTerrain": (
                "retained from baseline projection samples; no longitudinal smoothing"
            ),
            "width": (
                "unchanged configured full visual width from the pinned road package; "
                "not measured kerb width"
            ),
            "transitionDistance": (
                "max(configured full width, two grid cells) beyond each ribbon edge"
            ),
            "transitionDistanceFactor": config.transition_distance_factor,
            "blend": "cubic smoothstep with zero slope at both transition ends",
            "ambiguity": {
                "equalDistanceToleranceM": config.ambiguity_distance_m,
                "minimumAnchorHeightDifferenceM": config.ambiguity_height_difference_m,
                "coreRadius": ("larger involved half-width plus one grid spacing"),
                "fadeDistance": ("larger involved configured full width or two grid spacings"),
                "fadeBlend": (
                    "cubic smoothstep multiplier applied to treatment change; zero "
                    "slope at both ends"
                ),
                "effect": (
                    "retain original ground in the core and smoothly fade treatment "
                    "around it; never average disconnected road anchors"
                ),
            },
            "harmFallback": {
                "maximumAbsoluteLocalChangeM": config.fallback_absolute_change_m,
                "minimumAddedGradientMPerM": config.fallback_added_gradient_m_per_m,
                "minimumConnectedGradientRegionAreaM2": config.fallback_minimum_region_area_m2,
                "fadeDistanceM": config.fallback_fade_distance_m,
                "blend": "cubic smoothstep with zero slope at the retained core and outer edge",
                "interpretation": (
                    "preview safety heuristic only; locally retain source ground where the "
                    "absolute change threshold is reached, or where a connected added-gradient "
                    "region meets both its threshold and minimum area; fade back to the candidate "
                    "outside the region"
                ),
                "effect": (
                    "preserve the coherent shared display surface while avoiding a hard mask edge; "
                    "local roads may remain source-draped where the fallback applies"
                ),
            },
            "roadSurfaceOffsetM": ROAD_SURFACE_OFFSET_M,
            "displayTerrainStatus": "approximate visual grading; surrounding ground adjusted",
            "coordinates": (
                "source X/Z centerlines and widths are unchanged; local Y is derived "
                "for display only"
            ),
        },
        "gridTreatment": grid_report,
        "registeredTerrainSections": terrain_sections,
        "profiles": {
            "maximumStationSpacingM": MAX_PROFILE_STATION_SPACING_M,
            "crossfallMethod": (
                "opposite samples at plus/minus half the unchanged configured width "
                "at interval midpoints"
            ),
            "longitudinalMethod": (
                "successive centerline stations in stored way direction; absolute grade percent"
            ),
            "sourceEA1mMethod": (
                "original EA DTM raster sampled bilinearly between 1 m pixel centers; "
                "orthometric heights are reported separately from local terrain heights"
            ),
            "ways": profile_records,
        },
        "buildingBases": buildings,
        "registeredWgs84MapContexts": map_contexts,
        "browserContexts": contexts,
        "limitations": [
            (
                "The 2 m grid is a visual approximation, not a surveyed road surface "
                "or engineering design."
            ),
            (
                "No kerbs, cambers, cuttings, retaining walls, bridge elevations, or "
                "tunnel elevations are inferred."
            ),
            (
                "Path features remain source-draped and can contact locally changed "
                "shared display ground."
            ),
            (
                "Building base changes follow the existing highest-under-footprint "
                "roof-base policy and are disclosed above."
            ),
            (
                "The AOI remains selected_pending_coverage / not_checked; mapped "
                "counts do not establish completeness."
            ),
            (
                "The selected WGS84-to-BNG operation reports 2 m accuracy and lacks "
                "the preferred OSTN15 grid; context points are not survey controls."
            ),
        ],
    }
    qa_bytes = _canonical_json(_safe_float(qa))
    qa_hash = hashlib.sha256(qa_bytes).hexdigest()
    manifest = {
        "formatVersion": 1,
        "worldId": "torquay-poc-001",
        "sceneProfile": "current_2km",
        "packageType": "road-surface-display-grid-derivative",
        "algorithmVersion": ALGORITHM_VERSION,
        "interpretation": (
            "Visual approximation only; not EA source terrain and not "
            "engineering-grade road levels."
        ),
        "source": {
            "releaseId": inputs.release_id,
            "readySha256": inputs.ready_sha256,
            "inventorySha256": inputs.inventory_sha256,
            "terrainManifestSha256": inputs.manifest_sha256,
            "terrainHeightfieldSha256": expected_height_hash,
            "roadManifestSha256": inputs.road_manifest_sha256,
            "roadPayloadSha256": inputs.road_payload_sha256,
        },
        "grid": {
            "columns": inputs.columns,
            "rows": inputs.rows,
            "spacingM": inputs.spacing_m,
            "widthM": inputs.width_m,
            "depthM": inputs.depth_m,
            "rowOrder": "north-to-south",
            "byteOrder": "little-endian",
            "encoding": "float32",
            "valueMeaning": "visual world Y relative to original terrain origin elevation",
        },
        "parameters": {
            "transitionDistanceFactor": config.transition_distance_factor,
            "ambiguityDistanceM": config.ambiguity_distance_m,
            "ambiguityHeightDifferenceM": config.ambiguity_height_difference_m,
            "ambiguityRetentionCore": "larger involved half-width plus one grid spacing",
            "ambiguityFadeDistance": "larger involved configured width or two grid spacings",
            "maximumChangedHeightM": config.maximum_changed_height_m,
            "fallbackAbsoluteChangeM": config.fallback_absolute_change_m,
            "fallbackAddedGradientMPerM": config.fallback_added_gradient_m_per_m,
            "fallbackMinimumRegionAreaM2": config.fallback_minimum_region_area_m2,
            "fallbackFadeDistanceM": config.fallback_fade_distance_m,
            "targetCrossfallPercent": 0.0,
            "roadSurfaceOffsetM": ROAD_SURFACE_OFFSET_M,
        },
        "assets": {
            "heightfield": {
                "path": "heightfield.f32",
                "byteLength": len(derivative_bytes),
                "sha256": derivative_hash,
            },
            "qa": {"path": "qa.json", "byteLength": len(qa_bytes), "sha256": qa_hash},
        },
    }
    manifest_bytes = _canonical_json(manifest)
    # Capture protected inputs immediately before writing; verify the same used files afterward.
    current_inputs = load_release_inputs(project_root, config)
    if current_inputs.source_hashes != inputs.source_hashes:
        raise RoadSurfaceError("a protected source-package input changed during preview generation")
    for path, original in zip(raster_paths, raster_hashes, strict=True):
        if sha256_file(path) != original["sha256"]:
            raise RoadSurfaceError(
                f"EA raster comparison input changed during preview generation: '{path}'"
            )
    protected_output_inputs = [project_root / "public/worlds/torquay-poc-001-2km", release_root]
    guard_output_directory(project_root, output_directory, protected_output_inputs)
    output_directory = _prepare_output_directory(
        project_root, output_directory, protected_output_inputs
    )
    outputs = {
        name: hashlib.sha256(data).hexdigest()
        for name, data in {
            "manifest.json": manifest_bytes,
            "heightfield.f32": derivative_bytes,
            "qa.json": qa_bytes,
        }.items()
    }
    result = {
        "outputDirectory": output_directory.relative_to(project_root).as_posix(),
        "releaseId": inputs.release_id,
        "inputHashes": {
            key: value.get("sha256", value.get("readySha256", value.get("inventorySha256")))
            for key, value in sorted(inputs.source_hashes.items())
        },
        "outputHashes": outputs,
        "derivativeByteLength": len(derivative_bytes),
        "changedVertexCount": grid_report["changedVertexCount"],
        "ambiguousGridVertexCount": grid_report["ambiguousGridVertexCountRetainedAtOriginalGround"],
        "profileWayIds": [profile["wayId"] for profile in profile_records],
    }
    if execution_record_path is not None:
        refreshed_record_path = _preflight_execution_record(project_root, execution_record)
        if refreshed_record_path != execution_record_path:
            raise RoadSurfaceError("execution record destination changed during preview generation")
    record_stream = None
    record_identity = None
    if execution_record_path is not None:
        try:
            record_stream = execution_record_path.open("xb")
            stat = os.fstat(record_stream.fileno())
            record_identity = (stat.st_dev, stat.st_ino)
        except FileExistsError as exc:
            raise RoadSurfaceError(
                "execution record destination appeared during preview generation; "
                "refusing to overwrite it"
            ) from exc
    try:
        _atomic_write(
            output_directory,
            {
                "manifest.json": manifest_bytes,
                "heightfield.f32": derivative_bytes,
                "qa.json": qa_bytes,
            },
        )
        if record_stream is not None:
            record_stream.write(_canonical_json(_safe_float(result)))
            record_stream.flush()
            os.fsync(record_stream.fileno())
            record_stream.close()
            record_stream = None
    except BaseException:
        if record_stream is not None:
            record_stream.close()
            record_stream = None
        if execution_record_path is not None and record_identity is not None:
            try:
                stat = execution_record_path.stat(follow_symlinks=False)
                if (stat.st_dev, stat.st_ino) == record_identity:
                    execution_record_path.unlink()
            except FileNotFoundError:
                pass
        raise
    return _safe_float(result)
