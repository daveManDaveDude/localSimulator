"""Immutable content-addressed releases for the current 2 km browser scene.

Only the file-level readiness pointer is mutable. Runtime files are copied
exclusively into an immutable, content-addressed release directory; its
inventory is written last and the release is fully validated before
``ready.json`` is atomically activated.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

SCENE_PROFILE = "current_2km"
WORLD_ID = "torquay-poc-001"
READY_FILENAME = "ready.json"
INVENTORY_FILENAME = "inventory.json"
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
READY_LIMIT_BYTES = 8 * 1024
INVENTORY_LIMIT_BYTES = 32 * 1024


class SceneReleaseError(ValueError):
    """Raised when an immutable scene release cannot be safely published."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON identically in Python and the browser validator."""
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _is_reparse_point(path: Path) -> bool:
    """Detect links and Windows reparse points without following the entry."""
    try:
        entry = path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise SceneReleaseError(f"cannot inspect path component '{path}': {exc}") from exc
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = getattr(entry, "st_file_attributes", 0)
    return (
        stat.S_ISLNK(entry.st_mode)
        or bool(attributes & reparse_flag)
        or (hasattr(path, "is_junction") and path.is_junction())
    )


def assert_no_reparse_components(path: Path) -> Path:
    """Return an absolute lexical path after rejecting links/junctions in it.

    This deliberately runs before ``resolve``: resolving a Windows junction
    would erase the path entry that the guard needs to reject.
    """
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current /= component
        if _is_reparse_point(current):
            raise SceneReleaseError(
                f"symlink path component or junction/reparse point is not allowed: '{current}'"
            )
    return absolute


def _assert_no_symlink_components(path: Path, *, project_root: Path) -> None:
    absolute = assert_no_reparse_components(path)
    resolved = absolute.resolve(strict=False)
    try:
        resolved.relative_to(project_root)
    except ValueError as exc:
        raise SceneReleaseError(f"path escapes the workspace: '{path}'") from exc


def _resolve_validated_stage(validated_stage: Path, project_root: Path) -> Path:
    _assert_no_symlink_components(validated_stage, project_root=project_root)
    stage = validated_stage.resolve(strict=True)
    if not stage.is_dir() or not stage.name.startswith(".torquay-poc-001-2km.stage-"):
        raise SceneReleaseError(
            "validated stage must be an owned .torquay-poc-001-2km.stage-* directory"
        )
    return stage


def _resolve_package_root(package_root: Path, project_root: Path) -> Path:
    expected = Path(os.path.abspath(project_root / "public/worlds/torquay-poc-001-2km"))
    output = assert_no_reparse_components(package_root)
    _assert_no_symlink_components(output, project_root=project_root)
    if output != expected:
        raise SceneReleaseError(
            f"release root must be the fixed local path '{expected}', received '{output}'"
        )
    historical = Path(os.path.abspath(project_root / "public/worlds/torquay-poc-001"))
    if output == historical or historical in output.parents or output in historical.parents:
        raise SceneReleaseError("release root overlaps the immutable historical 1 km package")
    return output


def _runtime_inventory(stage: Path) -> tuple[list[dict[str, Any]], dict[str, tuple[int, str]]]:
    entries: list[dict[str, Any]] = []
    digests: dict[str, tuple[int, str]] = {}
    for relative in RUNTIME_FILES:
        source = stage.joinpath(*relative.split("/"))
        assert_no_reparse_components(source)
        if not source.is_file():
            raise SceneReleaseError(f"runtime stage file is missing or unsafe: '{relative}'")
        byte_length = source.stat().st_size
        sha256 = _sha256_file(source)
        entries.append({"path": relative, "byteLength": byte_length, "sha256": sha256})
        digests[relative] = (byte_length, sha256)
    return entries, digests


def _inventory_document(entries: list[dict[str, Any]]) -> tuple[str, bytes]:
    body = {
        "formatVersion": 1,
        "worldId": WORLD_ID,
        "sceneProfile": SCENE_PROFILE,
        "files": entries,
    }
    release_id = _sha256_bytes(canonical_json_bytes(body))
    document = {**body, "releaseId": release_id}
    return release_id, canonical_json_bytes(document)


def _verify_file(path: Path, expected: tuple[int, str], *, label: str) -> None:
    assert_no_reparse_components(path)
    if not path.is_file():
        raise SceneReleaseError(f"release file is missing or unsafe: '{label}'")
    byte_length, sha256 = expected
    actual_length = path.stat().st_size
    if actual_length != byte_length:
        raise SceneReleaseError(
            f"release file '{label}' byte length mismatch: "
            f"expected {byte_length}, received {actual_length}"
        )
    actual_sha256 = _sha256_file(path)
    if actual_sha256 != sha256:
        raise SceneReleaseError(
            f"release file '{label}' SHA-256 mismatch: expected {sha256}, received {actual_sha256}"
        )


def _release_file_inventory(release_dir: Path) -> set[str]:
    found: set[str] = set()
    pending = [release_dir]
    while pending:
        directory = pending.pop()
        for item in directory.iterdir():
            if _is_reparse_point(item):
                raise SceneReleaseError(f"release contains a symlink or junction: '{item}'")
            if item.is_dir():
                pending.append(item)
            elif item.is_file():
                found.add(item.relative_to(release_dir).as_posix())
            else:
                raise SceneReleaseError(
                    f"release contains an unsupported filesystem entry: '{item}'"
                )
    return found


def _validate_release_files(
    release_dir: Path,
    entries: list[dict[str, Any]],
    inventory_bytes: bytes,
) -> None:
    expected = {entry["path"]: (entry["byteLength"], entry["sha256"]) for entry in entries}
    expected[INVENTORY_FILENAME] = (len(inventory_bytes), _sha256_bytes(inventory_bytes))
    actual_names = _release_file_inventory(release_dir)
    if actual_names != set(expected):
        missing = sorted(set(expected) - actual_names)
        unexpected = sorted(actual_names - set(expected))
        raise SceneReleaseError(
            f"release inventory mismatch; missing={missing}, unexpected={unexpected}"
        )
    for relative, identity in expected.items():
        _verify_file(release_dir.joinpath(*relative.split("/")), identity, label=relative)


def _copy_exclusive(source: Path, destination: Path, relative: str) -> None:
    """Create a file once, stream exact bytes, then verify length and digest."""
    assert_no_reparse_components(source)
    assert_no_reparse_components(destination)
    assert_no_reparse_components(destination.parent)
    if destination.exists():
        raise SceneReleaseError(f"refusing to overwrite immutable release file '{relative}'")
    input_stream = source.open("rb")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if _is_reparse_point(destination.parent):
            raise SceneReleaseError(f"release parent is a reparse point for '{relative}'")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor = os.open(destination, flags, 0o666)
    except Exception:
        input_stream.close()
        raise
    try:
        with input_stream, os.fdopen(descriptor, "wb") as output_stream:
            shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
            output_stream.flush()
            os.fsync(output_stream.fileno())
    except Exception:
        # The destination was created exclusively by this call. Leave it in
        # place as evidence of the incomplete, non-activated release.
        raise
    if source.stat().st_size != destination.stat().st_size or _sha256_file(source) != _sha256_file(
        destination
    ):
        raise SceneReleaseError(f"exclusive copy verification failed for '{relative}'")


def _write_exclusive(path: Path, content: bytes, *, label: str) -> None:
    assert_no_reparse_components(path)
    if path.exists():
        existing = path.read_bytes()
        if existing != content:
            raise SceneReleaseError(f"existing immutable {label} differs from expected bytes")
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        # Remove only the partial file created exclusively by this call.
        path.unlink(missing_ok=True)
        raise
    if path.read_bytes() != content:
        raise SceneReleaseError(f"written {label} failed byte-for-byte verification")


def _atomic_activate_ready(package_root: Path, ready_bytes: bytes) -> None:
    ready_path = package_root / READY_FILENAME
    assert_no_reparse_components(ready_path)
    if _is_reparse_point(ready_path):
        raise SceneReleaseError("ready.json must not be a reparse point")
    temporary_path = package_root / f".ready.json.pending-{uuid.uuid4().hex}"
    descriptor = os.open(temporary_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(ready_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        if temporary_path.read_bytes() != ready_bytes:
            raise SceneReleaseError("temporary readiness pointer failed byte verification")
        # This is the only mutable publication operation and it is file-level.
        os.replace(temporary_path, ready_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _build_ready_document(release_id: str, inventory_bytes: bytes) -> bytes:
    return canonical_json_bytes(
        {
            "formatVersion": 1,
            "worldId": WORLD_ID,
            "sceneProfile": SCENE_PROFILE,
            "releaseId": release_id,
            "inventoryPath": f"releases/{release_id}/{INVENTORY_FILENAME}",
            "inventoryByteLength": len(inventory_bytes),
            "inventorySha256": _sha256_bytes(inventory_bytes),
        }
    )


def publish_scene_release(
    validated_stage: Path,
    package_root: Path,
    *,
    project_root: Path,
    validator: Callable[[Path], Mapping[str, Any]],
    stage_already_validated: bool = False,
) -> dict[str, Any]:
    """Copy a validated stage to an immutable release and atomically activate it.

    The validator is run on the release after inventory publication and before
    changing readiness. A caller may suppress the repeated source-stage
    validation only when it has just validated that same stage in-process.
    """
    root = project_root.resolve(strict=True)
    assert_no_reparse_components(validated_stage)
    assert_no_reparse_components(package_root)
    stage = _resolve_validated_stage(validated_stage, root)
    output = _resolve_package_root(package_root, root)
    if stage == output or stage in output.parents or output in stage.parents:
        raise SceneReleaseError("validated stage and release root must not overlap")
    entries, identities = _runtime_inventory(stage)
    release_id, inventory_bytes = _inventory_document(entries)
    if not stage_already_validated:
        validator(stage)
    releases_root = output / "releases"
    release_dir = releases_root / release_id
    for path in (output, releases_root, release_dir):
        _assert_no_symlink_components(path, project_root=root)
    output.mkdir(parents=True, exist_ok=True)
    releases_root.mkdir(parents=True, exist_ok=True)
    if _is_reparse_point(release_dir):
        raise SceneReleaseError("content-addressed release directory must not be a reparse point")
    release_dir.mkdir(exist_ok=True)

    existing_names = _release_file_inventory(release_dir)
    allowed_partial_names = set(RUNTIME_FILES) | {INVENTORY_FILENAME}
    unexpected = existing_names - allowed_partial_names
    if unexpected:
        raise SceneReleaseError(f"release contains unexpected files: {sorted(unexpected)}")
    for relative in RUNTIME_FILES:
        source = stage.joinpath(*relative.split("/"))
        destination = release_dir.joinpath(*relative.split("/"))
        if destination.exists():
            _verify_file(destination, identities[relative], label=relative)
        else:
            _copy_exclusive(source, destination, relative)
        _verify_file(destination, identities[relative], label=relative)

    inventory_path = release_dir / INVENTORY_FILENAME
    _write_exclusive(inventory_path, inventory_bytes, label="inventory.json")
    _validate_release_files(release_dir, entries, inventory_bytes)

    # Full source/schema/geometry validation is against the bytes that will be
    # served, not only against the staging tree.
    release_validation = dict(validator(release_dir))
    _validate_release_files(release_dir, entries, inventory_bytes)
    ready_bytes = _build_ready_document(release_id, inventory_bytes)
    _atomic_activate_ready(output, ready_bytes)
    return {
        "sceneProfile": SCENE_PROFILE,
        "worldId": WORLD_ID,
        "releaseId": release_id,
        "releaseDirectory": str(release_dir),
        "inventory": json.loads(inventory_bytes),
        "readyPath": str(output / READY_FILENAME),
        "readySha256": _sha256_bytes(ready_bytes),
        "releaseValidation": release_validation,
    }


def validate_published_scene(
    package_root: Path,
    *,
    project_root: Path,
    validator: Callable[[Path], Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate readiness, immutable inventory, every file and full scene data."""
    root = project_root.resolve(strict=True)
    assert_no_reparse_components(package_root)
    output = _resolve_package_root(package_root, root)
    ready_path = output / READY_FILENAME
    assert_no_reparse_components(ready_path)
    if _is_reparse_point(ready_path):
        raise SceneReleaseError("ready.json must not be a reparse point")
    try:
        ready_bytes = ready_path.read_bytes()
        if len(ready_bytes) > READY_LIMIT_BYTES:
            raise SceneReleaseError(f"ready.json exceeds the {READY_LIMIT_BYTES}-byte limit")
        ready = json.loads(ready_bytes)
    except SceneReleaseError:
        raise
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SceneReleaseError(f"ready.json is missing or invalid: {exc}") from exc
    if not isinstance(ready, dict):
        raise SceneReleaseError("ready.json must be a JSON object")
    if set(ready) != {
        "formatVersion",
        "worldId",
        "sceneProfile",
        "releaseId",
        "inventoryPath",
        "inventoryByteLength",
        "inventorySha256",
    }:
        raise SceneReleaseError("ready.json has unexpected or missing fields")
    release_id = ready.get("releaseId")
    if (
        ready.get("formatVersion") != 1
        or isinstance(ready.get("formatVersion"), bool)
        or ready.get("worldId") != WORLD_ID
        or ready.get("sceneProfile") != SCENE_PROFILE
        or not isinstance(release_id, str)
        or len(release_id) != 64
        or any(character not in "0123456789abcdef" for character in release_id)
        or ready.get("inventoryPath") != f"releases/{release_id}/{INVENTORY_FILENAME}"
    ):
        raise SceneReleaseError("ready.json does not identify a fixed current_2km release")
    inventory_path = output / "releases" / release_id / INVENTORY_FILENAME
    _assert_no_symlink_components(inventory_path, project_root=root)
    try:
        inventory_bytes = inventory_path.read_bytes()
        if len(inventory_bytes) > INVENTORY_LIMIT_BYTES:
            raise SceneReleaseError(
                f"inventory.json exceeds the {INVENTORY_LIMIT_BYTES}-byte limit"
            )
        inventory = json.loads(inventory_bytes)
    except SceneReleaseError:
        raise
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SceneReleaseError(f"release inventory is missing or invalid: {exc}") from exc
    if (
        not isinstance(ready.get("inventoryByteLength"), int)
        or isinstance(ready.get("inventoryByteLength"), bool)
        or ready["inventoryByteLength"] != len(inventory_bytes)
        or ready.get("inventorySha256") != _sha256_bytes(inventory_bytes)
    ):
        raise SceneReleaseError("ready.json inventory length or SHA-256 does not match")
    if not isinstance(inventory, dict):
        raise SceneReleaseError("inventory.json must be a JSON object")
    if set(inventory) != {
        "formatVersion",
        "worldId",
        "sceneProfile",
        "releaseId",
        "files",
    }:
        raise SceneReleaseError("inventory.json has unexpected or missing fields")
    entries = inventory.get("files")
    if (
        inventory.get("formatVersion") != 1
        or isinstance(inventory.get("formatVersion"), bool)
        or inventory.get("worldId") != WORLD_ID
        or inventory.get("sceneProfile") != SCENE_PROFILE
        or inventory.get("releaseId") != release_id
        or not isinstance(entries, list)
        or len(entries) != len(RUNTIME_FILES)
    ):
        raise SceneReleaseError("inventory.json has an invalid current_2km structure")
    expected_paths = list(RUNTIME_FILES)
    actual_paths: list[str] = []
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            raise SceneReleaseError(f"inventory.files[{index}] must be an object")
        if set(item) != {"path", "byteLength", "sha256"}:
            raise SceneReleaseError(f"inventory.files[{index}] has unexpected or missing fields")
        path = item.get("path")
        byte_length = item.get("byteLength")
        sha256 = item.get("sha256")
        if (
            not isinstance(path, str)
            or not isinstance(byte_length, int)
            or isinstance(byte_length, bool)
            or byte_length < 0
            or not isinstance(sha256, str)
            or len(sha256) != 64
            or any(character not in "0123456789abcdef" for character in sha256)
        ):
            raise SceneReleaseError(f"inventory.files[{index}] is malformed")
        actual_paths.append(path)
    if actual_paths != expected_paths:
        raise SceneReleaseError("inventory files do not match the fixed ordered runtime allowlist")
    body = {
        "formatVersion": 1,
        "worldId": WORLD_ID,
        "sceneProfile": SCENE_PROFILE,
        "files": entries,
    }
    if _sha256_bytes(canonical_json_bytes(body)) != release_id:
        raise SceneReleaseError("inventory contents do not match the content-addressed release ID")
    release_dir = output / "releases" / release_id
    _assert_no_symlink_components(release_dir, project_root=root)
    identities = {item["path"]: (item["byteLength"], item["sha256"]) for item in entries}
    identities[INVENTORY_FILENAME] = (len(inventory_bytes), _sha256_bytes(inventory_bytes))
    actual_names = _release_file_inventory(release_dir)
    if actual_names != set(identities):
        raise SceneReleaseError("release has missing or unexpected files relative to its inventory")
    for relative, identity in identities.items():
        _verify_file(release_dir.joinpath(*relative.split("/")), identity, label=relative)
    validation = dict(validator(release_dir))
    return {
        "sceneProfile": SCENE_PROFILE,
        "worldId": WORLD_ID,
        "releaseId": release_id,
        "releaseDirectory": str(release_dir),
        "inventory": inventory,
        "readySha256": _sha256_bytes(ready_bytes),
        "releaseValidation": validation,
    }
