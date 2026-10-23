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
import shapely
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

ALGORITHM_VERSION = "road-surface-preview-3.0.0"
FALLBACK_ABSOLUTE_CHANGE_HEADROOM_M = 0.5
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
SEVERE_CORRIDOR_WAY_IDS = (30480989, 78455388, 78455395)
SEVERE_CROSSFALL_NUMERICAL_MARGIN_M = 0.001
FALLBACK_MIN_CONNECTED_AREA_M2 = 8.0
TEIGNMOUTH_CANDIDATE_VARIANT = "teignmouth-circled-segment"
TEIGNMOUTH_CANDIDATE_OUTPUT = "public/worlds/torquay-road-surface-teignmouth-candidate"
TEIGNMOUTH_WAY_ID = 78455395
TEIGNMOUTH_PART_INDEX = 0
TEIGNMOUTH_STATION_START_M = 140.0
TEIGNMOUTH_STATION_END_M = 155.0
TEIGNMOUTH_CROSSFALL_LIMIT_PERCENT = 5.0
TEIGNMOUTH_WIDTH_SPAN_LIMIT_M = 0.30
# Leave deterministic float32/solver headroom beneath the inclusive preview gates.
TEIGNMOUTH_SOLVER_HEADROOM_M = 0.0001
TEIGNMOUTH_MAX_PROJECTION_ITERATIONS = 2000


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
    treatment_variant: str = "accepted-preview"


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
    station_start_m: float = 0.0

    @property
    def length_m(self) -> float:
        return math.sqrt(self.length_squared)


@dataclass(frozen=True)
class RoadPartTopology:
    """Endpoint graph for the connected source centerline parts."""

    lengths_m: dict[tuple[int, int], float]
    endpoint_nodes: dict[tuple[int, int], tuple[int, int]]
    adjacency: tuple[tuple[tuple[int, float], ...], ...]


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
    station_m: float


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
    accepted_preview_qa: dict[str, Any] | None = None


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
    candidate_shape = expected | {"treatment_variant"}
    if not isinstance(raw, dict) or set(raw) not in (expected, candidate_shape):
        raise RoadSurfaceError("preview config has an invalid object shape")
    treatment_variant = raw.get("treatment_variant", "accepted-preview")
    expected_output = {
        "accepted-preview": "public/worlds/torquay-road-surface-preview",
        TEIGNMOUTH_CANDIDATE_VARIANT: TEIGNMOUTH_CANDIDATE_OUTPUT,
    }.get(treatment_variant)
    if (
        raw["format_version"] != 1
        or raw["release_id"] != CURRENT_RELEASE_ID
        or raw["output_directory"] != expected_output
        or raw["transition_distance_factor"] != 1.0
        or ("treatment_variant" in raw) != (treatment_variant != "accepted-preview")
    ):
        raise RoadSurfaceError("preview config does not match an exact pinned output policy")
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
        treatment_variant=treatment_variant,
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


def guard_output_directory(
    project_root: Path,
    requested: Path,
    protected: list[Path],
    *,
    owned_files: frozenset[str] = OUTPUT_FILES,
) -> Path:
    """Guard the exact owned derivative directory before creating or replacing files."""
    project_root = project_root.resolve()
    expected_outputs = {
        project_root / "public/worlds/torquay-road-surface-preview",
        project_root / TEIGNMOUTH_CANDIDATE_OUTPUT,
    }
    candidate = requested if requested.is_absolute() else project_root / requested
    _assert_no_reparse_components(candidate)
    resolved = candidate.resolve(strict=False)
    if not any(
        os.path.normcase(str(resolved)) == os.path.normcase(str(expected))
        for expected in expected_outputs
    ):
        raise RoadSurfaceError(
            "output directory must be exactly one of the exact allowlisted derivative paths"
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
            if child.name not in owned_files or child.is_dir() or _is_reparse_point(child):
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
        project_root / "docs/milestones/Road-surface-treatment-teignmouth-spec.md",
        project_root / "config/road-surface-preview.json",
        project_root / "config/road-surface-teignmouth-candidate.json",
        project_root / "scripts/build-road-surface-preview.py",
        project_root / "pipeline/torquay_pipeline/road_surface.py",
        project_root / "pipeline/torquay_pipeline/road_surface_patch.py",
        project_root / "pipeline/tests/test_road_surface_patch.py",
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
            station_start_m = 0.0
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
                        station_start_m=station_start_m,
                    )
                )
                station_start_m += math.sqrt(length_squared)
    return sorted(segments, key=lambda item: item.sort_key)


def _road_part_topology(
    segments: list[RoadSegment], endpoint_tolerance_m: float = 0.05
) -> RoadPartTopology:
    """Connect continuous parts without routing harm retention across junction branches."""
    if not math.isfinite(endpoint_tolerance_m) or endpoint_tolerance_m <= 0:
        raise RoadSurfaceError("road topology endpoint tolerance must be finite and positive")
    grouped: dict[tuple[int, int], list[RoadSegment]] = {}
    for segment in segments:
        grouped.setdefault((segment.way_id, segment.sort_key[1]), []).append(segment)
    for part in grouped.values():
        part.sort(key=lambda segment: segment.sort_key[2])

    groups = sorted(grouped)
    lengths: dict[tuple[int, int], float] = {}
    endpoints: list[tuple[tuple[int, int], int, float, float]] = []
    for group in groups:
        part = grouped[group]
        first, last = part[0], part[-1]
        lengths[group] = last.station_start_m + last.length_m
        endpoints.append((group, 0, first.first_x, first.first_z))
        endpoints.append((group, 1, last.first_x + last.dx, last.first_z + last.dz))

    parent = list(range(len(endpoints)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first: int, second: int) -> None:
        first_root, second_root = find(first), find(second)
        if first_root != second_root:
            parent[max(first_root, second_root)] = min(first_root, second_root)

    buckets: dict[tuple[int, int], list[int]] = {}
    for index, (_group, _end, x, z) in enumerate(endpoints):
        bucket = (
            math.floor(x / endpoint_tolerance_m),
            math.floor(z / endpoint_tolerance_m),
        )
        for bucket_x in range(bucket[0] - 1, bucket[0] + 2):
            for bucket_z in range(bucket[1] - 1, bucket[1] + 2):
                for other in buckets.get((bucket_x, bucket_z), ()):
                    _other_group, _other_end, other_x, other_z = endpoints[other]
                    if math.hypot(x - other_x, z - other_z) <= endpoint_tolerance_m:
                        union(index, other)
        buckets.setdefault(bucket, []).append(index)

    node_ids = {index: index for index in range(len(endpoints))}
    endpoint_nodes: dict[tuple[int, int], list[int]] = {}
    for index, (group, end, _x, _z) in enumerate(endpoints):
        endpoint_nodes.setdefault(group, [0, 0])[end] = node_ids[index]
    adjacency: list[list[tuple[int, float]]] = [[] for _ in node_ids]
    normalized_endpoints: dict[tuple[int, int], tuple[int, int]] = {}
    for group in groups:
        start_node, end_node = endpoint_nodes[group]
        normalized_endpoints[group] = start_node, end_node
        length = lengths[group]
        adjacency[start_node].append((end_node, length))
        adjacency[end_node].append((start_node, length))
    clustered_endpoints: dict[int, list[int]] = {}
    for index in range(len(endpoints)):
        clustered_endpoints.setdefault(find(index), []).append(index)
    for cluster in clustered_endpoints.values():
        by_way: dict[int, list[int]] = {}
        for endpoint_index in cluster:
            way_id = endpoints[endpoint_index][0][0]
            by_way.setdefault(way_id, []).append(endpoint_index)
        for same_way_endpoints in by_way.values():
            for position, first in enumerate(same_way_endpoints):
                for second in same_way_endpoints[position + 1 :]:
                    adjacency[first].append((second, 0.0))
                    adjacency[second].append((first, 0.0))
        if len(cluster) == 2 and len(by_way) == 2:
            first, second = cluster
            adjacency[first].append((second, 0.0))
            adjacency[second].append((first, 0.0))
    return RoadPartTopology(
        lengths_m=lengths,
        endpoint_nodes=normalized_endpoints,
        adjacency=tuple(tuple(sorted(items)) for items in adjacency),
    )


def _topology_node_distances(
    topology: RoadPartTopology,
    seed_intervals: dict[tuple[int, int], list[tuple[float, float]]],
) -> list[float]:
    """Return shortest source-station distances to seed intervals at every endpoint."""
    distances = [math.inf] * len(topology.adjacency)
    queue: list[tuple[float, int]] = []
    for group, intervals in sorted(seed_intervals.items()):
        if group not in topology.lengths_m:
            continue
        length = topology.lengths_m[group]
        start_node, end_node = topology.endpoint_nodes[group]
        for start, end in intervals:
            if not (math.isfinite(start) and math.isfinite(end)):
                raise RoadSurfaceError("road retention interval contains a non-finite station")
            interval_low, interval_high = sorted((start, end))
            low = max(0.0, min(length, interval_low))
            high = max(0.0, min(length, interval_high))
            for node, distance in ((start_node, low), (end_node, length - high)):
                if distance < distances[node]:
                    distances[node] = distance
                    heapq.heappush(queue, (distance, node))
    while queue:
        distance, node = heapq.heappop(queue)
        if distance != distances[node]:
            continue
        for neighbor, edge_length in topology.adjacency[node]:
            next_distance = distance + edge_length
            if next_distance < distances[neighbor]:
                distances[neighbor] = next_distance
                heapq.heappush(queue, (next_distance, neighbor))
    return distances


def _topology_station_distances(
    topology: RoadPartTopology,
    node_distances: list[float],
    group: tuple[int, int],
    stations: np.ndarray,
    seed_intervals: dict[tuple[int, int], list[tuple[float, float]]],
) -> np.ndarray:
    """Distance from stations to any seed, continuous across shared part endpoints."""
    length = topology.lengths_m[group]
    start_node, end_node = topology.endpoint_nodes[group]
    station_values = np.asarray(stations, dtype=np.float64)
    distances = np.minimum(
        node_distances[start_node] + station_values,
        node_distances[end_node] + length - station_values,
    )
    for start, end in seed_intervals.get(group, ()):
        interval_low, interval_high = sorted((start, end))
        low = max(0.0, min(length, interval_low))
        high = max(0.0, min(length, interval_high))
        distances = np.minimum(
            distances, np.maximum(np.maximum(low - station_values, station_values - high), 0.0)
        )
    return distances


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
        station_m=segment.station_start_m + amount * segment.length_m,
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


def _transition_for_station(
    segment: RoadSegment,
    station_m: float,
    spacing_m: float,
    config: PreviewConfig,
    expanded_intervals: dict[tuple[int, int], list[tuple[float, float]]] | None,
) -> float:
    base_transition = max(segment.width_m, 2 * spacing_m) * config.transition_distance_factor
    if not expanded_intervals:
        return base_transition
    maximum_transition = 32.0
    if maximum_transition <= base_transition:
        return base_transition
    intervals = expanded_intervals.get((segment.way_id, segment.sort_key[1]), [])
    amount = 0.0
    for start_station, end_station in intervals:
        distance = max(start_station - station_m, station_m - end_station, 0.0)
        if distance >= config.fallback_fade_distance_m:
            continue
        position = distance / config.fallback_fade_distance_m
        blend = 1 - (3 * position * position - 2 * position * position * position)
        amount = max(amount, blend)
    return base_transition + amount * (maximum_transition - base_transition)


def _grid_tile_range(tile_index: int, spacing_m: float, half_extent: float, count: int) -> range:
    lower = math.ceil((tile_index * SPATIAL_TILE_M + half_extent) / spacing_m)
    upper_exclusive = math.ceil(((tile_index + 1) * SPATIAL_TILE_M + half_extent) / spacing_m)
    return range(max(0, lower), min(count, upper_exclusive))


def _sample_grid_many(
    heights: np.ndarray, x: np.ndarray, z: np.ndarray, spacing_m: float
) -> np.ndarray:
    """Vectorized form of the renderer's fixed-diagonal terrain sampler."""
    columns, rows = heights.shape[1], heights.shape[0]
    half_width = (columns - 1) * spacing_m / 2
    half_depth = (rows - 1) * spacing_m / 2
    gx = np.clip((x + half_width) / spacing_m, 0, columns - 1)
    gz = np.clip((z + half_depth) / spacing_m, 0, rows - 1)
    column = np.minimum(np.floor(gx).astype(np.int64), columns - 2)
    row = np.minimum(np.floor(gz).astype(np.int64), rows - 2)
    u, v = gx - column, gz - row
    a = heights[row, column].astype(np.float64)
    b = heights[row, column + 1].astype(np.float64)
    c = heights[row + 1, column].astype(np.float64)
    d = heights[row + 1, column + 1].astype(np.float64)
    first = a + (b - a) * u + (c - a) * v
    second = d + (c - d) * (1 - u) + (b - d) * (1 - v)
    return np.where(u + v <= 1, first, second)


def _carriageway_triangle_owners(
    baseline: np.ndarray,
    segments: list[RoadSegment],
    spacing_m: float,
    width_m: float,
    depth_m: float,
    ambiguity_height_difference_m: float,
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """Assign every grid vertex in a triangle touched by a road ribbon to its owner.

    The support stencil is formed by exact Shapely intersections against the same
    fixed diagonal triangles used by the displayed heightfield. All vertices of
    every intersected triangle receive the core target; the shoulder begins beyond
    this triangle support. Incompatible carriageway cores are retained at source
    ground.
    """
    rows, columns = baseline.shape
    half_width, half_depth = width_m / 2, depth_m / 2
    grouped: dict[tuple[int, int], list[tuple[int, RoadSegment]]] = {}
    for segment_index, segment in enumerate(segments):
        grouped.setdefault((segment.way_id, segment.sort_key[1]), []).append(
            (segment_index, segment)
        )
    owners = np.full(rows * columns, -1, dtype=np.int32)
    owner_is_core = np.zeros(rows * columns, dtype=bool)
    owner_distances = np.full(rows * columns, np.inf, dtype=np.float64)
    owner_targets = np.zeros(rows * columns, dtype=np.float64)
    owner_stations = np.zeros(rows * columns, dtype=np.float64)
    conflicts: dict[int, dict[str, Any]] = {}

    for group_key in sorted(grouped):
        group = sorted(grouped[group_key], key=lambda item: item[1].sort_key[2])
        group_segments = [segment for _index, segment in group]
        points = [(group_segments[0].first_x, group_segments[0].first_z)]
        points.extend(
            (segment.first_x + segment.dx, segment.first_z + segment.dz)
            for segment in group_segments
        )
        ribbon = LineString(points).buffer(
            group_segments[0].width_m / 2, cap_style="flat", join_style="mitre"
        )
        min_x, min_z, max_x, max_z = ribbon.bounds
        min_column = max(0, math.floor((min_x + half_width) / spacing_m))
        max_column = min(columns - 2, math.floor((max_x + half_width) / spacing_m))
        min_row = max(0, math.floor((min_z + half_depth) / spacing_m))
        max_row = min(rows - 2, math.floor((max_z + half_depth) / spacing_m))
        if min_column > max_column or min_row > max_row:
            continue

        grid_rows, grid_columns = np.mgrid[min_row : max_row + 1, min_column : max_column + 1]
        first_x = grid_columns.ravel() * spacing_m - half_width
        first_z = grid_rows.ravel() * spacing_m - half_depth
        lower_left = np.column_stack((first_x, first_z))
        lower_right = lower_left + np.array([spacing_m, 0.0])
        upper_left = lower_left + np.array([0.0, spacing_m])
        upper_right = lower_left + np.array([spacing_m, spacing_m])
        first_triangles = shapely.polygons(
            np.stack((lower_left, lower_right, upper_left, lower_left), axis=1)
        )
        second_triangles = shapely.polygons(
            np.stack((upper_right, upper_left, lower_right, upper_right), axis=1)
        )
        intersects_first = shapely.intersects(ribbon, first_triangles)
        intersects_second = shapely.intersects(ribbon, second_triangles)
        rr, cc = grid_rows.ravel(), grid_columns.ravel()
        triangle_vertices = np.concatenate(
            (
                np.column_stack(
                    (
                        rr[intersects_first] * columns + cc[intersects_first],
                        rr[intersects_first] * columns + cc[intersects_first] + 1,
                        (rr[intersects_first] + 1) * columns + cc[intersects_first],
                    )
                ),
                np.column_stack(
                    (
                        (rr[intersects_second] + 1) * columns + cc[intersects_second] + 1,
                        (rr[intersects_second] + 1) * columns + cc[intersects_second],
                        rr[intersects_second] * columns + cc[intersects_second] + 1,
                    )
                ),
            ),
            axis=0,
        )
        vertex_indices = np.unique(triangle_vertices)
        if not vertex_indices.size:
            continue
        vertex_rows, vertex_columns = np.divmod(vertex_indices, columns)
        x = vertex_columns.astype(np.float64) * spacing_m - half_width
        z = vertex_rows.astype(np.float64) * spacing_m - half_depth
        best_distances = np.full(vertex_indices.size, np.inf, dtype=np.float64)
        best_segments = np.full(vertex_indices.size, -1, dtype=np.int32)
        best_amounts = np.zeros(vertex_indices.size, dtype=np.float64)
        for segment_index, segment in group:
            amount = np.clip(
                ((x - segment.first_x) * segment.dx + (z - segment.first_z) * segment.dz)
                / segment.length_squared,
                0.0,
                1.0,
            )
            projected_x = segment.first_x + amount * segment.dx
            projected_z = segment.first_z + amount * segment.dz
            distance = np.hypot(projected_x - x, projected_z - z)
            choose = distance < best_distances - 1e-9
            best_distances[choose] = distance[choose]
            best_segments[choose] = segment_index
            best_amounts[choose] = amount[choose]
        target_x = np.empty(vertex_indices.size, dtype=np.float64)
        target_z = np.empty(vertex_indices.size, dtype=np.float64)
        for segment_index, segment in group:
            selected = best_segments == segment_index
            if not np.any(selected):
                continue
            amount = np.clip(
                (
                    (x[selected] - segment.first_x) * segment.dx
                    + (z[selected] - segment.first_z) * segment.dz
                )
                / segment.length_squared,
                0.0,
                1.0,
            )
            target_x[selected] = segment.first_x + amount * segment.dx
            target_z[selected] = segment.first_z + amount * segment.dz
        targets = _sample_grid_many(baseline, target_x, target_z, spacing_m)
        # The renderer samples the whole fixed triangle. A vertex outside the
        # geometric ribbon can still contribute to an intersected pavement
        # triangle, so every vertex in this exact support stencil must keep the
        # carriageway target instead of being weakened as a shoulder.
        candidate_is_core = np.ones(best_distances.shape, dtype=bool)
        candidate_stations = np.asarray(
            [
                segments[int(segment_index)].station_start_m
                + best_amounts[index] * segments[int(segment_index)].length_m
                for index, segment_index in enumerate(best_segments)
            ],
            dtype=np.float64,
        )
        previous = owners[vertex_indices]
        free = previous < 0
        # A prior incompatible conflict stays source-owned. Compatible overlaps
        # resolve by nearest centerline and the stable sorted feature order.
        conflict_vertex = previous == -2
        assign_free = free & ~conflict_vertex
        owners[vertex_indices[assign_free]] = best_segments[assign_free]
        owner_is_core[vertex_indices[assign_free]] = candidate_is_core[assign_free]
        owner_distances[vertex_indices[assign_free]] = best_distances[assign_free]
        owner_targets[vertex_indices[assign_free]] = targets[assign_free]
        owner_stations[vertex_indices[assign_free]] = candidate_stations[assign_free]
        occupied = (previous >= 0) & (previous != -2)
        if not np.any(occupied):
            continue
        old_indices = vertex_indices[occupied]
        old_segments = owners[old_indices].copy()
        old_ways = np.asarray([segments[index].way_id for index in old_segments], dtype=np.int64)
        new_ways = np.full(old_ways.shape, group_key[0], dtype=np.int64)
        different_ways = old_ways != new_ways
        if not np.any(different_ways):
            prior_is_core = owner_is_core[old_indices]
            new_is_core = candidate_is_core[occupied]
            choose_new = (new_is_core & ~prior_is_core) | (
                (new_is_core == prior_is_core)
                & (best_distances[occupied] < owner_distances[old_indices] - 1e-9)
            )
            owners[old_indices[choose_new]] = best_segments[occupied][choose_new]
            owner_is_core[old_indices[choose_new]] = new_is_core[choose_new]
            owner_distances[old_indices[choose_new]] = best_distances[occupied][choose_new]
            owner_targets[old_indices[choose_new]] = targets[occupied][choose_new]
            owner_stations[old_indices[choose_new]] = candidate_stations[occupied][choose_new]
            continue
        height_differences = np.abs(owner_targets[old_indices] - targets[occupied])
        prior_is_core = owner_is_core[old_indices]
        new_is_core = candidate_is_core[occupied]
        incompatible = (
            different_ways
            & prior_is_core
            & new_is_core
            & (height_differences >= ambiguity_height_difference_m)
        )
        for local_index in np.flatnonzero(incompatible):
            flat_index = int(old_indices[local_index])
            prior_segment = int(old_segments[local_index])
            record = conflicts.setdefault(
                flat_index,
                {
                    "ways": set(),
                    "heightDifferenceM": 0.0,
                    "stationByWayM": {},
                    "segmentByWay": {},
                    "partIndexByWay": {},
                },
            )
            new_segment = int(best_segments[occupied][local_index])
            record["ways"].update((segments[prior_segment].way_id, group_key[0]))
            record["heightDifferenceM"] = max(
                record["heightDifferenceM"], float(height_differences[local_index])
            )
            record["stationByWayM"][segments[prior_segment].way_id] = float(
                owner_stations[flat_index]
            )
            record["stationByWayM"][group_key[0]] = float(candidate_stations[occupied][local_index])
            record["segmentByWay"][segments[prior_segment].way_id] = prior_segment
            record["segmentByWay"][group_key[0]] = new_segment
            record["partIndexByWay"][segments[prior_segment].way_id] = segments[
                prior_segment
            ].sort_key[1]
            record["partIndexByWay"][group_key[0]] = segments[new_segment].sort_key[1]
            owners[flat_index] = -2
            owner_is_core[flat_index] = False
        compatible = different_ways & ~incompatible
        choose_compatible = compatible & (
            (new_is_core & ~prior_is_core)
            | (
                (new_is_core == prior_is_core)
                & (best_distances[occupied] < owner_distances[old_indices] - 1e-9)
            )
        )
        owners[old_indices[choose_compatible]] = best_segments[occupied][choose_compatible]
        owner_is_core[old_indices[choose_compatible]] = new_is_core[choose_compatible]
        owner_distances[old_indices[choose_compatible]] = best_distances[occupied][
            choose_compatible
        ]
        owner_targets[old_indices[choose_compatible]] = targets[occupied][choose_compatible]
        owner_stations[old_indices[choose_compatible]] = candidate_stations[occupied][
            choose_compatible
        ]

    segment_ways = np.asarray([segment.way_id for segment in segments], dtype=np.int64)

    # Edge checks use an immutable ownership snapshot. Mutating owners as each
    # edge is found would let later edges interpret the -2 conflict sentinel as
    # a segment index and serialize unrelated road identities.
    owners_snapshot = owners.copy()
    owner_is_core_snapshot = owner_is_core.copy()
    owner_targets_snapshot = owner_targets.copy()
    owner_stations_snapshot = owner_stations.copy()
    conflict_edge_vertices: set[int] = set()

    def mark_incompatible_edges(first: np.ndarray, second: np.ndarray) -> None:
        first_owner, second_owner = owners_snapshot[first], owners_snapshot[second]
        eligible = (first_owner >= 0) & (second_owner >= 0)
        eligible &= owner_is_core_snapshot[first] & owner_is_core_snapshot[second]
        eligible &= (
            segment_ways[np.maximum(first_owner, 0)] != segment_ways[np.maximum(second_owner, 0)]
        )
        eligible &= np.abs(owner_targets_snapshot[first] - owner_targets_snapshot[second]) >= (
            ambiguity_height_difference_m
        )
        for first_index, second_index in zip(first[eligible], second[eligible], strict=True):
            for flat_index, other_flat_index in (
                (int(first_index), int(second_index)),
                (int(second_index), int(first_index)),
            ):
                prior_segment = int(owners_snapshot[flat_index])
                other_segment = int(owners_snapshot[other_flat_index])
                prior_way, other_way = (
                    segments[prior_segment].way_id,
                    segments[other_segment].way_id,
                )
                record = conflicts.setdefault(
                    flat_index,
                    {
                        "ways": set(),
                        "heightDifferenceM": 0.0,
                        "stationByWayM": {},
                        "segmentByWay": {},
                        "partIndexByWay": {},
                    },
                )
                record["ways"].update((prior_way, other_way))
                record["heightDifferenceM"] = max(
                    record["heightDifferenceM"],
                    abs(
                        owner_targets_snapshot[flat_index]
                        - owner_targets_snapshot[other_flat_index]
                    ),
                )
                for way, segment_index, station in (
                    (prior_way, prior_segment, owner_stations_snapshot[flat_index]),
                    (other_way, other_segment, owner_stations_snapshot[other_flat_index]),
                ):
                    record["stationByWayM"][way] = float(station)
                    record["segmentByWay"][way] = segment_index
                    record["partIndexByWay"][way] = segments[segment_index].sort_key[1]
                conflict_edge_vertices.add(flat_index)

    flat_indices = np.arange(rows * columns, dtype=np.int64).reshape(rows, columns)
    mark_incompatible_edges(flat_indices[:, :-1], flat_indices[:, 1:])
    mark_incompatible_edges(flat_indices[:-1, :], flat_indices[1:, :])
    mark_incompatible_edges(flat_indices[:-1, 1:], flat_indices[1:, :-1])
    if conflict_edge_vertices:
        conflict_indices = np.fromiter(sorted(conflict_edge_vertices), dtype=np.int64)
        owners[conflict_indices] = -2
        owner_is_core[conflict_indices] = False

    return (
        owners.reshape(rows, columns),
        owner_is_core.reshape(rows, columns),
        [
            {
                "row": index // columns,
                "column": index % columns,
                "ways": sorted(record["ways"]),
                "heightDifferenceM": float(record["heightDifferenceM"]),
                "stationByWayM": record["stationByWayM"],
                "segmentByWay": record["segmentByWay"],
                "partIndexByWay": record["partIndexByWay"],
                "localXZ": [
                    (index % columns) * spacing_m - half_width,
                    (index // columns) * spacing_m - half_depth,
                ],
            }
            for index, record in sorted(conflicts.items())
        ],
    )


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
    cut_fill_seed_mask = np.abs(candidate.astype(np.float64) - baseline.astype(np.float64)) >= (
        config.fallback_absolute_change_m
    )
    gradient_seed_mask = np.zeros(baseline.shape, dtype=bool)
    steep_x = added_x >= config.fallback_added_gradient_m_per_m
    steep_z = added_z >= config.fallback_added_gradient_m_per_m
    gradient_seed_mask[:, :-1] |= steep_x
    gradient_seed_mask[:, 1:] |= steep_x
    gradient_seed_mask[:-1, :] |= steep_z
    gradient_seed_mask[1:, :] |= steep_z
    # Keep distinct harm causes as distinct connected regions. Unioning cut/fill
    # and gradient seeds can chain through roads and spuriously retain a long
    # corridor that includes otherwise safe mandatory stations.
    components_by_trigger = [
        ("absolute local cut/fill threshold", _mask_components(cut_fill_seed_mask)),
        (
            "connected added-gradient threshold and minimum area",
            _mask_components(gradient_seed_mask),
        ),
    ]
    half_width, half_depth = width_m / 2, depth_m / 2
    delta = candidate.astype(np.float64) - baseline.astype(np.float64)
    output = []
    for trigger_name, components in components_by_trigger:
        for component in components:
            vertex_mask = np.zeros(baseline.shape, dtype=bool)
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
            cut_fill_trigger = (
                trigger_name == "absolute local cut/fill threshold"
                and maximum_change >= config.fallback_absolute_change_m
            )
            gradient_trigger = (
                trigger_name == "connected added-gradient threshold and minimum area"
                and maximum_added_gradient >= config.fallback_added_gradient_m_per_m
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
                            (
                                "connected added-gradient threshold and minimum area",
                                gradient_trigger,
                            ),
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


def _inverse_smoothstep(weights: np.ndarray) -> np.ndarray:
    """Invert the smoothstep used by the distance fallback to recover normalized distance."""
    target = np.clip(np.asarray(weights, dtype=np.float64), 0.0, 1.0)
    low = np.zeros_like(target)
    high = np.ones_like(target)
    for _ in range(32):
        middle = (low + high) / 2.0
        value = 3.0 * middle * middle - 2.0 * middle * middle * middle
        lower_half = value < target
        low = np.where(lower_half, middle, low)
        high = np.where(lower_half, high, middle)
    return (low + high) / 2.0


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


def _apply_station_harm_fallback(
    baseline: np.ndarray,
    candidate: np.ndarray,
    segments: list[RoadSegment],
    spacing_m: float,
    width_m: float,
    depth_m: float,
    config: PreviewConfig,
    nearest_way_grid: np.ndarray,
    nearest_segment_grid: np.ndarray,
    nearest_station_grid: np.ndarray,
    nearest_distance_grid: np.ndarray,
    core_conflict_seeds: list[dict[str, Any]],
    triangle_owner_segments: np.ndarray | None = None,
    triangle_owner_is_core: np.ndarray | None = None,
    enforce_gradient_limit: bool = True,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Retain source ground along only the road station spans linked to measured harm."""
    rows, columns = baseline.shape
    scale = np.ones((rows, columns), dtype=np.float32)
    regions = _connected_fallback_regions(baseline, candidate, spacing_m, config, width_m, depth_m)
    segment_groups = {
        index: (segment.way_id, segment.sort_key[1]) for index, segment in enumerate(segments)
    }
    group_widths: dict[tuple[int, int], float] = {}
    for index, segment in enumerate(segments):
        group_widths.setdefault(segment_groups[index], segment.width_m)
    sorted_groups = sorted(set(segment_groups.values()))
    group_indexes = {group: index for index, group in enumerate(sorted_groups)}
    segment_group_indexes = np.asarray(
        [group_indexes[segment_groups[index]] for index in range(len(segments))],
        dtype=np.int32,
    )
    topology = _road_part_topology(segments)
    nearest_group_grid = np.full((rows, columns), -1, dtype=np.int32)
    valid_segments = nearest_segment_grid >= 0
    nearest_group_grid[valid_segments] = segment_group_indexes[nearest_segment_grid[valid_segments]]
    triangle_core_group_grid = np.full((rows, columns), -1, dtype=np.int32)
    if triangle_owner_segments is not None and triangle_owner_is_core is not None:
        if triangle_owner_segments.shape != (rows, columns) or triangle_owner_is_core.shape != (
            rows,
            columns,
        ):
            raise RoadSurfaceError("triangle support ownership does not match the terrain grid")
        triangle_core = (triangle_owner_segments >= 0) & triangle_owner_is_core
        triangle_core_group_grid[triangle_core] = segment_group_indexes[
            triangle_owner_segments[triangle_core]
        ]
    group_masks = {
        group: nearest_group_grid == group_index for group, group_index in group_indexes.items()
    }
    triangle_support_mask = np.zeros((rows, columns), dtype=bool)
    if triangle_owner_segments is not None and triangle_owner_is_core is not None:
        triangle_support_mask = (triangle_owner_segments >= 0) & triangle_owner_is_core

    def retain_intervals(
        seed_intervals: dict[tuple[int, int], list[tuple[float, float]]],
        lateral_band_offsets: tuple[float, float] | None = None,
        lateral_source_strength: float = 1.0,
    ) -> tuple[int, int]:
        if not seed_intervals:
            return 0, 0
        node_distances = _topology_node_distances(topology, seed_intervals)
        active_groups = set(seed_intervals)
        active_groups.update(
            group
            for group, (start_node, end_node) in topology.endpoint_nodes.items()
            if min(node_distances[start_node], node_distances[end_node])
            < config.fallback_fade_distance_m
        )
        retained_count = 0
        faded_count = 0
        for group in sorted(active_groups):
            group_index = group_indexes[group]
            mask = group_masks[group]
            station_grid = np.where(mask, nearest_station_grid, 0.0)
            distance = _topology_station_distances(
                topology, node_distances, group, station_grid, seed_intervals
            )
            station_strength = np.zeros((rows, columns), dtype=np.float32)
            station_core = mask & (distance <= 1e-9)
            station_fade = mask & (distance > 1e-9) & (distance < config.fallback_fade_distance_m)
            station_strength[station_core] = 1.0
            if np.any(station_fade):
                position = distance[station_fade] / config.fallback_fade_distance_m
                station_strength[station_fade] = (1 - 3 * position**2 + 2 * position**3).astype(
                    np.float32
                )

            lateral_strength = np.ones((rows, columns), dtype=np.float32)
            if lateral_band_offsets is not None:
                road_distance = np.where(mask, nearest_distance_grid, -1.0)
                half_road = group_widths[group] / 2
                lower = half_road + lateral_band_offsets[0]
                upper = half_road + lateral_band_offsets[1]
                lateral_strength[:] = 0.0
                protected_core = (
                    mask & (triangle_core_group_grid == group_index)
                    if triangle_owner_segments is not None and triangle_owner_is_core is not None
                    else mask & (road_distance <= half_road + 1e-9)
                )
                interior_fade = mask & (road_distance > half_road) & (road_distance < lower)
                band_core = mask & (road_distance >= lower) & (road_distance <= upper)
                exterior_fade = (
                    mask
                    & (road_distance > upper)
                    & (road_distance < upper + config.fallback_fade_distance_m)
                )
                lateral_strength[band_core] = lateral_source_strength
                if np.any(interior_fade):
                    width = max(lower - half_road, 1e-9)
                    position = (road_distance[interior_fade] - half_road) / width
                    lateral_strength[interior_fade] = (
                        lateral_source_strength * (3 * position**2 - 2 * position**3)
                    ).astype(np.float32)
                if np.any(exterior_fade):
                    position = (
                        road_distance[exterior_fade] - upper
                    ) / config.fallback_fade_distance_m
                    lateral_strength[exterior_fade] = (
                        lateral_source_strength * (1 - 3 * position**2 + 2 * position**3)
                    ).astype(np.float32)
                # Keep the full triangle support stencil at candidate height. Apply
                # this after shoulder bands/fades so their masks cannot overwrite it.
                lateral_strength[protected_core] = 0.0
            section_strength = station_strength * lateral_strength
            section_scale = np.ones((rows, columns), dtype=np.float32)
            section_scale[mask] = 1.0 - section_strength[mask]
            np.minimum(scale, section_scale, out=scale)
            retained_count += int(np.count_nonzero(section_strength >= 1.0))
            faded_count += int(
                np.count_nonzero((section_strength > 0.0) & (section_strength < 1.0))
            )
        return retained_count, faded_count

    conflict_station_values: dict[tuple[int, int], list[float]] = {}
    for seed in core_conflict_seeds:
        for way_id, station in seed.get("stationByWayM", {}).items():
            part_index = seed.get("partIndexByWay", {}).get(way_id)
            if part_index is None:
                continue
            conflict_station_values.setdefault((int(way_id), int(part_index)), []).append(
                float(station)
            )
    incompatible_sections = []
    conflict_seed_intervals: dict[tuple[int, int], list[tuple[float, float]]] = {}
    for group, values in sorted(conflict_station_values.items()):
        ordered = sorted(values)
        intervals: list[list[float]] = []
        for station in ordered:
            if intervals and station - intervals[-1][1] <= max(2 * spacing_m, 1.0):
                intervals[-1][1] = station
            else:
                intervals.append([station, station])
        for start_station, end_station in intervals:
            conflict_seed_intervals.setdefault(group, []).append((start_station, end_station))
            incompatible_sections.append(
                {
                    "wayId": group[0],
                    "partIndex": group[1],
                    "startM": float(start_station),
                    "endM": float(end_station),
                    "retainedLengthM": float(max(spacing_m, end_station - start_station)),
                    "fadeDistanceAtEachEndM": config.fallback_fade_distance_m,
                    "reason": "incompatible adjacent or overlapping carriageway core anchors",
                }
            )
    retain_intervals(conflict_seed_intervals)

    for region in regions:
        component = region.pop("corePoints")
        direct_core_component = (
            [point for point in component if triangle_support_mask[point]]
            if triangle_owner_segments is not None and triangle_owner_is_core is not None
            else []
        )
        region["nearestRoadWayIds"] = sorted(
            {
                int(nearest_way_grid[row, column])
                for row, column in component
                if nearest_way_grid[row, column] > 0
            }
        )
        min_row, min_column, local_candidate_weights = _fallback_distance_weights(
            component, rows, columns, spacing_m, config.fallback_fade_distance_m
        )
        max_row = min_row + local_candidate_weights.shape[0]
        max_column = min_column + local_candidate_weights.shape[1]
        local_support = triangle_support_mask[min_row:max_row, min_column:max_column]
        support_in_fade = local_support & (local_candidate_weights < 1.0)
        support_fade_points = [
            (min_row + int(row), min_column + int(column))
            for row, column in np.argwhere(support_in_fade)
        ]
        core_component = sorted(set(direct_core_component) | set(support_fade_points))
        has_off_core_seed = any(not triangle_support_mask[point] for point in component)
        core_cut_fill_harm = (
            bool(direct_core_component)
            and "absolute local cut/fill threshold" in region["harmTriggers"]
            and region["maximumCandidateAbsoluteChangeM"] >= config.fallback_absolute_change_m
        )
        if core_component and has_off_core_seed and not core_cut_fill_harm:
            support_local_points = [
                (int(row), int(column)) for row, column in np.argwhere(local_support)
            ]
            support_candidate_weights = np.ones_like(local_candidate_weights, dtype=np.float32)
            if support_local_points:
                support_min_row, support_min_column, support_weights = _fallback_distance_weights(
                    support_local_points,
                    local_candidate_weights.shape[0],
                    local_candidate_weights.shape[1],
                    spacing_m,
                    config.fallback_fade_distance_m,
                )
                support_candidate_weights[
                    support_min_row : support_min_row + support_weights.shape[0],
                    support_min_column : support_min_column + support_weights.shape[1],
                ] = support_weights
            support_distance = (
                _inverse_smoothstep(support_candidate_weights) * config.fallback_fade_distance_m
            )
            harm_distance = (
                _inverse_smoothstep(local_candidate_weights) * config.fallback_fade_distance_m
            )
            distance_sum = support_distance + harm_distance
            position = np.divide(
                support_distance,
                distance_sum,
                out=np.zeros_like(support_distance),
                where=distance_sum > 0.0,
            )
            smooth_ramp = 3.0 * position**2 - 2.0 * position**3
            local_source_strength = (1.0 - local_candidate_weights.astype(np.float64)) * smooth_ramp
            local_source_strength[local_support] = 0.0
            local_scale = 1.0 - local_source_strength
            scale[min_row:max_row, min_column:max_column] = np.minimum(
                scale[min_row:max_row, min_column:max_column], local_scale.astype(np.float32)
            )
            seed_intervals: dict[tuple[int, int], list[float]] = {}
            for row, column in component:
                segment_index = int(nearest_segment_grid[row, column])
                station = float(nearest_station_grid[row, column])
                if segment_index < 0 or station < 0:
                    continue
                group = segment_groups[segment_index]
                seed_intervals.setdefault(group, []).append(station)
            ramp_distances = [
                float(support_distance[row - min_row, column - min_column])
                for row, column in component
            ]
            region["fallbackMode"] = "core-aware spatial source-retention ramp"
            region["componentIntersectsTriangleCoreSupport"] = bool(direct_core_component)
            region["harmFadeEnvelopeIntersectsTriangleCoreSupport"] = bool(support_fade_points)
            region["stationIntervals"] = [
                {
                    "wayId": group[0],
                    "partIndex": group[1],
                    "startM": float(min(stations)),
                    "endM": float(max(stations)),
                    "rampFromTriangleCoreEdgeToHarmSeed": True,
                }
                for group, stations in sorted(seed_intervals.items())
            ]
            region["coreAreaEquivalentM2"] = float(
                np.count_nonzero(local_source_strength >= 1.0) * spacing_m * spacing_m
            )
            region["fadedAreaEquivalentM2"] = float(
                np.count_nonzero((local_source_strength > 0.0) & (local_source_strength < 1.0))
                * spacing_m
                * spacing_m
            )
            region["affectedAreaEquivalentM2"] = float(
                np.count_nonzero(local_source_strength > 0.0) * spacing_m * spacing_m
            )
            region["fadeDistanceM"] = config.fallback_fade_distance_m
            region["sourceRetentionRamp"] = {
                "start": "0 at immutable triangle-support vertices",
                "seed": "1 at the harmful component before strict surface-gradient validation",
                "blend": "cubic smoothstep of distances to support and harm sets",
                "maximumDistanceM": config.fallback_fade_distance_m,
                "seedDistanceToSupportRangeM": [
                    float(min(ramp_distances)) if ramp_distances else 0.0,
                    float(max(ramp_distances)) if ramp_distances else 0.0,
                ],
            }
            region["effect"] = (
                "keep triangle-supported road vertices at candidate height and ramp source "
                "retention smoothly toward the nearby harmful seed; the resulting shared terrain "
                "surface is checked against strict added-gradient and cut/fill limits"
            )
            region["fadeBlend"] = (
                "cubic smoothstep across measured support-to-seed distance and outward to candidate"
            )
            continue
        if not core_component:
            local_source_strength = 1.0 - local_candidate_weights.astype(np.float64)
            local_scale = 1.0 - local_source_strength
            scale[min_row:max_row, min_column:max_column] = np.minimum(
                scale[min_row:max_row, min_column:max_column], local_scale.astype(np.float32)
            )
            region["fallbackMode"] = "bounded spatial fade for non-core harm component"
            region["stationIntervals"] = []
            region["coreAreaEquivalentM2"] = float(len(component) * spacing_m * spacing_m)
            region["fadedAreaEquivalentM2"] = float(
                np.count_nonzero((local_source_strength > 0.0) & (local_source_strength < 1.0))
                * spacing_m
                * spacing_m
            )
            region["affectedAreaEquivalentM2"] = float(
                np.count_nonzero(local_source_strength > 0.0) * spacing_m * spacing_m
            )
            region["fadeDistanceM"] = config.fallback_fade_distance_m
            region["effect"] = (
                "retain source ground around the connected non-core harm component with a bounded "
                "spatial smoothstep fade; its full influence envelope is clear of "
                "triangle-supported "
                "carriageway vertices"
            )
            region["fadeBlend"] = "cubic smoothstep with zero slope at the harm core and outer edge"
            continue

        direct_core_set = set(direct_core_component)
        grouped_stations: dict[tuple[int, int], list[tuple[float, float, bool]]] = {}
        for row, column in core_component:
            segment_index = int(triangle_owner_segments[row, column])
            station = float(nearest_station_grid[row, column])
            if segment_index < 0 or station < 0:
                continue
            group = segment_groups[segment_index]
            grouped_stations.setdefault(group, []).append(
                (
                    station,
                    float(nearest_distance_grid[row, column]),
                    (row, column) in direct_core_set,
                )
            )
        # If the harm fade envelope reaches immutable triangle support, reject the road
        # section from the actual harm stations too. This avoids returning a flat core to
        # candidate midway through a source-ground transition.
        for row, column in component:
            segment_index = int(nearest_segment_grid[row, column])
            station = float(nearest_station_grid[row, column])
            if segment_index < 0 or station < 0:
                continue
            group = segment_groups[segment_index]
            grouped_stations.setdefault(group, []).append(
                (station, float(nearest_distance_grid[row, column]), False)
            )
        region["stationIntervals"] = []
        region["retainedCoreVertexCount"] = 0
        region["fadeVertexCount"] = 0
        seed_intervals: dict[tuple[int, int], list[tuple[float, float]]] = {}
        group_details: dict[tuple[int, int], dict[str, Any]] = {}
        lateral_offsets: list[tuple[float, float]] = []
        contains_core_harm = bool(support_fade_points or direct_core_component)
        for group, samples in sorted(grouped_stations.items()):
            stations = [sample[0] for sample in samples]
            lateral_distances = [sample[1] for sample in samples]
            has_triangle_core = any(sample[2] for sample in samples)
            start_station, end_station = min(stations), max(stations)
            minimum_lateral = min(lateral_distances)
            maximum_lateral = max(lateral_distances)
            half_road = group_widths[group] / 2
            seed_intervals[group] = [(start_station, end_station)]
            group_details[group] = {
                "startM": start_station,
                "endM": end_station,
                "minimumLateralM": minimum_lateral,
                "maximumLateralM": maximum_lateral,
                "hasTriangleCore": has_triangle_core,
            }
            contains_core_harm |= minimum_lateral <= half_road + 1e-9 or has_triangle_core
            lateral_offsets.append(
                (
                    max(0.0, minimum_lateral - half_road),
                    max(0.0, maximum_lateral - half_road),
                )
            )

        lateral_band_offsets = None
        lateral_source_strength = 0.0
        if seed_intervals and not contains_core_harm:
            lateral_band_offsets = (
                min(item[0] for item in lateral_offsets),
                max(item[1] for item in lateral_offsets),
            )
            if "absolute local cut/fill threshold" in region["harmTriggers"]:
                lateral_source_strength = max(
                    lateral_source_strength,
                    1.0
                    - max(
                        0.0,
                        config.fallback_absolute_change_m - FALLBACK_ABSOLUTE_CHANGE_HEADROOM_M,
                    )
                    / max(region["maximumCandidateAbsoluteChangeM"], 1e-9),
                )
            if "connected added-gradient threshold and minimum area" in region["harmTriggers"]:
                lateral_source_strength = 1.0
            lateral_source_strength = float(np.clip(lateral_source_strength, 0.0, 1.0))
        retained_count, faded_count = retain_intervals(
            seed_intervals,
            lateral_band_offsets,
            lateral_source_strength,
        )
        node_distances = _topology_node_distances(topology, seed_intervals)
        connected_groups = [
            group
            for group, (start_node, end_node) in topology.endpoint_nodes.items()
            if math.isfinite(node_distances[start_node]) or math.isfinite(node_distances[end_node])
        ]
        region["retainedCoreVertexCount"] += retained_count
        region["fadeVertexCount"] += faded_count
        for group, detail in sorted(group_details.items()):
            start_station = detail["startM"]
            end_station = detail["endM"]
            minimum_lateral = detail["minimumLateralM"]
            maximum_lateral = detail["maximumLateralM"]
            has_triangle_core = detail["hasTriangleCore"]
            core_samples = np.asarray(
                [
                    station
                    for row, column in component
                    if int(nearest_segment_grid[row, column]) >= 0
                    and segment_groups[int(nearest_segment_grid[row, column])] == group
                    for station in [float(nearest_station_grid[row, column])]
                    if station >= 0
                ],
                dtype=np.float64,
            )
            region["stationIntervals"].append(
                {
                    "wayId": group[0],
                    "partIndex": group[1],
                    "startM": float(start_station),
                    "endM": float(end_station),
                    "retainedLengthM": float(max(spacing_m, end_station - start_station)),
                    "fadeDistanceAtEachEndM": config.fallback_fade_distance_m,
                    "componentStationSampleCount": int(core_samples.size),
                    "componentLateralDistanceRangeM": [
                        float(minimum_lateral),
                        float(maximum_lateral),
                    ],
                    "componentIntersectsTriangleCoreSupport": has_triangle_core,
                    "maximumSourceGroundStrengthWithinBand": lateral_source_strength,
                    "topologyConnectedPartCount": len(connected_groups),
                    "fallbackScope": (
                        (
                            "full road section because candidate harm reaches carriageway core"
                            if direct_core_component
                            else (
                                "full road section because bounded harm fade reaches "
                                "carriageway core"
                            )
                        )
                        if lateral_band_offsets is None
                        else (
                            "affected shoulder band with smooth cross-road fade; "
                            "carriageway core protected"
                        )
                    ),
                }
            )
        region["fallbackMode"] = (
            "connected-section source retention for core cut/fill harm"
            if core_cut_fill_harm
            else (
                "connected-section source retention because harm fade reaches triangle core"
                if support_fade_points and not direct_core_component
                else "connected-section source retention because harm intersects triangle core"
            )
        )
        region["coreCutFillConnectedSectionFallback"] = core_cut_fill_harm
        region["componentIntersectsTriangleCoreSupport"] = bool(direct_core_component)
        region["harmFadeEnvelopeIntersectsTriangleCoreSupport"] = bool(support_fade_points)
        region["effect"] = (
            "retain source ground across linked road station intervals and the full cross-section, "
            "with smooth zero-ended longitudinal fades"
        )
        region["fadeDistanceM"] = config.fallback_fade_distance_m
        region["fadeBlend"] = "cubic smoothstep along road station with zero slope at both ends"
        region["coreAreaEquivalentM2"] = float(
            region["retainedCoreVertexCount"] * spacing_m * spacing_m
        )
        region["fadedAreaEquivalentM2"] = float(region["fadeVertexCount"] * spacing_m * spacing_m)
        region["affectedAreaEquivalentM2"] = (
            region["coreAreaEquivalentM2"] + region["fadedAreaEquivalentM2"]
        )

    output = (
        baseline.astype(np.float64)
        + scale.astype(np.float64) * (candidate.astype(np.float64) - baseline.astype(np.float64))
    ).astype("<f4")
    if not np.isfinite(output).all():
        raise RoadSurfaceError("station harm fallback produced a non-finite display height")
    actual_delta = np.abs(output.astype(np.float64) - baseline.astype(np.float64))
    maximum_after_fallback = float(np.max(actual_delta))
    if maximum_after_fallback > config.fallback_absolute_change_m + 1e-5:
        raise RoadSurfaceError(
            "station harm fallback could not keep the local terrain change within the "
            f"{config.fallback_absolute_change_m:g} m preview policy; residual is "
            f"{maximum_after_fallback:.6f} m"
        )
    gradient_change = _terrain_gradient_change_summary(
        baseline.astype(np.float64),
        output.astype(np.float64),
        spacing_m,
        width_m,
        depth_m,
    )
    if (
        enforce_gradient_limit
        and gradient_change["maximumPositiveIncreaseMPerM"]
        >= config.fallback_added_gradient_m_per_m
    ):
        edge = gradient_change["maximumPositiveIncreaseEdge"]
        edge_diagnostics = []
        for point in (edge["firstLocalXZ"], edge["secondLocalXZ"]):
            column = min(columns - 1, max(0, round((point[0] + width_m / 2) / spacing_m)))
            row = min(rows - 1, max(0, round((point[1] + depth_m / 2) / spacing_m)))
            segment_index = int(nearest_segment_grid[row, column])
            edge_diagnostics.append(
                {
                    "localXZ": point,
                    "wayId": int(nearest_way_grid[row, column]),
                    "stationM": float(nearest_station_grid[row, column]),
                    "segmentIndex": segment_index,
                }
            )
        raise RoadSurfaceError(
            "station harm fallback left a connected added-gradient safety heuristic "
            f"at {gradient_change['maximumPositiveIncreaseMPerM']:.6f} m/m near "
            f"{edge}; nearest projections {edge_diagnostics}"
        )
    for region in regions:
        bounds = region["coreLocalBoundsXZ"]
        min_column = max(0, math.floor((bounds[0] + width_m / 2) / spacing_m))
        max_column = min(columns - 1, math.ceil((bounds[2] + width_m / 2) / spacing_m))
        min_row = max(0, math.floor((bounds[1] + depth_m / 2) / spacing_m))
        max_row = min(rows - 1, math.ceil((bounds[3] + depth_m / 2) / spacing_m))
        local_delta = output[min_row : max_row + 1, min_column : max_column + 1].astype(
            np.float64
        ) - baseline[min_row : max_row + 1, min_column : max_column + 1].astype(np.float64)
        region["postFallbackMaximumAbsoluteChangeM"] = float(np.max(np.abs(local_delta)))
        region["postFallbackMaximumAddedGradientMPerM"] = float(
            gradient_change["maximumPositiveIncreaseMPerM"]
        )
    return output, {
        "policy": {
            "maximumAbsoluteLocalChangeM": config.fallback_absolute_change_m,
            "minimumNewGradientIncreaseMPerM": config.fallback_added_gradient_m_per_m,
            "minimumConnectedGradientAreaM2": config.fallback_minimum_region_area_m2,
            "alongRoadFadeDistanceM": config.fallback_fade_distance_m,
            "interpretation": (
                "preview safety heuristics only; connected cut/fill or added-gradient regions "
                "map to the nearest source road station interval, where source ground is retained "
                "and treatment fades along that same road"
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
        "incompatibleCoreSections": incompatible_sections,
        "maximumChangeAfterFallbackM": maximum_after_fallback,
        "maximumAddedGradientAfterFallbackMPerM": gradient_change["maximumPositiveIncreaseMPerM"],
    }


def _grade_grid(
    baseline: np.ndarray,
    segments: list[RoadSegment],
    spacing_m: float,
    width_m: float,
    depth_m: float,
    config: PreviewConfig,
    expanded_shoulder_intervals: dict[tuple[int, int], list[tuple[float, float]]] | None = None,
    inputs: ReleaseInputs | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Apply nearest-road anchored cross sections and retain ground in conflicts."""
    rows, columns = baseline.shape
    half_width, half_depth = width_m / 2, depth_m / 2
    configured_shoulder_intervals: dict[tuple[int, int], list[tuple[float, float]]] = {}
    if config.treatment_variant == TEIGNMOUTH_CANDIDATE_VARIANT:
        configured_shoulder_intervals[(TEIGNMOUTH_WAY_ID, TEIGNMOUTH_PART_INDEX)] = [
            (TEIGNMOUTH_STATION_START_M, TEIGNMOUTH_STATION_END_M)
        ]
    effective_shoulder_intervals = {
        group: list(intervals) for group, intervals in (expanded_shoulder_intervals or {}).items()
    }
    for group, intervals in configured_shoulder_intervals.items():
        existing = effective_shoulder_intervals.setdefault(group, [])
        existing.extend(interval for interval in intervals if interval not in existing)
    tiles: dict[tuple[int, int], list[int]] = {}
    triangle_owner_segments, triangle_owner_is_core, core_conflict_seeds = (
        _carriageway_triangle_owners(
            baseline,
            segments,
            spacing_m,
            width_m,
            depth_m,
            config.ambiguity_height_difference_m,
        )
    )
    for segment_index, segment in enumerate(segments):
        group = (segment.way_id, segment.sort_key[1])
        widened = bool(effective_shoulder_intervals and group in effective_shoulder_intervals)
        radius = segment.influence_m + config.ambiguity_distance_m
        if widened:
            radius = max(radius, segment.width_m / 2 + 32.0)
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
    nearest_segment_grid = np.full((rows, columns), -1, dtype=np.int32)
    nearest_station_grid = np.full((rows, columns), -1.0, dtype=np.float64)
    nearest_distance_grid = np.full((rows, columns), -1.0, dtype=np.float64)
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
                    group = (segment.way_id, segment.sort_key[1])
                    transition = (
                        _transition_for_station(
                            segment,
                            projection.station_m,
                            spacing_m,
                            config,
                            effective_shoulder_intervals,
                        )
                        if effective_shoulder_intervals and group in effective_shoulder_intervals
                        else segment.influence_m - segment.width_m / 2
                    )
                    active_extent = segment.width_m / 2 + transition
                    if projection.distance_m <= active_extent + config.ambiguity_distance_m + 1e-9:
                        ambiguity_projections.append(projection)
                        if projection.distance_m <= active_extent + 1e-9:
                            active_projections.append(projection)
                core_owner_index = int(triangle_owner_segments[row, column])
                if core_owner_index >= 0:
                    owner_projection = _project(
                        core_owner_index,
                        segments[core_owner_index],
                        x,
                        z,
                        baseline,
                        spacing_m,
                    )
                    if all(
                        projection.segment_index != core_owner_index
                        for projection in active_projections
                    ):
                        active_projections.append(owner_projection)
                elif core_owner_index == -2:
                    conflict = next(
                        (
                            item
                            for item in core_conflict_seeds
                            if item["row"] == row and item["column"] == column
                        ),
                        None,
                    )
                    if conflict is not None:
                        ambiguous[row * columns + column] = {
                            "row": row,
                            "column": column,
                            "ways": conflict["ways"],
                            "heightDifferenceM": conflict["heightDifferenceM"],
                            "retentionRadiusM": 0.0,
                            "fadeDistanceM": 0.0,
                        }
                    continue
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
                nearest = (
                    next(
                        projection
                        for projection in active_projections
                        if projection.segment_index == core_owner_index
                    )
                    if core_owner_index >= 0
                    else min(by_way.values(), key=lambda item: _projection_key(item, segments))
                )
                nearest_way_grid[row, column] = nearest.way_id
                nearest_segment_grid[row, column] = nearest.segment_index
                nearest_station_grid[row, column] = nearest.station_m
                nearest_distance_grid[row, column] = nearest.distance_m
                ambiguity_by_way: dict[int, Projection] = {}
                for projection in ambiguity_projections:
                    current = ambiguity_by_way.get(projection.way_id)
                    if current is None or _projection_key(projection, segments) < _projection_key(
                        current, segments
                    ):
                        ambiguity_by_way[projection.way_id] = projection
                competitors = (
                    []
                    if core_owner_index >= 0
                    else sorted(
                        (
                            item
                            for way_id, item in ambiguity_by_way.items()
                            if way_id != nearest.way_id
                        ),
                        key=lambda item: _projection_key(item, segments),
                    )
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
                        "retentionRadiusM": 0.0,
                        "fadeDistanceM": 0.0,
                    }
                    affected_segment_ids.update((nearest.segment_index, conflict.segment_index))
                    continue
                segment = segments[nearest.segment_index]
                half_road = segment.width_m / 2
                transition = _transition_for_station(
                    segment,
                    nearest.station_m,
                    spacing_m,
                    config,
                    effective_shoulder_intervals,
                )
                if half_road < nearest.distance_m < half_road + transition:
                    transition_mask[row, column] = True
                weight = (
                    1.0
                    if core_owner_index >= 0 and triangle_owner_is_core[row, column]
                    else _blend_weight(nearest.distance_m, half_road, transition)
                )
                if weight <= 0:
                    continue
                base_y = float(baseline[row, column])
                graded_y = base_y + weight * (nearest.target_y - base_y)
                if not math.isfinite(graded_y) or not math.isfinite(float(np.float32(graded_y))):
                    raise RoadSurfaceError("grading produced a non-finite visual height")
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
    shoulder_expansion_regions: list[dict[str, Any]] = []
    if expanded_shoulder_intervals is None:
        candidate_regions = _connected_fallback_regions(
            baseline, candidate_before_harm_fallback, spacing_m, config, width_m, depth_m
        )
        expansion_points: dict[tuple[int, int], list[float]] = {}
        expansion_region_records: dict[tuple[int, int], list[dict[str, Any]]] = {}
        for region in candidate_regions:
            component = region["corePoints"]
            local_by_group: dict[tuple[int, int], list[float]] = {}
            for row, column in component:
                segment_index = int(nearest_segment_grid[row, column])
                station = float(nearest_station_grid[row, column])
                if segment_index < 0 or station < 0:
                    continue
                group = (segments[segment_index].way_id, segments[segment_index].sort_key[1])
                local_by_group.setdefault(group, []).append(station)
            for group, stations in local_by_group.items():
                expansion_points.setdefault(group, []).extend(stations)
                expansion_region_records.setdefault(group, []).append(
                    {
                        "coreLocalBoundsXZ": region["coreLocalBoundsXZ"],
                        "maximumCandidateAbsoluteChangeM": region[
                            "maximumCandidateAbsoluteChangeM"
                        ],
                        "maximumCandidateAddedGradientMPerM": region[
                            "maximumCandidateAddedGradientMPerM"
                        ],
                        "harmTriggers": region["harmTriggers"],
                    }
                )
        if expansion_points:
            generated_intervals = {
                group: [(min(stations), max(stations))]
                for group, stations in expansion_points.items()
            }
            intervals = {
                group: list(values) for group, values in configured_shoulder_intervals.items()
            }
            for group, values in generated_intervals.items():
                intervals.setdefault(group, []).extend(
                    value for value in values if value not in intervals.get(group, [])
                )
            final_grid, final_report = _grade_grid(
                baseline,
                segments,
                spacing_m,
                width_m,
                depth_m,
                config,
                intervals,
                inputs,
            )
            for group, (start_station, end_station) in sorted(
                (group, values[0]) for group, values in generated_intervals.items()
            ):
                shoulder_expansion_regions.append(
                    {
                        "wayId": group[0],
                        "partIndex": group[1],
                        "stationStartM": float(start_station),
                        "stationEndM": float(end_station),
                        "transitionMaximumM": 32.0,
                        "fadeBeyondStationIntervalM": config.fallback_fade_distance_m,
                        "reason": "connected candidate cut/fill or added-gradient safety trigger",
                        "candidateRegions": expansion_region_records[group],
                    }
                )
            final_report["shoulderExpansionRegions"] = shoulder_expansion_regions
            final_report["shoulderExpansionCount"] = len(shoulder_expansion_regions)
            return final_grid, final_report
    output, harm_fallback = _apply_station_harm_fallback(
        baseline,
        output,
        segments,
        spacing_m,
        width_m,
        depth_m,
        config,
        nearest_way_grid,
        nearest_segment_grid,
        nearest_station_grid,
        nearest_distance_grid,
        core_conflict_seeds,
        triangle_owner_segments,
        triangle_owner_is_core,
        enforce_gradient_limit=inputs is None,
    )
    surface_projection_report = None
    if inputs is not None:
        output, surface_projection_report = _project_final_surface(
            inputs,
            baseline,
            output,
            spacing_m,
            config,
            harm_fallback,
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
        "finalSurfaceProjection": surface_projection_report,
        "shoulderExpansionRegions": shoulder_expansion_regions,
        "shoulderExpansionCount": len(shoulder_expansion_regions),
        "triangleCoreOwnership": {
            "supportRule": (
                "all three vertices of every fixed-diagonal terrain triangle intersected by "
                "a configured-width road ribbon are assigned the deterministic full carriageway "
                "target; shoulders begin beyond the triangle support stencil"
            ),
            "supportedVertexCount": int(np.count_nonzero(triangle_owner_segments >= 0)),
            "coreVertexCount": int(
                np.count_nonzero((triangle_owner_segments >= 0) & triangle_owner_is_core)
            ),
            "supportShoulderVertexCount": 0,
            "incompatibleCoreVertexCount": int(np.count_nonzero(triangle_owner_segments == -2)),
            "incompatibleCoreSeeds": core_conflict_seeds,
            "coreRoadOwnsOverlappingShoulders": True,
        },
    }
    if config.treatment_variant == TEIGNMOUTH_CANDIDATE_VARIANT:
        report["teignmouthCandidateShoulder"] = {
            "wayId": TEIGNMOUTH_WAY_ID,
            "partIndex": TEIGNMOUTH_PART_INDEX,
            "stationStartM": TEIGNMOUTH_STATION_START_M,
            "stationEndM": TEIGNMOUTH_STATION_END_M,
            "baseTransitionBeyondConfiguredHalfWidthM": max(6.0, 2 * spacing_m),
            "maximumTransitionBeyondConfiguredHalfWidthM": 32.0,
            "alongRoadFadeBeyondStationWindowM": config.fallback_fade_distance_m,
            "blend": (
                "existing cubic smoothstep from base to 32 m over the configured along-road fade"
            ),
            "reason": (
                "local shared-surface shoulder support for registered "
                "Teignmouth full-width controls"
            ),
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


def _risk_building_footing_metrics(
    inputs: ReleaseInputs, preview: np.ndarray, building_report: dict[str, Any]
) -> dict[str, Any]:
    """Register baseline/preview footing sections for Newton, Sanford and Cavern buildings."""
    groups = {
        "Newton Road": (
            "osm:way:196536218",
            "osm:way:196536220",
            "osm:way:196536221",
            "osm:way:196536227",
            "osm:way:196536217",
        ),
        "Sanford Road": ("osm:way:194444458",),
        "Cavern Road": (
            "osm:way:207341667",
            "osm:way:207341692",
            "osm:way:207341702",
            "osm:way:207341535",
            "osm:way:207341753",
        ),
    }
    features = {str(feature["id"]): feature for feature in inputs.buildings.get("buildings", [])}
    base_changes = {
        item["id"]: float(item["previewMinusBaselineM"])
        for item in building_report["individualChangesM"]
    }
    output = {}
    for context, building_ids in groups.items():
        records = []
        for building_id in building_ids:
            feature = features.get(building_id)
            if feature is None:
                raise RoadSurfaceError(
                    f"registered {context} footing building '{building_id}' is missing"
                )
            polygons = [
                Polygon(record["exteriorXZ"], record.get("interiorRingsXZ", []))
                for record in feature["geometry"]["polygons"]
            ]
            min_x = min(polygon.bounds[0] for polygon in polygons)
            min_z = min(polygon.bounds[1] for polygon in polygons)
            max_x = max(polygon.bounds[2] for polygon in polygons)
            max_z = max(polygon.bounds[3] for polygon in polygons)
            section_z = (min_z + max_z) / 2
            samples = []
            x_values = np.arange(math.ceil(min_x), math.floor(max_x) + 1, 1.0)
            for x_value in x_values:
                x = float(x_value)
                point = Point(x, section_z)
                if not any(polygon.covers(point) for polygon in polygons):
                    continue
                baseline_value = _sample_grid(inputs.baseline, x, section_z, inputs.spacing_m)
                preview_value = _sample_grid(preview, x, section_z, inputs.spacing_m)
                samples.append(
                    {
                        "localXZ": [x, section_z],
                        "baselineLocalM": baseline_value,
                        "previewLocalM": preview_value,
                        "previewMinusBaselineM": preview_value - baseline_value,
                    }
                )
            records.append(
                {
                    "buildingId": building_id,
                    "wholeBasePreviewMinusBaselineM": base_changes[building_id],
                    "sectionAxis": "local X through footprint-bounds midpoint Z",
                    "sectionSampleSpacingM": 1.0,
                    "sectionSampleCount": len(samples),
                    "maximumAbsoluteSectionChangeM": max(
                        (abs(item["previewMinusBaselineM"]) for item in samples), default=0.0
                    ),
                    "samples": samples,
                }
            )
        output[context] = records
    return {
        "verticalDatum": "package-local display-grid metres relative to original terrain origin",
        "sampling": "1 m local-X samples through each registered footprint bounds midpoint Z",
        "regions": output,
    }


def _active_triangle_vertex_indices(
    heights: np.ndarray, x: float, z: float, spacing_m: float
) -> tuple[int, int, int]:
    """Return the exact three grid vertices used by the renderer at one X/Z sample."""
    rows, columns = heights.shape
    width, depth = (columns - 1) * spacing_m, (rows - 1) * spacing_m
    if not (-width / 2 <= x <= width / 2 and -depth / 2 <= z <= depth / 2):
        raise RoadSurfaceError(f"surface control ({x}, {z}) lies outside the display grid")
    gx, gz = (x + width / 2) / spacing_m, (z + depth / 2) / spacing_m
    column, row = min(math.floor(gx), columns - 2), min(math.floor(gz), rows - 2)
    u, v = gx - column, gz - row
    lower_left = row * columns + column
    lower_right = lower_left + 1
    upper_left = lower_left + columns
    upper_right = upper_left + 1
    if u + v <= 1:
        return lower_left, lower_right, upper_left
    return upper_right, upper_left, lower_right


def _active_triangle_vertex_weights(
    heights: np.ndarray, x: float, z: float, spacing_m: float
) -> tuple[tuple[int, float], ...]:
    """Return exact renderer triangle barycentric weights for one local X/Z sample."""
    rows, columns = heights.shape
    width, depth = (columns - 1) * spacing_m, (rows - 1) * spacing_m
    if not (-width / 2 <= x <= width / 2 and -depth / 2 <= z <= depth / 2):
        raise RoadSurfaceError(f"surface constraint ({x}, {z}) lies outside the display grid")
    gx, gz = (x + width / 2) / spacing_m, (z + depth / 2) / spacing_m
    column, row = min(math.floor(gx), columns - 2), min(math.floor(gz), rows - 2)
    u, v = gx - column, gz - row
    lower_left = row * columns + column
    lower_right = lower_left + 1
    upper_left = lower_left + columns
    upper_right = upper_left + 1
    if u + v <= 1:
        raw = (
            (lower_left, 1.0 - u - v),
            (lower_right, u),
            (upper_left, v),
        )
    else:
        raw = (
            (upper_right, u + v - 1.0),
            (upper_left, 1.0 - u),
            (lower_right, 1.0 - v),
        )
    return tuple((index, weight) for index, weight in raw if weight > 1e-15)


def _severe_station_crossfall_constraints(
    inputs: ReleaseInputs,
    baseline: np.ndarray,
    spacing_m: float,
    harm_fallback: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build sparse linear bounds for every sampled severe mandatory station."""
    features = {
        int(feature.get("source", {}).get("osmId", -1)): feature
        for feature in inputs.road_payload.get("features", [])
        if isinstance(feature, dict)
    }
    fallback_stations: dict[tuple[int, int], list[float]] = {}
    for region in harm_fallback.get("regions", []):
        for interval in region.get("stationIntervals", []):
            group = (int(interval["wayId"]), int(interval["partIndex"]))
            start, end = float(interval["startM"]), float(interval["endM"])
            fade = float(interval.get("fadeDistanceAtEachEndM", 0.0))
            fallback_stations.setdefault(group, []).extend((start - fade, start, end, end + fade))

    constraints: list[dict[str, Any]] = []
    station_counts: dict[str, int] = {}
    baseline_worst_stations = []
    for way_id in SEVERE_CORRIDOR_WAY_IDS:
        feature = features.get(way_id)
        if feature is None:
            raise RoadSurfaceError(f"mandatory severe-corridor way {way_id} is missing")
        width_m = float(feature["estimatedWidthM"])
        part_counts = []
        for part_index, raw_part in enumerate(feature.get("centerlinePartsXZ", [])):
            part = [[float(point[0]), float(point[1])] for point in raw_part]
            cumulative = [0.0]
            for first, second in zip(part, part[1:], strict=False):
                cumulative.append(cumulative[-1] + math.dist(first, second))
            length_m = cumulative[-1]
            if length_m <= 0:
                continue
            sample_count = max(1, math.ceil(length_m / 1.0))
            stations = {index * length_m / sample_count for index in range(sample_count + 1)}
            stations.update(cumulative)
            if way_id == 30480989 and part_index == 0:
                stations.update(
                    station_m for station_m in (396.0108, 409.2610) if station_m <= length_m
                )
            for station_m in fallback_stations.get((way_id, part_index), []):
                if 0.0 <= station_m <= length_m:
                    stations.add(station_m)
            station_baseline: list[tuple[float, float]] = []
            for station_m in sorted(stations):
                (center_x, center_z), tangent = _line_point_tangent(part, station_m)
                normal_x, normal_z = -tangent[1], tangent[0]
                left_x = center_x - normal_x * width_m / 2
                left_z = center_z - normal_z * width_m / 2
                right_x = center_x + normal_x * width_m / 2
                right_z = center_z + normal_z * width_m / 2
                base_left = _sample_grid(baseline, left_x, left_z, spacing_m)
                base_right = _sample_grid(baseline, right_x, right_z, spacing_m)
                baseline_crossfall = abs(base_right - base_left) / width_m * 100.0
                station_baseline.append((station_m, baseline_crossfall))
                if baseline_crossfall < 10.0:
                    continue

                coefficients: dict[int, float] = {}
                for vertex, weight in _active_triangle_vertex_weights(
                    baseline, right_x, right_z, spacing_m
                ):
                    coefficients[vertex] = coefficients.get(vertex, 0.0) + weight
                for vertex, weight in _active_triangle_vertex_weights(
                    baseline, left_x, left_z, spacing_m
                ):
                    coefficients[vertex] = coefficients.get(vertex, 0.0) - weight
                sparse_indices = np.asarray(sorted(coefficients), dtype=np.int64)
                sparse_values = np.asarray(
                    [coefficients[index] for index in sparse_indices], dtype=np.float64
                )
                keep = np.abs(sparse_values) > 1e-15
                sparse_indices, sparse_values = sparse_indices[keep], sparse_values[keep]
                exact_limit_m = 0.5 * abs(base_right - base_left)
                limit_m = exact_limit_m - SEVERE_CROSSFALL_NUMERICAL_MARGIN_M
                label = {
                    "wayId": way_id,
                    "partIndex": part_index,
                    "stationM": float(station_m),
                    "baselineCrossfallPercent": float(baseline_crossfall),
                    "maximumPreviewCrossfallPercent": float(baseline_crossfall * 0.5),
                    "solverHeadroomM": SEVERE_CROSSFALL_NUMERICAL_MARGIN_M,
                }
                constraints.append(
                    {
                        "indices": sparse_indices,
                        "coefficients": sparse_values,
                        "limitM": limit_m,
                        "label": {**label, "direction": "right-minus-left"},
                    }
                )
                constraints.append(
                    {
                        "indices": sparse_indices,
                        "coefficients": -sparse_values,
                        "limitM": limit_m,
                        "label": {**label, "direction": "left-minus-right"},
                    }
                )
            if station_baseline:
                station_m, crossfall = max(station_baseline, key=lambda item: item[1])
                baseline_worst_stations.append(
                    {
                        "wayId": way_id,
                        "partIndex": part_index,
                        "stationM": station_m,
                        "baselineCrossfallPercent": crossfall,
                        "includedInSampledStationSet": True,
                    }
                )
                part_counts.append(
                    sum(crossfall >= 10.0 for _station, crossfall in station_baseline)
                )
        station_counts[str(way_id)] = sum(part_counts)
    return constraints, {
        "baselineSevereThresholdPercent": 10.0,
        "requiredMaximumBaselineFraction": 0.5,
        "strictNumericalHeadroomM": SEVERE_CROSSFALL_NUMERICAL_MARGIN_M,
        "maximumStationSpacingM": 1.0,
        "endpointInterpolation": "renderer fixed-diagonal triangle barycentric weights",
        "stationCountsByWay": station_counts,
        "baselineWorstStations": baseline_worst_stations,
        "inequalityCount": len(constraints),
    }


def _teignmouth_registered_stations(
    inputs: ReleaseInputs,
) -> tuple[dict[str, Any], list[list[float]], float, list[float]]:
    """Return the registered Teignmouth station set, including every source vertex."""
    matches = [
        feature
        for feature in inputs.road_payload.get("features", [])
        if isinstance(feature, dict) and feature.get("source", {}).get("osmId") == TEIGNMOUTH_WAY_ID
    ]
    if len(matches) != 1:
        raise RoadSurfaceError(
            f"Teignmouth candidate requires exactly one source way {TEIGNMOUTH_WAY_ID}"
        )
    feature = matches[0]
    raw_parts = feature.get("centerlinePartsXZ", [])
    if len(raw_parts) <= TEIGNMOUTH_PART_INDEX:
        raise RoadSurfaceError("Teignmouth candidate source part 0 is missing")
    part = [[float(point[0]), float(point[1])] for point in raw_parts[TEIGNMOUTH_PART_INDEX]]
    width_m = float(feature.get("estimatedWidthM", 0.0))
    if not math.isclose(width_m, 6.0, rel_tol=0.0, abs_tol=1e-9):
        raise RoadSurfaceError(
            f"Teignmouth candidate expected the unchanged configured 6 m width; found {width_m:g} m"
        )
    cumulative = [0.0]
    for first, second in zip(part, part[1:], strict=False):
        cumulative.append(cumulative[-1] + math.dist(first, second))
    if cumulative[-1] < TEIGNMOUTH_STATION_END_M:
        raise RoadSurfaceError("Teignmouth candidate station interval is outside source part 0")
    # The regular <=1 m lattice bounds all gaps; add exact source vertices and the
    # registered user-view worst section without dropping either class of sample.
    count = math.ceil(TEIGNMOUTH_STATION_END_M - TEIGNMOUTH_STATION_START_M)
    stations = {
        TEIGNMOUTH_STATION_START_M
        + (TEIGNMOUTH_STATION_END_M - TEIGNMOUTH_STATION_START_M) * index / count
        for index in range(count + 1)
    }
    stations.update(
        station
        for station in cumulative
        if TEIGNMOUTH_STATION_START_M <= station <= TEIGNMOUTH_STATION_END_M
    )
    stations.add(148.15104603556912)
    ordered = sorted(stations)
    if ordered[0] != TEIGNMOUTH_STATION_START_M or ordered[-1] != TEIGNMOUTH_STATION_END_M:
        raise RoadSurfaceError("Teignmouth candidate station coverage omitted a window endpoint")
    if max(np.diff(ordered), default=0.0) > 1.0 + 1e-9:
        raise RoadSurfaceError("Teignmouth candidate station spacing exceeds 1 m")
    return feature, part, width_m, ordered


def _teignmouth_section_samples(
    inputs: ReleaseInputs,
    baseline: np.ndarray,
    spacing_m: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build renderer-triangle samples and ≤5%/≤0.30 m local halfspaces."""
    _feature, part, width_m, stations = _teignmouth_registered_stations(inputs)
    lateral_step_m = 0.25
    lateral_count_float = width_m / lateral_step_m
    lateral_count = round(lateral_count_float)
    if not math.isclose(lateral_count_float, lateral_count, rel_tol=0.0, abs_tol=1e-9):
        raise RoadSurfaceError("configured Teignmouth width is not divisible by 0.25 m")

    constraints: list[dict[str, Any]] = []
    constraint_signatures: set[tuple[Any, ...]] = set()
    sample_records = []
    slope_limit_m = (
        TEIGNMOUTH_CROSSFALL_LIMIT_PERCENT / 100.0 * lateral_step_m - TEIGNMOUTH_SOLVER_HEADROOM_M
    )

    def add_constraint(
        coefficients: dict[int, float],
        limit_m: float,
        label: dict[str, Any],
    ) -> None:
        indices = np.asarray(sorted(coefficients), dtype=np.int64)
        values = np.asarray([coefficients[index] for index in indices], dtype=np.float64)
        keep = np.abs(values) > 1e-15
        indices, values = indices[keep], values[keep]
        if indices.size == 0:
            raise RoadSurfaceError(
                "Teignmouth cross-section constraint has no active grid vertices"
            )
        signature = (
            round(limit_m, 12),
            tuple(
                (int(index), round(float(value), 12))
                for index, value in zip(indices, values, strict=True)
            ),
        )
        if signature in constraint_signatures:
            return
        constraint_signatures.add(signature)
        constraints.append(
            {"indices": indices, "coefficients": values, "limitM": limit_m, "label": label}
        )

    for station_m in stations:
        (center_x, center_z), tangent = _line_point_tangent(part, station_m)
        normal_x, normal_z = -tangent[1], tangent[0]
        lateral_samples: list[dict[int, float]] = []
        baseline_heights = []
        for lateral_index in range(lateral_count + 1):
            offset_m = -width_m / 2 + lateral_index * lateral_step_m
            x = center_x + normal_x * offset_m
            z = center_z + normal_z * offset_m
            weights = dict(_active_triangle_vertex_weights(baseline, x, z, spacing_m))
            lateral_samples.append(weights)
            baseline_heights.append(
                sum(float(baseline.ravel()[vertex]) * weight for vertex, weight in weights.items())
            )
        baseline_slopes = [
            abs(second - first) / lateral_step_m * 100.0
            for first, second in zip(baseline_heights, baseline_heights[1:], strict=False)
        ]
        section = {
            "stationM": float(station_m),
            "baselineMaximumAbsoluteLateralSlopePercent": max(baseline_slopes, default=0.0),
            "baselineEndpointSpanM": abs(baseline_heights[-1] - baseline_heights[0]),
        }
        sample_records.append(section)
        for lateral_index, (first, second) in enumerate(
            zip(lateral_samples, lateral_samples[1:], strict=False)
        ):
            difference = dict(second)
            for vertex, weight in first.items():
                difference[vertex] = difference.get(vertex, 0.0) - weight
            label = {
                "kind": "teignmouth-local-lateral-slope",
                "wayId": TEIGNMOUTH_WAY_ID,
                "partIndex": TEIGNMOUTH_PART_INDEX,
                "stationM": float(station_m),
                "lateralOffsetStartM": float(-width_m / 2 + lateral_index * lateral_step_m),
                "sampleSpacingM": lateral_step_m,
                "limitPercent": TEIGNMOUTH_CROSSFALL_LIMIT_PERCENT,
            }
            add_constraint(difference, slope_limit_m, {**label, "direction": "increasing-offset"})
            add_constraint(
                {vertex: -weight for vertex, weight in difference.items()},
                slope_limit_m,
                {**label, "direction": "decreasing-offset"},
            )
    return constraints, {
        "wayId": TEIGNMOUTH_WAY_ID,
        "partIndex": TEIGNMOUTH_PART_INDEX,
        "stationStartM": TEIGNMOUTH_STATION_START_M,
        "stationEndM": TEIGNMOUTH_STATION_END_M,
        "configuredWidthM": width_m,
        "maximumStationSpacingM": max(np.diff(stations), default=0.0),
        "stationCount": len(stations),
        "sampleSpacingAcrossWidthM": lateral_step_m,
        "samplesPerSection": lateral_count + 1,
        "maximumAbsoluteLateralSlopePercent": TEIGNMOUTH_CROSSFALL_LIMIT_PERCENT,
        "maximumEndpointSpanM": TEIGNMOUTH_WIDTH_SPAN_LIMIT_M,
        "endpointSpanGateImpliedBySlopeHalfspaces": True,
        "derivedMaximumEndpointSpanM": lateral_count * slope_limit_m,
        "solverHeadroomM": TEIGNMOUTH_SOLVER_HEADROOM_M,
        "constraintCount": len(constraints),
        "constraintDeduplication": "identical sparse halfspaces collapsed per registered section",
        "baselineSections": sample_records,
        "interpolation": "renderer fixed-diagonal triangle barycentric weights",
    }


def _teignmouth_section_metrics(
    inputs: ReleaseInputs,
    baseline: np.ndarray,
    preview: np.ndarray,
    spacing_m: float,
) -> dict[str, Any]:
    """Measure candidate crossfall on the exact registered 1 m × 0.25 m lattice."""
    _feature, part, width_m, stations = _teignmouth_registered_stations(inputs)
    lateral_step_m = 0.25
    lateral_count = round(width_m / lateral_step_m)
    sections = []
    for station_m in stations:
        (center_x, center_z), tangent = _line_point_tangent(part, station_m)
        normal_x, normal_z = -tangent[1], tangent[0]
        values = {"baseline": [], "preview": []}
        for index in range(lateral_count + 1):
            offset = -width_m / 2 + index * lateral_step_m
            x = center_x + normal_x * offset
            z = center_z + normal_z * offset
            values["baseline"].append(_sample_grid(baseline, x, z, spacing_m))
            values["preview"].append(_sample_grid(preview, x, z, spacing_m))
        baseline_slopes = [
            abs(second - first) / lateral_step_m * 100.0
            for first, second in zip(values["baseline"], values["baseline"][1:], strict=False)
        ]
        preview_slopes = [
            abs(second - first) / lateral_step_m * 100.0
            for first, second in zip(values["preview"], values["preview"][1:], strict=False)
        ]
        sections.append(
            {
                "stationM": float(station_m),
                "baselineMaximumAbsoluteLateralSlopePercent": max(baseline_slopes, default=0.0),
                "previewMaximumAbsoluteLateralSlopePercent": max(preview_slopes, default=0.0),
                "baselineEndpointSpanM": abs(values["baseline"][-1] - values["baseline"][0]),
                "previewEndpointSpanM": abs(values["preview"][-1] - values["preview"][0]),
                "centerlineDeviationM": abs(
                    _sample_grid(preview, center_x, center_z, spacing_m)
                    - _sample_grid(baseline, center_x, center_z, spacing_m)
                ),
            }
        )
    max_slope = max(item["previewMaximumAbsoluteLateralSlopePercent"] for item in sections)
    max_span = max(item["previewEndpointSpanM"] for item in sections)
    max_centerline = max(item["centerlineDeviationM"] for item in sections)
    return {
        "wayId": TEIGNMOUTH_WAY_ID,
        "partIndex": TEIGNMOUTH_PART_INDEX,
        "stationStartM": TEIGNMOUTH_STATION_START_M,
        "stationEndM": TEIGNMOUTH_STATION_END_M,
        "configuredWidthM": width_m,
        "maximumStationSpacingM": max(np.diff(stations), default=0.0),
        "sampleSpacingAcrossWidthM": lateral_step_m,
        "samplesPerSection": lateral_count + 1,
        "maximumAbsoluteLateralSlopePercentLimit": TEIGNMOUTH_CROSSFALL_LIMIT_PERCENT,
        "maximumObservedAbsoluteLateralSlopePercent": max_slope,
        "maximumEndpointSpanM": TEIGNMOUTH_WIDTH_SPAN_LIMIT_M,
        "maximumObservedEndpointSpanM": max_span,
        "centerlineDeviationLimitM": 0.10,
        "maximumCenterlineDeviationM": max_centerline,
        "allStationsPass": bool(
            max_slope <= TEIGNMOUTH_CROSSFALL_LIMIT_PERCENT + 1e-6
            and max_span <= TEIGNMOUTH_WIDTH_SPAN_LIMIT_M + 1e-6
            and max_centerline <= 0.10 + 1e-6
        ),
        "sections": sections,
        "interpolation": "renderer fixed-diagonal triangle barycentric sampling",
    }


def _surface_control_vertices(
    inputs: ReleaseInputs, candidate: np.ndarray
) -> tuple[np.ndarray, list[tuple[float, float]], dict[str, Any]]:
    """Collect 1 m centerline stations and pin registered Parkfield cross-sections."""
    rows, columns = candidate.shape
    mask = np.zeros((rows, columns), dtype=bool)
    centerline_sample_count = 0
    centerline_positions: list[tuple[float, float]] = []
    for feature in inputs.road_payload["features"]:
        if (
            feature.get("displayGroup") != "vehicular"
            or feature.get("groundAssumption")
            != "ground_assumed_from_absent_or_explicit_no_vertical_tags"
        ):
            continue
        for raw_part in feature.get("centerlinePartsXZ", []):
            part = [[float(point[0]), float(point[1])] for point in raw_part]
            total_length = sum(
                math.dist(first, second) for first, second in zip(part, part[1:], strict=False)
            )
            if total_length <= 0:
                continue
            count = max(1, math.ceil(total_length / 1.0))
            for index in range(count + 1):
                position, _tangent = _line_point_tangent(part, total_length * index / count)
                centerline_positions.append(position)
                centerline_sample_count += 1

    parkfield = next(
        (
            feature
            for feature in inputs.road_payload["features"]
            if feature.get("source", {}).get("osmId") == 30480989
        ),
        None,
    )
    if parkfield is None or not parkfield.get("centerlinePartsXZ"):
        raise RoadSurfaceError("registered Parkfield full-width controls have no source centerline")
    parkfield_part = [
        [float(point[0]), float(point[1])] for point in parkfield["centerlinePartsXZ"][0]
    ]
    width_m = float(parkfield["estimatedWidthM"])
    cross_sample_count = math.ceil(width_m / 0.25)
    if not math.isclose(width_m / cross_sample_count, 0.25, abs_tol=1e-9):
        raise RoadSurfaceError("Parkfield configured width cannot be divided into 0.25 m controls")
    control_records = []
    for station_m in (396.0108, 409.2610):
        (center_x, center_z), tangent = _line_point_tangent(parkfield_part, station_m)
        normal_x, normal_z = -tangent[1], tangent[0]
        for index in range(cross_sample_count + 1):
            offset = -width_m / 2 + width_m * index / cross_sample_count
            position = (center_x + normal_x * offset, center_z + normal_z * offset)
            for vertex in _active_triangle_vertex_indices(candidate, *position, inputs.spacing_m):
                mask.flat[vertex] = True
        control_records.append(
            {
                "wayId": 30480989,
                "partIndex": 0,
                "stationM": station_m,
                "configuredWidthM": width_m,
                "crossfallSpacingM": width_m / cross_sample_count,
                "crossfallSampleCount": cross_sample_count + 1,
                "pinnedToCandidate": True,
            }
        )
    report = {
        "centerlineStationSpacingMaximumM": 1.0,
        "centerlineSampleCount": centerline_sample_count,
        "parkfieldControls": control_records,
        "registeredControlVertexCount": int(mask.sum()),
    }
    return mask, centerline_positions, report


def _centerline_retention_vertices(
    positions: list[tuple[float, float]],
    baseline: np.ndarray,
    preview: np.ndarray,
    spacing_m: float,
    maximum_deviation_m: float = 0.10,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Pin source-grid stencils only where projection exceeds the signed centerline limit."""
    rows, columns = baseline.shape
    mask = np.zeros((rows, columns), dtype=bool)
    if not positions:
        return mask, {
            "sampleCount": 0,
            "maximumAbsoluteDeviationM": 0.0,
            "violatingSampleCount": 0,
        }
    x = np.fromiter((point[0] for point in positions), dtype=np.float64, count=len(positions))
    z = np.fromiter((point[1] for point in positions), dtype=np.float64, count=len(positions))
    baseline_values = _sample_grid_many(baseline, x, z, spacing_m)
    preview_values = _sample_grid_many(preview, x, z, spacing_m)
    deviations = preview_values - baseline_values
    violating = np.flatnonzero(np.abs(deviations) > maximum_deviation_m)
    for index in violating:
        for vertex in _active_triangle_vertex_indices(baseline, *positions[int(index)], spacing_m):
            mask.flat[vertex] = True
    return mask, {
        "sampleCount": len(positions),
        "maximumAbsoluteDeviationM": float(np.max(np.abs(deviations))),
        "violatingSampleCount": int(violating.size),
        "maximumAllowedAbsoluteDeviationM": maximum_deviation_m,
        "newSourceGroundStencilVertexCount": int(mask.sum()),
    }


def _strict_corridor_metrics(
    inputs: ReleaseInputs,
    preview: np.ndarray,
    harm_fallback: dict[str, Any],
) -> dict[str, Any]:
    """Measure the complete required corridors after surface/building gates pass."""
    corridor_way_ids = (30480989, 78455388, 78455395)
    longitudinal_way_ids = tuple(sorted(set(corridor_way_ids) | set(PROFILE_WAY_IDS)))
    features = {
        int(feature.get("source", {}).get("osmId", -1)): feature
        for feature in inputs.road_payload["features"]
        if isinstance(feature, dict)
    }
    fallback_stations: dict[tuple[int, int], list[float]] = {}
    for region in harm_fallback.get("regions", []):
        for interval in region.get("stationIntervals", []):
            group = (int(interval["wayId"]), int(interval["partIndex"]))
            start, end = float(interval["startM"]), float(interval["endM"])
            fade = float(interval.get("fadeDistanceAtEachEndM", 0.0))
            fallback_stations.setdefault(group, []).extend((start - fade, start, end, end + fade))

    corridor_summaries = []
    severe_failures = []
    corridor_failures = []
    missing_corridor_ways = []
    for way_id in corridor_way_ids:
        feature = features.get(way_id)
        if feature is None:
            missing_corridor_ways.append(way_id)
            continue
        width_m = float(feature["estimatedWidthM"])
        lateral_count = max(1, math.ceil(width_m / 0.25))
        lateral_spacing = width_m / lateral_count
        if lateral_spacing > 0.25 + 1e-9:
            raise RoadSurfaceError(
                f"mandatory corridor way {way_id} width cannot be sampled at 0.25 m"
            )
        offsets = np.linspace(-width_m / 2, width_m / 2, lateral_count + 1, dtype=np.float64)
        parts_summary = []
        corridor_base_values: list[float] = []
        corridor_preview_values: list[float] = []
        for part_index, raw_part in enumerate(feature["centerlinePartsXZ"]):
            part = [[float(point[0]), float(point[1])] for point in raw_part]
            cumulative = [0.0]
            for first, second in zip(part, part[1:], strict=False):
                cumulative.append(cumulative[-1] + math.dist(first, second))
            length_m = cumulative[-1]
            if length_m <= 0:
                continue
            interval_count = max(1, math.ceil(length_m / 1.0))
            stations = {index * length_m / interval_count for index in range(interval_count + 1)}
            stations.update(cumulative)
            if way_id == 30480989 and part_index == 0:
                stations.update((396.0108, 409.2610))
            for station in fallback_stations.get((way_id, part_index), []):
                if 0.0 <= station <= length_m:
                    stations.add(station)
            ordered_stations = sorted(stations)
            station_records = []
            for station_m in ordered_stations:
                (center_x, center_z), tangent = _line_point_tangent(part, station_m)
                normal_x, normal_z = -tangent[1], tangent[0]
                sample_x = center_x + normal_x * offsets
                sample_z = center_z + normal_z * offsets
                baseline_values = _sample_grid_many(
                    inputs.baseline, sample_x, sample_z, inputs.spacing_m
                )
                preview_values = _sample_grid_many(preview, sample_x, sample_z, inputs.spacing_m)
                baseline_crossfall = abs(baseline_values[-1] - baseline_values[0]) / width_m * 100
                preview_crossfall = abs(preview_values[-1] - preview_values[0]) / width_m * 100
                changed_count = int(
                    np.count_nonzero(np.abs(preview_values - baseline_values) > 0.01)
                )
                classification = (
                    "untreated"
                    if changed_count == 0
                    else "treated"
                    if changed_count == offsets.size
                    else "transition"
                )
                record = {
                    "stationM": float(station_m),
                    "baselineCrossfallPercent": float(baseline_crossfall),
                    "previewCrossfallPercent": float(preview_crossfall),
                    "baselineFullWidthSpanM": float(np.ptp(baseline_values)),
                    "previewFullWidthSpanM": float(np.ptp(preview_values)),
                    "baselineMaximumLocalLateralSlopeMPerM": float(
                        np.max(np.abs(np.diff(baseline_values))) / (width_m / lateral_count)
                    ),
                    "previewMaximumLocalLateralSlopeMPerM": float(
                        np.max(np.abs(np.diff(preview_values))) / (width_m / lateral_count)
                    ),
                    "centerlineDeviationM": float(
                        _sample_grid(preview, center_x, center_z, inputs.spacing_m)
                        - _sample_grid(inputs.baseline, center_x, center_z, inputs.spacing_m)
                    ),
                    "surfaceClass": classification,
                }
                station_records.append(record)
                corridor_base_values.append(float(baseline_crossfall))
                corridor_preview_values.append(float(preview_crossfall))
                if (
                    baseline_crossfall >= 10.0
                    and preview_crossfall > baseline_crossfall * 0.5 + 1e-8
                ):
                    severe_failures.append({"wayId": way_id, "partIndex": part_index, **record})
            # Voronoi lengths assign the exact full part length across the sample classes.
            boundaries = [0.0]
            boundaries.extend(
                (first + second) / 2
                for first, second in zip(ordered_stations, ordered_stations[1:], strict=False)
            )
            boundaries.append(length_m)
            class_lengths = {"treated": 0.0, "transition": 0.0, "untreated": 0.0}
            for index, record in enumerate(station_records):
                class_lengths[record["surfaceClass"]] += max(
                    0.0, boundaries[index + 1] - boundaries[index]
                )
            base_array = np.asarray([item["baselineCrossfallPercent"] for item in station_records])
            preview_array = np.asarray(
                [item["previewCrossfallPercent"] for item in station_records]
            )
            severe_station_count = int(np.count_nonzero(base_array >= 10.0))
            severe_station_pass_count = int(
                sum(
                    sample["baselineCrossfallPercent"] >= 10.0
                    and sample["previewCrossfallPercent"]
                    <= sample["baselineCrossfallPercent"] * 0.5 + 1e-8
                    for sample in station_records
                )
            )
            severe_station_failures = [
                sample
                for sample in station_records
                if sample["baselineCrossfallPercent"] >= 10.0
                and sample["previewCrossfallPercent"]
                > sample["baselineCrossfallPercent"] * 0.5 + 1e-8
            ]
            baseline_worst_station = max(
                station_records,
                key=lambda sample: sample["baselineCrossfallPercent"],
            )
            if baseline_worst_station["surfaceClass"] == "untreated":
                corridor_failures.append(
                    {
                        "wayId": way_id,
                        "partIndex": part_index,
                        "reason": "baseline-worst station is untreated",
                        "baselineWorstStation": baseline_worst_station,
                    }
                )
            parts_summary.append(
                {
                    "partIndex": part_index,
                    "lengthM": length_m,
                    "sampleCount": len(station_records),
                    "maximumStationSpacingM": max(np.diff(ordered_stations), default=0.0),
                    "severeBaselineStationCount": severe_station_count,
                    "severeStationsMeeting50PercentReduction": severe_station_pass_count,
                    "severeStationFailureCount": len(severe_station_failures),
                    "worstSevereStationFailures": sorted(
                        severe_station_failures,
                        key=lambda sample: (
                            sample["previewCrossfallPercent"] / sample["baselineCrossfallPercent"]
                        ),
                        reverse=True,
                    )[:5],
                    "baselineWorstStation": baseline_worst_station,
                    "treatmentLengthsM": class_lengths,
                    "crossfallPercent": {
                        "baseline": {
                            "maximum": float(np.max(base_array)),
                            "p90": float(np.percentile(base_array, 90)),
                            "p95": float(np.percentile(base_array, 95)),
                            "median": float(np.median(base_array)),
                        },
                        "preview": {
                            "maximum": float(np.max(preview_array)),
                            "p90": float(np.percentile(preview_array, 90)),
                            "p95": float(np.percentile(preview_array, 95)),
                            "median": float(np.median(preview_array)),
                        },
                    },
                    "fullWidthSpanM": {
                        "baselineMaximum": float(
                            max(sample["baselineFullWidthSpanM"] for sample in station_records)
                        ),
                        "previewMaximum": float(
                            max(sample["previewFullWidthSpanM"] for sample in station_records)
                        ),
                    },
                    "maximumLocalLateralSlopeMPerM": {
                        "baseline": float(
                            max(
                                sample["baselineMaximumLocalLateralSlopeMPerM"]
                                for sample in station_records
                            )
                        ),
                        "preview": float(
                            max(
                                sample["previewMaximumLocalLateralSlopeMPerM"]
                                for sample in station_records
                            )
                        ),
                    },
                }
            )
        way_base = np.asarray(corridor_base_values, dtype=np.float64)
        way_preview = np.asarray(corridor_preview_values, dtype=np.float64)
        summary = {
            "wayId": way_id,
            "name": feature.get("sourceTags", {}).get("name"),
            "configuredWidthM": width_m,
            "parts": parts_summary,
            "crossfallPercent": {
                "baseline": {
                    "maximum": float(np.max(way_base)),
                    "p90": float(np.percentile(way_base, 90)),
                    "p95": float(np.percentile(way_base, 95)),
                    "median": float(np.median(way_base)),
                },
                "preview": {
                    "maximum": float(np.max(way_preview)),
                    "p90": float(np.percentile(way_preview, 90)),
                    "p95": float(np.percentile(way_preview, 95)),
                    "median": float(np.median(way_preview)),
                },
            },
        }
        before, after = (
            summary["crossfallPercent"]["baseline"],
            summary["crossfallPercent"]["preview"],
        )
        if any(after[key] >= before[key] for key in ("maximum", "p95")):
            corridor_failures.append(
                {
                    "wayId": way_id,
                    "reason": "maximum and p95 crossfall must each decrease",
                    "baseline": before,
                    "preview": after,
                }
            )
        corridor_summaries.append(summary)

    parkfield_controls = []
    parkfield = features[30480989]
    parkfield_part = [
        [float(point[0]), float(point[1])] for point in parkfield["centerlinePartsXZ"][0]
    ]
    width_m = float(parkfield["estimatedWidthM"])
    offsets = np.linspace(-width_m / 2, width_m / 2, math.ceil(width_m / 0.25) + 1)
    for station_m in (396.0108, 409.2610):
        (center_x, center_z), tangent = _line_point_tangent(parkfield_part, station_m)
        normal_x, normal_z = -tangent[1], tangent[0]
        x, z = center_x + normal_x * offsets, center_z + normal_z * offsets
        baseline_values = _sample_grid_many(inputs.baseline, x, z, inputs.spacing_m)
        preview_values = _sample_grid_many(preview, x, z, inputs.spacing_m)
        center_base = _sample_grid(inputs.baseline, center_x, center_z, inputs.spacing_m)
        center_preview = _sample_grid(preview, center_x, center_z, inputs.spacing_m)
        metrics = {
            "stationM": station_m,
            "sampleSpacingM": 0.25,
            "sampleCount": int(offsets.size),
            "baselineCrossfallPercent": float(
                abs(baseline_values[-1] - baseline_values[0]) / width_m * 100
            ),
            "previewCrossfallPercent": float(
                abs(preview_values[-1] - preview_values[0]) / width_m * 100
            ),
            "baselineFullWidthSpanM": float(np.ptp(baseline_values)),
            "previewFullWidthSpanM": float(np.ptp(preview_values)),
            "centerlineDeviationM": float(center_preview - center_base),
        }
        metrics["passes"] = (
            metrics["previewCrossfallPercent"] <= 5.0
            and metrics["previewFullWidthSpanM"] <= 0.30
            and abs(metrics["centerlineDeviationM"]) <= 0.10
        )
        parkfield_controls.append(metrics)

    longitudinal_summaries = []
    longitudinal_failures = []
    for way_id in longitudinal_way_ids:
        feature = features.get(way_id)
        if feature is None:
            missing_corridor_ways.append(way_id)
            continue
        way_parts = []
        way_maximum_deviation = 0.0
        way_maximum_grade_delta = 0.0
        for part_index, raw_part in enumerate(feature["centerlinePartsXZ"]):
            part = [[float(point[0]), float(point[1])] for point in raw_part]
            cumulative = [0.0]
            for first, second in zip(part, part[1:], strict=False):
                cumulative.append(cumulative[-1] + math.dist(first, second))
            length_m = cumulative[-1]
            if length_m <= 0:
                continue
            count = max(1, math.ceil(length_m / 5.0))
            stations = sorted(
                set([index * length_m / count for index in range(count + 1)] + cumulative)
            )
            positions = [_line_point_tangent(part, station)[0] for station in stations]
            baseline_values = _sample_grid_many(
                inputs.baseline,
                np.asarray([point[0] for point in positions]),
                np.asarray([point[1] for point in positions]),
                inputs.spacing_m,
            )
            preview_values = _sample_grid_many(
                preview,
                np.asarray([point[0] for point in positions]),
                np.asarray([point[1] for point in positions]),
                inputs.spacing_m,
            )
            deviation = preview_values - baseline_values
            baseline_grade = np.diff(baseline_values) / np.diff(stations) * 100
            preview_grade = np.diff(preview_values) / np.diff(stations) * 100
            grade_delta = preview_grade - baseline_grade
            way_maximum_deviation = max(way_maximum_deviation, float(np.max(np.abs(deviation))))
            way_maximum_grade_delta = max(
                way_maximum_grade_delta,
                float(np.max(np.abs(grade_delta))) if grade_delta.size else 0.0,
            )
            way_parts.append(
                {
                    "partIndex": part_index,
                    "lengthM": length_m,
                    "sampleCount": len(stations),
                    "maximumStationSpacingM": float(max(np.diff(stations), default=0.0)),
                    "signedHeightChangeRangeM": [
                        float(np.min(deviation)),
                        float(np.max(deviation)),
                    ],
                    "maximumAbsoluteHeightChangeM": float(np.max(np.abs(deviation))),
                    "signedGradeChangeRangePercentagePoints": [
                        float(np.min(grade_delta)) if grade_delta.size else 0.0,
                        float(np.max(grade_delta)) if grade_delta.size else 0.0,
                    ],
                    "maximumAbsoluteGradeChangePercentagePoints": (
                        float(np.max(np.abs(grade_delta))) if grade_delta.size else 0.0
                    ),
                }
            )
        if way_maximum_deviation > 0.10 or way_maximum_grade_delta > 2.0:
            longitudinal_failures.append(
                {
                    "wayId": way_id,
                    "maximumAbsoluteHeightChangeM": way_maximum_deviation,
                    "maximumAbsoluteGradeChangePercentagePoints": way_maximum_grade_delta,
                }
            )
        longitudinal_summaries.append(
            {
                "wayId": way_id,
                "maximumAbsoluteHeightChangeM": way_maximum_deviation,
                "maximumAbsoluteGradeChangePercentagePoints": way_maximum_grade_delta,
                "parts": way_parts,
            }
        )
    severe_baseline_station_count = sum(
        part["severeBaselineStationCount"]
        for corridor in corridor_summaries
        for part in corridor["parts"]
    )
    severe_station_pass_count = sum(
        part["severeStationsMeeting50PercentReduction"]
        for corridor in corridor_summaries
        for part in corridor["parts"]
    )
    metrics = {
        "corridorSamplingMaximumStationSpacingM": 1.0,
        "crossfallStationingIncludes": [
            "uniform stations at <=1 m",
            "original source vertices",
            "registered Parkfield controls",
            "connected fallback interval and fade boundaries",
        ],
        "lateralSampleSpacingM": 0.25,
        "baselineSevereCrossfallThresholdPercent": 10.0,
        "minimumSevereStationReductionPercent": 50.0,
        "severeStationFailureCount": len(severe_failures),
        "severeBaselineStationCount": severe_baseline_station_count,
        "severeStationsMeeting50PercentReduction": severe_station_pass_count,
        "missingRequiredWayIds": sorted(set(missing_corridor_ways)),
        "corridorSummaryFailures": corridor_failures,
        "severeStationFailures": severe_failures,
        "corridorSummaries": corridor_summaries,
        "parkfieldControls": parkfield_controls,
        "longitudinalStationSpacingMaximumM": 5.0,
        "longitudinalHeightChangeLimitM": 0.10,
        "longitudinalGradeChangeLimitPercentagePoints": 2.0,
        "longitudinalFailures": longitudinal_failures,
        "longitudinalComparisons": longitudinal_summaries,
    }
    metrics["acceptance"] = {
        "allSevereStationsMeet50PercentReduction": not severe_failures,
        "allCorridorsReduceMaximumAndP95": not corridor_failures,
        "bothParkfieldControlsPass": len(parkfield_controls) == 2
        and all(item["passes"] for item in parkfield_controls),
        "signedLongitudinalLimitsPass": not longitudinal_failures,
        "allRequiredWaysPresent": not metrics["missingRequiredWayIds"],
    }
    metrics["acceptance"]["allNumericalCorridorGatesPass"] = all(metrics["acceptance"].values())
    return metrics


def _building_support_vertices(inputs: ReleaseInputs, building_ids: set[str]) -> np.ndarray:
    """Return every active triangle vertex contributing under selected footprints."""
    rows, columns = inputs.baseline.shape
    mask = np.zeros((rows, columns), dtype=bool)
    features = {str(feature["id"]): feature for feature in inputs.buildings.get("buildings", [])}
    for building_id in sorted(building_ids):
        feature = features.get(building_id)
        if feature is None:
            raise RoadSurfaceError(f"selected building '{building_id}' is absent from pinned data")
        for record in feature["geometry"]["polygons"]:
            polygon = Polygon(record["exteriorXZ"], record.get("interiorRingsXZ", []))
            min_x, min_z, max_x, max_z = polygon.bounds
            first_column = max(0, math.floor((min_x + inputs.width_m / 2) / inputs.spacing_m))
            last_column = min(
                columns - 2, math.floor((max_x + inputs.width_m / 2) / inputs.spacing_m)
            )
            first_row = max(0, math.floor((min_z + inputs.depth_m / 2) / inputs.spacing_m))
            last_row = min(rows - 2, math.floor((max_z + inputs.depth_m / 2) / inputs.spacing_m))
            for row in range(first_row, last_row + 1):
                z0 = row * inputs.spacing_m - inputs.depth_m / 2
                z1 = z0 + inputs.spacing_m
                for column in range(first_column, last_column + 1):
                    x0 = column * inputs.spacing_m - inputs.width_m / 2
                    x1 = x0 + inputs.spacing_m
                    lower_left = row * columns + column
                    lower_right = lower_left + 1
                    upper_left = lower_left + columns
                    upper_right = upper_left + 1
                    first_triangle = Polygon(((x0, z0), (x0, z1), (x1, z0)))
                    if polygon.intersects(first_triangle):
                        for vertex in (lower_left, upper_left, lower_right):
                            mask.flat[vertex] = True
                    second_triangle = Polygon(((x1, z0), (x0, z1), (x1, z1)))
                    if polygon.intersects(second_triangle):
                        for vertex in (upper_right, upper_left, lower_right):
                            mask.flat[vertex] = True
    return mask


def _project_grid_edge_constraints(
    baseline: np.ndarray,
    candidate: np.ndarray,
    spacing_m: float,
    adjustable: np.ndarray,
    pinned_mask: np.ndarray,
    pinned_values: np.ndarray,
    maximum_change_m: float = 4.999,
    maximum_added_gradient_m_per_m: float = 0.999,
    maximum_iterations: int = 500,
    tolerance_m: float = 2e-5,
    linear_constraints: list[dict[str, Any]] | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Project onto grid, earthwork, and sparse linear surface constraints."""
    linear_constraints = linear_constraints or []
    if not (
        baseline.shape
        == candidate.shape
        == adjustable.shape
        == pinned_mask.shape
        == pinned_values.shape
    ):
        raise RoadSurfaceError("final-surface projection arrays must share one grid shape")
    if not np.isfinite(baseline).all() or not np.isfinite(candidate).all():
        raise RoadSurfaceError("final-surface projection inputs contain non-finite values")
    baseline64 = baseline.astype(np.float64)
    target = candidate.astype(np.float64)
    fixed = ~adjustable | pinned_mask
    fixed_values = baseline64.copy()
    fixed_values[pinned_mask] = pinned_values[pinned_mask].astype(np.float64)
    lower = baseline64 - maximum_change_m
    upper = baseline64 + maximum_change_m
    edge_limit_x = np.abs(np.diff(baseline64, axis=1)) + spacing_m * maximum_added_gradient_m_per_m
    edge_limit_z = np.abs(np.diff(baseline64, axis=0)) + spacing_m * maximum_added_gradient_m_per_m

    fixed_conflicts = []
    fixed_x = fixed[:, :-1] & fixed[:, 1:]
    fixed_z = fixed[:-1, :] & fixed[1:, :]
    violations_x = np.abs(np.diff(fixed_values, axis=1)) - edge_limit_x
    violations_z = np.abs(np.diff(fixed_values, axis=0)) - edge_limit_z
    if np.any(fixed_x & (violations_x > tolerance_m)):
        row, column = np.unravel_index(
            int(np.argmax(np.where(fixed_x, violations_x, -np.inf))), violations_x.shape
        )
        fixed_conflicts.append(
            {
                "axis": "x",
                "row": int(row),
                "column": int(column),
                "excessM": float(violations_x[row, column]),
            }
        )
    if np.any(fixed_z & (violations_z > tolerance_m)):
        row, column = np.unravel_index(
            int(np.argmax(np.where(fixed_z, violations_z, -np.inf))), violations_z.shape
        )
        fixed_conflicts.append(
            {
                "axis": "z",
                "row": int(row),
                "column": int(column),
                "excessM": float(violations_z[row, column]),
            }
        )
    if fixed_conflicts:
        raise RoadSurfaceError(
            "strict final-surface projection is infeasible because pinned samples violate "
            f"a grid-edge gradient bound: {fixed_conflicts}"
        )
    fixed_change = np.abs(fixed_values[fixed] - baseline64[fixed])
    if fixed_change.size and float(np.max(fixed_change)) > maximum_change_m:
        raise RoadSurfaceError(
            "strict final-surface projection is infeasible because a fixed control exceeds "
            f"the {maximum_change_m:g} m earthwork bound"
        )

    fixed_linear_conflicts = []
    for constraint in linear_constraints:
        indices = constraint["indices"]
        coefficients = constraint["coefficients"]
        limit_m = float(constraint["limitM"])
        if (
            indices.ndim != 1
            or coefficients.shape != indices.shape
            or not np.isfinite(coefficients).all()
            or not np.isfinite(limit_m)
            or np.any(indices < 0)
            or np.any(indices >= target.size)
            or float(np.dot(coefficients, coefficients)) <= 0
        ):
            raise RoadSurfaceError("sparse linear surface constraint is malformed")
        fixed_support = fixed.ravel()[indices]
        if np.all(fixed_support):
            fixed_value = float(np.dot(coefficients, fixed_values.ravel()[indices]))
            if fixed_value > limit_m + tolerance_m:
                fixed_linear_conflicts.append(
                    {
                        **constraint["label"],
                        "excessM": fixed_value - limit_m,
                    }
                )
    if fixed_linear_conflicts:
        raise RoadSurfaceError(
            "strict projection has fixed-node conflicts with required severe-station "
            "crossfall constraints: "
            + json.dumps(fixed_linear_conflicts[:12], sort_keys=True, separators=(",", ":"))
        )

    node_correction = np.zeros_like(target)
    correction_x = np.zeros_like(edge_limit_x)
    correction_z = np.zeros_like(edge_limit_z)
    linear_corrections = np.zeros(len(linear_constraints), dtype=np.float64)
    linear_norms = np.asarray(
        [float(np.dot(item["coefficients"], item["coefficients"])) for item in linear_constraints],
        dtype=np.float64,
    )
    projected = target.copy()

    def project_edge_batch(
        values: np.ndarray,
        correction: np.ndarray,
        limits: np.ndarray,
        first_slice: tuple[slice, slice],
        second_slice: tuple[slice, slice],
    ) -> None:
        first = values[first_slice]
        second = values[second_slice]
        correction_view = correction[first_slice]
        first_adjusted = first - correction_view
        second_adjusted = second + correction_view
        difference = second_adjusted - first_adjusted
        clipped = np.clip(difference, -limits[first_slice], limits[first_slice])
        new_correction = (difference - clipped) * 0.5
        values[first_slice] = first_adjusted + new_correction
        values[second_slice] = second_adjusted - new_correction
        correction_view[...] = new_correction

    maximum_violation = math.inf
    iteration = 0
    rows, columns = projected.shape
    for iteration in range(1, maximum_iterations + 1):
        for parity in (0, 1):
            first_columns = slice(parity, columns - 1, 2)
            second_columns = slice(parity + 1, columns, 2)
            project_edge_batch(
                projected,
                correction_x,
                edge_limit_x,
                (slice(None), first_columns),
                (slice(None), second_columns),
            )
        for parity in (0, 1):
            first_rows = slice(parity, rows - 1, 2)
            second_rows = slice(parity + 1, rows, 2)
            project_edge_batch(
                projected,
                correction_z,
                edge_limit_z,
                (first_rows, slice(None)),
                (second_rows, slice(None)),
            )
        adjusted = projected + node_correction
        clipped_nodes = np.clip(adjusted, lower, upper)
        clipped_nodes[fixed] = fixed_values[fixed]
        node_correction = adjusted - clipped_nodes
        projected = clipped_nodes
        projected_flat = projected.ravel()
        for constraint_index, constraint in enumerate(linear_constraints):
            indices = constraint["indices"]
            coefficients = constraint["coefficients"]
            correction = linear_corrections[constraint_index]
            adjusted_values = projected_flat[indices] + correction * coefficients
            violation = float(np.dot(coefficients, adjusted_values) - constraint["limitM"])
            next_correction = max(0.0, violation / linear_norms[constraint_index])
            projected_flat[indices] = adjusted_values - next_correction * coefficients
            linear_corrections[constraint_index] = next_correction
        if iteration == 1 or iteration % 5 == 0:
            linear_violations = [
                float(
                    np.dot(item["coefficients"], projected.ravel()[item["indices"]])
                    - item["limitM"]
                )
                for item in linear_constraints
            ]
            max_linear_violation = max(linear_violations, default=0.0)
            maximum_violation = max(
                float(np.max(np.abs(np.diff(projected, axis=1)) - edge_limit_x)),
                float(np.max(np.abs(np.diff(projected, axis=0)) - edge_limit_z)),
                float(np.max(np.abs(projected[fixed] - fixed_values[fixed])))
                if np.any(fixed)
                else 0.0,
                float(np.max(np.maximum(lower - projected, projected - upper))),
                max_linear_violation,
            )
            if maximum_violation <= tolerance_m:
                break
    if maximum_violation > tolerance_m:
        residual_x = np.abs(np.diff(projected, axis=1)) - edge_limit_x
        residual_z = np.abs(np.diff(projected, axis=0)) - edge_limit_z
        edge_x_index = np.unravel_index(int(np.argmax(residual_x)), residual_x.shape)
        edge_z_index = np.unravel_index(int(np.argmax(residual_z)), residual_z.shape)
        fixed_residual = (
            float(np.max(np.abs(projected[fixed] - fixed_values[fixed]))) if np.any(fixed) else 0.0
        )
        node_residual = float(np.max(np.maximum(lower - projected, projected - upper)))
        remaining_linear_violations = [
            float(np.dot(item["coefficients"], projected.ravel()[item["indices"]]) - item["limitM"])
            for item in linear_constraints
        ]
        worst_linear_index = (
            int(np.argmax(remaining_linear_violations)) if remaining_linear_violations else None
        )
        worst_linear = (
            {
                **linear_constraints[worst_linear_index]["label"],
                "excessM": remaining_linear_violations[worst_linear_index],
            }
            if worst_linear_index is not None
            else None
        )
        raise RoadSurfaceError(
            "strict final-surface projection did not converge within "
            f"{maximum_iterations} iterations; maximum residual is {maximum_violation:.6f} m "
            f"(edgeX={float(residual_x[edge_x_index]):.6f} at {edge_x_index}, "
            f"edgeZ={float(residual_z[edge_z_index]):.6f} at {edge_z_index}, "
            f"fixed={fixed_residual:.6f}, node={node_residual:.6f}); "
            f"worst linear constraint is {worst_linear}"
        )
    output = projected.astype("<f4")
    output_violation = max(
        float(np.max(np.abs(np.diff(output.astype(np.float64), axis=1)) - edge_limit_x)),
        float(np.max(np.abs(np.diff(output.astype(np.float64), axis=0)) - edge_limit_z)),
        float(np.max(np.abs(output[fixed].astype(np.float64) - fixed_values[fixed])))
        if np.any(fixed)
        else 0.0,
        float(np.max(np.abs(output.astype(np.float64) - baseline64))) - maximum_change_m,
        max(
            (
                float(
                    np.dot(item["coefficients"], output.ravel()[item["indices"]].astype(np.float64))
                    - item["limitM"]
                )
                for item in linear_constraints
            ),
            default=0.0,
        ),
    )
    if output_violation > 5e-5:
        raise RoadSurfaceError(
            "float32 final-surface projection exceeds a strict safety constraint; "
            f"maximum residual is {output_violation:.6f} m"
        )
    output_linear_violations = [
        float(
            np.dot(item["coefficients"], output.ravel()[item["indices"]].astype(np.float64))
            - item["limitM"]
        )
        for item in linear_constraints
    ]
    worst_linear_index = (
        int(np.argmax(output_linear_violations)) if output_linear_violations else None
    )
    return output, {
        "iterations": iteration,
        "maximumConstraintResidualM": maximum_violation,
        "maximumFloat32ConstraintResidualM": output_violation,
        "maximumAbsoluteChangeM": float(np.max(np.abs(output.astype(np.float64) - baseline64))),
        "maximumPositiveAddedGradientMPerM": float(
            max(
                np.max(
                    np.abs(np.diff(output.astype(np.float64), axis=1))
                    - np.abs(np.diff(baseline64, axis=1))
                ),
                np.max(
                    np.abs(np.diff(output.astype(np.float64), axis=0))
                    - np.abs(np.diff(baseline64, axis=0))
                ),
            )
            / spacing_m
        ),
        "maximumChangeLimitM": maximum_change_m,
        "maximumPositiveAddedGradientLimitMPerM": maximum_added_gradient_m_per_m,
        "linearConstraintCount": len(linear_constraints),
        "maximumLinearConstraintViolationM": max(output_linear_violations, default=0.0),
        "worstLinearConstraint": (
            {
                **linear_constraints[worst_linear_index]["label"],
                "excessM": output_linear_violations[worst_linear_index],
            }
            if worst_linear_index is not None
            else None
        ),
        "fixedLinearConflictCount": len(fixed_linear_conflicts),
        "adjustableVertexCount": int(np.count_nonzero(adjustable)),
        "fixedVertexCount": int(np.count_nonzero(fixed)),
    }


def _project_final_surface(
    inputs: ReleaseInputs,
    baseline: np.ndarray,
    candidate: np.ndarray,
    spacing_m: float,
    config: PreviewConfig,
    harm_fallback: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    """Enforce strict final-grid and building constraints after treatment fallbacks."""
    baseline64 = baseline.astype(np.float64)
    candidate64 = candidate.astype(np.float64)
    controls, centerline_positions, control_report = _surface_control_vertices(inputs, candidate)
    severe_constraints, severe_constraint_report = _severe_station_crossfall_constraints(
        inputs, baseline, spacing_m, harm_fallback
    )
    teignmouth_constraint_report = None
    teignmouth_constraints: list[dict[str, Any]] = []
    if config.treatment_variant == TEIGNMOUTH_CANDIDATE_VARIANT:
        teignmouth_constraints, teignmouth_constraint_report = _teignmouth_section_samples(
            inputs, baseline, spacing_m
        )
    projection_constraints = severe_constraints + teignmouth_constraints
    constrained_station_vertices = np.zeros_like(controls)
    for constraint in projection_constraints:
        constrained_station_vertices.ravel()[constraint["indices"]] = True
    initial_buildings = _building_base_report(inputs, candidate)
    building_limit = 2.424
    building_p95_limit = 0.183
    selected = {
        item["id"]
        for item in initial_buildings["individualChangesM"]
        if abs(item["previewMinusBaselineM"]) > building_p95_limit
        or abs(item["previewMinusBaselineM"]) > building_limit
    }
    if initial_buildings["signedPreviewMinusBaselineBaseM"]["maximumAbsolute"] > building_limit:
        selected.update(
            item["id"]
            for item in initial_buildings["individualChangesM"]
            if abs(item["previewMinusBaselineM"]) > building_limit
        )

    projection_report = None
    final_buildings = None
    centerline_pins = np.zeros_like(controls)
    centerline_report = None
    selection_count = 0
    for _ in range(1, 17):
        selection_count += 1
        building_vertices = _building_support_vertices(inputs, selected)
        source_ground_pins = building_vertices | centerline_pins
        fixed_value_conflicts = (
            controls & source_ground_pins & (np.abs(candidate64 - baseline64) > 1e-5)
        )
        if np.any(fixed_value_conflicts):
            overlap = np.argwhere(fixed_value_conflicts)
            row, column = map(int, overlap[0])
            raise RoadSurfaceError(
                "strict controls are infeasible: a registered centerline/Parkfield control "
                f"stencil overlaps a selected source-ground building footprint at grid row "
                f"{row}, column {column}"
            )
        adjustable = (np.abs(candidate64 - baseline64) > 1e-9) | constrained_station_vertices
        pinned_mask = controls | source_ground_pins
        pinned_values = candidate.copy()
        pinned_values[source_ground_pins] = baseline[source_ground_pins]
        projected, projection_report = _project_grid_edge_constraints(
            baseline,
            candidate,
            spacing_m,
            adjustable,
            pinned_mask,
            pinned_values,
            maximum_iterations=(
                TEIGNMOUTH_MAX_PROJECTION_ITERATIONS
                if config.treatment_variant == TEIGNMOUTH_CANDIDATE_VARIANT
                else 500
            ),
            linear_constraints=projection_constraints,
        )
        new_centerline_pins, centerline_report = _centerline_retention_vertices(
            centerline_positions, baseline, projected, spacing_m
        )
        additional_centerline_pins = new_centerline_pins & ~centerline_pins
        if np.any(additional_centerline_pins):
            centerline_pins |= additional_centerline_pins
            continue
        final_buildings = _building_base_report(inputs, projected)
        signed = final_buildings["signedPreviewMinusBaselineBaseM"]
        if (
            signed["p95Absolute"] <= building_p95_limit
            and signed["maximumAbsolute"] <= building_limit
        ):
            break
        changed = [
            item
            for item in final_buildings["individualChangesM"]
            if abs(item["previewMinusBaselineM"]) > building_p95_limit
        ]
        additional = {item["id"] for item in changed} - selected
        if not additional:
            raise RoadSurfaceError(
                "final-surface projection leaves a building-base cap violated without any "
                f"newly selectable source-ground footprints: p95={signed['p95Absolute']:.6f} m, "
                f"maximum={signed['maximumAbsolute']:.6f} m"
            )
        selected.update(additional)
    else:
        assert final_buildings is not None
        signed = final_buildings["signedPreviewMinusBaselineBaseM"]
        raise RoadSurfaceError(
            "building-aware final-surface projection did not meet strict p95/max caps after "
            f"16 selections: p95={signed['p95Absolute']:.6f} m, "
            f"maximum={signed['maximumAbsolute']:.6f} m"
        )

    assert projection_report is not None and final_buildings is not None
    teignmouth_metrics = None
    if config.treatment_variant == TEIGNMOUTH_CANDIDATE_VARIANT:
        teignmouth_metrics = _teignmouth_section_metrics(inputs, baseline, projected, spacing_m)
        if not teignmouth_metrics["allStationsPass"]:
            worst_slope = max(
                teignmouth_metrics["sections"],
                key=lambda item: item["previewMaximumAbsoluteLateralSlopePercent"],
            )
            worst_span = max(
                teignmouth_metrics["sections"],
                key=lambda item: item["previewEndpointSpanM"],
            )
            raise RoadSurfaceError(
                "strict Teignmouth local shared-surface gate failed: "
                f"maxSlope={teignmouth_metrics['maximumObservedAbsoluteLateralSlopePercent']:.6f}% "
                f"at station {worst_slope['stationM']:.6f} m, "
                f"maxSpan={teignmouth_metrics['maximumObservedEndpointSpanM']:.6f} m "
                f"at station {worst_span['stationM']:.6f} m, "
                f"centerlineMax={teignmouth_metrics['maximumCenterlineDeviationM']:.6f} m"
            )
    gradient = _terrain_gradient_change_summary(
        baseline64, projected.astype(np.float64), spacing_m, inputs.width_m, inputs.depth_m
    )
    signed = final_buildings["signedPreviewMinusBaselineBaseM"]
    building_changes = {
        item["id"]: float(item["previewMinusBaselineM"])
        for item in final_buildings["individualChangesM"]
    }
    newton_legacy_ids = (
        "osm:way:196536218",
        "osm:way:196536220",
        "osm:way:196536221",
        "osm:way:196536227",
        "osm:way:196536217",
    )
    newton_legacy_changes = {
        building_id: building_changes.get(building_id) for building_id in newton_legacy_ids
    }
    if any(value is None or abs(value) > 0.05 for value in newton_legacy_changes.values()):
        raise RoadSurfaceError(
            f"strict Newton legacy building-base limit failed at ±0.05 m: {newton_legacy_changes}"
        )
    if (
        projection_report["maximumAbsoluteChangeM"] >= 5.0
        or gradient["maximumPositiveIncreaseMPerM"] >= 1.0
        or signed["p95Absolute"] > building_p95_limit
        or signed["maximumAbsolute"] > building_limit
    ):
        edge = gradient["maximumPositiveIncreaseEdge"]
        raise RoadSurfaceError(
            "strict final-surface projection failed a required numerical gate: "
            f"maxChange={projection_report['maximumAbsoluteChangeM']:.6f} m, "
            f"addedGradient={gradient['maximumPositiveIncreaseMPerM']:.6f} m/m at {edge}, "
            f"buildingP95={signed['p95Absolute']:.6f} m, "
            f"buildingMax={signed['maximumAbsolute']:.6f} m"
        )
    corridor_metrics = _strict_corridor_metrics(inputs, projected, harm_fallback)
    footing_metrics = _risk_building_footing_metrics(inputs, projected, final_buildings)
    projection_report.update(
        {
            "buildingSelectionIterations": selection_count,
            "sourceGroundBuildingCount": len(selected),
            "sourceGroundBuildingIds": sorted(selected),
            "buildingBaseP95AbsoluteM": signed["p95Absolute"],
            "buildingBaseMaximumAbsoluteM": signed["maximumAbsolute"],
            "buildingP95LimitM": building_p95_limit,
            "buildingMaximumLimitM": building_limit,
            "newtonLegacyBuildingBaseChangesM": newton_legacy_changes,
            "registeredRiskFootingSections": footing_metrics,
            "controlStencil": control_report,
            "severeStationCrossfallConstraints": {
                **severe_constraint_report,
                "maximumConstraintViolationM": projection_report[
                    "maximumLinearConstraintViolationM"
                ],
                "worstConstraint": projection_report["worstLinearConstraint"],
            },
            "centerlineProfileConstraint": centerline_report,
            "strictCorridorMetrics": corridor_metrics,
            "terrainGradientChange": gradient,
            "teignmouthLocalCrossfall": (
                {
                    **teignmouth_constraint_report,
                    **teignmouth_metrics,
                    "constraintCount": len(teignmouth_constraints),
                }
                if teignmouth_metrics is not None and teignmouth_constraint_report is not None
                else None
            ),
            "policy": (
                "preview-only deterministic projection: preserve active centerline and registered "
                "Parkfield sample stencils; pin only buildings exceeding accepted base-shift caps; "
                "constrain final grid edges to baseline magnitude plus 0.999 m/m and node changes "
                "to ±4.999 m"
            ),
        }
    )
    return projected, projection_report


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
    protected_output_inputs = [
        project_root / "public/worlds/torquay-poc-001-2km",
        release_root,
    ]
    if config.treatment_variant == TEIGNMOUTH_CANDIDATE_VARIANT:
        protected_output_inputs.append(project_root / "public/worlds/torquay-road-surface-preview")
    output_directory = guard_output_directory(
        project_root,
        project_root / config.output_directory,
        protected_output_inputs,
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
        inputs.baseline,
        segments,
        inputs.spacing_m,
        inputs.width_m,
        inputs.depth_m,
        config,
        inputs=inputs,
    )
    strict_corridor = grid_report.get("finalSurfaceProjection", {}).get("strictCorridorMetrics")
    if strict_corridor and not strict_corridor.get("acceptance", {}).get(
        "allNumericalCorridorGatesPass", False
    ):
        raise RoadSurfaceError(
            "strict full-corridor or signed longitudinal acceptance failed; refusing to "
            "write preview files or execution record: "
            + json.dumps(strict_corridor["acceptance"], sort_keys=True, separators=(",", ":"))
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
    if config.treatment_variant == TEIGNMOUTH_CANDIDATE_VARIANT:
        qa["treatmentVariant"] = TEIGNMOUTH_CANDIDATE_VARIANT
        qa["teignmouthLocalAcceptance"] = grid_report["finalSurfaceProjection"][
            "teignmouthLocalCrossfall"
        ]
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
    protected_output_inputs = [
        project_root / "public/worlds/torquay-poc-001-2km",
        release_root,
    ]
    if config.treatment_variant == TEIGNMOUTH_CANDIDATE_VARIANT:
        protected_output_inputs.append(project_root / "public/worlds/torquay-road-surface-preview")
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
