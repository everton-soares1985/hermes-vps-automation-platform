# CONFIGURATION
# Tests role-invocation isolation without contacting Hermes or OmniRoute.

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hermes_builder.config import BuilderConfig, GatesConfig, LimitsConfig, RoutesConfig, RuntimeConfig, SecurityConfig
from hermes_builder.evidence import CommandEvidence
from hermes_builder.role_runner import _container_is_owned_by_builder, _normalize_hermes_result, run_role


class RoleRunnerTests(unittest.TestCase):
    def test_invocation_pins_unique_workspace_and_restricted_tools(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "work"
            evidence = root / "evidence"
            workspace.mkdir()
            config = BuilderConfig(
                runtime=RuntimeConfig(Path("/bin/hermes"), "builder", root / "state", root / "runs", 60, Path("/bin/specify")),
                routes=RoutesConfig("architect", "implementer", "reviewer"),
                limits=LimitsConfig(2, 20, 10000, 2),
                gates=GatesConfig(("python3 -m unittest",), True, True),
                security=SecurityConfig((root,), (root / "protected",)),
            )
            record = CommandEvidence("cmd", str(workspace), "start", "finish", 0, "out", "err", "a", "b")
            with patch("hermes_builder.role_runner.run_command", return_value=record) as mocked:
                run_role(config, "architect", "route", "role prompt", workspace, evidence, 0)

            argv = mocked.call_args.args[0]
            env = mocked.call_args.kwargs["env"]
            prompt = argv[argv.index("-z") + 1]
            self.assertEqual(argv[argv.index("--toolsets") + 1], "terminal,file,code_execution")
            self.assertIn(f"Controller host workspace: {workspace.resolve()}", prompt)
            self.assertIn("fresh invocation", prompt)
            self.assertEqual(env["TERMINAL_CWD"], str(workspace.resolve()))
            self.assertIn("Agent-visible workspace: /workspace", prompt)

    def test_container_ownership_requires_profile_and_workspace_mount(self) -> None:
        root = Path("/srv/builder-workspaces")
        config = BuilderConfig(
            runtime=RuntimeConfig(Path("/bin/hermes"), "builder", Path("/tmp/state"), root, 60, Path("/bin/specify")),
            routes=RoutesConfig("architect", "implementer", "reviewer"),
            limits=LimitsConfig(2, 20, 10000, 2),
            gates=GatesConfig(("python3 -m unittest",), True, True),
            security=SecurityConfig((Path("/tmp/input"),), (Path("/tmp/protected"),)),
        )
        owned = {
            "Config": {"Labels": {"hermes-agent": "1", "hermes-profile": "builder"}},
            "Mounts": [{"Type": "bind", "Source": "/srv/builder-workspaces/project/run/work"}],
        }
        foreign = {
            "Config": {"Labels": {"hermes-agent": "1", "hermes-profile": "default"}},
            "Mounts": [{"Type": "bind", "Source": "/srv/builder-workspaces/project/run/work"}],
        }
        outside = {
            "Config": {"Labels": {"hermes-agent": "1", "hermes-profile": "builder"}},
            "Mounts": [{"Type": "bind", "Source": "/srv/automation/production"}],
        }
        self.assertTrue(_container_is_owned_by_builder(owned, config))
        self.assertFalse(_container_is_owned_by_builder(foreign, config))
        self.assertFalse(_container_is_owned_by_builder(outside, config))

    def test_omniroute_soft_failure_becomes_nonzero_exit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stdout = root / "stdout.log"
            stderr = root / "stderr.log"
            stdout.write_text(
                "API call failed after 3 retries: HTTP 503: all upstream accounts are inactive",
                encoding="utf-8",
            )
            stderr.write_text("", encoding="utf-8")
            record = CommandEvidence(
                "hermes",
                str(root),
                "start",
                "finish",
                0,
                str(stdout),
                str(stderr),
                "a",
                "b",
            )

            normalized = _normalize_hermes_result(record)

            self.assertEqual(normalized.exit_code, 75)


if __name__ == "__main__":
    unittest.main()
