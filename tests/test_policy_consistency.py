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

    def test_adaptive_execution_policy_is_linked_from_skill(self) -> None:
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

    def test_single_agent_remains_strong_default(self) -> None:
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
        self.assertIn("not replace it with a growing rulebook", policy)
        self.assertIn("brittle thresholds", policy)

    def test_project_wiki_is_project_local_not_agent_lore_storage(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        context = (ROOT / "references" / "PROJECT_CONTEXT.md").read_text(encoding="utf-8")
        lifecycle = (ROOT / "references" / "LIFECYCLE.md").read_text(encoding="utf-8")
        self.assertIn("Project state belongs to the project", skill)
        self.assertIn("does not require the OpenWiki product/service or any extra AI API key", context)
        self.assertIn("Agent Lore should neither mirror nor synchronize project wiki content", context)
        self.assertIn("Full-repository re-analysis is exceptional", context)
        self.assertIn("Do not store project wiki/current-state snapshots in Agent Lore", lifecycle)


if __name__ == "__main__":
    unittest.main()
