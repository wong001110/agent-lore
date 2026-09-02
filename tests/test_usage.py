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


class KnowledgeUsageTest(unittest.TestCase):
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

    def rejected_cli(self, home: Path, *args: str) -> dict:
        result = self.invoke_cli(home, *args)
        self.assertNotEqual(result.returncode, 0, msg=result.stdout)
        return json.loads(result.stdout)

    def create_knowledge(self, home: Path) -> dict:
        return self.run_cli(
            home,
            "record",
            "--task", "preserve the distinction between retrieval and use",
            "--project", "usage-project",
            "--module", "memory",
            "--type", "implementation",
            "--outcome", "success",
            "--verification-status", "passed",
            "--acceptance-status", "accepted",
            "--lesson", "Count reuse only when knowledge is actually applied",
        )

    def test_retrieval_is_read_only_and_usage_distinguishes_applied_from_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            recorded = self.create_knowledge(home)
            knowledge_id = recorded["experience_id"]

            first = self.run_cli(
                home,
                "retrieve",
                "--task", "count reuse when knowledge is applied",
                "--project", "usage-project",
                "--module", "memory",
                "--type", "implementation",
            )
            second = self.run_cli(
                home,
                "retrieve",
                "--task", "count reuse when knowledge is applied",
                "--project", "usage-project",
                "--module", "memory",
                "--type", "implementation",
            )
            self.assertEqual(first["knowledge"][0]["reuse_count"], 0)
            self.assertEqual(second["knowledge"][0]["reuse_count"], 0)

            ignored = self.run_cli(
                home,
                "usage", knowledge_id,
                "--decision", "ignored",
                "--reason", "current repository constraints made it inapplicable",
                "--source", "test-harness",
            )
            self.assertEqual(ignored["reuse_count"], 0)
            self.assertIsNone(ignored["last_used_at"])

            applied = self.run_cli(
                home,
                "usage", knowledge_id,
                "--decision", "applied",
                "--run-id", recorded["run_id"],
                "--reason", "the guidance informed the implementation",
                "--source", "test-harness",
            )
            self.assertEqual(applied["reuse_count"], 1)
            self.assertIsNotNone(applied["last_used_at"])

            with closing(sqlite3.connect(home / "agent-lore.db")) as conn:
                rows = conn.execute(
                    "SELECT decision, reason, source, run_id FROM knowledge_usage "
                    "WHERE experience_id=? ORDER BY created_at, rowid",
                    (knowledge_id,),
                ).fetchall()

            self.assertEqual([row[0] for row in rows], ["ignored", "applied"])
            self.assertEqual(rows[0][1], "current repository constraints made it inapplicable")
            self.assertEqual(rows[1][2], "test-harness")
            self.assertEqual(rows[1][3], recorded["run_id"])

    def test_usage_rejects_unknown_knowledge_or_run_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            recorded = self.create_knowledge(home)
            knowledge_id = recorded["experience_id"]

            missing_knowledge = self.rejected_cli(
                home,
                "usage", "exp-does-not-exist",
                "--decision", "applied",
            )
            self.assertIn("unknown knowledge id", missing_knowledge["error"])
            missing_run = self.rejected_cli(
                home,
                "usage", knowledge_id,
                "--decision", "applied",
                "--run-id", "run-does-not-exist",
            )
            self.assertIn("unknown run id", missing_run["error"])

            with closing(sqlite3.connect(home / "agent-lore.db")) as conn:
                reuse_count, last_used_at = conn.execute(
                    "SELECT reuse_count, last_used_at FROM experiences WHERE id=?",
                    (knowledge_id,),
                ).fetchone()
                usage_count = conn.execute("SELECT COUNT(*) FROM knowledge_usage").fetchone()[0]

            self.assertEqual(reuse_count, 0)
            self.assertIsNone(last_used_at)
            self.assertEqual(usage_count, 0)


if __name__ == "__main__":
    unittest.main()
