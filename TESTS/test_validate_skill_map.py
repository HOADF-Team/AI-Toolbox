"""Security regression tests for Skill-map discovery."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_skill_map import discover_skills


class SkillMapPathSecurityTests(unittest.TestCase):
    def test_rejects_symlinked_skill_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "skills"
            outside = Path(temp_dir) / "outside-skill"
            root.mkdir()
            outside.mkdir()
            (outside / "SKILL.md").write_text("# External Skill\n", encoding="utf-8")
            (root / "linked-skill").symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "must not be a symbolic link"):
                discover_skills(root)

    def test_rejects_symlinked_skill_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "skills"
            skill_dir = root / "demo"
            skill_dir.mkdir(parents=True)
            outside = Path(temp_dir) / "outside.md"
            outside.write_text("# External manifest\n", encoding="utf-8")
            (skill_dir / "SKILL.md").symlink_to(outside)

            with self.assertRaisesRegex(ValueError, "manifest must not be a symbolic link"):
                discover_skills(root)

    def test_rejects_symlinked_skills_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            actual = Path(temp_dir) / "actual-skills"
            actual.mkdir()
            linked = Path(temp_dir) / "linked-skills"
            linked.symlink_to(actual, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "Skills directory must not be a symbolic link"):
                discover_skills(linked)


if __name__ == "__main__":
    unittest.main()
