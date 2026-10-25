"""Named timing and input-map transition for remaining Teignmouth trials."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import road_surface
from .road_surface_patch import RoadSurfacePatchError
from .road_surface_study import RAW_TRIAL_FILES

TRANSITION_ID = "teignmouth-validation-window-120-125-135-v2"
PREPARATION_SOLVER_SECONDS = 120.0
VALIDATION_CUTOFF_SECONDS = 125.0
FINALIZATION_CUTOFF_SECONDS = 135.0
QUALIFICATION_SECONDS = 125.0
MAXIMUM_ITERATIONS = 2_000
FINALIZATION_RESERVE_SECONDS = 10.0
ELIGIBLE_TRIALS = ("collar-05", "local-025", "local-0125")
CONSUMED_TRIALS = ("flip-05", "road-05")
EVIDENCE_TREE_KEY = "studyEvidenceTree:docs/milestones/artifacts/Road-surface-treatment"
CHECKPOINT_KEY = "protected:.codex/torquay-plan-implementation.md"


class TransitionDeadlineExceeded(RoadSurfacePatchError):
    """A named transition phase exceeded its fixed cutoff."""


@dataclass(frozen=True)
class TransitionDeadlines:
    """Absolute deadlines measured from one invocation timestamp T0."""

    invocation_start: float

    @property
    def solver(self) -> float:
        return self.invocation_start + PREPARATION_SOLVER_SECONDS

    @property
    def validation(self) -> float:
        return self.invocation_start + VALIDATION_CUTOFF_SECONDS

    @property
    def finalization(self) -> float:
        return self.invocation_start + FINALIZATION_CUTOFF_SECONDS

    def remaining_solver(self, now: float) -> float:
        return max(0.0, self.solver - now)

    def check(self, phase: str, now: float) -> float:
        limits = {
            "preparation": self.solver,
            "solver": self.solver,
            "validation": self.validation,
            "finalization": self.finalization,
        }
        if phase not in limits:
            raise ValueError(f"unknown trial phase {phase!r}")
        remaining = limits[phase] - now
        if remaining <= 0:
            raise TransitionDeadlineExceeded(f"{phase} cutoff reached")
        return remaining

    def qualification(self, elapsed_including_finalization: float) -> bool:
        return 0.0 <= elapsed_including_finalization <= QUALIFICATION_SECONDS


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def admit_remaining_trial(trial_id: str) -> None:
    if trial_id not in ELIGIBLE_TRIALS:
        if trial_id in CONSUMED_TRIALS:
            raise RoadSurfacePatchError(f"trial {trial_id} is consumed and cannot be retried")
        raise RoadSurfacePatchError(f"trial {trial_id!r} is not eligible under transition v2")


def validate_prior_input_transition(
    raw_root: Path,
    trial_id: str,
    current_map: dict[str, str],
    expected_current_digest: str,
    *,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Allow exactly the pinned inventory/checkpoint transition for old attempts.

    New v2 attempts must match the current input map exactly. Previous topology
    and refinement prerequisites are still validated by the frozen stage-order
    validators before this function is called.
    """
    if canonical_digest(current_map) != expected_current_digest:
        raise RoadSurfacePatchError("current protected map does not match its invocation digest")
    try:
        current_index = tuple(config["eligible_trial_ids"]).index(trial_id)
    except (KeyError, ValueError, TypeError) as exc:
        raise RoadSurfacePatchError("trial is not admitted by the transition config") from exc
    if tuple(config["eligible_trial_ids"]) != ELIGIBLE_TRIALS:
        raise RoadSurfacePatchError(
            "transition config eligibility differs from the fixed allowlist"
        )

    checkpoint_policy = config["input_state_transition"]
    old_checkpoint = checkpoint_policy["legacy_checkpoint_sha256"]
    old_tree = checkpoint_policy["legacy_evidence_tree_sha256"]
    new_tree = checkpoint_policy["current_evidence_tree_sha256"]
    current_checkpoint = current_map.get(CHECKPOINT_KEY)
    if not isinstance(current_checkpoint, str) or len(current_checkpoint) != 64:
        raise RoadSurfacePatchError("current checkpoint digest is missing or malformed")
    if current_checkpoint == checkpoint_policy["implementation_start_checkpoint_sha256"]:
        raise RoadSurfacePatchError(
            "checkpoint has not recorded the named validation transition state"
        )
    if current_map.get(EVIDENCE_TREE_KEY) != new_tree:
        raise RoadSurfacePatchError(
            "current evidence tree differs from the pinned transition target"
        )

    previous_ids = CONSUMED_TRIALS + ELIGIBLE_TRIALS[:current_index]
    transitions = []
    for previous_id in previous_ids:
        trial_dir = raw_root / previous_id
        attempt = _read_json(trial_dir / "attempt.json", f"{previous_id} attempt")
        aggregate = _read_json(trial_dir / "offline-aggregate.json", f"{previous_id} aggregate")
        previous_map = aggregate.get("protectedHashesAfter")
        if not isinstance(previous_map, dict):
            raise RoadSurfacePatchError(f"{previous_id} aggregate has no final protected map")
        if set(previous_map) != set(current_map):
            raise RoadSurfacePatchError(f"{previous_id} protected map key set changed")
        if previous_id in CONSUMED_TRIALS:
            expected_legacy_codes = config.get(
                "legacy_road05_code_hashes"
                if previous_id == "road-05"
                else "legacy_flip05_code_hashes"
            )
            recorded_codes = attempt.get("codeHashes")
            if (
                not isinstance(expected_legacy_codes, dict)
                or recorded_codes != expected_legacy_codes
            ):
                raise RoadSurfacePatchError(
                    f"{previous_id} immutable legacy code-hash map differs from its pin"
                )
            if aggregate.get("protectedHashesBefore") != attempt.get("protectedHashesBefore"):
                raise RoadSurfacePatchError(
                    f"{previous_id} aggregate before map differs from the retained attempt"
                )
            if canonical_digest(attempt["protectedHashesBefore"]) != attempt.get(
                "inputSnapshotSha256"
            ):
                raise RoadSurfacePatchError(f"{previous_id} attempt input-map digest is invalid")
            if (
                aggregate.get("codeHashesBefore") != recorded_codes
                or aggregate.get("codeHashesAfter") != recorded_codes
            ):
                raise RoadSurfacePatchError(f"{previous_id} code-hash maps differ from attempt")
            if aggregate.get("codeUnchangedDuringTrial") is not True:
                raise RoadSurfacePatchError(f"{previous_id} did not preserve its code identity")
            if aggregate.get("studyConfigSha256Before") != attempt.get(
                "studyConfigSha256"
            ) or aggregate.get("studyConfigSha256After") != attempt.get("studyConfigSha256"):
                raise RoadSurfacePatchError(f"{previous_id} study-config identity changed")
            if aggregate.get("baseCandidateConfigSha256Before") != attempt.get(
                "baseCandidateConfigSha256"
            ) or aggregate.get("baseCandidateConfigSha256After") != attempt.get(
                "baseCandidateConfigSha256"
            ):
                raise RoadSurfacePatchError(f"{previous_id} base-config identity changed")
            if (
                aggregate.get("candidatePublicOutputWritten") is not False
                or aggregate.get("candidateOutputStillAbsent") is not True
            ):
                raise RoadSurfacePatchError(f"{previous_id} claims a candidate output")
            if aggregate.get("releaseId") not in (None, config["pinned_inputs"]["release_id"]):
                raise RoadSurfacePatchError(f"{previous_id} release identity differs from pin")
            if attempt.get("releaseId") != config["pinned_inputs"]["release_id"]:
                raise RoadSurfacePatchError(f"{previous_id} attempt release identity differs")
            if attempt.get("acceptedPreviewHashes") != config["pinned_inputs"]["accepted_preview"]:
                raise RoadSurfacePatchError(f"{previous_id} accepted-preview identity differs")
            if previous_map.get(CHECKPOINT_KEY) != old_checkpoint:
                raise RoadSurfacePatchError(
                    f"{previous_id} checkpoint does not match the approved transition source"
                )
            if previous_map.get(EVIDENCE_TREE_KEY) != old_tree:
                raise RoadSurfacePatchError(
                    f"{previous_id} evidence tree does not match the approved transition source"
                )
            if (
                previous_id == "flip-05"
                and attempt["protectedHashesBefore"].get(CHECKPOINT_KEY)
                != checkpoint_policy["flip05_interrupted_checkpoint_sha256"]
            ):
                raise RoadSurfacePatchError(
                    "flip-05 invocation checkpoint differs from the pinned interruption source"
                )
            differences = {key for key in current_map if previous_map[key] != current_map[key]}
            if differences != {CHECKPOINT_KEY, EVIDENCE_TREE_KEY}:
                raise RoadSurfacePatchError(
                    f"{previous_id} has unapproved protected-input differences: "
                    f"{sorted(differences)}"
                )
            if (
                previous_map.get(CHECKPOINT_KEY) != old_checkpoint
                or previous_map.get(EVIDENCE_TREE_KEY) != old_tree
            ):
                raise RoadSurfacePatchError("legacy input transition source hashes changed")
            if previous_id == "road-05" and previous_map != attempt.get("protectedHashesBefore"):
                raise RoadSurfacePatchError(
                    "road-05 after map differs from its exact invocation input map"
                )
            if previous_id == "flip-05" and aggregate.get(
                "postInterruptionInputSnapshotSha256"
            ) != canonical_digest(previous_map):
                raise RoadSurfacePatchError(
                    "flip-05 reconciliation digest differs from its retained after map"
                )
        elif previous_map != current_map:
            raise RoadSurfacePatchError(
                f"{previous_id} protected inputs differ from the current exact snapshot"
            )
        before = attempt.get("protectedHashesBefore")
        if not isinstance(before, dict) or canonical_digest(before) != attempt.get(
            "inputSnapshotSha256"
        ):
            raise RoadSurfacePatchError(f"{previous_id} attempt input digest is invalid")
        transitions.append(
            {
                "trialId": previous_id,
                "recordedInputSnapshotSha256": attempt["inputSnapshotSha256"],
                "finalProtectedMapSha256": canonical_digest(previous_map),
                "permittedLegacyDifferences": sorted(
                    key for key in current_map if previous_map[key] != current_map[key]
                ),
            }
        )
    return {
        "transitionId": TRANSITION_ID,
        "currentInputSnapshotSha256": expected_current_digest,
        "currentProtectedEntryCount": len(current_map),
        "priorInputTransitions": transitions,
        "passed": True,
    }


def tree_digest_excluding(root: Path, excluded_relative: str) -> str:
    """Hash a stable file tree using the study runner format, omitting one exact file."""
    excluded = Path(excluded_relative).as_posix()
    digest = hashlib.sha256()
    for current, child_dirs, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in sorted(child_dirs):
            child = current_path / name
            if (
                child.is_symlink()
                or getattr(child.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400
            ):
                raise RoadSurfacePatchError(f"evidence tree has a reparse directory: {child}")
        for name in sorted(filenames):
            child = current_path / name
            relative = child.relative_to(root).as_posix()
            if relative == excluded:
                continue
            if (
                child.is_symlink()
                or getattr(child.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400
            ):
                raise RoadSurfacePatchError(f"evidence tree has a reparse file: {child}")
            payload_digest = file_digest(child)
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(child.stat().st_size).encode("ascii"))
            digest.update(b"\0")
            digest.update(payload_digest.encode("ascii"))
            digest.update(b"\n")
    return digest.hexdigest()


def validate_consumed_trial_inventory(
    project_root: Path,
    inventory: dict[str, Any],
    *,
    raw_trial_directory: str,
) -> dict[str, Any]:
    """Bind both consumed directories to every entry in the pinned inventory."""
    root = project_root.resolve(strict=True)
    trial_root = root / raw_trial_directory
    road_surface._assert_no_reparse_components(trial_root)
    if not trial_root.is_dir():
        raise RoadSurfacePatchError("consumed raw trial root is missing")
    if set(inventory) != set(CONSUMED_TRIALS):
        raise RoadSurfacePatchError("consumed trial inventory IDs differ from the fixed set")
    summary: dict[str, Any] = {}
    expected_names = set(RAW_TRIAL_FILES)
    for trial_id in CONSUMED_TRIALS:
        trial_path = trial_root / trial_id
        road_surface._assert_no_reparse_components(trial_path)
        if not trial_path.is_dir():
            raise RoadSurfacePatchError(f"consumed trial directory is missing: {trial_id}")
        expected_files = inventory[trial_id]
        if not isinstance(expected_files, dict) or set(expected_files) != expected_names:
            raise RoadSurfacePatchError(f"consumed file inventory differs for {trial_id}")
        actual_children = list(trial_path.iterdir())
        if any(
            child.is_dir() or road_surface._is_reparse_point(child) for child in actual_children
        ):
            raise RoadSurfacePatchError(f"consumed trial contains an unsafe child: {trial_id}")
        if {child.name for child in actual_children} != expected_names:
            raise RoadSurfacePatchError(f"consumed trial file set differs for {trial_id}")
        verified: dict[str, dict[str, Any]] = {}
        for name in sorted(expected_names):
            entry = expected_files[name]
            path = trial_path / name
            if (
                not isinstance(entry, dict)
                or not isinstance(entry.get("byteLength"), int)
                or isinstance(entry.get("byteLength"), bool)
                or not isinstance(entry.get("sha256"), str)
            ):
                raise RoadSurfacePatchError(f"malformed consumed file inventory: {trial_id}/{name}")
            if path.stat().st_size != entry["byteLength"] or file_digest(path) != entry["sha256"]:
                raise RoadSurfacePatchError(f"consumed trial bytes differ: {trial_id}/{name}")
            verified[name] = {
                "byteLength": entry["byteLength"],
                "sha256": entry["sha256"],
            }
        summary[trial_id] = verified
    return summary


def validate_transition_inputs(
    project_root: Path,
    current_map: dict[str, str],
    *,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Verify the pinned source, evidence-inventory and named checkpoint transition."""
    root = project_root.resolve(strict=True)
    expected = config["input_state_transition"]
    inventory = config["consumed_inventory"]
    inventory_path = root / inventory["path"]
    if not inventory_path.is_file() or inventory_path.is_symlink():
        raise RoadSurfacePatchError("consumed trial inventory is missing or unsafe")
    if inventory_path.stat().st_size != inventory["byte_length"]:
        raise RoadSurfacePatchError("consumed trial inventory byte length changed")
    if file_digest(inventory_path) != inventory["sha256"]:
        raise RoadSurfacePatchError("consumed trial inventory hash changed")
    try:
        inventory_payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoadSurfacePatchError(f"consumed trial inventory is unreadable: {exc}") from exc
    retained_trial_files = validate_consumed_trial_inventory(
        root,
        inventory_payload,
        raw_trial_directory=inventory["raw_trial_directory"],
    )

    evidence_root = root / expected["evidence_tree_path"]
    if (
        tree_digest_excluding(evidence_root, inventory["tree_relative_path"])
        != expected["legacy_evidence_tree_sha256"]
    ):
        raise RoadSurfacePatchError(
            "excluding only the exact consumed inventory does not restore the legacy evidence tree"
        )
    current_tree = _tree_digest(evidence_root)
    if current_tree != expected["current_evidence_tree_sha256"]:
        raise RoadSurfacePatchError("current Road-surface-treatment evidence tree differs from pin")
    if current_map.get(EVIDENCE_TREE_KEY) != current_tree:
        raise RoadSurfacePatchError("protected input map does not bind the complete evidence tree")

    checkpoint_path = root / expected["checkpoint_path"]
    if checkpoint_path.is_symlink() or not checkpoint_path.is_file():
        raise RoadSurfacePatchError("coordinator checkpoint is missing or unsafe")
    checkpoint_hash = file_digest(checkpoint_path)
    if current_map.get(CHECKPOINT_KEY) != checkpoint_hash:
        raise RoadSurfacePatchError("protected input map does not bind current checkpoint bytes")
    checkpoint_text = checkpoint_path.read_text(encoding="utf-8")
    activation = config.get("activation", {})
    if activation.get("enabled") is True:
        approval_chain = config.get("approval_chain", {})
        receipt_relative = approval_chain.get("coordinator_receipt_path")
        if not isinstance(receipt_relative, str):
            raise RoadSurfacePatchError("active transition has no coordinator receipt binding")
        receipt_path = root / receipt_relative
        road_surface._assert_no_reparse_components(receipt_path)
        if not receipt_path.is_file() or receipt_path.is_symlink():
            raise RoadSurfacePatchError("active transition coordinator receipt is missing")
        marker = approval_chain.get("accepted_checkpoint_marker_prefix", "") + file_digest(
            receipt_path
        )
        marker_prefix = approval_chain.get("accepted_checkpoint_marker_prefix", "")
        stale_marker = expected["required_checkpoint_marker"]
        if (
            not isinstance(marker_prefix, str)
            or not marker_prefix
            or checkpoint_text.count(marker_prefix) != 1
            or stale_marker in checkpoint_text
        ):
            raise RoadSurfacePatchError(
                "active checkpoint marker count or pending state is invalid"
            )
    else:
        marker = expected["required_checkpoint_marker"]
    if checkpoint_text.count(marker) != 1:
        raise RoadSurfacePatchError(
            "checkpoint does not contain exactly one named transition marker"
        )

    pinned = config["pinned_inputs"]
    if current_map.get(CHECKPOINT_KEY) == pinned["implementation_start_checkpoint_sha256"]:
        raise RoadSurfacePatchError("checkpoint remains at the pre-implementation baseline")
    for asset_name, digest in pinned["accepted_preview"].items():
        if current_map.get(f"acceptedPreview:{asset_name}") != digest:
            raise RoadSurfacePatchError(f"accepted-preview input changed: {asset_name}")
    if (
        current_map.get(f"protected:{pinned['source_manifest_path']}")
        != pinned["source_manifest_sha256"]
    ):
        raise RoadSurfacePatchError("pinned source manifest changed")
    for relative, digest in pinned["release_files"].items():
        if current_map.get(f"release:{relative}") != digest:
            raise RoadSurfacePatchError(f"pinned release asset changed: {relative}")
    return {
        "passed": True,
        "checkpointSha256": checkpoint_hash,
        "checkpointBaselineAtImplementationStartSha256": pinned[
            "implementation_start_checkpoint_sha256"
        ],
        "evidenceTreeSha256": current_tree,
        "legacyEvidenceTreeReconstructedSha256": expected["legacy_evidence_tree_sha256"],
        "inventory": {
            "path": inventory["path"],
            "byteLength": inventory["byte_length"],
            "sha256": inventory["sha256"],
        },
        "retainedTrialInventory": retained_trial_files,
    }


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for current, child_dirs, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in sorted(child_dirs):
            child = current_path / name
            if (
                child.is_symlink()
                or getattr(child.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400
            ):
                raise RoadSurfacePatchError(f"evidence tree has a reparse directory: {child}")
        for name in sorted(filenames):
            child = current_path / name
            if (
                child.is_symlink()
                or getattr(child.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400
            ):
                raise RoadSurfacePatchError(f"evidence tree has a reparse file: {child}")
            relative = child.relative_to(root).as_posix()
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(child.stat().st_size).encode("ascii"))
            digest.update(b"\0")
            digest.update(file_digest(child).encode("ascii"))
            digest.update(b"\n")
    return digest.hexdigest()


def _read_json(path: Path, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoadSurfacePatchError(f"cannot read {description}: {exc}") from exc
    if not isinstance(value, dict):
        raise RoadSurfacePatchError(f"{description} must be a JSON object")
    return value


def phase_for_runner_check(phase: str) -> str:
    """Map frozen runner check labels onto the accepted absolute windows."""
    if phase in {
        "path preflight",
        "pinned input loading",
        "protected-input snapshot",
        "stage identity validation",
        "one-shot record creation",
        "target influence preparation",
        "topology mesh construction",
        "topology validation",
        "topology report generation",
        "constraint preparation",
        "bounded solver",
    }:
        return "solver"
    if phase == "solver result validation":
        return "solver"
    if phase == "offline aggregate validation":
        return "validation"
    if phase in {"independent asset assembly", "resource and determinism validation"}:
        return "validation"
    raise RoadSurfacePatchError(f"runner emitted an unmapped transition phase {phase!r}")
