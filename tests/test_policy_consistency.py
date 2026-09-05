import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import lore_common  # noqa: E402


class PolicyConsistencyTest(unittest.TestCase):
    def test_skill_and_runtime_versions_match(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        match = re.search(r'^\s*version:\s*"([^"]+)"\s*$', text, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), lore_common.APP_VERSION)
        self.assertEqual(lore_common.SCHEMA_VERSION, "9")

    def test_sidecar_model_freedom_principles_are_explicit(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        sidecar = (ROOT / "references" / "SIDECAR.md").read_text(encoding="utf-8")
        for phrase in (
            "Constrain capability, not cognition",
            "Observe execution, do not script it",
            "Expose history on demand, do not preload it",
            "Respect project structure, do not replace it",
        ):
            self.assertIn(phrase, skill)
            self.assertIn(phrase, sidecar)
        self.assertIn("no automatic bridge", sidecar)

    def test_pull_based_memory_and_retired_skills(self) -> None:
        memory = (ROOT / "references" / "MEMORY.md").read_text(encoding="utf-8")
        lifecycle = (ROOT / "references" / "LIFECYCLE.md").read_text(encoding="utf-8")
        self.assertIn("Memory should be queryable, not preloaded", memory)
        self.assertIn("off | guardrail | rescue | proactive", memory)
        self.assertIn("blind-plan then historical reveal", memory.lower())
        self.assertIn("stops creating/materializing learned Agent Skills", memory)
        self.assertIn("Learned Skills are legacy read-only", lifecycle)
        self.assertIn("task\nmodule\nproject\nstack\nglobal", lifecycle)

    def test_adaptive_execution_remains_reasoning_aid_not_recipe(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        execution = (ROOT / "references" / "EXECUTION.md").read_text(encoding="utf-8")
        self.assertIn("references/EXECUTION.md", skill)
        self.assertIn("EvidencePlan", execution)
        self.assertIn("V0-V4 are **risk/depth signals, not recipes**", execution)
        self.assertIn("Checkpoint vs Git commit", execution)
        self.assertIn("Delegation and nested agents", execution)

    def test_security_policy_is_proportional_not_universal(self) -> None:
        security = (ROOT / "references" / "SECURITY.md").read_text(encoding="utf-8")
        self.assertIn("Security applicability and depth", security)
        self.assertIn("none\nsmoke\nfocused\ndeep\nadversarial", security)
        self.assertIn("Do not automatically run every security family for every change", security)
        self.assertIn("Continual security learning", security)

    def test_single_agent_remains_economic_default_not_model_assumption(self) -> None:
        routing = (ROOT / "references" / "ROUTING.md").read_text(encoding="utf-8")
        self.assertIn("Strong default: single agent", routing)
        self.assertIn("If expected gain is not clearly positive, do not delegate", routing)
        self.assertIn("Nested delegation should emerge recursively", routing)

    def test_policy_strength_preserves_model_freedom(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        policy = (ROOT / "references" / "POLICY.md").read_text(encoding="utf-8")
        self.assertIn("hard            -> cannot be overridden", skill)
        self.assertIn("strong-default", policy)
        self.assertIn("advisory", policy)
        self.assertIn("experimental", policy)
        self.assertIn("Constrain capability, not cognition", policy)
        self.assertIn("No automatic Experience -> Policy promotion", policy)
        self.assertIn("Avoid brittle recipes", policy)

    def test_project_context_is_structure_agnostic_and_project_owned(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        context = (ROOT / "references" / "PROJECT_CONTEXT.md").read_text(encoding="utf-8")
        lifecycle = (ROOT / "references" / "LIFECYCLE.md").read_text(encoding="utf-8")
        self.assertIn("Project state belongs to the project", skill)
        self.assertIn("Semantic interface, not directory convention", context)
        self.assertIn("Zero-config discovery", context)
        self.assertIn("does not require every repository", context.lower().replace("does **not** require", "does not require"))
        self.assertIn("Full-repository review remains exceptional", context)
        self.assertIn("Project state is separate", lifecycle)


if __name__ == "__main__":
    unittest.main()
