from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from torquay_pipeline.scene_release import (
    INVENTORY_FILENAME,
    READY_FILENAME,
    RUNTIME_FILES,
    SceneReleaseError,
    publish_scene_release,
    validate_published_scene,
)


def _workspace(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "workspace"
    root.mkdir()
    stage = root / ".torquay-poc-001-2km.stage-fixture"
    package_root = root / "public/worlds/torquay-poc-001-2km"
    stage.mkdir()
    for relative in RUNTIME_FILES:
        target = stage.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f"fixture:{relative}:v1".encode())
    return root, stage, package_root


def _validator_calls() -> tuple[Any, list[Path]]:
    calls: list[Path] = []

    def validate(package: Path) -> dict[str, Any]:
        calls.append(package)
        return {"packageDirectory": str(package), "validated": True}

    return validate, calls


def _publish(root: Path, stage: Path, package_root: Path, validator: Any) -> dict[str, Any]:
    return publish_scene_release(
        stage,
        package_root,
        project_root=root,
        validator=validator,
    )


def test_publish_writes_content_addressed_release_and_inventory_before_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, stage, package_root = _workspace(tmp_path)
    validator, calls = _validator_calls()
    copy_calls: list[str] = []
    original_copy = __import__("torquay_pipeline.scene_release", fromlist=["x"])._copy_exclusive
    original_write = __import__("torquay_pipeline.scene_release", fromlist=["x"])._write_exclusive

    def record_copy(source: Path, destination: Path, relative: str) -> None:
        copy_calls.append(relative)
        original_copy(source, destination, relative)

    def record_write(path: Path, content: bytes, *, label: str) -> None:
        assert copy_calls == list(RUNTIME_FILES)
        original_write(path, content, label=label)

    monkeypatch.setattr("torquay_pipeline.scene_release._copy_exclusive", record_copy)
    monkeypatch.setattr("torquay_pipeline.scene_release._write_exclusive", record_write)
    result = _publish(root, stage, package_root, validator)

    release_dir = Path(result["releaseDirectory"])
    assert release_dir.name == result["releaseId"]
    assert [path.name for path in calls] == [stage.name, release_dir.name]
    assert copy_calls == list(RUNTIME_FILES)
    assert (release_dir / INVENTORY_FILENAME).is_file()
    assert (package_root / READY_FILENAME).is_file()
    ready = json.loads((package_root / READY_FILENAME).read_bytes())
    assert ready["releaseId"] == result["releaseId"]
    assert ready["inventoryPath"] == f"releases/{result['releaseId']}/inventory.json"
    validated = validate_published_scene(package_root, project_root=root, validator=validator)
    assert validated["releaseId"] == result["releaseId"]


def test_republishing_identical_stage_is_deterministic_and_preserves_ready_bytes(
    tmp_path: Path,
) -> None:
    root, stage, package_root = _workspace(tmp_path)
    validator, _calls = _validator_calls()
    first = _publish(root, stage, package_root, validator)
    first_ready = (package_root / READY_FILENAME).read_bytes()

    second = _publish(root, stage, package_root, validator)

    assert second["releaseId"] == first["releaseId"]
    assert second["inventory"] == first["inventory"]
    assert (package_root / READY_FILENAME).read_bytes() == first_ready


def test_invalid_stage_is_rejected_before_any_publication_write(tmp_path: Path) -> None:
    root, stage, package_root = _workspace(tmp_path)

    def reject_stage(_package: Path) -> dict[str, Any]:
        raise ValueError("injected stage validation failure")

    with pytest.raises(ValueError, match="injected stage validation failure"):
        _publish(root, stage, package_root, reject_stage)

    assert stage.is_dir()
    assert not package_root.exists()


def test_partial_copy_failure_keeps_previous_ready_pointer_and_never_writes_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, stage, package_root = _workspace(tmp_path)
    validator, _calls = _validator_calls()
    initial = _publish(root, stage, package_root, validator)
    old_ready = (package_root / READY_FILENAME).read_bytes()
    changed_stage = root / ".torquay-poc-001-2km.stage-next"
    changed_stage.mkdir()
    for relative in RUNTIME_FILES:
        target = changed_stage.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f"fixture:{relative}:v2".encode())

    original_copy = __import__("torquay_pipeline.scene_release", fromlist=["x"])._copy_exclusive
    copied = 0

    def fail_after_first(source: Path, destination: Path, relative: str) -> None:
        nonlocal copied
        copied += 1
        if copied == 2:
            raise OSError("injected copy failure")
        original_copy(source, destination, relative)

    monkeypatch.setattr("torquay_pipeline.scene_release._copy_exclusive", fail_after_first)
    with pytest.raises(OSError, match="injected copy failure"):
        _publish(root, changed_stage, package_root, validator)

    assert (package_root / READY_FILENAME).read_bytes() == old_ready
    assert (package_root / "releases" / initial["releaseId"] / INVENTORY_FILENAME).is_file()
    next_release = next(
        item for item in (package_root / "releases").iterdir() if item.name != initial["releaseId"]
    )
    assert not (next_release / INVENTORY_FILENAME).exists()


@pytest.mark.parametrize("failure_phase", ["release_validation", "ready_replace"])
def test_activation_failure_keeps_previous_ready_pointer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_phase: str
) -> None:
    root, stage, package_root = _workspace(tmp_path)
    validator, _calls = _validator_calls()
    first = _publish(root, stage, package_root, validator)
    old_ready = (package_root / READY_FILENAME).read_bytes()
    changed_stage = root / ".torquay-poc-001-2km.stage-next"
    changed_stage.mkdir()
    for relative in RUNTIME_FILES:
        target = changed_stage.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f"fixture:{relative}:v2".encode())

    if failure_phase == "release_validation":
        calls = 0

        def fail_on_release(package: Path) -> dict[str, Any]:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise ValueError("injected release validation failure")
            return {"validated": True}

        with pytest.raises(ValueError, match="injected release validation failure"):
            _publish(root, changed_stage, package_root, fail_on_release)
    else:
        original_replace = os.replace

        def fail_ready_replace(
            source: str | os.PathLike[str], target: str | os.PathLike[str]
        ) -> None:
            if Path(target) == package_root / READY_FILENAME:
                raise PermissionError("injected file activation failure")
            original_replace(source, target)

        monkeypatch.setattr("torquay_pipeline.scene_release.os.replace", fail_ready_replace)
        with pytest.raises(PermissionError, match="injected file activation failure"):
            _publish(root, changed_stage, package_root, validator)

    assert (package_root / READY_FILENAME).read_bytes() == old_ready
    assert json.loads(old_ready)["releaseId"] == first["releaseId"]


def test_existing_content_addressed_file_is_never_overwritten(tmp_path: Path) -> None:
    root, stage, package_root = _workspace(tmp_path)
    validator, _calls = _validator_calls()
    result = _publish(root, stage, package_root, validator)
    release_dir = Path(result["releaseDirectory"])
    payload_path = release_dir / "roads/roads.json"
    payload_path.write_bytes(b"mutated")
    old_ready = (package_root / READY_FILENAME).read_bytes()

    with pytest.raises(SceneReleaseError, match="byte length mismatch|SHA-256 mismatch"):
        _publish(root, stage, package_root, validator)

    assert payload_path.read_bytes() == b"mutated"
    assert (package_root / READY_FILENAME).read_bytes() == old_ready


def test_release_validator_rejects_payload_mutation_and_tampered_ready_inventory(
    tmp_path: Path,
) -> None:
    root, stage, package_root = _workspace(tmp_path)
    validator, _calls = _validator_calls()
    result = _publish(root, stage, package_root, validator)
    release_dir = Path(result["releaseDirectory"])
    payload = release_dir / "buildings/buildings.json"
    payload.write_bytes(payload.read_bytes() + b"tamper")

    with pytest.raises(SceneReleaseError, match="byte length mismatch|SHA-256 mismatch"):
        validate_published_scene(package_root, project_root=root, validator=validator)

    ready_path = package_root / READY_FILENAME
    ready = json.loads(ready_path.read_bytes())
    ready["inventorySha256"] = "0" * 64
    ready_path.write_text(json.dumps(ready), encoding="utf-8")
    with pytest.raises(SceneReleaseError, match="inventory length or SHA-256"):
        validate_published_scene(package_root, project_root=root, validator=validator)


def test_refuses_symlink_stage_and_non_fixed_output_root(tmp_path: Path) -> None:
    root, stage, package_root = _workspace(tmp_path)
    validator, _calls = _validator_calls()
    with pytest.raises(SceneReleaseError, match="fixed local path"):
        publish_scene_release(
            stage,
            root / "public/worlds/other",
            project_root=root,
            validator=validator,
        )
    symlink_stage = root / ".torquay-poc-001-2km.stage-symlink"
    try:
        symlink_stage.symlink_to(stage, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable for this account")
    with pytest.raises(SceneReleaseError, match="symlink path component"):
        publish_scene_release(
            symlink_stage,
            package_root,
            project_root=root,
            validator=validator,
        )


def _make_directory_junction(path: Path, target: Path) -> None:
    if os.name != "nt":
        pytest.skip("Windows directory junction regression requires Windows")
    command = f"mklink /J {path} {target}"
    result = subprocess.run(
        ["cmd.exe", "/c", command],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not path.is_junction():
        pytest.skip(
            "this Windows filesystem cannot create a junction: "
            f"{result.stdout.strip()} {result.stderr.strip()}"
        )


def test_rejects_output_junction_before_validation_or_any_write(tmp_path: Path) -> None:
    root, stage, package_root = _workspace(tmp_path)
    validator, calls = _validator_calls()
    public = root / "public"
    public.mkdir()
    protected_target = tmp_path / "protected-target"
    protected_package = protected_target / "torquay-poc-001-2km"
    protected_package.mkdir(parents=True)
    sentinel = protected_package / "keep.txt"
    sentinel.write_bytes(b"protected output target")
    junction = public / "worlds"
    _make_directory_junction(junction, protected_target)

    with pytest.raises(SceneReleaseError, match="junction/reparse"):
        publish_scene_release(
            stage,
            package_root,
            project_root=root,
            validator=validator,
        )

    assert calls == []
    assert sentinel.read_bytes() == b"protected output target"
    assert sorted(path.name for path in protected_package.iterdir()) == ["keep.txt"]


def test_rejects_stage_junction_before_validation_or_any_write(tmp_path: Path) -> None:
    root, stage, package_root = _workspace(tmp_path)
    validator, calls = _validator_calls()
    stage_link = root / ".torquay-poc-001-2km.stage-junction"
    _make_directory_junction(stage_link, stage)
    sentinel = stage / "manifest.json"
    original = sentinel.read_bytes()

    with pytest.raises(SceneReleaseError, match="junction/reparse"):
        publish_scene_release(
            stage_link,
            package_root,
            project_root=root,
            validator=validator,
        )

    assert calls == []
    assert sentinel.read_bytes() == original
    assert not package_root.exists()


def test_publish_cli_rejects_junction_before_resolving_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from torquay_pipeline import cli

    root, stage, package_root = _workspace(tmp_path)
    stage_link = root / ".torquay-poc-001-2km.stage-cli-junction"
    _make_directory_junction(stage_link, stage)
    monkeypatch.setattr(cli, "PROJECT_ROOT", root)
    monkeypatch.chdir(root)

    result = cli.main(
        [
            "publish-scene",
            "--validated-stage",
            str(stage_link),
            "--package-root",
            str(package_root),
        ]
    )

    assert result == 2
    assert "junction/reparse" in capsys.readouterr().err
    assert not package_root.exists()
    assert stage.joinpath("manifest.json").read_bytes() == b"fixture:manifest.json:v1"
