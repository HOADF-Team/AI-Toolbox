from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_crypto_security_skill import CONTROL_PATTERNS, validate_skill_text


class CryptoSecuritySkillContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.complete_contract = "\\n".join(
            alternatives[0] for alternatives in CONTROL_PATTERNS.values()
        ) + "\\nБезопасно изолируй скомпрометированный узел"

    def test_complete_contract_passes(self) -> None:
        self.assertEqual(validate_skill_text(self.complete_contract), [])

    def test_missing_urgent_revocation_control_is_reported(self) -> None:
        content = self.complete_contract.replace("немедленно отзови их", "")
        self.assertIn(
            "revoke_exposed_credentials_urgently",
            validate_skill_text(content),
        )

    def test_missing_restore_control_is_reported(self) -> None:
        content = self.complete_contract.replace("тест восстановления", "")
        self.assertIn("test_backup_restore", validate_skill_text(content))

    def test_credential_revocation_must_precede_host_isolation(self) -> None:
        reordered = (
            self.complete_contract
            .replace("немедленно отзови их", "REVOCATION")
            .replace(
                "Безопасно изолируй скомпрометированный узел",
                "немедленно отзови их",
            )
            .replace("REVOCATION", "Безопасно изолируй скомпрометированный узел")
        )
        self.assertIn(
            "urgent_credential_revocation_must_precede_host_isolation",
            validate_skill_text(reordered),
        )

    def test_all_required_controls_are_named(self) -> None:
        self.assertEqual(len(CONTROL_PATTERNS), 13)
        self.assertIn("do_not_auto_liquidate_positions", CONTROL_PATTERNS)


if __name__ == "__main__":
    unittest.main()
