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

    def accepted_record(self, home: Path, project: str, model: str, cost: str, wall: str, lesson: str | None = None) -> dict:
        args = [
            "record",
            "--task", "change a PostgreSQL enum without breaking existing rows",
            "--project", project,
            "--module", "data-model",
            "--type", "migration",
            "--subtype", "enum-change",
            "--language", "typescript",
            "--framework", "prisma",
            "--framework-version", "6",
            "--outcome", "success",
            "--model", model,
            "--harness", "example-harness",
            "--agent-role", "implementation-worker",
            "--quality-score", "0.94",
            "--cost-usd", cost,
            "--wall-time-ms", wall,
            "--compute-time-ms", wall,
            "--verification", "migration test and e2e passed",
            "--verification-status", "passed",
            "--acceptance-status", "accepted",
            "--acceptance-source", "reviewer",
        ]
        if lesson:
            args += [
                "--lesson", lesson,
                "--solution", "add transitional value, migrate data, then remove legacy value",
            ]
        return self.run_cli(home, *args)

    def test_phase_1_to_4_plus_acceptance_observability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home-a"

            initialized = self.run_cli(home, "init")
            self.assertEqual(initialized["integrity"], "ok")
            self.assertEqual(initialized["schema_version"], "5")
            self.assertEqual(initialized["policy"]["mode"], "observe")

            self.run_cli(
                home, "config", "add",
                "--name", "fast-worker",
                "--model", "example-fast-model",
                "--harness", "example-harness",
                "--agent-role", "implementation-worker",
                "--quality-tier", "4",
                "--cost-tier", "1",
                "--priority", "60",
            )
            self.run_cli(
                home, "config", "add",
                "--name", "strong-worker",
                "--model", "example-strong-model",
                "--harness", "example-harness",
                "--agent-role", "implementation-worker",
                "--quality-tier", "5",
                "--cost-tier", "4",
                "--priority", "50",
            )
            self.run_cli(
                home, "config", "add",
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
            for project in ("project-a", "project-b", "project-a"):
                recorded = self.accepted_record(home, project, "example-fast-model", "0.04", "35000", lesson)
            experience_id = recorded["experience_id"]
            self.assertIsNotNone(experience_id)

            for project in ("project-a", "project-b"):
                self.accepted_record(home, project, "example-strong-model", "0.30", "52000")

            preview = self.run_cli(home, "consolidate")
            self.assertEqual(preview["status"], "preview")
            self.assertTrue(any(item["id"] == experience_id for item in preview["changes"]))
            applied = self.run_cli(home, "consolidate", "--apply")
            self.assertEqual(applied["status"], "applied")

            knowledge = self.run_cli(home, "knowledge", "--status", "active")
            active_ids = {item["id"] for item in knowledge["knowledge"]}
            self.assertIn(experience_id, active_ids)
            item = next(item for item in knowledge["knowledge"] if item["id"] == experience_id)
            self.assertGreaterEqual(item["acceptance_metrics"]["accepted_runs"], 3)

            retrieved = self.run_cli(
                home,
                "retrieve",
                "--task", "safe PostgreSQL enum migration",
                "--project", "project-a",
                "--module", "data-model",
                "--type", "migration",
                "--subtype", "enum-change",
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
                "--project", "project-a",
                "--module", "data-model",
                "--type", "migration",
                "--subtype", "validation",
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
            decision_id = recommendation["decision_id"]

            pending = self.run_cli(
                home,
                "record",
                "--task", "simplify refresh token controls",
                "--project", "project-a",
                "--module", "authentication",
                "--type", "implementation",
                "--subtype", "product-flow",
                "--operation", "implement",
                "--outcome", "success",
                "--model", "example-fast-model",
                "--harness", "example-harness",
                "--agent-role", "implementation-worker",
                "--verification", "unit and e2e passed",
                "--verification-status", "passed",
                "--wall-time-ms", "30000",
                "--compute-time-ms", "22000",
                "--verification-time-ms", "5000",
                "--review-time-ms", "3000",
                "--files-touched", "4",
                "--lines-changed", "90",
                "--route-decision-id", decision_id,
            )
            self.assertEqual(pending["acceptance_status"], "pending")

            feedback = self.run_cli(
                home,
                "feedback", pending["run_id"],
                "--verdict", "rework",
                "--reason", "interaction is technically correct but too complicated",
            )
            self.assertEqual(feedback["acceptance_status"], "rework")

            corrected = self.run_cli(
                home,
                "record",
                "--task", "simplify refresh token controls",
                "--parent-run-id", pending["run_id"],
                "--outcome", "success",
                "--model", "example-strong-model",
                "--harness", "example-harness",
                "--verification", "unit and e2e passed",
                "--verification-status", "passed",
                "--acceptance-status", "accepted",
                "--acceptance-source", "human",
                "--acceptance-reason", "simplified flow accepted",
                "--wall-time-ms", "44000",
                "--compute-time-ms", "32000",
                "--review-time-ms", "5000",
            )
            self.assertEqual(corrected["attempt_index"], 2)
            self.assertEqual(corrected["task_group_id"], pending["task_group_id"])
            self.assertEqual(corrected["module"], "authentication")

            stats = self.run_cli(home, "stats", "--project", "project-a", "--module", "authentication")
            self.assertGreaterEqual(stats["count"], 1)
            self.assertTrue(any(group["acceptance_observed"] >= 1 for group in stats["groups"]))

            report_path = base / "report.md"
            reported = self.run_cli(
                home,
                "report",
                "--project", "project-a",
                "--output", str(report_path),
            )
            self.assertEqual(reported["status"], "reported")
            text = report_path.read_text(encoding="utf-8")
            self.assertIn("Project / Module / Task Benchmark", text)
            self.assertIn("authentication", text)
            self.assertIn("Rework / Acceptance History", text)

            promoted = self.run_cli(
                home,
                "promote", experience_id,
                "--kind", "skill",
                "--name", "safe-enum-migration",
                "--reason", "accepted reusable procedure",
            )
            self.assertEqual(promoted["kind"], "skill")
            materialized = self.run_cli(home, "materialize-skills")
            self.assertEqual(materialized["count"], 1)
            self.assertTrue((home / "knowledge" / "skills" / "safe-enum-migration" / "SKILL.md").exists())

            policy = self.run_cli(home, "policy", "set", "--mode", "adaptive", "--max-agents", "5")
            self.assertEqual(policy["policy"]["mode"], "adaptive")

            bundle = base / "agent-lore-backup.zip"
            exported = self.run_cli(home, "export", "--output", str(bundle))
            self.assertTrue(Path(exported["path"]).exists())

            restored_home = base / "home-b"
            restored = self.run_cli(restored_home, "import", str(bundle))
            self.assertEqual(restored["status"], "imported")
            doctor = self.run_cli(restored_home, "doctor")
            self.assertEqual(doctor["integrity"], "ok")
            self.assertEqual(doctor["schema_version"], "5")
            self.assertGreaterEqual(doctor["accepted_runs"], 1)
            self.assertGreaterEqual(doctor["rework_runs"], 1)
            self.assertEqual(doctor["skills"], 1)

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
            self.assertEqual(upgraded["schema_version"], "5")
            doctor = self.run_cli(home, "doctor")
            self.assertEqual(doctor["integrity"], "ok")
            self.assertEqual(doctor["enabled_agent_configs"], 0)
            self.assertEqual(doctor["awaiting_acceptance"], 0)


if __name__ == "__main__":
    unittest.main()
