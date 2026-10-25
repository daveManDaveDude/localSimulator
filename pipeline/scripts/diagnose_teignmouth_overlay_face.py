"""One reserved, face-only source-overlay diagnostic for Float32 build 2.

The parent verifies a frozen manifest and diagnostic-2 reservation, creates one
fresh evidence leaf, and supervises one worker under a 120-second wall budget.
The worker reads one serialized face and only its intersecting source cells.
This script never edits the attempt ledger or candidate/product outputs.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import secrets
import subprocess
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ISSUE = "Teignmouth-float32-topology-representation-1"
ARTIFACT_ROOT = "docs/milestones/artifacts/Teignmouth-float32-topology"
DIAGNOSTIC_ROOT = f"{ARTIFACT_ROOT}/diagnostic-2"
EVIDENCE_RELATIVE = f"{DIAGNOSTIC_ROOT}/run-1"
MANIFEST_RELATIVE = f"{DIAGNOSTIC_ROOT}/input-manifest.json"
LEDGER_RELATIVE = f"{ARTIFACT_ROOT}/attempt-ledger.json"
SNAPSHOT_RELATIVE = f"{DIAGNOSTIC_ROOT}/attempt-ledger-snapshot.json"
EXTERNAL_SUPERVISOR_RELATIVE = "pipeline/scripts/run_teignmouth_overlay_face_diagnostic.py"
BUILD_ROOT = f"{ARTIFACT_ROOT}/build-2/run-1"
BUILD_MANIFEST_RELATIVE = f"{ARTIFACT_ROOT}/build-2/input-manifest.json"
TARGET_FACE_ID = 19669
EXPECTED_FACE_AREA_M2 = 0.020639419555664062
EXPECTED_CLIP_AREA_M2 = 1.1028883815799223e-12
AREA_FILTER_M2 = 1e-12
WALL_LIMIT_SECONDS = 120.0
WORKER_BUDGET_RESERVE_SECONDS = 8.0
ORIGIN_XYZ_M = (-140.0, 0.0, -95.0)
GRID_ROWS = 1001
GRID_COLUMNS = 1001
GRID_SPACING_M = 2.0
GRID_WIDTH_M = 2000.0
GRID_DEPTH_M = 2000.0
INDEX_FIRST_ROW = 432
INDEX_LAST_ROW = 473
INDEX_FIRST_COLUMN = 409
INDEX_LAST_COLUMN = 451
REQUIRED_FILES = {
    SNAPSHOT_RELATIVE,
    BUILD_MANIFEST_RELATIVE,
    f"{ARTIFACT_ROOT}/spec.md",
    f"{ARTIFACT_ROOT}/coordinator-disposition-13.md",
    f"{ARTIFACT_ROOT}/independent-review-7.md",
    f"{ARTIFACT_ROOT}/independent-review-8.md",
    f"{ARTIFACT_ROOT}/diagnostic-2/plan.md",
    f"{ARTIFACT_ROOT}/build-2/run-1/build-report.json",
    f"{ARTIFACT_ROOT}/build-2/run-1/supervisor-report.json",
    f"{ARTIFACT_ROOT}/build-2/run-1/candidate-failure.json",
    f"{ARTIFACT_ROOT}/build-2/run-1/gate-state.json",
    f"{ARTIFACT_ROOT}/build-2/run-1/serialization-stage.json",
    f"{ARTIFACT_ROOT}/build-2/run-1/pre-run-preservation.json",
    f"{ARTIFACT_ROOT}/build-2/run-1/post-run-preservation.json",
    f"{ARTIFACT_ROOT}/build-2/run-1/serialized-local-positions.xyz.f32",
    f"{ARTIFACT_ROOT}/build-2/run-1/serialized-world-positions.xyz.f64",
    f"{ARTIFACT_ROOT}/build-2/run-1/serialized-indices.u32",
    f"{ARTIFACT_ROOT}/build-2/run-1/serialized-candidate-y.f32",
    f"{ARTIFACT_ROOT}/build-2/run-1/serialized-source-y.f32",
    f"{ARTIFACT_ROOT}/build-2/run-1/chart-stations.f64",
    f"{ARTIFACT_ROOT}/build-2/run-1/chart-points.xz.f64",
    f"{ARTIFACT_ROOT}/build-2/run-1/chart-fields.station-lateral.f64",
    f"{ARTIFACT_ROOT}/build-2/run-1/chart-indices.u32",
    f"{ARTIFACT_ROOT}/build-2/run-1/chart-stage.json",
    f"{ARTIFACT_ROOT}/build-2/run-1/construction-world-xz.f64",
    f"{DIAGNOSTIC_ROOT}/runtime-identity.json",
    "pipeline/scripts/teignmouth_overlay_diagnostic_runtime_identity.schema.json",
    "config/road-surface-teignmouth-float32.json",
    "config/road-surface-teignmouth-corridor-continuation.json",
    "pipeline/.venv/Scripts/python.exe",
    "pipeline/.venv/pyvenv.cfg",
    "pipeline/scripts/diagnose_teignmouth_overlay_face.py",
    EXTERNAL_SUPERVISOR_RELATIVE,
    "pipeline/torquay_pipeline/road_surface.py",
    "pipeline/torquay_pipeline/road_surface_float32_frame.py",
    "pipeline/torquay_pipeline/road_surface_topology.py",
    "pipeline/torquay_pipeline/teignmouth_corridor_prototype.py",
    "pipeline/torquay_pipeline/teignmouth_corridor_continuation.py",
    "pipeline/torquay_pipeline/teignmouth_float32_candidate.py",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".pending")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _verify_inputs(
    root: Path,
    manifest_path: Path,
    expected_manifest_sha256: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest_sha_before = _sha256(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema") != "teignmouth-float32-diagnostic-input-v1"
        or manifest.get("issueId") != ISSUE
        or manifest.get("diagnosticOrdinal") != 2
        or manifest.get("originXYZM") != list(ORIGIN_XYZ_M)
    ):
        raise ValueError("diagnostic manifest identity, ordinal or fixed origin mismatch")
    bindings: dict[str, dict[str, Any]] = {}
    failures = []
    checked = 0
    for binding in manifest.get("files", []):
        relative = binding.get("path")
        if not isinstance(relative, str) or relative in bindings:
            failures.append({"path": relative, "reason": "invalid or duplicate binding"})
            continue
        path = (root / relative).resolve(strict=False)
        try:
            canonical = path.relative_to(root).as_posix()
        except ValueError:
            failures.append({"path": relative, "reason": "binding escapes repository root"})
            continue
        if canonical != relative or not path.is_file():
            failures.append({"path": relative, "reason": "noncanonical or unavailable file"})
            continue
        checked += 1
        try:
            size = path.stat().st_size
            digest = _sha256(path)
        except OSError as exc:
            failures.append({"path": relative, "reason": f"unreadable: {exc}"})
            continue
        if size != binding.get("byteLength") or digest != binding.get("sha256"):
            failures.append({"path": relative, "reason": "byte length or sha256 mismatch"})
        bindings[relative] = binding
    missing = sorted(REQUIRED_FILES - bindings.keys())
    if missing:
        failures.extend({"path": path, "reason": "mandatory binding missing"} for path in missing)

    build_manifest_path = root / BUILD_MANIFEST_RELATIVE
    try:
        build_manifest = json.loads(build_manifest_path.read_text(encoding="utf-8"))
        diagnostic_bindings = {
            path: (item.get("byteLength"), item.get("sha256"))
            for path, item in bindings.items()
        }
        for item in build_manifest.get("files", []):
            path = item.get("path")
            expected = (item.get("byteLength"), item.get("sha256"))
            if diagnostic_bindings.get(path) != expected:
                failures.append(
                    {"path": path, "reason": "build-2 protected binding absent or not identical"}
                )
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        failures.append({"path": BUILD_MANIFEST_RELATIVE, "reason": f"invalid build manifest: {exc}"})

    for preservation in (root / ARTIFACT_ROOT).rglob("*preservation*.json"):
        if preservation.is_relative_to(root / EVIDENCE_RELATIVE):
            continue
        relative = preservation.relative_to(root).as_posix()
        if relative not in bindings:
            failures.append({"path": relative, "reason": "existing preservation record is not bound"})
    manifest_sha_after = _sha256(manifest_path)
    if manifest_sha_after != manifest_sha_before:
        failures.append({"path": MANIFEST_RELATIVE, "reason": "manifest changed during verification"})
    if expected_manifest_sha256 is not None and manifest_sha_after != expected_manifest_sha256:
        failures.append({"path": MANIFEST_RELATIVE, "reason": "manifest hash differs from pre-run pin"})
    preservation = {
        "passes": not failures,
        "checkedFileCount": checked,
        "changed": failures,
        "manifestSha256": manifest_sha_after,
        "boundFilePaths": sorted(bindings),
        "build2ProtectedBindingCount": len(build_manifest.get("files", []))
        if "build_manifest" in locals()
        else 0,
    }
    return manifest, bindings, preservation


def _runtime_identity(root: Path, bindings: dict[str, Any]) -> dict[str, Any]:
    import numpy as np
    import shapely

    relative = f"{DIAGNOSTIC_ROOT}/runtime-identity.json"
    if relative not in bindings:
        raise ValueError("frozen runtime identity is not bound")
    frozen = json.loads((root / relative).read_text(encoding="utf-8"))
    schema_relative = "pipeline/scripts/teignmouth_overlay_diagnostic_runtime_identity.schema.json"
    if schema_relative not in bindings:
        raise ValueError("runtime identity schema is not bound")
    schema = json.loads((root / schema_relative).read_text(encoding="utf-8"))
    required_keys = set(schema.get("required", []))
    if (
        schema.get("title") != "Teignmouth face-overlay diagnostic runtime identity"
        or schema.get("additionalProperties") is not False
        or set(frozen) != required_keys
        or frozen.get("schema") != "teignmouth-overlay-runtime-identity-v1"
    ):
        raise ValueError("frozen runtime identity does not match the bound schema")
    actual = {
        "schema": "teignmouth-overlay-runtime-identity-v1",
        "resolvedExecutable": str(Path(sys.executable).resolve()),
        "pythonVersion": sys.version,
        "pythonImplementation": platform.python_implementation(),
        "interpreterSha256": _sha256(Path(sys.executable).resolve()),
        "numpyVersion": np.__version__,
        "shapelyVersion": importlib.metadata.version("shapely"),
        "geosVersion": shapely.geos_version_string,
    }
    if frozen != actual:
        raise ValueError(
            "actual Python/NumPy/Shapely/GEOS identity differs from frozen runtime input"
        )
    return {"frozen": frozen, "actual": actual, "matches": True}


def _verify_release_identity(
    root: Path,
    bindings: dict[str, Any],
    build_report: dict[str, Any],
    release_id: str,
) -> dict[str, Any]:
    source_hashes = build_report.get("stages", {}).get("frozenInputs", {}).get("sourceHashes", {})
    if not isinstance(source_hashes, dict):
        raise ValueError("build-2 release source identity is missing")
    normalized: dict[str, dict[str, Any]] = {}
    for name, descriptor in source_hashes.items():
        raw_path = descriptor.get("path")
        if not isinstance(raw_path, str):
            raise ValueError(f"build-2 source descriptor has no path: {name}")
        source_path = Path(raw_path)
        if not source_path.is_absolute():
            source_path = root / source_path
        try:
            relative = source_path.resolve(strict=True).relative_to(root).as_posix()
        except (OSError, ValueError) as exc:
            raise ValueError(f"build-2 source path is unavailable/outside repository: {name}") from exc
        binding = bindings.get(relative)
        expected_hash = descriptor.get("sha256", descriptor.get("readySha256"))
        expected_size = descriptor.get("byteLength")
        if binding is None or binding.get("sha256") != expected_hash:
            raise ValueError(f"build-2 source identity is not identically bound: {relative}")
        if expected_size is not None and binding.get("byteLength") != expected_size:
            raise ValueError(f"build-2 source byte length differs: {relative}")
        normalized[name] = {"path": relative, "sha256": expected_hash, "byteLength": binding["byteLength"]}

    required_names = {
        "ready.json": "ready.json",
        "inventory.json": "inventory.json",
        "manifest.json": "manifest.json",
        "heightfield.f32": "heightfield.f32",
        "roads/manifest.json": "roads/manifest.json",
        "roads/roads.json": "roads/roads.json",
    }
    source_paths = {name: normalized[name]["path"] for name in required_names if name in normalized}
    for name, expected_suffix in required_names.items():
        if name not in normalized:
            raise ValueError(f"build-2 source identity omits {name}")
        if not normalized[name]["path"].endswith(expected_suffix):
            raise ValueError(f"build-2 source path identity is not {expected_suffix}")
    release_root = root / source_paths["manifest.json"]
    release_root = release_root.parent
    release_manifest = json.loads((root / source_paths["manifest.json"]).read_text(encoding="utf-8"))
    inventory = json.loads((root / source_paths["inventory.json"]).read_text(encoding="utf-8"))
    ready = json.loads((root / source_paths["ready.json"]).read_text(encoding="utf-8"))
    road_manifest = json.loads((root / source_paths["roads/manifest.json"]).read_text(encoding="utf-8"))
    height_binding = bindings[source_paths["heightfield.f32"]]
    inventory_binding = bindings[source_paths["inventory.json"]]
    manifest_binding = bindings[source_paths["manifest.json"]]
    roads_binding = bindings[source_paths["roads/roads.json"]]
    height = release_manifest.get("heightfield", {})
    terrain = road_manifest.get("terrainIdentity", {})
    release_matches = (
        ready.get("releaseId") == release_id
        and ready.get("inventoryPath") == f"releases/{release_id}/inventory.json"
        and ready.get("inventorySha256") == inventory_binding["sha256"]
        and ready.get("inventoryByteLength") == inventory_binding["byteLength"]
        and inventory.get("releaseId") == release_id
        and inventory.get("worldId") == ready.get("worldId")
        and inventory.get("sceneProfile") == ready.get("sceneProfile")
        and release_manifest.get("heightfield", {}).get("path") == "heightfield.f32"
        and height.get("sha256") == height_binding["sha256"]
        and height.get("byteLength") == height_binding["byteLength"]
        and height.get("rows") == GRID_ROWS
        and height.get("columns") == GRID_COLUMNS
        and height.get("spacingM") == GRID_SPACING_M
        and release_manifest.get("extentM") == {"width": GRID_WIDTH_M, "depth": GRID_DEPTH_M}
        and terrain.get("heightfieldSha256") == height_binding["sha256"]
        and terrain.get("heightfieldByteLength") == height_binding["byteLength"]
        and terrain.get("manifestSha256") == manifest_binding["sha256"]
        and terrain.get("heightfieldDimensions") == [GRID_ROWS, GRID_COLUMNS]
        and roads_binding["sha256"] == normalized["roads/roads.json"]["sha256"]
    )
    if not release_matches:
        raise ValueError("ready/inventory/release/road/heightfield identities disagree with build 2")
    inventory_files = {
        item.get("path"): item
        for item in inventory.get("files", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    release_prefix = release_root.relative_to(root).as_posix() + "/"
    checked_inventory_paths = []
    for relative_path, item in inventory_files.items():
        full_relative = release_prefix + relative_path
        binding = bindings.get(full_relative)
        if binding is None or (item.get("sha256"), item.get("byteLength")) != (
            binding.get("sha256"), binding.get("byteLength")
        ):
            raise ValueError(f"release inventory file identity mismatch: {relative_path}")
        checked_inventory_paths.append(full_relative)
    for required_path in ("heightfield.f32", "manifest.json", "roads/manifest.json", "roads/roads.json"):
        if required_path not in inventory_files:
            raise ValueError(f"release inventory omits required source identity: {required_path}")
    return {
        "passes": True,
        "releaseId": release_id,
        "worldId": ready["worldId"],
        "sceneProfile": ready["sceneProfile"],
        "sourceIdentities": normalized,
        "checkedInventoryPaths": checked_inventory_paths,
        "grid": {"rows": GRID_ROWS, "columns": GRID_COLUMNS, "spacingM": GRID_SPACING_M},
    }


def _read_bound_json(root: Path, relative: str, bindings: dict[str, Any]) -> dict[str, Any]:
    if relative not in bindings:
        raise ValueError(f"required JSON is not frozen: {relative}")
    value = json.loads((root / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {relative}")
    return value


class _JsonStream:
    """Small-buffer JSON token stream; only one feature object is decoded at once."""

    def __init__(self, path: Path) -> None:
        self.stream = path.open("r", encoding="utf-8")
        self.decoder = json.JSONDecoder()
        self.buffer = ""
        self.eof = False

    def _fill(self) -> None:
        if not self.eof:
            chunk = self.stream.read(64 * 1024)
            if chunk:
                self.buffer += chunk
            else:
                self.eof = True

    def _skip_ws(self) -> None:
        while True:
            stripped = self.buffer.lstrip()
            self.buffer = stripped
            if stripped or self.eof:
                return
            self._fill()

    def _peek(self) -> str:
        self._skip_ws()
        if not self.buffer:
            return ""
        return self.buffer[0]

    def _take(self, expected: str) -> None:
        if self._peek() != expected:
            raise ValueError(f"invalid roads JSON structure; expected {expected!r}")
        self.buffer = self.buffer[1:]

    def _decode_one(self) -> Any:
        while True:
            self._skip_ws()
            try:
                value, end = self.decoder.raw_decode(self.buffer)
            except json.JSONDecodeError:
                if self.eof:
                    raise
                self._fill()
                continue
            if end == len(self.buffer) and not self.eof and not isinstance(value, (dict, list, str)):
                self._fill()
                continue
            self.buffer = self.buffer[end:]
            return value

    def _skip_one(self) -> None:
        """Skip a JSON value lexically without retaining an unrelated payload object."""
        first = self._peek()
        if not first:
            raise ValueError("truncated roads JSON value")
        if first in "[{":
            stack: list[str] = []
            quoted = False
            escaped = False
            while True:
                if not self.buffer:
                    if self.eof:
                        raise ValueError("truncated nested roads JSON value")
                    self._fill()
                    continue
                char, self.buffer = self.buffer[0], self.buffer[1:]
                if quoted:
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == '"':
                        quoted = False
                    continue
                if char == '"':
                    quoted = True
                elif char in "[{":
                    stack.append("}" if char == "{" else "]")
                elif char in "]}":
                    if not stack or char != stack.pop():
                        raise ValueError("mismatched roads JSON value delimiters")
                    if not stack:
                        return
        elif first == '"':
            self._decode_one()
        else:
            while True:
                self._skip_ws()
                if not self.buffer:
                    if self.eof:
                        return
                    self._fill()
                    continue
                if self.buffer[0] in ",}":
                    return
                self.buffer = self.buffer[1:]

    def target_feature(self, way_id: int) -> tuple[dict[str, Any], dict[str, int]]:
        self._take("{")
        found_features = False
        selected = None
        counts = {"topLevelMembers": 0, "featuresSeen": 0, "targetWayMatches": 0}
        while True:
            token = self._peek()
            if token == "}":
                self.buffer = self.buffer[1:]
                break
            if counts["topLevelMembers"]:
                self._take(",")
            key = self._decode_one()
            if not isinstance(key, str):
                raise ValueError("roads JSON top-level key is not a string")
            self._take(":")
            counts["topLevelMembers"] += 1
            if key != "features":
                self._skip_one()
                continue
            if found_features:
                raise ValueError("roads JSON repeats its features key")
            found_features = True
            self._take("[")
            while True:
                token = self._peek()
                if token == "]":
                    self.buffer = self.buffer[1:]
                    break
                if counts["featuresSeen"]:
                    self._take(",")
                feature = self._decode_one()
                counts["featuresSeen"] += 1
                if not isinstance(feature, dict):
                    raise ValueError("roads feature is not an object")
                source = feature.get("source")
                if isinstance(source, dict) and source.get("osmId") == way_id:
                    counts["targetWayMatches"] += 1
                    if selected is None:
                        selected = feature
            if self._peek() not in ",}":
                raise ValueError("invalid delimiter after roads features array")
        self._skip_ws()
        if self.buffer or not self.eof:
            # Read the remainder only to confirm there is no non-whitespace suffix.
            while not self.eof:
                self._fill()
                if self.buffer.strip():
                    raise ValueError("trailing content after roads JSON object")
                self.buffer = ""
        if not found_features or selected is None:
            raise ValueError(f"target OSM way {way_id} part was not found")
        return selected, counts

    def close(self) -> None:
        self.stream.close()


def _load_target_feature(path: Path) -> tuple[dict[str, Any], dict[str, int]]:
    stream = _JsonStream(path)
    try:
        return stream.target_feature(78455395)
    finally:
        stream.close()


def _geometry_record(geometry: Any) -> dict[str, Any]:
    import numpy as np
    import shapely

    coordinates = shapely.get_coordinates(geometry)
    area = float(geometry.area)
    length = float(geometry.length)
    finite = bool(
        np.isfinite(coordinates).all()
        and math.isfinite(area)
        and math.isfinite(length)
        and (geometry.is_empty or all(math.isfinite(float(value)) for value in geometry.bounds))
    )
    return {
        "geometryType": geometry.geom_type,
        "isEmpty": bool(geometry.is_empty),
        "isValid": bool(geometry.is_valid),
        "finiteCoordinatesAndMeasures": finite,
        "areaM2": area if math.isfinite(area) else None,
        "lengthM": length if math.isfinite(length) else None,
        "wkbHex": geometry.wkb_hex,
        "wkt": geometry.wkt,
    }


def _require_valid_finite_geometry(geometry: Any, label: str) -> None:
    import numpy as np
    import shapely

    coordinates = shapely.get_coordinates(geometry)
    measures = (float(geometry.area), float(geometry.length))
    bounds = () if geometry.is_empty else tuple(float(value) for value in geometry.bounds)
    if (
        not geometry.is_valid
        or not np.isfinite(coordinates).all()
        or not all(math.isfinite(value) for value in measures + bounds)
    ):
        raise ValueError(f"invalid/nonfinite geometry at {label}")


def _components(geometry: Any) -> list[Any]:
    if geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [geometry]
    if hasattr(geometry, "geoms"):
        return [part for item in geometry.geoms for part in _components(item)]
    return []


def _component_summary(geometry: Any, polygon_parts: list[Any]) -> dict[str, Any]:
    positive_area = math.fsum(float(polygon.area) for polygon in polygon_parts)
    return {
        "componentCount": 0 if geometry.is_empty else len(geometry.geoms) if hasattr(geometry, "geoms") else 1,
        "polygonComponentCount": len(polygon_parts),
        "polygonExteriorVertexCount": sum(len(polygon.exterior.coords) for polygon in polygon_parts),
        "polygonInteriorRingCount": sum(len(polygon.interiors) for polygon in polygon_parts),
        "positivePolygonAreaM2": positive_area if math.isfinite(positive_area) else None,
    }


def _plane_witnesses(
    topology: Any,
    face_xz: Any,
    candidate_y: Any,
    source_xz: Any,
    source_y: Any,
    fragments: list[tuple[int, Any]],
) -> dict[str, Any]:
    import numpy as np

    face_plane = topology._plane_coefficients(np.asarray(face_xz), np.asarray(candidate_y))
    face_matrix = np.column_stack((np.asarray(face_xz), np.ones(3)))
    face_condition = float(np.linalg.cond(face_matrix))
    if not np.isfinite(face_plane).all() or not math.isfinite(face_condition) or face_condition >= 1.0 / np.finfo(np.float64).eps:
        raise ValueError("candidate face plane is nonfinite or ill-conditioned")
    values: list[dict[str, Any]] = []
    zero_contacts = []
    for source_id, geometry in fragments:
        leaves = []

        def collect_leaves(value: Any) -> None:
            if hasattr(value, "geoms") and value.geom_type != "Polygon":
                for child in value.geoms:
                    collect_leaves(child)
            else:
                leaves.append(value)

        collect_leaves(geometry)
        polygons = [leaf for leaf in leaves if leaf.geom_type == "Polygon"]
        for leaf in leaves:
            if leaf.geom_type != "Polygon" and not leaf.is_empty and float(leaf.area) == 0.0:
                zero_contacts.append(
                    {"sourceTriangleId": source_id, "geometry": _geometry_record(leaf)}
                )
        if not polygons:
            continue
        source_plane = topology._plane_coefficients(np.asarray(source_xz[source_id]), np.asarray(source_y[source_id]))
        matrix = np.column_stack((np.asarray(source_xz[source_id]), np.ones(3)))
        condition = float(np.linalg.cond(matrix))
        if not np.isfinite(source_plane).all() or not math.isfinite(condition) or condition >= 1.0 / np.finfo(np.float64).eps:
            raise ValueError(f"source triangle plane {source_id} is nonfinite or ill-conditioned")
        for polygon_index, polygon in enumerate(polygons):
            rings = [("exterior", polygon.exterior)] + [
                (f"interior-{index}", ring) for index, ring in enumerate(polygon.interiors)
            ]
            for ring_name, ring in rings:
                for vertex_index, (x, z) in enumerate(list(ring.coords)[:-1]):
                    candidate_value = float(face_plane @ (x, z, 1.0))
                    source_value = float(source_plane @ (x, z, 1.0))
                    delta = candidate_value - source_value
                    if not all(math.isfinite(value) for value in (candidate_value, source_value, delta)):
                        raise ValueError("nonfinite candidate-minus-source plane evaluation")
                    values.append(
                        {
                            "sourceTriangleId": source_id,
                            "polygonIndex": polygon_index,
                            "ring": ring_name,
                            "ringVertexIndex": vertex_index,
                            "worldXZ": [float(x), float(z)],
                            "candidateY": candidate_value,
                            "sourceY": source_value,
                            "signedDeltaM": delta,
                            "absoluteDeltaM": abs(delta),
                            "candidatePlaneConditionNumber": face_condition,
                            "sourcePlaneConditionNumber": condition,
                        }
                    )
    if not values:
        return {
            "candidateMinusSourcePlaneVertexCount": 0,
            "first": None,
            "minimumSigned": None,
            "maximumSigned": None,
            "minimumAbsolute": None,
            "maximumAbsolute": None,
            "zeroAreaContacts": zero_contacts,
            "candidateFacePlaneConditionNumber": face_condition,
            "candidateFacePlaneCoefficients": face_plane.tolist(),
        }
    first = values[0]
    return {
        "candidateMinusSourcePlaneVertexCount": len(values),
        "first": first,
        "minimumSigned": min(values, key=lambda item: item["signedDeltaM"]),
        "maximumSigned": max(values, key=lambda item: item["signedDeltaM"]),
        "minimumAbsolute": min(values, key=lambda item: item["absoluteDeltaM"]),
        "maximumAbsolute": max(values, key=lambda item: item["absoluteDeltaM"]),
        "zeroAreaContacts": zero_contacts,
        "candidateFacePlaneConditionNumber": face_condition,
        "candidateFacePlaneCoefficients": face_plane.tolist(),
    }


def _read_bytes_at(path: Path, offset: int, length: int) -> bytes:
    with path.open("rb") as stream:
        stream.seek(offset)
        value = stream.read(length)
    if len(value) != length:
        raise ValueError(f"short read from {path} at byte {offset}")
    return value


def _target_geometry(feature: dict[str, Any], line_point_tangent: Any, candidate_config: Any) -> tuple[Any, dict[str, Any]]:
    import numpy as np
    from shapely.geometry import LineString, box

    if feature.get("estimatedWidthM") != 6 or feature.get("groundAssumption") != (
        "ground_assumed_from_absent_or_explicit_no_vertical_tags"
    ):
        raise ValueError("target way width or ground eligibility differs from frozen build contract")
    parts = feature.get("centerlinePartsXZ")
    if not isinstance(parts, list) or not parts or not isinstance(parts[0], list):
        raise ValueError("target way has no exact part 0 centerline")
    part = [[float(point[0]), float(point[1])] for point in parts[0]]
    if len(part) < 2 or not all(math.isfinite(value) for point in part for value in point):
        raise ValueError("target way part 0 is malformed or nonfinite")
    lengths = [math.dist(first, second) for first, second in zip(part, part[1:], strict=False)]
    cumulative = [0.0]
    for length in lengths:
        if not math.isfinite(length) or length <= 0:
            raise ValueError("target way has a zero/nonfinite source segment")
        cumulative.append(cumulative[-1] + length)
    start = float(candidate_config.recipe["assessment_station_start_m"])
    end = float(candidate_config.recipe["assessment_station_end_m"])
    buffer_m = float(candidate_config.recipe["influence_buffer_m"])
    if (start, end, buffer_m) != (140.0, 155.0, 35.0):
        raise ValueError("target stations or influence buffer differ from frozen config")
    target_points = [line_point_tangent(part, start)[0]]
    inside_breaks = [
        (tuple(part[index]), station)
        for index, station in enumerate(cumulative)
        if start < station < end
    ]
    target_points.extend(point for point, _station in inside_breaks)
    target_points.append(line_point_tangent(part, end)[0])
    target_line = LineString(target_points)
    influence = target_line.buffer(buffer_m)
    bounds = tuple(candidate_config.bounds_global_xz_m)
    domain = box(*bounds)
    _require_valid_finite_geometry(influence, "reconstructed influence buffer")
    _require_valid_finite_geometry(domain, "fixed candidate domain")
    if not domain.covers(influence):
        raise ValueError("reconstructed fixed influence escapes bound candidate domain")
    return influence, {
        "wayId": 78455395,
        "partIndex": 0,
        "partVertexCount": len(part),
        "totalPartLengthM": cumulative[-1],
        "stationWindowM": [start, end],
        "sourceBreakCountInsideWindow": len(inside_breaks),
        "sourceBreaksInsideWindow": [
            {"stationM": station, "worldXZ": list(point)} for point, station in inside_breaks
        ],
        "targetLinePointCount": len(target_points),
        "targetLineWkbHex": target_line.wkb_hex,
        "influenceBufferDistanceM": buffer_m,
        "bufferUsesShapelyDefaultDiscretization": True,
        "influenceGeometry": _geometry_record(influence),
        "outsideGeometry": _geometry_record(domain.difference(influence)),
        "domainBoundsGlobalXZ": list(bounds),
    }


def _read_face_buffers(root: Path, config: Any, bindings: dict[str, Any]) -> dict[str, Any]:
    import numpy as np

    prefix = f"{BUILD_ROOT}/"
    local_path = root / f"{prefix}serialized-local-positions.xyz.f32"
    world_path = root / f"{prefix}serialized-world-positions.xyz.f64"
    index_path = root / f"{prefix}serialized-indices.u32"
    candidate_y_path = root / f"{prefix}serialized-candidate-y.f32"
    source_y_path = root / f"{prefix}serialized-source-y.f32"
    construction_path = root / f"{prefix}construction-world-xz.f64"
    vertex_count = bindings[f"{prefix}serialized-local-positions.xyz.f32"]["byteLength"] // 12
    face_count = bindings[f"{prefix}serialized-indices.u32"]["byteLength"] // 12
    if (
        vertex_count * 12 != bindings[f"{prefix}serialized-local-positions.xyz.f32"]["byteLength"]
        or vertex_count * 24 != bindings[f"{prefix}serialized-world-positions.xyz.f64"]["byteLength"]
        or vertex_count * 4 != bindings[f"{prefix}serialized-candidate-y.f32"]["byteLength"]
        or vertex_count * 4 != bindings[f"{prefix}serialized-source-y.f32"]["byteLength"]
        or face_count * 12 != bindings[f"{prefix}serialized-indices.u32"]["byteLength"]
        or face_count <= TARGET_FACE_ID
    ):
        raise ValueError("serialized buffers have incompatible exact lengths")
    import struct

    vertex_ids = struct.unpack("<III", _read_bytes_at(index_path, TARGET_FACE_ID * 12, 12))
    if any(index >= vertex_count for index in vertex_ids):
        raise ValueError("serialized face 19669 references a missing position")
    stored_xyz = np.asarray(
        [np.frombuffer(_read_bytes_at(local_path, index * 12, 12), dtype="<f4") for index in vertex_ids],
        dtype="<f4",
    )
    saved_world_xyz = np.asarray(
        [np.frombuffer(_read_bytes_at(world_path, index * 24, 24), dtype="<f8") for index in vertex_ids],
        dtype="<f8",
    )
    saved_candidate_y = np.asarray(
        [np.frombuffer(_read_bytes_at(candidate_y_path, index * 4, 4), dtype="<f4")[0] for index in vertex_ids],
        dtype="<f4",
    )
    saved_source_y = np.asarray(
        [np.frombuffer(_read_bytes_at(source_y_path, index * 4, 4), dtype="<f4")[0] for index in vertex_ids],
        dtype="<f4",
    )
    decoded_world = config.frame.decode_xyz_to_world64(stored_xyz)
    if not np.array_equal(decoded_world, saved_world_xyz):
        raise ValueError("face world buffer does not exactly match decoded stored local XYZ")
    if not np.array_equal(stored_xyz[:, 1], saved_candidate_y) or not np.array_equal(
        saved_world_xyz[:, 1], saved_candidate_y.astype(np.float64)
    ):
        raise ValueError("face candidate Y differs between stored, candidate-Y and world buffers")
    construction_xz = np.asarray(
        [np.frombuffer(_read_bytes_at(construction_path, index * 16, 16), dtype="<f8") for index in vertex_ids],
        dtype="<f8",
    )
    face_xz = saved_world_xyz[:, (0, 2)]
    return {
        "faceId": TARGET_FACE_ID,
        "faceCount": face_count,
        "vertexCount": vertex_count,
        "vertexIds": list(vertex_ids),
        "storedLocalXYZF32": stored_xyz.tolist(),
        "decodedWorldXYZF64": decoded_world.tolist(),
        "savedWorldXYZF64": saved_world_xyz.tolist(),
        "candidateHeightsF32": saved_candidate_y.tolist(),
        "sourceHeightsF32": saved_source_y.tolist(),
        "storedWorldXZ": face_xz.tolist(),
        "constructionWorldXZSecondaryOnly": construction_xz.tolist(),
        "exactDecodedWorldMatchesSaved": True,
        "candidateYBuffersMatch": True,
        "sourceYFromSerializedBufferOnly": True,
    }


def _source_triangles_for_face(
    face: Any, heights_path: Path, heightfield_sha256: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    import numpy as np
    from shapely.geometry import Polygon, box
    from shapely.strtree import STRtree

    if _sha256(heights_path) != heightfield_sha256:
        raise ValueError("heightfield hash changed before local-node access")
    heights = np.memmap(
        heights_path,
        dtype="<f4",
        mode="r",
        shape=(GRID_ROWS, GRID_COLUMNS),
        order="C",
    )
    xmin, zmin, xmax, zmax = face.bounds
    grid_min_column = (xmin + GRID_WIDTH_M / 2.0) / GRID_SPACING_M
    grid_max_column = (xmax + GRID_WIDTH_M / 2.0) / GRID_SPACING_M
    grid_min_row = (zmin + GRID_DEPTH_M / 2.0) / GRID_SPACING_M
    grid_max_row = (zmax + GRID_DEPTH_M / 2.0) / GRID_SPACING_M
    first_column = max(INDEX_FIRST_COLUMN, math.floor(grid_min_column) - 1)
    last_column = min(INDEX_LAST_COLUMN - 1, math.floor(grid_max_column) + 1)
    first_row = max(INDEX_FIRST_ROW, math.floor(grid_min_row) - 1)
    last_row = min(INDEX_LAST_ROW - 1, math.floor(grid_max_row) + 1)
    if first_column > last_column or first_row > last_row:
        raise ValueError("face envelope has no source cells within the frozen index bounds")
    index_bounds = (
        INDEX_FIRST_COLUMN * GRID_SPACING_M - GRID_WIDTH_M / 2.0,
        INDEX_FIRST_ROW * GRID_SPACING_M - GRID_DEPTH_M / 2.0,
        INDEX_LAST_COLUMN * GRID_SPACING_M - GRID_WIDTH_M / 2.0,
        INDEX_LAST_ROW * GRID_SPACING_M - GRID_DEPTH_M / 2.0,
    )
    if not box(*index_bounds).covers(face):
        raise ValueError("serialized face escapes original source index bounds")
    candidates: list[dict[str, Any]] = []
    node_values: dict[tuple[int, int], float] = {}

    def node(row: int, column: int) -> float:
        key = (row, column)
        if key not in node_values:
            value = float(heights[row, column])
            if not math.isfinite(value):
                raise ValueError(f"nonfinite source heightfield node {key}")
            node_values[key] = value
        return node_values[key]

    cells_examined = []
    for row in range(first_row, last_row + 1):
        z0 = row * GRID_SPACING_M - GRID_DEPTH_M / 2.0
        z1 = z0 + GRID_SPACING_M
        for column in range(first_column, last_column + 1):
            x0 = column * GRID_SPACING_M - GRID_WIDTH_M / 2.0
            x1 = x0 + GRID_SPACING_M
            cell_id = row * (GRID_COLUMNS - 1) + column
            triangle_specs = (
                (
                    2 * cell_id,
                    [(x0, z0), (x1, z0), (x0, z1)],
                    [(row, column), (row, column + 1), (row + 1, column)],
                ),
                (
                    2 * cell_id + 1,
                    [(x1, z1), (x0, z1), (x1, z0)],
                    [(row + 1, column + 1), (row + 1, column), (row, column + 1)],
                ),
            )
            cells_examined.append({"row": row, "column": column, "cellId": cell_id})
            for source_id, coordinates, nodes in triangle_specs:
                polygon = Polygon(coordinates)
                if polygon.intersects(face):
                    y_values = [node(node_row, node_column) for node_row, node_column in nodes]
                    candidates.append(
                        {
                            "sourceTriangleId": source_id,
                            "row": row,
                            "column": column,
                            "nodeIndices": [list(item) for item in nodes],
                            "coordinatesXZ": coordinates,
                            "heightsY": y_values,
                            "polygon": polygon,
                        }
                    )
    candidates.sort(key=lambda item: item["sourceTriangleId"])
    if not candidates:
        raise ValueError("no queried source triangles intersect the saved face")
    candidate_polygons = [item["polygon"] for item in candidates]
    tree = STRtree(candidate_polygons)
    queried_indexes = sorted(int(value) for value in tree.query(face, predicate="intersects"))
    if queried_indexes != list(range(len(candidates))):
        candidates = [candidates[index] for index in queried_indexes]
    if not candidates:
        raise ValueError("production-equivalent source STRtree query returned no candidates")
    final = candidates
    heights._mmap.close()
    return final, {
        "sourceReadScope": "read-only memmap nodes for envelope cells whose source triangles intersect face",
        "heightfieldSha256VerifiedBeforeAccess": heightfield_sha256,
        "gridContract": {
            "rows": GRID_ROWS,
            "columns": GRID_COLUMNS,
            "spacingM": GRID_SPACING_M,
            "widthM": GRID_WIDTH_M,
            "depthM": GRID_DEPTH_M,
            "indexRows": [INDEX_FIRST_ROW, INDEX_LAST_ROW],
            "indexColumns": [INDEX_FIRST_COLUMN, INDEX_LAST_COLUMN],
        },
        "faceEnvelopeWorldXZ": [xmin, zmin, xmax, zmax],
        "closedEnvelopeCellRangeInclusive": {
            "rows": [first_row, last_row],
            "columns": [first_column, last_column],
        },
        "boundaryTouchingNeighborCellsIncluded": True,
        "cellsExamined": cells_examined,
        "queriedTriangleCount": len(final),
        "queriedSourceTriangleIds": [item["sourceTriangleId"] for item in final],
        "queriedSourceTriangles": [
            {
                "sourceTriangleId": item["sourceTriangleId"],
                "row": item["row"],
                "column": item["column"],
                "nodeIndices": item["nodeIndices"],
                "coordinatesXZ": item["coordinatesXZ"],
                "heightsY": item["heightsY"],
                "geometry": _geometry_record(item["polygon"]),
            }
            for item in final
        ],
        "heightfieldNodesRead": [
            {"row": row, "column": column, "heightY": value}
            for (row, column), value in sorted(node_values.items())
        ],
        "noOtherSourceTriangleCanIntersect": (
            "all cells intersecting or touching the face closed envelope were enumerated "
            "inside the production SourceOverlapIndex row/column bounds; STRtree "
            "predicate=intersects selected the exact source triangle set"
        ),
    }


def _write_fragment(stream: Any, value: dict[str, Any]) -> None:
    stream.write(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")
    stream.flush()
    os.fsync(stream.fileno())


def _worker(
    root: Path,
    manifest_path: Path,
    bindings: dict[str, Any],
    evidence: Path,
    runtime_identity: dict[str, Any],
) -> int:
    import numpy as np
    import shapely
    from shapely.geometry import Polygon

    started = time.perf_counter()
    report: dict[str, Any] = {
        "issueId": ISSUE,
        "diagnosticOrdinal": 2,
        "targetFaceId": TARGET_FACE_ID,
        "status": "INCONCLUSIVE",
        "candidateBuilt": False,
        "candidateEligibleForServing": False,
        "candidateOutputChanged": False,
        "fragmentEvidence": f"{EVIDENCE_RELATIVE}/source-fragments.jsonl",
    }
    _write_json(evidence / "report.json", report)
    _write_json(evidence / "progress.json", {"stage": "worker-started", "status": "IN_PROGRESS"})

    def checkpoint(stage: str, status: str = "COMPLETE", **values: Any) -> None:
        report["currentStage"] = stage
        report["stageStatus"] = status
        report.update(values)
        _write_json(evidence / "report.json", report)
        _write_json(evidence / "progress.json", {"stage": stage, "status": status, **values})

    try:
        sys.path.insert(0, str(root / "pipeline"))
        from shapely.geometry import box
        from torquay_pipeline import road_surface_topology as topology
        from torquay_pipeline import teignmouth_corridor_continuation as continuation
        from torquay_pipeline.road_surface import _line_point_tangent
        from torquay_pipeline.teignmouth_float32_candidate import (
            EXPECTED_BOUNDS,
            load_candidate_config,
        )

        local_sources = []
        for module in list(sys.modules.values()):
            filename = getattr(module, "__file__", None)
            if filename is None:
                continue
            source_path = Path(filename).resolve()
            try:
                source_relative = source_path.relative_to(root / "pipeline/torquay_pipeline").as_posix()
            except ValueError:
                continue
            relative = f"pipeline/torquay_pipeline/{source_relative}"
            if source_path.suffix == ".py":
                if relative not in bindings:
                    raise ValueError(f"imported local helper missing from frozen manifest: {relative}")
                local_sources.append(relative)
        report["importedLocalHelperBindings"] = sorted(set(local_sources))
        report["runtimeIdentity"] = runtime_identity
        report["environment"] = runtime_identity["actual"]
        report["inputManifestSha256"] = _sha256(manifest_path)
        report["frozenInputCount"] = len(bindings)
        checkpoint("bound-build-evidence")

        build_report = _read_bound_json(root, f"{BUILD_ROOT}/build-report.json", bindings)
        if build_report.get("status") != "BLOCKED_EXCEPTION":
            raise ValueError("bound build-2 report does not record the expected blocking exception")
        error = build_report.get("primaryError", {})
        expected_error = "face=19669"
        if (
            error.get("type") != "TopologyError"
            or expected_error not in error.get("message", "")
            or f"expectedOverlayArea={EXPECTED_CLIP_AREA_M2:.17g}" not in error.get("message", "")
        ):
            raise ValueError("bound build-2 face-19669 error differs from approved diagnostic target")
        report["build2Failure"] = {
            "type": error["type"],
            "message": error["message"],
            "recordedFaceAreaM2": EXPECTED_FACE_AREA_M2,
            "recordedExpectedClipAreaM2": EXPECTED_CLIP_AREA_M2,
            "recordedFilteredCoveredAreaM2": 0.0,
        }
        release_identity = _verify_release_identity(
            root, bindings, build_report, "616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a"
        )
        report["releaseIdentity"] = release_identity
        checkpoint("release-identities-verified")

        candidate_config = load_candidate_config(root / "config/road-surface-teignmouth-float32.json")
        continuation.load_continuation_config(
            root / "config/road-surface-teignmouth-corridor-continuation.json"
        )
        if tuple(candidate_config.bounds_global_xz_m) != tuple(EXPECTED_BOUNDS):
            raise ValueError("exact frozen candidate domain helper does not match")
        report["frame"] = {
            "originXYZM": list(candidate_config.frame.origin_xyz_m),
            "frameVersion": candidate_config.frame.version,
            "candidateConfigExactParserPassed": True,
            "continuationConfigExactParserPassed": True,
        }

        road_relative = next(
            (
                path
                for path in bindings
                if path.endswith(f"/releases/{candidate_config.release_id}/roads/roads.json")
            ),
            None,
        )
        if road_relative is None:
            raise ValueError("manifest has no release-bound target roads payload")
        road_path = root / road_relative
        road_sha = _sha256(road_path)
        build_sources = build_report["stages"]["frozenInputs"]["sourceHashes"]
        source_descriptor = build_sources.get("roads/roads.json")
        if source_descriptor is None or source_descriptor.get("sha256") != road_sha:
            raise ValueError("roads payload hash differs from build-2 source identity")
        if bindings[road_relative]["sha256"] != road_sha:
            raise ValueError("roads payload is not bound to the exact manifest hash")
        feature, feature_counts = _load_target_feature(road_path)
        if _sha256(road_path) != road_sha:
            raise ValueError("roads payload changed during streaming target extraction")
        if feature.get("source", {}).get("osmId") != 78455395:
            raise ValueError("streaming JSON target identity differs")
        influence, clip_inputs = _target_geometry(feature, _line_point_tangent, candidate_config)
        outside_geometry = box(*candidate_config.bounds_global_xz_m).difference(influence)
        _require_valid_finite_geometry(outside_geometry, "outside-influence clip")
        clip_inputs["streamingFeatureCounts"] = feature_counts
        clip_inputs["geometryOperationOrder"] = (
            "LineString(target sections).buffer(35.0) using Shapely default; "
            "box(*EXPECTED_BOUNDS).difference(influence)"
        )
        _write_json(evidence / "clip-reconstruction.json", clip_inputs)
        report["clipReconstruction"] = {
            "passesBoundsAndSourceIdentity": True,
            "targetFeatureCounts": feature_counts,
            "sourceBreakCountInsideWindow": clip_inputs["sourceBreakCountInsideWindow"],
            "influenceAreaM2": influence.area,
            "outsideClipBounds": outside_geometry.bounds,
            "outsideClipGeometryType": outside_geometry.geom_type,
        }
        checkpoint("clip-reconstructed")

        face_buffers = _read_face_buffers(root, candidate_config, bindings)
        face_xz = np.asarray(face_buffers["storedWorldXZ"], dtype=np.float64)
        candidate_y = np.asarray(face_buffers["candidateHeightsF32"], dtype=np.float64)
        face = Polygon(face_xz)
        _require_valid_finite_geometry(face, "serialized face 19669")
        face_clip = face.intersection(outside_geometry)
        _require_valid_finite_geometry(face_clip, "serialized face outside-influence intersection")
        expected_area = float(face_clip.area)
        report["face"] = {
            **face_buffers,
            "geometry": _geometry_record(face),
            "expectedOutsideClip": _geometry_record(face_clip),
            "expectedClipAreaM2": expected_area,
            "expectedFaceAreaMatchesBuild2": float(face.area) == EXPECTED_FACE_AREA_M2,
            "expectedClipAreaMatchesBuild2": expected_area == EXPECTED_CLIP_AREA_M2,
        }
        if float(face.area) != EXPECTED_FACE_AREA_M2 or expected_area != EXPECTED_CLIP_AREA_M2:
            raise ValueError(
                "exact face/clip reproduction failed; no source-set analysis or substitute geometry permitted"
            )
        _write_json(evidence / "face-reconstruction.json", report["face"])
        checkpoint("serialized-face-and-clip-reproduced")

        height_relative = next(
            (
                path
                for path in bindings
                if path.endswith(f"/releases/{candidate_config.release_id}/heightfield.f32")
            ),
            None,
        )
        if height_relative is None:
            raise ValueError("manifest has no release-bound heightfield")
        height_descriptor = build_sources.get("heightfield.f32")
        if height_descriptor is None or bindings[height_relative]["sha256"] != height_descriptor.get("sha256"):
            raise ValueError("heightfield binding differs from original build-2 release identity")
        source_triangles, source_report = _source_triangles_for_face(
            face, root / height_relative, height_descriptor["sha256"]
        )
        source_polygons = [item["polygon"] for item in source_triangles]
        source_xz = {
            item["sourceTriangleId"]: np.asarray(item["coordinatesXZ"], dtype=np.float64)
            for item in source_triangles
        }
        source_y = {
            item["sourceTriangleId"]: np.asarray(item["heightsY"], dtype=np.float64)
            for item in source_triangles
        }
        _write_json(evidence / "source-query.json", source_report)
        checkpoint("local-source-triangles-loaded")

        fragment_path = evidence / "source-fragments.jsonl"
        production_filtered_area = 0.0
        positive_areas: list[float] = []
        discarded_positive_areas: list[float] = []
        positive_geometries = []
        alt_fragments: list[tuple[int, Any]] = []
        all_prod_fragments: list[tuple[int, Any]] = []
        completed_fragments = 0
        with fragment_path.open("w", encoding="utf-8") as fragment_stream:
            for item in source_triangles:
                completed_fragments += 1
                source_id = item["sourceTriangleId"]
                source_polygon = item["polygon"]
                production_intersection = face.intersection(source_polygon)
                production_clipped = (
                    production_intersection.intersection(outside_geometry)
                    if not production_intersection.is_empty
                    else production_intersection
                )
                alternative_clipped = (
                    face_clip.intersection(source_polygon) if not face_clip.is_empty else face_clip
                )
                order_symmetric_difference = production_clipped.symmetric_difference(alternative_clipped)
                area_value = float(production_clipped.area)
                area_finite = math.isfinite(area_value)
                polygon_parts = topology._polygon_parts(production_clipped)
                positive_area_value = math.fsum(float(poly.area) for poly in polygon_parts)
                positive_area_finite = math.isfinite(positive_area_value)
                positive_area = positive_area_value if positive_area_finite else None
                discarded = (
                    production_clipped.is_empty
                    or not area_finite
                    or production_clipped.area <= AREA_FILTER_M2
                )
                if not discarded:
                    production_filtered_area += area_value
                if positive_area_finite and positive_area_value > 0.0:
                    positive_areas.append(positive_area_value)
                    positive_geometries.extend(polygon_parts)
                    if discarded:
                        discarded_positive_areas.append(positive_area_value)
                all_prod_fragments.append((source_id, production_clipped))
                if not alternative_clipped.is_empty and alternative_clipped.area > 0.0:
                    alt_fragments.append((source_id, alternative_clipped))
                _write_fragment(
                    fragment_stream,
                    {
                        "sourceTriangleId": source_id,
                        "sourceCell": {"row": item["row"], "column": item["column"]},
                        "sourceTriangle": _geometry_record(source_polygon),
                        "productionIntersection": _geometry_record(production_intersection),
                        "productionClipOrder": "face.intersection(source_triangle).intersection(outside_geometry)",
                        "productionClippedResult": _geometry_record(production_clipped),
                        "alternativeClippedResult": _geometry_record(alternative_clipped),
                        "alternativeClipOrder": "face.intersection(outside_geometry).intersection(source_triangle)",
                        "components": _component_summary(production_clipped, polygon_parts),
                        "frozenAreaFilterM2": AREA_FILTER_M2,
                        "discardedByFrozenInclusiveAreaFilter": discarded,
                        "positiveAreaDiscardedM2": (
                            positive_area if positive_area is not None and positive_area > 0 and discarded else 0.0
                        ),
                        "orderSymmetricDifference": _geometry_record(order_symmetric_difference),
                    },
                )
                _require_valid_finite_geometry(production_intersection, f"source {source_id} face intersection")
                _require_valid_finite_geometry(production_clipped, f"source {source_id} production clip")
                _require_valid_finite_geometry(alternative_clipped, f"source {source_id} alternate clip")
                _require_valid_finite_geometry(order_symmetric_difference, f"source {source_id} clip-order difference")
                checkpoint(
                    "source-fragment-enumeration",
                    "IN_PROGRESS",
                    completedSourceTriangles=completed_fragments,
                    currentSourceTriangleId=source_id,
                )
        # Keep exact query order distinct from the positive-area subset.
        fragment_count = completed_fragments
        positive_union = shapely.union_all(positive_geometries) if positive_geometries else Polygon()
        _require_valid_finite_geometry(positive_union, "positive clipped-fragment union")
        positive_sum = sum(positive_areas)
        positive_fsum = math.fsum(positive_areas)
        discarded_fsum = math.fsum(discarded_positive_areas)
        union_uncovered = face_clip.difference(positive_union)
        union_excess = positive_union.difference(face_clip)
        union_symmetric = positive_union.symmetric_difference(face_clip)
        _require_valid_finite_geometry(union_uncovered, "expected clip minus positive-fragment union")
        _require_valid_finite_geometry(union_excess, "positive-fragment union minus expected clip")
        _require_valid_finite_geometry(union_symmetric, "positive-fragment union symmetric difference")

        # Independently inspect the original source partition only within the expected clip.
        source_union = shapely.union_all(source_polygons)
        _require_valid_finite_geometry(source_union, "queried source-triangle union")
        source_union_in_clip = source_union.intersection(face_clip)
        _require_valid_finite_geometry(source_union_in_clip, "source coverage within expected clip")
        source_gap = face_clip.difference(source_union_in_clip)
        _require_valid_finite_geometry(source_gap, "expected clip source-coverage gap")
        source_intersections_in_clip = []
        for source_id, source_polygon in zip(
            (item["sourceTriangleId"] for item in source_triangles), source_polygons, strict=True
        ):
            intersection_in_clip = source_polygon.intersection(face_clip)
            _require_valid_finite_geometry(
                intersection_in_clip, f"source {source_id} intersection within expected clip"
            )
            source_intersections_in_clip.append(intersection_in_clip)
        source_coverage_sum_in_clip = math.fsum(
            float(intersection.area) for intersection in source_intersections_in_clip
        )
        source_overlap_area_in_clip = source_coverage_sum_in_clip - float(source_union_in_clip.area)
        if not all(
            math.isfinite(value)
            for value in (
                source_coverage_sum_in_clip,
                source_overlap_area_in_clip,
                production_filtered_area,
            )
        ):
            raise ValueError("source coverage/overlap or production area summary is nonfinite")
        source_pair_overlaps = []
        for first_index, first in enumerate(source_polygons):
            if not first.intersects(face_clip):
                continue
            for second_index in range(first_index + 1, len(source_polygons)):
                second = source_polygons[second_index]
                if not second.intersects(face_clip) or not first.intersects(second):
                    continue
                first_second = first.intersection(second)
                _require_valid_finite_geometry(first_second, "pairwise source triangle intersection")
                overlap = first_second.intersection(face_clip)
                if overlap.area > 0.0:
                    _require_valid_finite_geometry(overlap, "pairwise source overlap inside expected clip")
                    source_pair_overlaps.append(
                        {
                            "sourceTriangleIds": [
                                source_triangles[first_index]["sourceTriangleId"],
                                source_triangles[second_index]["sourceTriangleId"],
                            ],
                            "overlap": _geometry_record(overlap),
                        }
                    )

        plane_extrema = _plane_witnesses(
            topology,
            face_xz,
            candidate_y,
            source_xz,
            source_y,
            all_prod_fragments,
        )
        filtered_residual = production_filtered_area - expected_area
        filtered_tolerance = max(AREA_FILTER_M2, expected_area * 1e-10)
        original_failure_reproduced = production_filtered_area == 0.0
        exact_reproduction = (
            float(face.area) == EXPECTED_FACE_AREA_M2
            and expected_area == EXPECTED_CLIP_AREA_M2
            and original_failure_reproduced
            and fragment_count == len(source_triangles)
        )
        aggregate_geometries = {
            "positiveFragmentUnion": positive_union,
            "expectedClipMinusPositiveUnion": union_uncovered,
            "positiveUnionMinusExpectedClip": union_excess,
            "positiveUnionSymmetricDifferenceExpectedClip": union_symmetric,
            "queriedSourceCoverageWithinExpectedClip": source_union_in_clip,
            "sourceCoverageGapWithinExpectedClip": source_gap,
        }
        for label, geometry in aggregate_geometries.items():
            _require_valid_finite_geometry(geometry, label)
        alternative_union = (
            shapely.union_all([geom for _source_id, geom in alt_fragments])
            if alt_fragments
            else Polygon()
        )
        _require_valid_finite_geometry(alternative_union, "alternative-order positive fragment union")
        clip_order_union_difference = positive_union.symmetric_difference(alternative_union)
        _require_valid_finite_geometry(
            clip_order_union_difference, "production/alternative positive-union symmetric difference"
        )
        if not exact_reproduction:
            diagnostic_classification = "INCONCLUSIVE_EXACT_REPRODUCTION_FAILED"
        elif source_gap.area > 0.0 or source_overlap_area_in_clip > 0.0:
            diagnostic_classification = "SOURCE_PARTITION_GAP_OR_OVERLAP"
        elif clip_order_union_difference.area > 0.0:
            diagnostic_classification = "CLIPPING_ORDER_ARITHMETIC_MISMATCH"
        elif (
            production_filtered_area == 0.0
            and discarded_fsum > 0.0
            and union_symmetric.area == 0.0
        ):
            diagnostic_classification = "CONSISTENT_WITH_PER_FRAGMENT_DISCARD"
        else:
            diagnostic_classification = "INCONCLUSIVE_OTHER_GEOMETRY_RELATION"
        report.update(
            {
                "status": "COMPLETE_DIAGNOSTIC_OBSERVATION" if exact_reproduction else "INCONCLUSIVE",
                "diagnosticClassification": diagnostic_classification,
                "exactFaceClipAndFilteredFailureReproduced": exact_reproduction,
                "fragmentCount": fragment_count,
                "productionFilteredAccumulatedAreaM2": production_filtered_area,
                "productionExpectedClipAreaM2": expected_area,
                "productionFilteredResidualM2": filtered_residual,
                "unchangedProductionResidualToleranceM2": filtered_tolerance,
                "unchangedProductionResidualWithinTolerance": abs(filtered_residual) <= filtered_tolerance,
                "unfilteredOrdinaryPositiveAreaSumM2": positive_sum,
                "unfilteredFsumPositiveAreaM2": positive_fsum,
                "sumOfDiscardedPositiveAreaM2": discarded_fsum,
                "positiveFragmentUnion": _geometry_record(positive_union),
                "summedPositiveAreaMinusUnionAreaM2": positive_fsum - float(positive_union.area),
                "expectedClipMinusPositiveUnion": _geometry_record(union_uncovered),
                "positiveUnionMinusExpectedClip": _geometry_record(union_excess),
                "positiveUnionSymmetricDifferenceExpectedClip": _geometry_record(union_symmetric),
                "sourcePartitionWithinExpectedClip": {
                    "queriedSourceTriangleUnion": _geometry_record(source_union),
                    "queriedSourceCoverageWithinExpectedClip": _geometry_record(source_union_in_clip),
                    "expectedClipMinusSourceCoverageGap": _geometry_record(source_gap),
                    "sourceTriangleIntersectionAreaSumWithinClipM2": source_coverage_sum_in_clip,
                    "sourceUnionAreaWithinClipM2": float(source_union_in_clip.area),
                    "summedSourceAreaMinusUnionWithinClipM2": source_overlap_area_in_clip,
                    "positiveAreaPairwiseSourceOverlaps": source_pair_overlaps,
                    "pairwiseOverlapCount": len(source_pair_overlaps),
                },
                "productionVersusAlternativeClipOrder": {
                    "production": "face.intersection(source_triangle).intersection(outside_geometry)",
                    "alternative": "face.intersection(outside_geometry).intersection(source_triangle)",
                    "allSourceTriangleResultsPersisted": True,
                    "positiveAreaAlternativeUnion": _geometry_record(alternative_union),
                    "productionPositiveUnionSymmetricDifferenceAlternative": _geometry_record(
                        clip_order_union_difference
                    ),
                    "notAnAcceptanceAlternative": True,
                },
                "candidateMinusSourcePlaneExtrema": plane_extrema,
                "inputProvenance": {
                    "inputManifestSha256": _sha256(manifest_path),
                    "buildReportSha256": bindings[f"{BUILD_ROOT}/build-report.json"]["sha256"],
                    "sourceTriangleIds": [item["sourceTriangleId"] for item in source_triangles],
                    "heightfieldReadScope": source_report["sourceReadScope"],
                },
                "partialEvidence": {
                    "fragmentJsonl": f"{EVIDENCE_RELATIVE}/source-fragments.jsonl",
                    "clipReconstruction": f"{EVIDENCE_RELATIVE}/clip-reconstruction.json",
                    "faceReconstruction": f"{EVIDENCE_RELATIVE}/face-reconstruction.json",
                    "sourceQuery": f"{EVIDENCE_RELATIVE}/source-query.json",
                },
                "omissions": [
                    "No full candidate loader, assembly, mesh build, all-face scan, new source acquisition, buildings, product or browser work.",
                    "The observation does not authorize a filter/tolerance change, candidate correction, or serving eligibility.",
                ],
            }
        )
        if not exact_reproduction:
            report["status"] = "INCONCLUSIVE"
        _write_json(evidence / "report.json", report)
        _write_json(evidence / "progress.json", {"stage": "diagnostic-complete", "status": report["status"], "fragmentCount": fragment_count})
        return 0 if exact_reproduction else 2
    except Exception as exc:
        report["status"] = "INCONCLUSIVE"
        report["primaryError"] = {"type": type(exc).__name__, "message": str(exc)}
        report["traceback"] = traceback.format_exc()
        report["partialEvidencePreserved"] = True
        _write_json(evidence / "report.json", report)
        _write_json(
            evidence / "progress.json",
            {"stage": "worker-stopped", "status": "INCONCLUSIVE", "errorType": type(exc).__name__},
        )
        return 2
    finally:
        report["workerElapsedSeconds"] = time.perf_counter() - started
        if (evidence / "report.json").exists():
            try:
                saved = json.loads((evidence / "report.json").read_text(encoding="utf-8"))
                saved["workerElapsedSeconds"] = report["workerElapsedSeconds"]
                _write_json(evidence / "report.json", saved)
            except Exception:
                pass


class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def _working_set(pid: int) -> tuple[int | None, str]:
    if os.name != "nt":
        return None, "unavailable: GetProcessMemoryInfo is Windows-only"
    try:
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        open_process = kernel32.OpenProcess
        open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        open_process.restype = wintypes.HANDLE
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL
        get_info = psapi.GetProcessMemoryInfo
        get_info.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_PROCESS_MEMORY_COUNTERS),
            wintypes.DWORD,
        ]
        get_info.restype = wintypes.BOOL
        handle = open_process(0x0400 | 0x0010, False, pid)
        if not handle:
            return None, f"unavailable: OpenProcess winerror={ctypes.get_last_error()}"
        try:
            counters = _PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(counters)
            if not get_info(handle, ctypes.byref(counters), counters.cb):
                return None, f"unavailable: GetProcessMemoryInfo winerror={ctypes.get_last_error()}"
            return int(counters.PeakWorkingSetSize), "measured via GetProcessMemoryInfo"
        finally:
            close_handle(handle)
    except Exception as exc:
        return None, f"unavailable: {type(exc).__name__}: {exc}"


def main(argv: list[str] | None = None) -> int:
    started = time.perf_counter()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--worker-token", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    expected_python = (root / "pipeline/.venv/Scripts/python.exe").resolve()
    if Path(sys.executable).resolve() != expected_python:
        parser.error("use exactly pipeline/.venv/Scripts/python.exe")
    manifest_path = args.input_manifest.resolve(strict=True)
    if manifest_path != (root / MANIFEST_RELATIVE).resolve():
        parser.error(f"manifest must be the fixed {MANIFEST_RELATIVE}")
    evidence = root / EVIDENCE_RELATIVE
    if args.worker:
        if not args.worker_token or not (evidence / "attempt.json").is_file():
            parser.error("worker requires parent-created attempt and one-time token")
        attempt = json.loads((evidence / "attempt.json").read_text(encoding="utf-8"))
        if hashlib.sha256(args.worker_token.encode()).hexdigest() != attempt.get("workerTokenSha256"):
            parser.error("worker token is not parent-authorized")
        try:
            _manifest, bindings, preservation = _verify_inputs(
                root, manifest_path, attempt["inputManifestSha256"]
            )
            if not preservation["passes"]:
                raise ValueError(f"worker pre-run preservation mismatch: {preservation['changed'][:12]}")
            runtime_identity = _runtime_identity(root, bindings)
            _write_json(evidence / "worker-pre-run-preservation.json", preservation)
            return _worker(root, manifest_path, bindings, evidence, runtime_identity)
        except Exception as exc:
            if not (evidence / "report.json").exists():
                _write_json(
                    evidence / "report.json",
                    {
                    "issueId": ISSUE,
                    "diagnosticOrdinal": 2,
                    "status": "INCONCLUSIVE",
                    "primaryError": {"type": type(exc).__name__, "message": str(exc)},
                    "traceback": traceback.format_exc(),
                    "candidateBuilt": False,
                    "candidateEligibleForServing": False,
                    },
                )
            return 2
    if evidence.exists():
        parser.error("diagnostic-2 run leaf exists; no retry or overwrite")
    before: dict[str, Any] | None = None
    expected_manifest_sha256: str | None = None
    evidence_created = False
    process: subprocess.Popen[bytes] | None = None
    child_exit: int | None = None
    peak_bytes: int | None = None
    memory_status = "unavailable: no successful process sample"
    timed_out = False
    try:
        manifest, bindings, before = _verify_inputs(root, manifest_path)
        if not before["passes"]:
            raise ValueError(f"pre-run input/preservation verification failed: {before['changed'][:12]}")
        expected_manifest_sha256 = before["manifestSha256"]
        runtime_identity = _runtime_identity(root, bindings)
        sys.path.insert(0, str(root / "pipeline"))
        from torquay_pipeline.teignmouth_float32_candidate import load_candidate_config

        preflight_config = load_candidate_config(root / "config/road-surface-teignmouth-float32.json")
        preflight_build_report = _read_bound_json(root, f"{BUILD_ROOT}/build-report.json", bindings)
        preflight_release_identity = _verify_release_identity(
            root, bindings, preflight_build_report, preflight_config.release_id
        )
        for module in list(sys.modules.values()):
            filename = getattr(module, "__file__", None)
            if filename is None:
                continue
            helper_path = Path(filename).resolve()
            try:
                helper_relative = helper_path.relative_to(root / "pipeline/torquay_pipeline").as_posix()
            except ValueError:
                continue
            if helper_path.suffix == ".py" and f"pipeline/torquay_pipeline/{helper_relative}" not in bindings:
                raise ValueError(f"preflight imported unbound local helper: {helper_relative}")
        snapshot = _read_bound_json(root, SNAPSHOT_RELATIVE, bindings)
        ledger = json.loads((root / LEDGER_RELATIVE).read_text(encoding="utf-8"))
        diagnostics = ledger.get("budget", {}).get("diagnostics", {})
        if (
            ledger.get("issueId") != ISSUE
            or diagnostics.get("used") != 1
            or diagnostics.get("reserved") != 1
            or diagnostics.get("maximumSecondsEach") != WALL_LIMIT_SECONDS
        ):
            raise ValueError("diagnostic ordinal 2 is not uniquely reserved in the coordinator ledger")
        if snapshot != ledger:
            raise ValueError("bound immutable pre-run ledger snapshot differs from live ledger")
        if _sha256(root / "pipeline/.venv/Scripts/python.exe") != bindings[
            "pipeline/.venv/Scripts/python.exe"
        ]["sha256"]:
            raise ValueError("exact repository interpreter hash mismatch")
        evidence.mkdir(parents=True, exist_ok=False)
        evidence_created = True
        token = secrets.token_hex(32)
        _write_json(
            evidence / "attempt.json",
            {
                "issueId": ISSUE,
                "diagnosticOrdinal": 2,
                "wallLimitSeconds": WALL_LIMIT_SECONDS,
                "command": [sys.executable, *sys.argv],
                "interpreter": sys.executable,
                "inputManifestSha256": expected_manifest_sha256,
                "frozenRuntimeIdentity": runtime_identity["frozen"],
                "preflightReleaseIdentity": preflight_release_identity,
                "workerTokenSha256": hashlib.sha256(token.encode()).hexdigest(),
                "startedUtc": datetime.now(UTC).isoformat(),
                "candidateBuildExecuted": False,
            },
        )
        _write_json(evidence / "pre-run-preservation.json", before)
        remaining = min(
            WALL_LIMIT_SECONDS - WORKER_BUDGET_RESERVE_SECONDS,
            WALL_LIMIT_SECONDS - (time.perf_counter() - started) - WORKER_BUDGET_RESERVE_SECONDS,
        )
        if remaining <= 0:
            raise TimeoutError("manifest verification consumed the diagnostic wall budget")
        worker_stdout = (evidence / "worker.stdout.log").open("w", encoding="utf-8")
        worker_stderr = (evidence / "worker.stderr.log").open("w", encoding="utf-8")
        process = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--input-manifest",
                str(manifest_path),
                "--worker",
                "--worker-token",
                token,
            ],
            cwd=root,
            stdout=worker_stdout,
            stderr=worker_stderr,
            close_fds=True,
        )
        try:
            while process.poll() is None:
                sample, status = _working_set(process.pid)
                if sample is not None:
                    peak_bytes = max(peak_bytes or 0, sample)
                    memory_status = status
                elif memory_status.startswith("unavailable"):
                    memory_status = status
                elapsed = time.perf_counter() - started
                if elapsed >= WALL_LIMIT_SECONDS - WORKER_BUDGET_RESERVE_SECONDS:
                    timed_out = True
                    process.kill()
                    break
                time.sleep(0.15)
        finally:
            if process.poll() is None:
                process.kill()
            child_exit = process.wait()
            worker_stdout.close()
            worker_stderr.close()
        if not timed_out and process.poll() is not None:
            child_exit = process.returncode
        after_error = None
        try:
            _manifest, _bindings, after = _verify_inputs(
                root, manifest_path, expected_manifest_sha256
            )
        except Exception as exc:
            after_error = {"type": type(exc).__name__, "message": str(exc)}
            after = {
                "passes": False,
                "checkedFileCount": 0,
                "changed": [{"reason": f"post-run input verification error: {exc}"}],
                "manifestSha256": None,
            }
        _write_json(evidence / "post-run-preservation.json", after)
        try:
            worker_report = json.loads((evidence / "report.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            worker_report = None
        worker_status = worker_report.get("status") if worker_report else "WORKER_REPORT_MISSING"
        if timed_out:
            runner_status = "STOP_TIMEOUT"
        elif after_error or not after["passes"]:
            runner_status = "STOP_PRESERVATION_MISMATCH"
        elif worker_report is None:
            runner_status = "STOP_WORKER_REPORT_MISSING"
        elif child_exit != 0:
            runner_status = "WORKER_NONZERO_EXIT"
        else:
            runner_status = "WORKER_EXIT_ZERO"
        runner_exit = 0 if runner_status == "WORKER_EXIT_ZERO" else 2
        runner_report = {
            "schema": "teignmouth-overlay-diagnostic-runner-report-v1",
            "issueId": ISSUE,
            "diagnosticOrdinal": 2,
            "status": runner_status,
            "workerReportedStatus": worker_status,
            "actualWorkerExitCode": child_exit,
            "runnerChosenExitCode": runner_exit,
            "wallLimitSeconds": WALL_LIMIT_SECONDS,
            "elapsedWallSeconds": time.perf_counter() - started,
            "timedOut": timed_out,
            "peakWorkingSetBytes": peak_bytes,
            "peakWorkingSetStatus": memory_status,
            "preRunPreservation": before,
            "postRunPreservation": after,
            "postRunVerificationError": after_error,
            "inputManifestSha256PreRun": expected_manifest_sha256,
            "inputManifestSha256PostRun": after.get("manifestSha256"),
            "manifestHashStable": after.get("manifestSha256") == expected_manifest_sha256,
            "externalSupervisor": EXTERNAL_SUPERVISOR_RELATIVE,
            "externalSupervisorEvidence": f"{EVIDENCE_RELATIVE}/external-supervisor.json",
            "coordinatorMustConsumeReservation": True,
            "candidateBuilt": False,
            "candidateEligibleForServing": False,
        }
        _write_json(evidence / "runner-report.json", runner_report)
        print(
            json.dumps(
                {
                    "status": runner_status,
                    "runnerChosenExitCode": runner_exit,
                    "elapsedWallSeconds": runner_report["elapsedWallSeconds"],
                    "evidence": str(evidence),
                },
                sort_keys=True,
            )
        )
        return runner_exit
    except Exception as exc:
        elapsed = time.perf_counter() - started
        if process is not None and process.poll() is None:
            try:
                process.kill()
            except Exception:
                pass
            try:
                child_exit = process.wait(timeout=2)
            except Exception:
                child_exit = None
        if evidence_created:
            after_error = None
            try:
                _manifest, _bindings, after = _verify_inputs(
                    root, manifest_path, expected_manifest_sha256
                )
            except Exception as verification_exc:
                after_error = {"type": type(verification_exc).__name__, "message": str(verification_exc)}
                after = {
                    "passes": False,
                    "checkedFileCount": 0,
                    "changed": [{"reason": f"post-run input verification error: {verification_exc}"}],
                    "manifestSha256": None,
                }
            try:
                _write_json(evidence / "post-run-preservation.json", after)
            except Exception as telemetry_exc:
                after_error = after_error or {"type": type(telemetry_exc).__name__, "message": str(telemetry_exc)}
            try:
                worker_report = json.loads((evidence / "report.json").read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                worker_report = None
            runner_status = "STOP_TIMEOUT" if timed_out or isinstance(exc, (TimeoutError, subprocess.TimeoutExpired)) else "RUNNER_ERROR"
            runner_report = {
                "schema": "teignmouth-overlay-diagnostic-runner-report-v1",
                "issueId": ISSUE,
                "diagnosticOrdinal": 2,
                "status": runner_status,
                "runnerError": {"type": type(exc).__name__, "message": str(exc)},
                "workerReportedStatus": worker_report.get("status") if worker_report else "WORKER_REPORT_MISSING",
                "actualWorkerExitCode": child_exit,
                "runnerChosenExitCode": 2,
                "wallLimitSeconds": WALL_LIMIT_SECONDS,
                "elapsedWallSeconds": elapsed,
                "timedOut": timed_out or isinstance(exc, (TimeoutError, subprocess.TimeoutExpired)),
                "peakWorkingSetBytes": peak_bytes,
                "peakWorkingSetStatus": memory_status,
                "preRunPreservation": before,
                "postRunPreservation": after,
                "postRunVerificationError": after_error,
                "inputManifestSha256PreRun": expected_manifest_sha256,
                "inputManifestSha256PostRun": after.get("manifestSha256"),
                "externalSupervisor": EXTERNAL_SUPERVISOR_RELATIVE,
                "externalSupervisorEvidence": f"{EVIDENCE_RELATIVE}/external-supervisor.json",
                "coordinatorMustConsumeReservation": True,
                "candidateBuilt": False,
                "candidateEligibleForServing": False,
            }
            try:
                _write_json(evidence / "runner-report.json", runner_report)
            except Exception:
                pass
        print(json.dumps({"status": "INCONCLUSIVE", "error": str(exc), "evidence": str(evidence)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
