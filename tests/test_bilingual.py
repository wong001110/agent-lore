import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "agent_lore.py"


class BilingualKnowledgeTest(unittest.TestCase):
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

    def test_preserves_chinese_and_retrieves_native_or_canonical_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            recorded = self.run_cli(
                home,
                "record",
                "--task", "修复刷新令牌并发重试导致状态覆盖",
                "--task-canonical", "Fix refresh-token retry concurrency overwriting newer state",
                "--project", "auth-app",
                "--module", "authentication",
                "--type", "debugging",
                "--source-language", "zh-CN",
                "--canonicalizer", "host-model:test",
                "--outcome", "success",
                "--verification-status", "passed",
                "--acceptance-status", "accepted",
                "--acceptance-source", "reviewer",
                "--lesson", "刷新令牌更新必须使用版本检查避免旧请求覆盖新状态",
                "--lesson-canonical", "Use version checks so stale refresh requests cannot overwrite newer token state",
                "--solution", "以版本号执行条件更新",
                "--solution-canonical", "Use a conditional update guarded by the token version",
            )
            self.assertIsNotNone(recorded["experience_id"])

            native = self.run_cli(
                home,
                "retrieve",
                "--task", "刷新令牌并发重试状态覆盖",
                "--project", "auth-app",
            )
            self.assertGreaterEqual(native["count"], 1)
            self.assertEqual(native["knowledge"][0]["lesson"], "刷新令牌更新必须使用版本检查避免旧请求覆盖新状态")
            self.assertIn("native-token-overlap", native["knowledge"][0]["match_reasons"])

            canonical = self.run_cli(
                home,
                "retrieve",
                "--task", "查找相关经验",
                "--task-canonical", "refresh token retry overwrites newer state",
                "--project", "auth-app",
            )
            self.assertGreaterEqual(canonical["count"], 1)
            item = canonical["knowledge"][0]
            self.assertEqual(item["source_language"], "zh-CN")
            self.assertIn("stale refresh requests", item["lesson_canonical"])
            self.assertIn("canonical-token-overlap", item["match_reasons"])

    def test_project_match_is_a_positive_ranking_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            for project, lesson in (
                ("project-a", "project A retry convention"),
                ("project-b", "project B retry convention"),
            ):
                self.run_cli(
                    home,
                    "record",
                    "--task", "repair retry timeout behavior",
                    "--project", project,
                    "--type", "debugging",
                    "--outcome", "success",
                    "--verification-status", "passed",
                    "--acceptance-status", "accepted",
                    "--acceptance-source", "reviewer",
                    "--lesson", lesson,
                )

            result = self.run_cli(
                home,
                "retrieve",
                "--task", "repair retry timeout behavior",
                "--project", "project-b",
                "--limit", "2",
            )
            self.assertEqual(result["knowledge"][0]["source_project"], "project-b")
            self.assertIn("project-match", result["knowledge"][0]["match_reasons"])

            self.run_cli(home, "policy", "set", "--active-memory-limit", "0")
            disabled = self.run_cli(home, "retrieve", "--task", "repair retry timeout behavior")
            self.assertEqual(disabled["count"], 0)


if __name__ == "__main__":
    unittest.main()
