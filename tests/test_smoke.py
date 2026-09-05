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


class AgentLoreV09SmokeTest(unittest.TestCase):
    def invoke_cli(self, home: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["AGENT_LORE_HOME"] = str(home)
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def run_cli(self, home: Path, *args: str) -> dict:
        result = self.invoke_cli(home, *args)
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        return json.loads(result.stdout)

    def test_v09_scoped_memory_sidecar_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home-a"

            initialized = self.run_cli(home, "init")
            self.assertEqual(initialized["integrity"], "ok")
            self.assertEqual(initialized["schema_version"], "9")
            self.assertEqual(initialized["policy"]["memory_mode"], "off")
            self.assertTrue((home / "agent-lore.db").exists())
            self.assertFalse((home / "knowledge").exists())
            self.assertFalse((home / "traces").exists())
            self.assertFalse((home / "reports").exists())
            self.assertFalse((home / "exports").exists())
            self.assertFalse((home / "archive").exists())

            self.run_cli(
                home, "config", "add",
                "--name", "lead-config",
                "--model", "example-lead-model",
                "--harness", "example-harness",
                "--can-delegate",
                "--max-depth", "2",
                "--quality-tier", "5",
                "--cost-tier", "3",
            )

            record_args = [
                "record",
                "--task", "fix websocket reconnect duplicate processing",
                "--project", "project-a",
                "--module", "realtime",
                "--type", "debugging",
                "--subtype", "reconnect",
                "--language", "typescript",
                "--framework", "node",
                "--outcome", "success",
                "--verification", "reconnect regression passed",
                "--verification-status", "passed",
                "--acceptance-status", "accepted",
                "--acceptance-source", "reviewer",
                "--knowledge-scope", "module",
                "--experience-family", "websocket-reconnect-duplicate",
                "--observation", "Reconnect replay caused duplicate logical event processing",
                "--invariant", "One logical event must not be processed twice",
                "--root-cause", "Replay lacked idempotency protection",
                "--root-cause-status", "established",
                "--applies-when", "reconnect changes,retry changes,replay changes",
                "--not-proven", "serialization is universally required",
                "--solution", "add an idempotency guard",
                "--solution-status", "conditional",
            ]
            first = self.run_cli(home, *record_args)
            self.assertIsNotNone(first["experience_id"])
            knowledge_id = first["experience_id"]

            guardrail = self.run_cli(
                home, "retrieve",
                "--task", "change websocket reconnect retry behavior",
                "--project", "project-a",
                "--module", "realtime",
                "--type", "debugging",
                "--subtype", "reconnect",
                "--memory-mode", "guardrail",
            )
            self.assertEqual(guardrail["count"], 1)
            card = guardrail["knowledge"][0]
            self.assertEqual(card["scope"], "module")
            self.assertIn("duplicate", card["observation"].lower())
            self.assertIn("must not", card["invariant"].lower())
            self.assertNotIn("historical_solution", card)

            proactive = self.run_cli(
                home, "retrieve",
                "--task", "change websocket reconnect retry behavior",
                "--project", "project-a",
                "--module", "realtime",
                "--type", "debugging",
                "--subtype", "reconnect",
                "--memory-mode", "proactive",
            )
            self.assertEqual(proactive["knowledge"][0]["historical_solution"], "add an idempotency guard")
            self.assertEqual(proactive["knowledge"][0]["solution_status"], "conditional")

            unrelated = self.run_cli(
                home, "retrieve",
                "--task", "change websocket reconnect retry behavior",
                "--project", "project-b",
                "--module", "realtime",
                "--type", "debugging",
                "--memory-mode", "proactive",
            )
            self.assertEqual(unrelated["count"], 0)

            # Repeated accepted evidence can become a scoped pattern without
            # becoming an injected Agent Skill.
            for _ in range(3):
                self.run_cli(home, *record_args)
            consolidated = self.run_cli(home, "consolidate", "--apply")
            self.assertTrue(any(item["id"] == knowledge_id for item in consolidated["changes"]))
            knowledge = self.run_cli(home, "knowledge", "--scope", "module")
            item = next(item for item in knowledge["knowledge"] if item["id"] == knowledge_id)
            self.assertIn(item["kind"], ("experience", "pattern"))
            self.assertFalse(item["legacy_read_only"])

            # Recommendation does not preload historical memory by default.
            recommendation = self.run_cli(
                home, "recommend",
                "--task", "implement three independent checks",
                "--parallelizable", "yes",
                "--estimated-subtasks", "3",
                "--dependency-level", "low",
            )
            self.assertEqual(recommendation["knowledge"]["count"], 0)
            self.assertEqual(recommendation["topology"]["recommended"], "flat-parallel")

            report_path = base / "report.md"
            reported = self.run_cli(home, "report", "--project", "project-a", "--output", str(report_path))
            self.assertEqual(reported["status"], "reported")
            self.assertTrue(report_path.exists())

            policy = self.run_cli(
                home, "policy", "set",
                "--mode", "adaptive",
                "--memory-mode", "guardrail",
                "--memory-token-budget", "240",
            )
            self.assertEqual(policy["policy"]["memory_mode"], "guardrail")
            self.assertEqual(policy["policy"]["memory_token_budget"], 240)

            bundle = base / "agent-lore-backup.zip"
            exported = self.run_cli(home, "export", "--output", str(bundle))
            self.assertTrue(Path(exported["path"]).exists())

            restored_home = base / "home-b"
            restored = self.run_cli(restored_home, "import", str(bundle))
            self.assertEqual(restored["status"], "imported")
            doctor = self.run_cli(restored_home, "doctor")
            self.assertEqual(doctor["integrity"], "ok")
            self.assertEqual(doctor["schema_version"], "9")
            self.assertEqual(doctor["legacy_skills"], 0)
            self.assertGreaterEqual(doctor["accepted_runs"], 1)

    def test_stack_scope_can_transfer_without_project_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            self.run_cli(
                home,
                "record",
                "--task", "prisma migration compatibility",
                "--project", "project-a",
                "--type", "migration",
                "--language", "typescript",
                "--framework", "prisma",
                "--outcome", "success",
                "--verification-status", "passed",
                "--acceptance-status", "accepted",
                "--knowledge-scope", "stack",
                "--observation", "two-step migration preserved compatibility",
            )
            transferred = self.run_cli(
                home,
                "retrieve",
                "--task", "prisma migration compatibility",
                "--project", "project-b",
                "--language", "typescript",
                "--framework", "prisma",
                "--memory-mode", "guardrail",
            )
            self.assertEqual(transferred["count"], 1)
            self.assertEqual(transferred["knowledge"][0]["scope"], "stack")

    def test_upgrades_v01_database_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "legacy-home"
            home.mkdir(parents=True)
            db = home / "agent-lore.db"
            conn = sqlite3.connect(db)
            conn.executescript(
                """
                CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE experiences (
                    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'candidate', source_project TEXT, task_type TEXT,
                    task_summary TEXT NOT NULL, language TEXT, framework TEXT, framework_version TEXT,
                    lesson TEXT NOT NULL, lesson_key TEXT NOT NULL, failure_reason TEXT, solution_summary TEXT,
                    confidence REAL NOT NULL DEFAULT 0.5, utility REAL NOT NULL DEFAULT 0.0,
                    evidence_count INTEGER NOT NULL DEFAULT 1, success_count INTEGER NOT NULL DEFAULT 0,
                    failure_count INTEGER NOT NULL DEFAULT 0, reuse_count INTEGER NOT NULL DEFAULT 0,
                    last_used_at TEXT, tags TEXT NOT NULL DEFAULT '[]'
                );
                CREATE TABLE runs (
                    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, source_project TEXT, task_type TEXT,
                    task_summary TEXT NOT NULL, language TEXT, framework TEXT, framework_version TEXT,
                    agent_role TEXT, model TEXT, harness TEXT, outcome TEXT NOT NULL, verification TEXT,
                    latency_ms INTEGER, cost_usd REAL, retry_count INTEGER NOT NULL DEFAULT 0, notes TEXT,
                    tags TEXT NOT NULL DEFAULT '[]', experience_id TEXT
                );
                INSERT INTO meta(key, value) VALUES('schema_version', '1');
                """
            )
            conn.commit()
            conn.close()

            upgraded = self.run_cli(home, "init")
            self.assertEqual(upgraded["schema_version"], "9")
            doctor = self.run_cli(home, "doctor")
            self.assertEqual(doctor["integrity"], "ok")
            with closing(sqlite3.connect(db)) as conn:
                columns = {row[1] for row in conn.execute("PRAGMA table_info(experiences)")}
            self.assertIn("knowledge_scope", columns)
            self.assertIn("invariant", columns)
            self.assertIn("solution_status", columns)


if __name__ == "__main__":
    unittest.main()
