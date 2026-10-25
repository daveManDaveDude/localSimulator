from __future__ import annotations

import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture(
    params=[
        "profile_teignmouth_complete_dispatch_sol.py",
        "profile_teignmouth_frame_selected_sol.py",
    ]
)
def profile_module(request):
    return runpy.run_path(str(Path(__file__).parents[1] / "scripts" / request.param))


def test_projection_is_explicitly_a_proxy_not_qualification(profile_module) -> None:
    result = profile_module["_project"]({"retained": 42.0, "measured": 80.0})
    assert result["sumSeconds"] == 122.0
    assert result["actualCollarEndToEndMeasured"] is False
    assert result["qualifiesCurrentPolicy"] is False
    with pytest.raises(ValueError):
        profile_module["_project"]({"invalid": float("nan")})


def test_source_and_release_manifest_fields_are_distinct(profile_module, tmp_path) -> None:
    function = profile_module["_source_identities"]
    function.__globals__["ROOT"] = tmp_path
    data = tmp_path / "data/source-manifest.json"
    data.parent.mkdir()
    data.write_bytes(b"source metadata")
    legacy = tmp_path / "old-profile.json"
    legacy.write_bytes(b"preserved")
    function.__globals__["LEGACY_PROFILE"] = legacy
    result = function(SimpleNamespace(source_hashes={"manifest.json": {"sha256": "a" * 64}}))
    assert result["releaseTerrainManifestSha256"] == "a" * 64
    assert result["dataSourceManifestSha256"] != "a" * 64
    assert result["legacyProfileFieldCorrection"]["oldProfilePreserved"] is True
    assert legacy.read_bytes() == b"preserved"


def test_write_once_rejects_unknown_output_and_collision(profile_module, tmp_path) -> None:
    function = profile_module["_write_once"]
    target = tmp_path / "profile.json"
    function.__globals__["OUTPUT"] = target
    with pytest.raises(RuntimeError, match="allowlist"):
        function(tmp_path / "candidate.f32", b"forbidden")
    function(target, b"timing only")
    with pytest.raises(FileExistsError):
        function(target, b"replacement")
    assert target.read_bytes() == b"timing only"


def test_existing_profile_prevents_any_dispatch(profile_module, tmp_path) -> None:
    function = profile_module["main"]
    target = tmp_path / "profile.json"
    target.write_bytes(b"previous evidence")
    function.__globals__["OUTPUT"] = target
    function.__globals__["REPORT_OUTPUT"] = tmp_path / "report.json"
    with pytest.raises(RuntimeError, match="absent"):
        function()
    assert target.read_bytes() == b"previous evidence"
