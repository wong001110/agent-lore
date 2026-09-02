import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "agent_lore.py"


class ModernRoutingTest(unittest.TestCase):
    def run_cli(self, home: Path, *args: str, expected: int = 0) -> dict:
        env = os.environ.copy()
        env["AGENT_LORE_HOME"] = str(home)
        result = subprocess.run(
            [sys.executable, str(CLI), *args], cwd=ROOT, env=env,
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, expected, msg=result.stderr or result.stdout)
        return json.loads(result.stdout)

    def add_lead(self, home: Path) -> None:
        self.run_cli(home, "init")
        self.run_cli(
            home, "config", "add", "--name", "lead", "--model", "lead-model",
            "--can-delegate", "--max-depth", "2", "--quality-tier", "5",
        )

    def test_task_shape_builds_scope_safe_dag_waves_and_persists_advisory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            self.add_lead(home)
            shape = {
                "objective": "implement and integrate two components",
                "delegation": {"decision": "delegate", "coordination": "manager-worker", "schedule": "parallel", "depth": 1},
                "workstreams": [
                    {"id": "api", "objective": "edit API", "depends_on": [], "write_scope": ["src/api"]},
                    {"id": "ui", "objective": "edit UI", "depends_on": [], "write_scope": ["src/ui"]},
                    {"id": "api-tests", "objective": "edit API tests", "depends_on": [], "write_scope": ["src/api/tests"]},
                    {"id": "integration", "objective": "integrate", "depends_on": ["api", "ui"], "contract_scope": ["public-api"]},
                ],
            }
            result = self.run_cli(
                home, "recommend", "--task", "实现并集成组件", "--task-canonical", "implement and integrate components",
                "--source-language", "zh-CN", "--task-shape-json", json.dumps(shape), "--mode", "adaptive",
            )
            plan = result["execution_plan"]
            self.assertEqual(plan["coordination"], "manager-worker")
            self.assertEqual(plan["schedule"], "hybrid")
            self.assertEqual(plan["waves"], [["api", "ui"], ["api-tests", "integration"]])
            self.assertEqual(plan["serialized_scope_conflicts"][0]["second"], "api-tests")
            self.assertEqual(result["topology"]["recommended"], "flat-parallel")
            self.assertIn("flat-parallel", result["topology"]["allowed"])
            self.assertTrue(result["eligible_for_host_application"])
            self.assertTrue(result["requires_host_execution"])
            self.assertFalse(result["applied_by_policy"])
            with closing(sqlite3.connect(home / "agent-lore.db")) as conn:
                row = conn.execute(
                    "SELECT applied, coordination, schedule, task_summary_canonical, source_language FROM routing_decisions WHERE id=?",
                    (result["decision_id"],),
                ).fetchone()
            self.assertEqual(row, (0, "manager-worker", "hybrid", "implement and integrate components", "zh-CN"))

    def test_at_path_policy_caps_depth_and_validates_evidence_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            self.add_lead(home)
            self.run_cli(home, "policy", "set", "--max-depth", "1", "--max-agents", "2")
            shape_path = base / "shape.json"
            evidence_path = base / "evidence.json"
            shape_path.write_text(json.dumps({
                "objective": "bounded migration",
                "delegation": {"decision": "hierarchical", "depth": 3},
                "workstreams": [
                    {"id": "a", "objective": "a", "depends_on": []},
                    {"id": "b", "objective": "b", "depends_on": []},
                    {"id": "c", "objective": "c", "depends_on": []},
                ],
            }), encoding="utf-8")
            evidence_path.write_text(json.dumps({
                "claims": ["migration preserves data"], "checks": [{"kind": "integration", "command": "targeted"}],
                "escalate_if": ["data mismatch"], "stop_when": "claim proven",
                "verification_tier": "V3", "security_depth": "focused",
            }), encoding="utf-8")
            result = self.run_cli(
                home, "recommend", "--task", "migration", "--task-shape-json", f"@{shape_path}",
                "--evidence-plan-json", f"@{evidence_path}",
            )
            self.assertEqual(result["execution_plan"]["coordination"], "manager-worker")
            self.assertEqual(result["execution_plan"]["delegation_depth"], 1)
            self.assertTrue(all(len(wave) <= 2 for wave in result["execution_plan"]["waves"]))
            self.assertEqual(result["verification_tier"], "V3")
            self.assertEqual(result["security_depth"], "focused")
            self.assertEqual(result["evidence_plan"]["source"], "provided")

    def test_cycle_and_invalid_evidence_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            self.run_cli(home, "init")
            cycle = {
                "objective": "cycle", "delegation": "delegate",
                "workstreams": [
                    {"id": "a", "objective": "a", "depends_on": ["b"]},
                    {"id": "b", "objective": "b", "depends_on": ["a"]},
                ],
            }
            error = self.run_cli(home, "recommend", "--task", "cycle", "--task-shape-json", json.dumps(cycle), expected=1)
            self.assertIn("cycle", error["error"])
            valid_shape = {"objective": "one", "workstreams": [{"id": "a", "objective": "a"}]}
            error = self.run_cli(
                home, "recommend", "--task", "one", "--task-shape-json", json.dumps(valid_shape),
                "--evidence-plan-json", json.dumps({"claims": [], "checks": ["x"]}), expected=1,
            )
            self.assertIn("claims", error["error"])

    def test_legacy_heuristic_still_emits_modern_execution_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            self.add_lead(home)
            result = self.run_cli(
                home, "recommend", "--task", "three independent checks", "--parallelizable", "yes",
                "--estimated-subtasks", "3", "--dependency-level", "low",
            )
            self.assertEqual(result["topology"]["recommended"], "flat-parallel")
            self.assertEqual(result["execution_plan"]["source"], "legacy-heuristic")
            self.assertEqual(result["execution_plan"]["coordination"], "manager-worker")
            self.assertIn(result["verification_tier"], ("V0", "V1", "V2", "V3", "V4"))
            self.assertEqual(result["evidence_plan"]["source"], "generated")


if __name__ == "__main__":
    unittest.main()
