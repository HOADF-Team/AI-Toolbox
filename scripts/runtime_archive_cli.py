"""Command-line interface for portable runtime archive export and offline audit.

The CLI is a thin local wrapper around the existing archive exporter and verifier.
It never discovers source files, contacts a TSA, or authorizes runtime handoff.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from runtime_archive_export import create_cryptographic_runtime_archive
from runtime_archive_verification import verify_runtime_archive_cryptographically


class RuntimeArchiveCLIError(ValueError):
    """Raised when a CLI request or host trust configuration is invalid."""


_PRIVATE_MARKERS = (
    b"-----BEGIN PRIVATE KEY-----",
    b"-----BEGIN ENCRYPTED PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"-----BEGIN EC PRIVATE KEY-----",
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
)
_EXPORT_FIELDS = {"source_root", "destination", "metadata", "files"}
_TRUST_FIELDS = {
    "history_anchor_public_key",
    "history_anchor_key_id",
    "timestamp_ca_file",
}
_OPTIONAL_TRUST_FIELDS = {
    "timestamp_untrusted_chain_file",
    "require_trusted_timestamps",
}


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeArchiveCLIError(f"{label}_file_unavailable")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeArchiveCLIError(f"{label}_file_invalid_json") from exc
    if not isinstance(value, dict):
        raise RuntimeArchiveCLIError(f"{label}_must_be_json_object")
    return value


def _resolve_path(value: Any, base: Path, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeArchiveCLIError(f"{label}_path_required")
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    if candidate.is_symlink():
        raise RuntimeArchiveCLIError(f"{label}_symlink_not_allowed")
    return candidate


def _validate_trust_file(path: Path, label: str) -> Path:
    if path.is_symlink() or not path.is_file():
        raise RuntimeArchiveCLIError(f"{label}_file_unavailable")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise RuntimeArchiveCLIError(f"{label}_file_unreadable") from exc
    if any(marker in data for marker in _PRIVATE_MARKERS):
        raise RuntimeArchiveCLIError(f"{label}_private_key_material_not_allowed")
    return path


def load_trust_policy(config_path: Path) -> dict[str, Any]:
    """Load independently provisioned trust roots from a verifier-host JSON file."""
    config = _load_json(config_path, "trust_config")
    unknown = set(config) - _TRUST_FIELDS - _OPTIONAL_TRUST_FIELDS
    missing = _TRUST_FIELDS - set(config)
    if missing:
        raise RuntimeArchiveCLIError("trust_config_missing_fields:" + ",".join(sorted(missing)))
    if unknown:
        raise RuntimeArchiveCLIError("trust_config_unknown_fields:" + ",".join(sorted(unknown)))
    key_id = config["history_anchor_key_id"]
    if not isinstance(key_id, str) or not key_id.strip():
        raise RuntimeArchiveCLIError("trust_config_invalid_history_anchor_key_id")
    require_timestamps = config.get("require_trusted_timestamps", True)
    if not isinstance(require_timestamps, bool):
        raise RuntimeArchiveCLIError("trust_config_invalid_timestamp_policy")

    base = config_path.resolve(strict=True).parent
    policy: dict[str, Any] = {
        "history_anchor_public_key": _validate_trust_file(
            _resolve_path(config["history_anchor_public_key"], base, "history_anchor_public_key"),
            "history_anchor_public_key",
        ),
        "history_anchor_key_id": key_id,
        "timestamp_ca_file": _validate_trust_file(
            _resolve_path(config["timestamp_ca_file"], base, "timestamp_ca_file"),
            "timestamp_ca_file",
        ),
        "require_trusted_timestamps": require_timestamps,
    }
    chain_value = config.get("timestamp_untrusted_chain_file")
    if chain_value is not None:
        policy["timestamp_untrusted_chain_file"] = _validate_trust_file(
            _resolve_path(chain_value, base, "timestamp_untrusted_chain_file"),
            "timestamp_untrusted_chain_file",
        )
    return policy


def export_from_request(request_path: Path) -> dict[str, Any]:
    request = _load_json(request_path, "export_request")
    if set(request) != _EXPORT_FIELDS:
        missing = _EXPORT_FIELDS - set(request)
        unknown = set(request) - _EXPORT_FIELDS
        if missing:
            raise RuntimeArchiveCLIError("export_request_missing_fields:" + ",".join(sorted(missing)))
        raise RuntimeArchiveCLIError("export_request_unknown_fields:" + ",".join(sorted(unknown)))
    base = request_path.resolve(strict=True).parent
    source_root = _resolve_path(request["source_root"], base, "source_root")
    destination = _resolve_path(request["destination"], base, "destination")
    if not isinstance(request["metadata"], dict) or not isinstance(request["files"], dict):
        raise RuntimeArchiveCLIError("export_request_metadata_and_files_must_be_objects")
    return create_cryptographic_runtime_archive(
        source_root, destination, request["metadata"], request["files"]
    )


def verify_archive(
    archive_path: Path, trust_config_path: Path
) -> dict[str, Any]:
    policy = load_trust_policy(trust_config_path)
    return verify_runtime_archive_cryptographically(archive_path, policy)


def _write_report(report: dict[str, Any], output: Path | None) -> None:
    rendered = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    if output is None:
        sys.stdout.write(rendered)
        return
    if output.exists() or output.is_symlink():
        raise RuntimeArchiveCLIError("report_destination_already_exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="runtime-archive",
        description="Export or independently verify portable runtime evidence archives.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    export_parser = commands.add_parser("export", help="create an archive from an explicit file map")
    export_parser.add_argument("--request", required=True, type=Path, help="JSON export request")
    export_parser.add_argument("--report", type=Path, help="write the package report to a new JSON file")
    verify_parser = commands.add_parser("verify", help="perform offline cryptographic audit")
    verify_parser.add_argument("--archive", required=True, type=Path, help="archive directory")
    verify_parser.add_argument("--trust-config", required=True, type=Path, help="host trust-root JSON")
    verify_parser.add_argument("--report", type=Path, help="write the audit report to a new JSON file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "export":
            report = export_from_request(args.request)
        else:
            report = verify_archive(args.archive, args.trust_config)
        _write_report(report, args.report)
    except (OSError, RuntimeArchiveCLIError, ValueError) as exc:
        print(f"runtime-archive: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
