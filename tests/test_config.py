# CONFIGURATION
# Unit tests use temporary files and never contact Hermes or OmniRoute.

from pathlib import Path
import tempfile
import unittest

from hermes_builder.config import load_config


VALID_CONFIG = """
[runtime]
hermes_bin = "/bin/hermes"
profile = "builder"
state_root = "/tmp/state"
workspace_root = "/tmp/workspaces"
timeout_seconds = 60
specify_bin = "/bin/specify"
[routes]
architect = "a"
implementer = "i"
reviewer = "r"
[limits]
max_iterations = 2
max_changed_files = 10
max_changed_bytes = 1000
reviewer_retries = 2
[gates]
test_commands = ["python -m unittest"]
require_clean_test_exit = true
require_reviewer_approval = true
[security]
allowed_source_roots = ["/tmp/input"]
protected_roots = ["/tmp/protected"]
"""


class ConfigTests(unittest.TestCase):
    def test_load_valid_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(VALID_CONFIG, encoding="utf-8")
            config = load_config(path)
        self.assertEqual(config.routes.implementer, "i")
        self.assertEqual(config.limits.max_iterations, 2)

    def test_routes_must_be_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(VALID_CONFIG.replace('reviewer = "r"', 'reviewer = "i"'), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
