#!/usr/bin/env python3
"""Validate mandatory safety controls in the canonical crypto-security Skill."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

CONTROL_PATTERNS: dict[str, tuple[str, ...]] = {
    "untrusted_input_is_not_instruction": (
        r"недоверенными данными, а не инструкциями",
        r"untrusted data, not instructions",
    ),
    "read_only_default": (
        r"По умолчанию выполняй read-only аудит",
        r"default.{0,30}read-only audit",
    ),
    "never_request_secrets": (
        r"Никогда не проси пользователя присылать",
        r"never ask the user to provide",
    ),
    "revoke_exposed_credentials_urgently": (
        r"немедленно отзови их",
        r"revoke.{0,50}immediately",
    ),
    "do_not_delay_revocation_for_investigation": (
        r"Не жди завершения расследования",
        r"do not wait for the investigation",
    ),
    "do_not_auto_liquidate_positions": (
        r"Не закрывай автоматически существующие позиции",
        r"do not automatically close existing positions",
    ),
    "verify_tls_certificate_and_hostname": (
        r"проверкой сертификата и hostname",
        r"verify the certificate and hostname",
    ),
    "separate_encryption_keys_from_data": (
        r"Разделяй ключи шифрования и зашифрованные данные",
        r"separate encryption keys from encrypted data",
    ),
    "test_backup_restore": (
        r"тест восстановления",
        r"restore drill",
    ),
    "warn_about_dependency_build_execution": (
        r"может запускать установку/build-процессы",
        r"may execute package build processes",
    ),
    "configure_trivy_exit_code_for_ci_gate": (
        r"настраивай exit code",
        r"configure the exit code",
    ),
    "verify_expected_signer_identity": (
        r"точной keyless identity",
        r"exact keyless identity",
    ),
    "report_unverified_areas": (
        r"непроверенные области",
        r"unverified areas",
    ),
}


def validate_skill_text(content: str) -> list[str]:
    """Return control IDs whose required safety guidance is absent."""
    missing: list[str] = []
    for control_id, alternatives in CONTROL_PATTERNS.items():
        if not any(re.search(pattern, content, re.IGNORECASE | re.DOTALL) for pattern in alternatives):
            missing.append(control_id)
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skill",
        type=Path,
        default=Path("Personal-AI-Library/skills/crypto-security/SKILL.md"),
        help="Path to the canonical crypto-security SKILL.md",
    )
    args = parser.parse_args()
    try:
        content = args.skill.read_text(encoding="utf-8")
    except OSError as exc:
        parser.error(str(exc))
    missing = validate_skill_text(content)
    if missing:
        print("FAIL: missing crypto-security controls:")
        for control_id in missing:
            print(f"- {control_id}")
        return 1
    print(f"PASS: all {len(CONTROL_PATTERNS)} crypto-security safety controls are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
