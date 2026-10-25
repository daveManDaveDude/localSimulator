"""Synthetic protocol/supervision tests; real containment runs only in one probe."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from shapely.geometry import Polygon
from test_road_surface_validation_v1 import _small_patch_surface

from torquay_pipeline import road_surface_patch as patch
from torquay_pipeline import road_surface_validation_process_v1 as process

TEST_INVOCATION = "a" * 32


def request():
    return {"bindings": {"test": "synthetic-only"}, "candidateSha256": "a" * 64}


def response(*, success=False, complete=True):
    report = {name: {"passes": success} for name in patch.PATCH_OFFLINE_GATE_NAMES}
    report.update(
        gateNames=list(patch.PATCH_OFFLINE_GATE_NAMES),
        candidateFloat32Sha256="a" * 64,
        passes=success,
        validationComplete=complete,
    )
    result = {
        "bindings": request()["bindings"],
        "report": report,
        "gateSeconds": {},
        "operations": list(process.OPERATIONS) if success else [process.OPERATIONS[0]],
    }
    if success:
        first = {name: name.encode() for name in patch.PATCH_OUTPUT_FILES}
        second = dict(first)
        result.update(
            firstAssets=first,
            secondAssets=second,
            resources={"peakConstructionBufferBytes": 100},
            hashes={
                "first": {k: process.digest(v) for k, v in sorted(first.items())},
                "second": {k: process.digest(v) for k, v in sorted(second.items())},
            },
        )
    return result


def write_request_bundle(directory, envelope):
    payload = process.canonical(envelope)
    manifest = process.manifest_envelope(
        protocol=process.PROTOCOL,
        invocation=envelope["invocation"],
        payload=payload,
        files=process.encoded_file_manifest(envelope["request"]),
    )
    process.write_exclusive(directory / "request.json", payload)
    process.write_exclusive(directory / "request.manifest.json", process.canonical(manifest))


def test_codec_roundtrip_preserves_mesh_and_canonical_arrays(tmp_path):
    surface = _small_patch_surface()
    original = {
        ("tuple", 1): (
            surface.mesh,
            np.asarray([1, 2], dtype=">i4"),
            Polygon([(0, 0), (1, 0), (0, 1)]),
            b"bytes",
            Path("synthetic"),
        )
    }
    encoded = process.Codec(tmp_path, "request").encode(original)
    decoded = process.Codec(tmp_path, "request").decode(json.loads(process.canonical(encoded)))
    mesh, array, polygon, payload, path = decoded[("tuple", 1)]
    assert np.array_equal(mesh.triangles, surface.mesh.triangles)
    assert mesh.edge_counts == surface.mesh.edge_counts
    assert array.dtype.str == "<i4"
    assert array.tolist() == [1, 2]
    assert polygon.equals(original[("tuple", 1)][2])
    assert payload == b"bytes" and path == Path("synthetic")


def test_codec_reconstructs_ordered_geometry_index(tmp_path):
    from dataclasses import replace

    from shapely.strtree import STRtree

    mesh = _small_patch_surface().mesh
    polygons = tuple(Polygon(mesh.vertices_xz[face]) for face in mesh.triangles)
    mesh = replace(mesh, triangle_geometries=polygons, triangle_tree=STRtree(polygons))
    result = process.Codec(tmp_path, "request").decode(
        process.Codec(tmp_path, "request").encode(mesh)
    )
    assert len(result.triangle_tree.geometries) == len(polygons)
    assert all(
        a.equals_exact(b, 0) for a, b in zip(result.triangle_geometries, polygons, strict=True)
    )


@pytest.mark.parametrize(
    "value",
    [
        object(),
        SimpleNamespace(x=1),
        np.asarray([float("nan")]),
        np.asarray([object()]),
        float("inf"),
    ],
)
def test_codec_rejects_unsupported_or_nonfinite_values(tmp_path, value):
    with pytest.raises(process.ProcessValidationError):
        process.Codec(tmp_path, "request").encode(value)


def test_blob_mutation_shape_traversal_and_large_transport_are_typed(tmp_path):
    node = process.Codec(tmp_path, "request").encode(np.asarray([1, 2], dtype="<f4"))
    broken = deepcopy(node)
    broken["shape"] = [100]
    with pytest.raises(process.ProcessValidationError, match="shape"):
        process.Codec(tmp_path, "request").decode(broken)
    (tmp_path / node["blob"]["file"]).write_bytes(b"mutation")
    with pytest.raises(process.ProcessValidationError, match="identity"):
        process.Codec(tmp_path, "request").decode(node)
    with pytest.raises(process.ProcessValidationError, match="basename"):
        process.safe_file(tmp_path, "../other")
    codec = process.Codec(tmp_path, "large")
    codec.byte_count = 64 * 1024 * 1024
    encoded = codec.encode(b"xx")
    assert encoded["blob"]["bytes"] == 2
    assert codec.byte_count > 64 * 1024 * 1024


def test_exact_envelope_and_sidecar_bindings_accept_files_above_retired_caps(tmp_path):
    import hashlib

    envelope = process.canonical({"payload": "x" * (16 * 1024 * 1024 + 1)})
    envelope_path = tmp_path / "large-envelope.json"
    process.write_exclusive(envelope_path, envelope)
    observed, decoded = process.read_json_exact(envelope_path)
    assert len(observed) > 16 * 1024 * 1024
    assert decoded["payload"].startswith("x")

    sidecar_path = tmp_path / "request-large.bin"
    sidecar_length = 64 * 1024 * 1024 + 1
    with sidecar_path.open("xb") as stream:
        stream.seek(sidecar_length - 1)
        stream.write(b"\0")
    zero_hash = hashlib.sha256()
    remaining = sidecar_length
    zeros = bytes(1024 * 1024)
    while remaining:
        chunk = zeros[: min(len(zeros), remaining)]
        zero_hash.update(chunk)
        remaining -= len(chunk)
    process.verify_sidecar_files(
        tmp_path,
        [{"file": sidecar_path.name, "bytes": sidecar_length, "sha256": zero_hash.hexdigest()}],
    )


def test_gate_failure_and_cooperative_partial_are_diagnostics_only():
    for result in (response(), response(complete=False)):
        process.verify_response(request(), result)
        assert not result["report"]["passes"]


@pytest.mark.parametrize(
    "change",
    [
        "operations",
        "candidate",
        "bindings",
        "missing-gate",
        "partial-success",
        "shared-assets",
        "hashes",
    ],
)
def test_incomplete_replayed_or_reordered_results_rejected(change):
    result = response(success=True)
    if change == "operations":
        result["operations"].append("resources")
    elif change == "candidate":
        result["report"]["candidateFloat32Sha256"] = "b" * 64
    elif change == "bindings":
        result["bindings"] = {}
    elif change == "missing-gate":
        del result["report"][patch.PATCH_OFFLINE_GATE_NAMES[-1]]
    elif change == "partial-success":
        result["report"]["validationComplete"] = False
    elif change == "shared-assets":
        result["secondAssets"] = result["firstAssets"]
    else:
        result["hashes"] = {}
    with pytest.raises(process.ProcessValidationError):
        process.verify_response(request(), result)


def test_late_wait_and_exact_cutoff_are_rejected():
    job = SimpleNamespace(exited=lambda: True, exit_code=lambda: 0)
    with pytest.raises(process.ProcessValidationError, match="after"):
        process.wait_worker(job, 125, clock=lambda: 125)
    assert process.wait_worker(job, 125, clock=lambda: 124) == 0


class FakeJob:
    result = None
    behavior = "normal"
    last = None

    def __init__(self, argv, root, **kwargs):
        type(self).last = self
        self.terminated = self.closed = False
        self.scratch = Path(argv[-1])
        if self.behavior == "assignment-failure":
            raise process.ProcessValidationError("synthetic assignment failure")
        envelope = json.loads((self.scratch / "request.json").read_bytes())
        response_codec = process.Codec(self.scratch, "result")
        result = {
            "protocol": process.PROTOCOL,
            "invocation": envelope["invocation"],
            "requestSha256": process.digest((self.scratch / "request.json").read_bytes()),
            "response": response_codec.encode(self.result),
            "memory": {
                "constructionPeakBytes": self.result.get("resources", {}).get(
                    "peakConstructionBufferBytes", 0
                )
            },
        }
        if self.behavior == "replay":
            result["invocation"] = "another-invocation"
        output = b"{" if self.behavior == "truncated" else process.canonical(result)
        manifest = process.manifest_envelope(
            protocol=process.PROTOCOL,
            invocation=envelope["invocation"],
            payload=output,
            files=response_codec.file_records,
            request_sha256=process.digest((self.scratch / "request.json").read_bytes()),
        )
        if self.behavior == "bad-manifest-hash":
            manifest["envelopeSha256"] = "0" * 64
        process.write_exclusive(
            self.scratch / "result.json",
            output,
        )
        process.write_exclusive(
            self.scratch / "result.manifest.json",
            process.canonical(manifest),
        )
        if self.behavior == "extra-output":
            (self.scratch / "unexpected.bin").write_bytes(b"unexpected")
        if self.behavior == "result-sidecar-mutation" and response_codec.file_records:
            name = response_codec.file_records[0]["file"]
            (self.scratch / name).write_bytes(b"mutated")

    def exited(self):
        return self.behavior != "blocked" or self.terminated

    def empty(self):
        return self.terminated

    def exit_code(self):
        return 2 if self.behavior == "crash" else 0

    def terminate(self):
        self.terminated = True

    def wait_exit(self, deadline, *, clock):
        return self.exited() and self.empty()

    def close(self):
        self.closed = True


@pytest.mark.parametrize(
    "behavior",
    [
        "normal",
        "crash",
        "replay",
        "truncated",
        "bad-manifest-hash",
        "extra-output",
        "blocked",
        "assignment-failure",
    ],
)
def test_supervisor_lifecycle_and_cleanup(tmp_path, monkeypatch, behavior):
    monkeypatch.setattr(FakeJob, "behavior", behavior)
    monkeypatch.setattr(FakeJob, "result", response())
    ticks = iter([100, 100, 100, 126, 126, 126, 126, 126]) if behavior == "blocked" else None
    clock = (lambda: next(ticks, 126)) if ticks else lambda: 100
    if behavior == "normal":
        result = process.supervise(
            tmp_path,
            request(),
            deadline=125,
            finalization_deadline=135,
            clock=clock,
            backend=FakeJob,
        )
        assert result["report"]["validationComplete"] is True
    else:
        with pytest.raises((process.ProcessValidationError, json.JSONDecodeError)):
            process.supervise(
                tmp_path,
                request(),
                deadline=125,
                finalization_deadline=135,
                clock=clock,
                backend=FakeJob,
            )
    assert not FakeJob.last.scratch.exists()
    if behavior != "assignment-failure":
        assert FakeJob.last.terminated and FakeJob.last.closed


def test_combined_transfer_resource_peak_is_not_hidden(tmp_path, monkeypatch):
    result = response(success=True)
    result["resources"]["peakConstructionBufferBytes"] = 64 * 1024 * 1024 + 1
    monkeypatch.setattr(FakeJob, "behavior", "normal")
    monkeypatch.setattr(FakeJob, "result", result)
    transported = process.supervise(
        tmp_path,
        request(),
        deadline=125,
        finalization_deadline=135,
        clock=lambda: 100,
        backend=FakeJob,
    )
    assert transported["resources"]["peakConstructionBufferBytes"] > 64 * 1024 * 1024
    assert transported["processTransport"]["constructionPeakIncludingTransferBytes"] > (
        64 * 1024 * 1024
    )
    transport = transported["processTransport"]
    assert transport["requestEnvelopeBytes"] > 0
    assert transport["requestEnvelopeSha256"] == transport["requestSha256"]
    assert transport["responseEnvelopeBytes"] > 0
    assert transport["responseEnvelopeSha256"]
    assert transport["responseFiles"]


def test_supervisor_rejects_mutated_result_sidecar(tmp_path, monkeypatch):
    monkeypatch.setattr(FakeJob, "behavior", "result-sidecar-mutation")
    monkeypatch.setattr(FakeJob, "result", response(success=True))
    with pytest.raises(process.ProcessValidationError, match="sidecar"):
        process.supervise(
            tmp_path,
            request(),
            deadline=125,
            finalization_deadline=135,
            clock=lambda: 100,
            backend=FakeJob,
        )
    assert not FakeJob.last.scratch.exists()
    assert FakeJob.last.terminated and FakeJob.last.closed


def test_resource_report_keeps_construction_measurement_without_64_mib_gate():
    resource_values = {
        "replacementTriangleCount": 1,
        "replacementVertexCount": 3,
        "addedDrawCalls": 2,
        "runtimeAssetBytes": 100,
        "manifestBytes": 10,
        "qaBytes": 10,
        "addedResidentGeometryBytes": 80,
        "peakConstructionBufferBytes": 64 * 1024 * 1024 + 1,
        "peakConstructionBufferByteLimit": 64 * 1024 * 1024,
        "passes": False,
    }
    runner = {
        "_resource_report": lambda *args: dict(resource_values),
        "PATCH_MAX_TRIANGLES": 10,
        "PATCH_MAX_VERTICES": 10,
        "PATCH_MAX_ASSET_BYTES": 1000,
        "PATCH_MAX_MANIFEST_BYTES": 100,
        "PATCH_MAX_QA_BYTES": 100,
        "PATCH_MAX_RESIDENT_GEOMETRY_BYTES": 1000,
    }
    report = process.resource_report_without_construction_limit(runner, object(), {}, {}, {})
    assert report["peakConstructionBufferBytes"] == 64 * 1024 * 1024 + 1
    assert report["peakConstructionBufferByteLimit"] is None
    assert report["passes"] is True


def test_containment_failure_has_no_uncontained_fallback(tmp_path):
    calls = []

    def reject(*args, **kwargs):
        calls.append(args)
        raise process.ProcessValidationError("containment unavailable")

    with pytest.raises(process.ProcessValidationError, match="containment unavailable"):
        process.supervise(
            tmp_path,
            request(),
            deadline=125,
            finalization_deadline=135,
            clock=lambda: 100,
            backend=reject,
        )
    assert len(calls) == 1


def test_startup_exception_retains_child_and_scratch_until_exit_confirmed(tmp_path):
    import shutil

    observed = {}
    job = SimpleNamespace(
        pid=123456,
        terminate=lambda: observed.update(terminated=True),
        wait_exit=lambda deadline, **kwargs: False,
        close=lambda: observed.update(closed=True),
    )

    def failed_start(argv, root, **kwargs):
        observed["scratch"] = Path(argv[-1])
        observed["deadline"] = kwargs["finalization_deadline"]
        raise process.ProcessStartupError(job, ValueError("assignment failed"))

    with pytest.raises(process.ProcessValidationError, match="exit unconfirmed"):
        process.supervise(
            tmp_path,
            request(),
            deadline=125,
            finalization_deadline=135,
            clock=lambda: 100,
            backend=failed_start,
        )
    assert observed["terminated"] and observed["deadline"] == 135
    assert "closed" not in observed and observed["scratch"].is_dir()
    shutil.rmtree(observed["scratch"])  # Fake backend has no actual child.


def test_native_startup_termination_and_wait_results_are_checked():
    job = object.__new__(process.WindowsJob)
    calls = []
    job.process, job.job, job.pid, job.assigned = 1, 2, 123456, False
    job.kernel = SimpleNamespace(
        WaitForSingleObject=lambda handle, milliseconds: calls.append(milliseconds) or 258,
        TerminateProcess=lambda *args: False,
        TerminateJobObject=lambda *args: True,
    )
    with pytest.raises(process.ProcessValidationError, match="TerminateProcess failed"):
        job.terminate()
    assert job.wait_exit(100.05, clock=lambda: 100) is False
    assert 0 <= calls[-1] <= 50  # No fixed one-second wait beyond remaining budget.
    job.kernel.WaitForSingleObject = lambda *args: 0xFFFFFFFF
    with pytest.raises(process.ProcessValidationError, match="cleanup wait failed"):
        job.wait_exit(100.05, clock=lambda: 100)


def test_request_and_result_accounting_above_former_cap_are_not_rejected(tmp_path, monkeypatch):
    result = response(success=True)
    result["resources"]["peakConstructionBufferBytes"] = 64 * 1024 * 1024 + 1
    monkeypatch.setattr(FakeJob, "behavior", "normal")
    monkeypatch.setattr(FakeJob, "result", result)
    monkeypatch.setattr(
        process,
        "value_bound",
        lambda value, **kwargs: (64 * 1024 * 1024 + 1, 128),
    )
    assert process.validate_byte_count(64 * 1024 * 1024 + 1) is None
    transported = process.supervise(
        tmp_path,
        request(),
        deadline=125,
        finalization_deadline=135,
        clock=lambda: 100,
        backend=FakeJob,
    )
    assert transported["resources"]["peakConstructionBufferBytes"] > 64 * 1024 * 1024


def test_probe_failure_records_case_cleanup_and_all_unrun_cases(monkeypatch):
    import runpy

    module = runpy.run_path(
        str(Path(__file__).parents[1] / "scripts/profile_teignmouth_process_validation_v1.py")
    )

    class FailedImmediate:
        def __init__(self, *args, **kwargs):
            self.pid = 123456

        def exited(self):
            return True

        def exit_code(self):
            return 2

        def empty(self):
            return True

        def terminate(self):
            pass

        def wait_exit(self, *args):
            return True

        def close(self):
            pass

    module["containment_probe"].__globals__["WindowsJob"] = FailedImmediate
    result = module["containment_probe"](Path.cwd())
    assert result["passes"] is False
    assert [item["case"] for item in result["cases"]] == list(module["PROBE_CASES"])
    assert result["cases"][0]["outcome"] == "fail"
    assert result["cases"][0]["exitCodeBeforeCleanup"] == 2
    assert result["cases"][0]["cleanupConfirmed"] is True
    assert all(item["outcome"] == "not_run" for item in result["cases"][1:])


def test_worker_request_rejects_before_decode(tmp_path, monkeypatch):
    envelope = {
        "protocol": process.PROTOCOL,
        "invocation": TEST_INVOCATION,
        "request": {
            "tag": "bytes",
            "blob": {"file": "request-000000.bin", "bytes": 64 * 1024 * 1024, "sha256": "a" * 64},
        },
        "memory": {"baselineBytes": 64 * 1024 * 1024},
    }
    write_request_bundle(tmp_path, envelope)
    monkeypatch.setattr(process.Codec, "decode", lambda *args: pytest.fail("must preflight"))
    with pytest.raises(process.ProcessValidationError, match="sidecar length"):
        process.worker_main(tmp_path, tmp_path)


def test_worker_serializes_result_above_former_cap(tmp_path, monkeypatch):
    encoded = process.Codec(tmp_path, "request").encode(request())
    envelope = {
        "protocol": process.PROTOCOL,
        "invocation": TEST_INVOCATION,
        "request": encoded,
        "memory": {"baselineBytes": 100000},
    }
    write_request_bundle(tmp_path, envelope)
    result = response(success=True)
    result["resources"]["peakConstructionBufferBytes"] = 64 * 1024 * 1024 + 1
    monkeypatch.setattr(process, "execute_transaction", lambda *args, **kwargs: result)
    assert process.worker_main(tmp_path, tmp_path) == 0
    saved = json.loads((tmp_path / "result.json").read_bytes())
    assert saved["memory"]["constructionPeakBytes"] == 64 * 1024 * 1024 + 1
    result_manifest = json.loads((tmp_path / "result.manifest.json").read_bytes())
    assert result_manifest["envelopeBytes"] == (tmp_path / "result.json").stat().st_size
    assert result_manifest["files"] == process.encoded_file_manifest(saved["response"])


@pytest.mark.parametrize("mutation", ["envelope-hash", "unexpected-file", "sidecar-hash"])
def test_worker_rejects_unbound_request_files_before_decode(tmp_path, monkeypatch, mutation):
    codec = process.Codec(tmp_path, "request")
    encoded = codec.encode({**request(), "payload": b"synthetic bytes"})
    envelope = {
        "protocol": process.PROTOCOL,
        "invocation": TEST_INVOCATION,
        "request": encoded,
        "memory": {"baselineBytes": 0},
    }
    write_request_bundle(tmp_path, envelope)
    manifest_path = tmp_path / "request.manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    if mutation == "envelope-hash":
        manifest["envelopeSha256"] = "0" * 64
        manifest_path.write_bytes(process.canonical(manifest))
    elif mutation == "unexpected-file":
        (tmp_path / "extra.bin").write_bytes(b"unexpected")
    else:
        manifest["files"][0]["sha256"] = "0" * 64
        manifest_path.write_bytes(process.canonical(manifest))
    monkeypatch.setattr(process.Codec, "decode", lambda *args: pytest.fail("must preflight"))
    with pytest.raises(process.ProcessValidationError):
        process.worker_main(tmp_path, tmp_path)


def test_successful_assembly_reaches_assets_above_former_cap(monkeypatch):
    import runpy
    import sys

    import shapely

    from torquay_pipeline import road_surface_validation_v2 as validator

    root = Path(__file__).resolve().parents[2]
    wrapper = runpy.run_path(
        str(root / "pipeline/scripts/run_teignmouth_topology_validation_v2.py")
    )
    config_path = root / "config/road-surface-teignmouth-topology-transition-v2.json"
    config = json.loads(config_path.read_bytes())
    mesh = SimpleNamespace(
        vertices_xz=np.zeros((3, 2)),
        base_y=np.zeros(3),
        triangles=np.asarray([[0, 1, 2]], dtype="<u4"),
    )
    surface = SimpleNamespace(mesh=mesh, patch_heights=np.zeros(3, dtype="<f4"))
    bindings = {
        "runtimeHashes": {
            **wrapper["_runtime_code_hashes"](config, root),
            config_path.relative_to(root).as_posix(): process.digest(config_path.read_bytes()),
        },
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "shapely": shapely.__version__,
            "geos": shapely.geos_version_string,
        },
        "dataSourceManifestSha256": process.digest(
            (root / "data/source-manifest.json").read_bytes()
        ),
    }
    synthetic = {
        "surface": surface,
        "bindings": bindings,
        "candidateSha256": process.digest(surface.patch_heights.tobytes()),
        "influence": None,
        "constraints": [],
        "solver": {},
        "acceptedPreviewHashes": {},
        "deadline": 125,
        "_transportBaselineBytes": 64 * 1024 * 1024,
    }
    monkeypatch.setattr(
        validator,
        "validate_offline_candidate_v2",
        lambda *args, **kwargs: (
            {"passes": True, "roadPathReclip": {"groups": {}}},
            SimpleNamespace(gate_seconds={}),
        ),
    )

    class ReachedAssembly(Exception):
        pass

    monkeypatch.setattr(
        patch,
        "assemble_deterministic_candidate_assets",
        lambda *args: (_ for _ in ()).throw(ReachedAssembly()),
    )
    with pytest.raises(ReachedAssembly):
        process.execute_transaction(synthetic, root=root)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "ASCII",
        '"\\\n\r\t\b\f\x00\x1f',
        "caf\u00e9",
        "e\u0301",
        "\uffff",
        "\U00010000",
        "\U0001f600",
        "\U0010ffff",
        "\ud800",
        "\udfff",
        "a\U0001f600\ud800\u0301\\\n",
    ],
)
def test_unicode_string_bound_covers_unchanged_ascii_json_bytes(text):
    expected = json.dumps(text, ensure_ascii=True, allow_nan=False).encode("ascii")
    assert process.json_string_bound(text) >= len(expected)
    assert process.value_bound(text) == (0, process.json_string_bound(text))
    assert process.canonical(text) == expected


def test_supplementary_code_point_reserves_both_surrogate_escapes():
    assert process.json_string_bound("\U0001f600") == 14
    assert process.canonical("\U0001f600") == b'"\\ud83d\\ude00"'
    assert process.json_string_bound("\ud800") == 8


@pytest.mark.parametrize(
    "value",
    [
        Path("synthetic/\U0001f600/\U0010ffff"),
        {"\U0001f600": ["\U0010ffff", ("\ud800", "e\u0301")]},
        {(1, "\U0001f600"): {Path("\U0010ffff"): [None, True, 3, 1.25]}},
        {"path": Path("\ud800"), 3: "\uffff", False: "\U00010000"},
    ],
)
def test_unicode_paths_keys_and_nested_values_cover_encoded_structure(tmp_path, value):
    binary, metadata = process.value_bound(value)
    encoder = process.Codec(tmp_path, "request")
    encoded = encoder.encode(value)
    assert metadata >= len(process.canonical(encoded))
    assert binary >= encoder.byte_count


def test_unicode_bound_includes_dataclass_structure(tmp_path):
    mesh = _small_patch_surface().mesh
    binary, metadata = process.value_bound(mesh)
    encoder = process.Codec(tmp_path, "request")
    encoded = encoder.encode(mesh)
    assert metadata >= len(process.canonical(encoded))
    assert binary >= encoder.byte_count


def test_non_bmp_accounting_above_former_cap_is_observational_only():
    # Keep the source string only; do not allocate its larger escaped JSON form.
    former_cap = 64 * 1024 * 1024
    empty_metadata = process.value_bound({"payload": ""})[1]
    count = (former_cap // 4 - 1024 - empty_metadata) // 12 + 1
    payload = {"payload": "\U0001f600" * count}
    _, metadata = process.value_bound(payload)
    assert 4 * (metadata + 1024) > former_cap
    assert process.validate_byte_count(4 * (metadata + 1024)) is None


def test_canonical_bytes_remain_identical_to_previous_serializer():
    value = {"\U0001f600": ["\ud800", "a\n\\", "\u0301", "\U0010ffff", 1.25, None]}
    before = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    assert process.canonical(value) == before
