import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "agent_lore.py"


class AgentLoreIntegratedAlphaTest(unittest.TestCase):
    def run_cli(self, home: Path, *args: str) -> dict:
        env = os.environ.copy()
        env["AGENT_LORE_HOME"] = str(home)
        result = subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        return json.loads(result.stdout)

    def test_phase_1_to_4_integrated_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home-a"

            initialized = self.run_cli(home, "init")
            self.assertEqual(initialized["integrity"], "ok")
            self.assertEqual(initialized["schema_version"], "4")
            self.assertEqual(initialized["policy"]["mode"], "observe")

            self.run_cli(
                home,
                "config", "add",
                "--name", "fast-worker",
                "--model", "example-fast-model",
                "--harness", "example-harness",
                "--agent-role", "implementation-worker",
                "--quality-tier", "4",
                "--cost-tier", "1",
                "--priority", "60",
            )
            self.run_cli(
                home,
                "config", "add",
                "--name", "strong-worker",
                "--model", "example-strong-model",
                "--harness", "example-harness",
                "--agent-role", "implementation-worker",
                "--quality-tier", "5",
                "--cost-tier", "4",
                "--priority", "50",
            )
            self.run_cli(
                home,
                "config", "add",
                "--name", "lead-config",
                "--model", "example-lead-model",
                "--harness", "example-harness",
                "--agent-role", "implementation-worker",
                "--can-delegate",
                "--max-depth", "2",
                "--quality-tier", "5",
                "--cost-tier", "3",
            )

            lesson = "Prefer a transitional enum migration when existing rows depend on legacy values"
            for index, project in enumerate(("project-a", "project-b", "project-a"), start=1):
                recorded = self.run_cli(
                    home,
                    "record",
                    "--task", "change a PostgreSQL enum without breaking existing rows",
                    "--type", "migration",
                    "--language", "typescript",
                    "--framework", "prisma",
                    "--framework-version", "6",
                    "--outcome", "success",
                    "--project", project,
                    "--model", "example-fast-model",
                    "--harness", "example-harness",
                    "--agent-role", "implementation-worker",
                    "--quality-score", "0.94",
                    "--cost-usd", "0.04",
                    "--latency-ms", str(35000 + index),
                    "--verification", "migration test and e2e passed",
                    "--lesson", lesson,
                    "--solution", "add transitional value, migrate data, then remove legacy value",
                )
            experience_id = recorded["experience_id"]
            self.assertIsNotNone(experience_id)

            for project in ("project-a", "project-b"):
                self.run_cli(
                    home,
                    "record",
                    "--task", "change a PostgreSQL enum without breaking existing rows",
                    "--type", "migration",
                    "--language", "typescript",
                    "--framework", "prisma",
                    "--outcome", "success",
                    "--project", project,
                    "--model", "example-strong-model",
                    "--harness", "example-harness",
                    "--agent-role", "implementation-worker",
                    "--quality-score", "0.95",
                    "--cost-usd", "0.30",
                    "--latency-ms", "52000",
                    "--verification", "tests passed",
                )

            preview = self.run_cli(home, "consolidate")
            self.assertEqual(preview["status"], "preview")
            self.assertTrue(any(item["id"] == experience_id for item in preview["changes"]))
            applied = self.run_cli(home, "consolidate", "--apply")
            self.assertEqual(applied["status"], "applied")

            knowledge = self.run_cli(home, "knowledge", "--status", "active")
            active_ids = {item["id"] for item in knowledge["knowledge"]}
            self.assertIn(experience_id, active_ids)

            retrieved = self.run_cli(
                home,
                "retrieve",
                "--task", "safe PostgreSQL enum migration",
                "--type", "migration",
                "--language", "typescript",
                "--framework", "prisma",
                "--framework-version", "6",
            )
            self.assertGreaterEqual(retrieved["count"], 1)
            self.assertIn("transitional enum", retrieved["knowledge"][0]["lesson"].lower())

            recommendation = self.run_cli(
                home,
                "recommend",
                "--task", "implement three independent migration validation checks",
                "--type", "migration",
                "--language", "typescript",
                "--framework", "prisma",
                "--agent-role", "implementation-worker",
                "--complexity", "medium",
                "--risk", "medium",
                "--parallelizable", "yes",
                "--dependency-level", "low",
                "--estimated-subtasks", "3",
                "--uncertainty", "0.3",
                "--deterministic-evidence", "weak",
            )
            self.assertEqual(recommendation["topology"]["recommended"], "flat-parallel")
            self.assertEqual(recommendation["agent_config"]["name"], "fast-worker")
            self.assertIn(recommendation["challenge"]["level"], ("none", "self-check", "cheap-challenger"))
            decision_id = recommendation["decision_id"]

            high_risk = self.run_cli(
                home,
                "recommend",
                "--task", "replace production auth architecture",
                "--type", "architecture",
                "--agent-role", "implementation-worker",
                "--complexity", "high",
                "--risk", "critical",
                "--dependency-level", "high",
                "--uncertainty", "0.95",
                "--memory-conflict",
                "--stale-memory",
                "--cost-of-failure", "critical",
            )
            self.assertEqual(high_risk["topology"]["recommended"], "sequential")
            self.assertEqual(high_risk["challenge"]["level"], "strong-challenger")

            routed_run = self.run_cli(
                home,
                "record",
                "--task", "implement three independent migration validation checks",
                "--type", "migration",
                "--language", "typescript",
                "--framework", "prisma",
                "--outcome", "success",
                "--model", "example-fast-model",
                "--harness", "example-harness",
                "--agent-role", "implementation-worker",
                "--topology", "flat-parallel",
                "--agent-count", "3",
                "--quality-score", "0.93",
                "--cost-usd", "0.06",
                "--route-decision-id", decision_id,
            )
            self.assertTrue(routed_run["run_id"].startswith("run-"))

            promoted = self.run_cli(
                home,
                "promote", experience_id,
                "--kind", "skill",
                "--name", "safe-enum-migration",
                "--reason", "validated reusable procedure",
            )
            self.assertEqual(promoted["kind"], "skill")
            materialized = self.run_cli(home, "materialize-skills")
            self.assertEqual(materialized["count"], 1)
            self.assertTrue((home / "knowledge" / "skills" / "safe-enum-migration" / "SKILL.md").exists())

            policy = self.run_cli(home, "policy", "set", "--mode", "adaptive", "--max-agents", "5")
            self.assertEqual(policy["policy"]["mode"], "adaptive")
            self.assertEqual(policy["policy"]["max_agents"], 5)

            stats = self.run_cli(home, "stats")
            self.assertGreaterEqual(stats["count"], 1)
            self.assertGreaterEqual(len(stats["routing"]), 1)

            bundle = base / "agent-lore-backup.zip"
            exported = self.run_cli(home, "export", "--output", str(bundle))
            self.assertEqual(Path(exported["path"]), bundle)
            self.assertTrue(bundle.exists())

            restored_home = base / "home-b"
            restored = self.run_cli(restored_home, "import", str(bundle))
            self.assertEqual(restored["status"], "imported")

            doctor = self.run_cli(restored_home, "doctor")
            self.assertEqual(doctor["integrity"], "ok")
            self.assertGreaterEqual(doctor["runs"], 6)
            self.assertEqual(doctor["skills"], 1)
            self.assertEqual(doctor["enabled_agent_configs"], 3)
            self.assertGreaterEqual(doctor["routing_decisions"], 2)

    def test_upgrades_v01_database_in_place(self) -> None:
        import sqlite3

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
            self.assertEqual(upgraded["schema_version"], "4")
            doctor = self.run_cli(home, "doctor")
            self.assertEqual(doctor["integrity"], "ok")
            self.assertEqual(doctor["enabled_agent_configs"], 0)


if __name__ == "__main__":
    unittest.main()
