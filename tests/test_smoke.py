import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "agent_lore.py"


class AgentLoreSmokeTest(unittest.TestCase):
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

    def test_end_to_end_local_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home-a"

            initialized = self.run_cli(home, "init")
            self.assertEqual(initialized["integrity"], "ok")

            recorded = self.run_cli(
                home,
                "record",
                "--task",
                "change a PostgreSQL enum without breaking existing rows",
                "--type",
                "migration",
                "--language",
                "typescript",
                "--framework",
                "prisma",
                "--framework-version",
                "6",
                "--outcome",
                "success",
                "--model",
                "example-fast-model",
                "--agent-role",
                "implementation-worker",
                "--verification",
                "migration test and e2e passed",
                "--lesson",
                "Prefer a transitional enum migration when existing rows depend on legacy values",
                "--solution",
                "add transitional value, migrate data, then remove legacy value",
            )
            self.assertIsNotNone(recorded["experience_id"])

            retrieved = self.run_cli(
                home,
                "retrieve",
                "--task",
                "safe PostgreSQL enum migration",
                "--type",
                "migration",
                "--language",
                "typescript",
                "--framework",
                "prisma",
                "--framework-version",
                "6",
            )
            self.assertGreaterEqual(retrieved["count"], 1)
            self.assertIn("transitional enum", retrieved["experiences"][0]["lesson"].lower())

            stats = self.run_cli(home, "stats")
            self.assertEqual(stats["count"], 1)
            self.assertEqual(stats["groups"][0]["runs"], 1)
            self.assertEqual(stats["groups"][0]["success_rate_pct"], 100.0)

            bundle = base / "agent-lore-backup.zip"
            exported = self.run_cli(home, "export", "--output", str(bundle))
            self.assertEqual(Path(exported["path"]), bundle)
            self.assertTrue(bundle.exists())

            restored_home = base / "home-b"
            restored = self.run_cli(restored_home, "import", str(bundle))
            self.assertEqual(restored["status"], "imported")

            doctor = self.run_cli(restored_home, "doctor")
            self.assertEqual(doctor["integrity"], "ok")
            self.assertEqual(doctor["runs"], 1)
            self.assertEqual(doctor["experiences"], 1)


if __name__ == "__main__":
    unittest.main()
