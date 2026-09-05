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


class ExecutionObservabilityTest(unittest.TestCase):
    def invoke_cli(self, home: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["AGENT_LORE_HOME"] = str(home)
        return subprocess.run(
            [sys.executable, str(CLI), *args], cwd=ROOT, env=env,
            text=True, capture_output=True, check=False,
        )

    def run_cli(self, home: Path, *args: str) -> dict:
        result = self.invoke_cli(home, *args)
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        return json.loads(result.stdout)

    def rejected_cli(self, home: Path, *args: str) -> dict:
        result = self.invoke_cli(home, *args)
        self.assertNotEqual(result.returncode, 0, msg=result.stdout)
        return json.loads(result.stdout)

    def record_run(self, home: Path) -> dict:
        return self.run_cli(
            home, "record",
            "--task", "build an interactive product slice",
            "--project", "opsdesk",
            "--module", "full-stack",
            "--type", "implementation",
            "--outcome", "success",
            "--verification-status", "passed",
            "--acceptance-status", "pending",
            "--topology", "lead-worker",
            "--model", "run-model",
            "--harness", "run-harness",
        )

    def test_optional_agent_ledger_is_after_the_fact_observation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            initialized = self.run_cli(home, "init")
            self.assertEqual(initialized["schema_version"], "9")
            run = self.record_run(home)

            before = self.run_cli(home, "agents", "show", run["run_id"])
            self.assertEqual(before["run"]["execution_capture_status"], "not-collected")
            self.assertEqual(before["known_agents"], 0)
            self.assertFalse(before["agent_count_exact"])

            manifest = {
                "capture_status": "complete",
                "source": "codex-host",
                "notes": "captured after integration",
                "agents": [
                    {"agent_id": "/root", "name": "Main", "role": "Orchestrator", "model": "example-main", "status": "completed"},
                    {"agent_id": "/root/frontend", "parent_id": "/root", "role": "Worker", "specialization": "frontend", "status": "completed", "provider_trace": "opaque-host-value"},
                    {"agent_id": "/root/backend", "parent_id": "/root", "role": "Worker", "specialization": "backend", "status": "completed", "wall_time_ms": 1200, "cost_usd": 0.03},
                ],
            }
            recorded = self.run_cli(
                home, "agents", "record", run["run_id"],
                "--manifest-json", json.dumps(manifest),
            )
            self.assertEqual(recorded["capture_status"], "complete")
            self.assertEqual(recorded["known_agents"], 3)
            self.assertTrue(recorded["agent_count_exact"])
            self.assertEqual(recorded["inherited_from_run"], {"model": 2, "harness": 3})

            shown = self.run_cli(home, "agents", "show", run["run_id"])
            self.assertEqual(shown["run"]["agent_count"], 3)
            by_id = {agent["agent_id"]: agent for agent in shown["agents"]}
            self.assertEqual(by_id["/root"]["depth"], 0)
            self.assertEqual(by_id["/root/frontend"]["depth"], 1)
            self.assertEqual(by_id["/root/frontend"]["model"], "run-model")
            self.assertEqual(by_id["/root/frontend"]["harness"], "run-harness")
            self.assertEqual(by_id["/root/frontend"]["metadata"]["provider_trace"], "opaque-host-value")

            report_path = base / "report.md"
            self.run_cli(home, "report", "--project", "opsdesk", "--output", str(report_path))
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("## Actual Agent Execution", report)
            self.assertIn("/root/frontend", report)
            self.assertIn("Complete agent capture: 1", report)
            self.assertIn("## Execution Telemetry Coverage", report)
            self.assertIn("**Pending**", report)

            dashboard_path = base / "dashboard.html"
            dashboard = self.run_cli(
                home, "report", "--project", "opsdesk", "--format", "html", "--output", str(dashboard_path),
            )
            self.assertEqual(dashboard["format"], "html")
            self.assertIn("<!doctype html>", dashboard_path.read_text(encoding="utf-8"))

    def test_partial_capture_and_complete_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            run = self.record_run(home)
            partial = {
                "capture_status": "partial",
                "agents": [{"agent_id": "visible-child", "parent_agent_id": "host-owned-parent", "role": "Verifier"}],
            }
            result = self.run_cli(home, "agents", "record", run["run_id"], "--manifest-json", json.dumps(partial))
            self.assertEqual(result["capture_status"], "partial")
            self.assertFalse(result["agent_count_exact"])

            complete = dict(partial)
            complete["capture_status"] = "complete"
            error = self.rejected_cli(home, "agents", "record", run["run_id"], "--manifest-json", json.dumps(complete))
            self.assertIn("parents missing", error["error"])

            replacement = {"capture_status": "complete", "agents": [{"agent_id": "visible-root", "role": "Orchestrator"}]}
            replaced = self.run_cli(home, "agents", "record", run["run_id"], "--manifest-json", json.dumps(replacement))
            self.assertTrue(replaced["agent_count_exact"])
            final = self.run_cli(home, "agents", "show", run["run_id"])
            self.assertEqual([agent["agent_id"] for agent in final["agents"]], ["visible-root"])

            cannot_erase = self.rejected_cli(
                home, "agents", "record", run["run_id"],
                "--manifest-json", json.dumps({"capture_status": "not-collected", "agents": []}),
            )
            self.assertIn("ledger entries already exist", cannot_erase["error"])

    def test_cycle_and_unknown_run_are_rejected_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            run = self.record_run(home)
            cycle = {
                "capture_status": "complete",
                "agents": [
                    {"agent_id": "a", "parent_agent_id": "b"},
                    {"agent_id": "b", "parent_agent_id": "a"},
                ],
            }
            error = self.rejected_cli(home, "agents", "record", run["run_id"], "--manifest-json", json.dumps(cycle))
            self.assertIn("cycle", error["error"])
            missing = self.rejected_cli(
                home, "agents", "record", "run-missing",
                "--manifest-json", json.dumps({"capture_status": "partial", "agents": []}),
            )
            self.assertIn("unknown run id", missing["error"])
            with closing(sqlite3.connect(home / "agent-lore.db")) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM run_agents").fetchone()[0], 0)

    def test_legacy_runs_upgrade_to_explicit_not_collected_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            self.record_run(home)
            with closing(sqlite3.connect(home / "agent-lore.db")) as conn:
                conn.execute("UPDATE meta SET value='7' WHERE key='schema_version'")
                conn.commit()

            upgraded = self.run_cli(home, "init")
            self.assertEqual(upgraded["schema_version"], "9")
            doctor = self.run_cli(home, "doctor")
            self.assertEqual(doctor["agent_ledger_entries"], 0)
            self.assertEqual(doctor["agent_capture_not_collected"], 1)


if __name__ == "__main__":
    unittest.main()
