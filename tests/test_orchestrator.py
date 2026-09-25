# CONFIGURATION
# Tests deterministic workspace hygiene without running Spec Kit or Git.

from pathlib import Path
import tempfile
import unittest

from hermes_builder.evidence import CommandEvidence
from hermes_builder.orchestrator import _controller_test_feedback, _ensure_runtime_gitignore


class OrchestratorTests(unittest.TestCase):
    def test_runtime_gitignore_is_appended_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            ignore = workspace / ".gitignore"
            ignore.write_text("user-rule/\n", encoding="utf-8")
            _ensure_runtime_gitignore(workspace)
            _ensure_runtime_gitignore(workspace)
            content = ignore.read_text(encoding="utf-8")
            self.assertIn("user-rule/", content)
            self.assertIn("__pycache__/", content)
            self.assertEqual(content.count("# Hermes Builder runtime hygiene"), 1)

    def test_controller_feedback_contains_bounded_failure_details(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stdout = root / "stdout.log"
            stderr = root / "stderr.log"
            stdout.write_text("useful output", encoding="utf-8")
            stderr.write_text("x" * 7000 + "\nFileNotFoundError: /workspace", encoding="utf-8")
            record = CommandEvidence(
                command="bash -lc python3 -m unittest",
                cwd=str(root),
                started_utc="2026-08-10T00:00:00Z",
                finished_utc="2026-08-10T00:00:01Z",
                exit_code=1,
                stdout_path=str(stdout),
                stderr_path=str(stderr),
                stdout_sha256="stdout-sha",
                stderr_sha256="stderr-sha",
            )

            feedback = _controller_test_feedback([record])

            self.assertEqual(feedback["source"], "controller")
            failure = feedback["failures"][0]
            self.assertEqual(failure["exit_code"], 1)
            self.assertIn("FileNotFoundError: /workspace", failure["stderr_tail"])
            self.assertLessEqual(len(failure["stderr_tail"]), 6000)
            self.assertEqual(failure["stdout_tail"], "useful output")


if __name__ == "__main__":
    unittest.main()
