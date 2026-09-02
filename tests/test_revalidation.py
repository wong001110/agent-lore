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


class KnowledgeRevalidationTest(unittest.TestCase):
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

    def record_with_lesson(
        self,
        home: Path,
        *,
        task: str,
        lesson: str,
        outcome: str = "success",
        verification_status: str = "passed",
        acceptance_status: str = "accepted",
    ) -> dict:
        return self.run_cli(
            home,
            "record",
            "--task", task,
            "--project", "revalidation-project",
            "--module", "knowledge-lifecycle",
            "--type", "implementation",
            "--subtype", "revalidation",
            "--outcome", outcome,
            "--verification-status", verification_status,
            "--acceptance-status", acceptance_status,
            "--acceptance-source", "reviewer",
            "--lesson", lesson,
            "--solution", "validate linked accepted evidence before restoring trust",
        )

    def test_revalidate_clears_flag_records_audit_and_preserves_lifecycle_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            lesson = "Require accepted linked evidence before revalidating knowledge"
            original = self.record_with_lesson(
                home,
                task="record reusable guidance",
                lesson=lesson,
            )
            experience_id = original["experience_id"]
            self.run_cli(
                home,
                "feedback", original["run_id"],
                "--verdict", "invalidate",
                "--reason", "later evidence contradicted the original conclusion",
            )
            validating = self.record_with_lesson(
                home,
                task="repeat the guidance under corrected conditions",
                lesson=lesson,
            )
            self.assertEqual(validating["experience_id"], experience_id)

            # Revalidation restores evidence trust but must not revive intentionally
            # deprecated or archived knowledge into the active lifecycle.
            self.run_cli(
                home,
                "deprecate", experience_id,
                "--reason", "retained for historical compatibility only",
            )
            result = self.run_cli(
                home,
                "revalidate", experience_id,
                "--run-id", validating["run_id"],
                "--reason", "corrected behavior passed deterministic review",
                "--source", "reviewer",
            )

            self.assertEqual(result["status"], "revalidated")
            self.assertEqual(result["knowledge_status"], "deprecated")
            self.assertFalse(result["needs_revalidation"])
            with closing(sqlite3.connect(home / "agent-lore.db")) as conn:
                conn.row_factory = sqlite3.Row
                knowledge = conn.execute(
                    "SELECT status, needs_revalidation, last_verified_at, status_reason "
                    "FROM experiences WHERE id=?",
                    (experience_id,),
                ).fetchone()
                evidence = conn.execute(
                    "SELECT relation FROM experience_evidence "
                    "WHERE experience_id=? AND run_id=?",
                    (experience_id, validating["run_id"]),
                ).fetchone()
                audit = conn.execute(
                    "SELECT * FROM knowledge_revalidations WHERE id=?",
                    (result["revalidation_id"],),
                ).fetchone()

            self.assertEqual(knowledge["status"], "deprecated")
            self.assertEqual(knowledge["needs_revalidation"], 0)
            self.assertEqual(knowledge["last_verified_at"], result["last_verified_at"])
            self.assertIn(validating["run_id"], knowledge["status_reason"])
            self.assertEqual(evidence["relation"], "supports")
            self.assertEqual(audit["experience_id"], experience_id)
            self.assertEqual(audit["run_id"], validating["run_id"])
            self.assertEqual(audit["reason"], "corrected behavior passed deterministic review")
            self.assertEqual(audit["source"], "reviewer")

    def test_revalidate_rejects_unqualified_and_unlinked_evidence_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            target_lesson = "Only qualified evidence may restore this knowledge"
            original = self.record_with_lesson(
                home,
                task="create target knowledge",
                lesson=target_lesson,
            )
            experience_id = original["experience_id"]
            self.run_cli(home, "feedback", original["run_id"], "--verdict", "reject")

            unqualified = self.record_with_lesson(
                home,
                task="produce a failed linked attempt",
                lesson=target_lesson,
                outcome="failure",
            )
            unqualified_error = self.rejected_cli(
                home,
                "revalidate", experience_id,
                "--run-id", unqualified["run_id"],
                "--reason", "must not be accepted",
            )
            self.assertIn("outcome must be success", unqualified_error["error"])

            unrelated = self.record_with_lesson(
                home,
                task="produce valid evidence for different knowledge",
                lesson="A distinct lesson that creates another experience",
            )
            unlinked_error = self.rejected_cli(
                home,
                "revalidate", experience_id,
                "--run-id", unrelated["run_id"],
                "--reason", "must also be rejected",
            )
            self.assertIn("is not linked as evidence", unlinked_error["error"])

            with closing(sqlite3.connect(home / "agent-lore.db")) as conn:
                flag = conn.execute(
                    "SELECT needs_revalidation FROM experiences WHERE id=?",
                    (experience_id,),
                ).fetchone()[0]
                relation = conn.execute(
                    "SELECT relation FROM experience_evidence "
                    "WHERE experience_id=? AND run_id=?",
                    (experience_id, unqualified["run_id"]),
                ).fetchone()[0]
                audit_count = conn.execute(
                    "SELECT COUNT(*) FROM knowledge_revalidations WHERE experience_id=?",
                    (experience_id,),
                ).fetchone()[0]

            self.assertEqual(flag, 1)
            self.assertEqual(relation, "related")
            self.assertEqual(audit_count, 0)


if __name__ == "__main__":
    unittest.main()
