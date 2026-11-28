from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from provider_neutral_runtime import (  # noqa: E402
    RuntimeInterfaceError,
    build_skill_planner_request,
    run_skill_planner,
)


class MockRuntime:
    runtime_name = "mock-runtime"
    planner_version = "unit-test-1"

    def __init__(self, response: Any) -> None:
        self.response = response
        self.calls = 0
        self.last_request: dict[str, Any] | None = None

    def generate_json(self, *, system_prompt: str, user_prompt: str,
                      response_schema: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        self.last_request = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "response_schema": response_schema,
        }
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class ProviderNeutralRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.revision = "a" * 40
        self.request = build_skill_planner_request(
            "Audit this Python project",
            {"code-audit": "# Code audit\nReview source safely."},
            self.revision,
            {"code-audit": "https://example.invalid/skills/code-audit/SKILL.md"},
        )

    def test_builds_pinned_provider_neutral_request(self) -> None:
        self.assertEqual(self.request["skills_revision"], self.revision)
        self.assertIn("code-audit", self.request["available_skills"])
        self.assertNotIn("provider", self.request)

    def test_rejects_non_full_revision(self) -> None:
        with self.assertRaisesRegex(RuntimeInterfaceError, "40-character"):
            build_skill_planner_request("task", {"code-audit": "# Skill"}, "main",
                                        {"code-audit": "ref"})

    def test_rejects_missing_manifest_reference(self) -> None:
        with self.assertRaisesRegex(RuntimeInterfaceError, "exactly"):
            build_skill_planner_request("task", {"code-audit": "# Skill"}, self.revision, {})

    def test_calls_injected_runtime_and_normalizes_result(self) -> None:
        runtime = MockRuntime({
            "decision": "select",
            "selected_skills": ["code-audit"],
            "rationale": "The task requests source-code review.",
        })
        result = run_skill_planner(self.request, runtime)
        self.assertEqual(runtime.calls, 1)
        self.assertEqual(result["selected_skills"], ["code-audit"])
        self.assertEqual(result["runtime"]["name"], "mock-runtime")
        self.assertIn("MANIFEST_CONTENT", runtime.last_request["user_prompt"])

    def test_unknown_skill_is_rejected(self) -> None:
        runtime = MockRuntime({
            "decision": "select", "selected_skills": ["made-up"],
            "rationale": "Not valid.",
        })
        with self.assertRaisesRegex(RuntimeInterfaceError, "unknown Skills"):
            run_skill_planner(self.request, runtime)

    def test_select_requires_non_empty_skill_list(self) -> None:
        runtime = MockRuntime({
            "decision": "select", "selected_skills": [], "rationale": "No match.",
        })
        with self.assertRaisesRegex(RuntimeInterfaceError, "requires at least one"):
            run_skill_planner(self.request, runtime)

    def test_clarify_cannot_include_selected_skills(self) -> None:
        runtime = MockRuntime({
            "decision": "clarify", "selected_skills": ["code-audit"],
            "rationale": "Need more detail.",
        })
        with self.assertRaisesRegex(RuntimeInterfaceError, "must not select"):
            run_skill_planner(self.request, runtime)

    def test_extra_fields_are_rejected(self) -> None:
        runtime = MockRuntime({
            "decision": "select", "selected_skills": ["code-audit"],
            "rationale": "Valid.", "tool_call": "execute",
        })
        with self.assertRaisesRegex(RuntimeInterfaceError, "only decision"):
            run_skill_planner(self.request, runtime)

    def test_runtime_exception_is_safely_wrapped(self) -> None:
        runtime = MockRuntime(RuntimeError("private endpoint details"))
        with self.assertRaisesRegex(RuntimeInterfaceError, "RuntimeError") as caught:
            run_skill_planner(self.request, runtime)
        self.assertNotIn("private endpoint details", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
