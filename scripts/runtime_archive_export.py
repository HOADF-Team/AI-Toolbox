"""Prepare complete, verifier-compatible cryptographic runtime archives.

This exporter accepts only an explicit source-file allowlist. It validates that the
allowlist is complete for the declared run and refuses private-key material.
"""
from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from runtime_run_archive import create_runtime_archive


class RuntimeArchiveExportError(ValueError):
    """Raised when an export mapping is incomplete or unsafe."""


_SHA256 = re.compile(r"[0-9a-f]{64}$")
_STAGE_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}$")
_PRIVATE_KEY_MARKERS = (
    b"-----BEGIN PRIVATE KEY-----",
    b"-----BEGIN ENCRYPTED PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"-----BEGIN EC PRIVATE KEY-----",
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
)


def _relative(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or chr(92) in value:
        raise RuntimeArchiveExportError("unsafe_export_path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise RuntimeArchiveExportError("unsafe_export_path")
    if path.as_posix() != value or ":" in path.parts[0]:
        raise RuntimeArchiveExportError("non_normalized_export_path")
    return path


def _source_file(root: Path, relative: str) -> Path:
    rel = _relative(relative)
    base = root.resolve(strict=True)
    current = base
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise RuntimeArchiveExportError("source_symlink_not_allowed")
    try:
        resolved = current.resolve(strict=True)
        resolved.relative_to(base)
    except (OSError, ValueError) as exc:
        raise RuntimeArchiveExportError("source_file_missing_or_outside_root") from exc
    if not resolved.is_file():
        raise RuntimeArchiveExportError("source_must_be_regular_file")
    return resolved


def _json_file(root: Path, files: dict[str, str], archive_path: str) -> Any:
    source_name = files.get(archive_path)
    if not isinstance(source_name, str):
        raise RuntimeArchiveExportError(f"required_export_file_missing:{archive_path}")
    try:
        return json.loads(_source_file(root, source_name).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeArchiveExportError(f"invalid_export_json:{archive_path}") from exc


def create_cryptographic_runtime_archive(
    source_root: Path,
    destination: Path,
    metadata: dict[str, Any],
    files: dict[str, str],
) -> dict[str, Any]:
    """Create a complete archive layout accepted by the cryptographic verifier.

    files maps archive-relative paths to source-relative paths. The exporter
    derives the required package layout from the contract, stage integrity
    statements, trust registry, and registry history. It never searches for files
    or includes anything not explicitly mapped by the caller.
    """
    if not isinstance(metadata, dict) or not isinstance(files, dict):
        raise RuntimeArchiveExportError("metadata_and_file_map_required")
    policy = metadata.get("verification_policy")
    if not isinstance(policy, dict) or policy.get("require_trusted_timestamp") is not True:
        raise RuntimeArchiveExportError("cryptographic_archive_requires_trusted_timestamps")
    policy_version = metadata.get("verification_policy_version")
    if policy_version is not None and (type(policy_version) is not int or policy_version != 2):
        raise RuntimeArchiveExportError("unsupported_verification_policy_version")
    if policy_version == 2 and policy.get("require_tsa_revocation") is not True:
        raise RuntimeArchiveExportError("version_2_policy_requires_tsa_revocation")
    stage_ids = metadata.get("stage_ids")
    skill_ids = metadata.get("skill_ids")
    if (
        not isinstance(stage_ids, list) or not stage_ids
        or any(not isinstance(item, str) or not _STAGE_ID.fullmatch(item) for item in stage_ids)
        or len(set(stage_ids)) != len(stage_ids)
        or not isinstance(skill_ids, list) or len(skill_ids) != len(stage_ids)
        or any(not isinstance(item, str) or not item for item in skill_ids)
    ):
        raise RuntimeArchiveExportError("invalid_export_stage_metadata")

    normalized: dict[str, str] = {}
    for archive_name, source_name in files.items():
        archive_path = _relative(archive_name).as_posix()
        source_path = _relative(source_name).as_posix()
        if archive_path in normalized:
            raise RuntimeArchiveExportError("duplicate_export_path")
        normalized[archive_path] = source_path

    source_base = Path(source_root).resolve(strict=True)
    contract = _json_file(source_base, normalized, "workflow/contract.json")
    if not isinstance(contract, dict) or contract.get("workflow_id") != metadata.get("workflow_id"):
        raise RuntimeArchiveExportError("export_workflow_contract_mismatch")
    stages = contract.get("stages")
    if not isinstance(stages, list) or [item.get("id") for item in stages if isinstance(item, dict)] != stage_ids:
        raise RuntimeArchiveExportError("export_contract_stage_sequence_mismatch")
    contract_skills = [
        item.get("skill_id", item.get("id")) if isinstance(item, dict) else None
        for item in stages
    ]
    if contract_skills != skill_ids:
        raise RuntimeArchiveExportError("export_contract_skill_sequence_mismatch")

    required_paths = {
        "workflow/contract.json",
        "trust/registry.json",
        "trust/history.json",
        "trust/history-checkpoint.json",
        "trust/history-anchor.json",
        "trust/history-anchor.tsr",
    }
    registry = _json_file(source_base, normalized, "trust/registry.json")
    history = _json_file(source_base, normalized, "trust/history.json")
    if not isinstance(registry, dict) or registry.get("registry_version") != "1.0":
        raise RuntimeArchiveExportError("export_trust_registry_invalid")
    if not isinstance(registry.get("keys"), list) or not registry["keys"]:
        raise RuntimeArchiveExportError("export_trust_registry_keys_required")
    if not isinstance(history, list):
        raise RuntimeArchiveExportError("export_registry_history_invalid")

    for entry in registry["keys"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("public_key_file"), str):
            raise RuntimeArchiveExportError("export_registry_public_key_reference_invalid")
        public_key = _relative(entry["public_key_file"]).as_posix()
        required_paths.add(f"trust/keys/{public_key}")

    for record in history:
        event = record.get("event") if isinstance(record, dict) else None
        digest = event.get("registry_sha256") if isinstance(event, dict) else None
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise RuntimeArchiveExportError("export_history_snapshot_reference_invalid")
        required_paths.add(f"trust/registry-snapshots/{digest}.json")

    for index, stage_id in enumerate(stage_ids):
        result_path = f"workflow/stages/{stage_id}.json"
        required_paths.add(result_path)
        required_paths.add(f"workflow/stages/{stage_id}/timestamp.tsr")
        result = _json_file(source_base, normalized, result_path)
        if not isinstance(result, dict) or result.get("status") != "completed":
            raise RuntimeArchiveExportError(f"export_stage_not_completed:{stage_id}")
        if result.get("stage") != stage_id or result.get("skill_id") != skill_ids[index]:
            raise RuntimeArchiveExportError(f"export_stage_identity_mismatch:{stage_id}")
        envelope = result.get("artifact_provenance")
        if not isinstance(envelope, dict):
            raise RuntimeArchiveExportError(f"export_stage_provenance_missing:{stage_id}")
        bundle = result.get("integrity_bundle")
        if not isinstance(bundle, dict) or not isinstance(bundle.get("statement"), dict):
            raise RuntimeArchiveExportError(f"export_stage_integrity_bundle_missing:{stage_id}")
        context = bundle["statement"].get("execution_context")
        if not isinstance(context, dict) or any(
            context.get(key) != expected
            for key, expected in {
                "run_id": metadata["run_id"],
                "workflow_id": metadata["workflow_id"],
                "stage_id": stage_id,
                "skill_id": skill_ids[index],
                "input_ref": result.get("input_ref"),
            }.items()
        ):
            raise RuntimeArchiveExportError(f"export_signed_context_mismatch:{stage_id}")
        evidence = bundle["statement"].get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise RuntimeArchiveExportError(f"export_stage_evidence_manifest_missing:{stage_id}")
        evidence_paths: set[str] = set()
        for item in evidence:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                raise RuntimeArchiveExportError(f"export_stage_evidence_entry_invalid:{stage_id}")
            relative_evidence = _relative(item["path"]).as_posix()
            archive_evidence = f"workflow/stages/{stage_id}/evidence/{relative_evidence}"
            if archive_evidence in evidence_paths:
                raise RuntimeArchiveExportError(f"export_duplicate_stage_evidence:{stage_id}")
            evidence_paths.add(archive_evidence)
        required_paths.update(evidence_paths)

    missing = sorted(required_paths - set(normalized))
    unexpected = sorted(set(normalized) - required_paths)
    if missing:
        raise RuntimeArchiveExportError("export_required_files_missing:" + ",".join(missing))
    if unexpected:
        raise RuntimeArchiveExportError("export_unexpected_files:" + ",".join(unexpected))

    for archive_name, source_name in normalized.items():
        if "private" in archive_name.lower().split("/")[-1] or "private" in source_name.lower().split("/")[-1]:
            raise RuntimeArchiveExportError("private_key_filename_not_allowed")
        data = _source_file(source_base, source_name).read_bytes()
        if any(marker in data for marker in _PRIVATE_KEY_MARKERS):
            raise RuntimeArchiveExportError("private_key_material_not_allowed")

    return create_runtime_archive(source_base, Path(destination), metadata, normalized)
