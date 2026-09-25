# CONFIGURATION
# Security tests confirm protected and out-of-root paths fail closed.

from pathlib import Path
import tempfile
import unittest

from hermes_builder.config import SecurityConfig
from hermes_builder.security import validate_no_escaping_symlinks, validate_source_path, validate_workspace_path


class SecurityTests(unittest.TestCase):
    def test_source_must_be_inside_allowed_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            allowed = root / "allowed"
            protected = allowed / "protected"
            source = allowed / "project"
            source.mkdir(parents=True)
            protected.mkdir()
            config = SecurityConfig((allowed,), (protected,))
            self.assertEqual(validate_source_path(source, config), source.resolve())
            with self.assertRaises(PermissionError):
                validate_source_path(protected, config)

    def test_workspace_root_itself_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(PermissionError):
                validate_workspace_path(root, root)

    @unittest.skipIf(__import__("os").name == "nt", "Windows symlink creation may require elevation")
    def test_escaping_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            outside = root / "outside.txt"
            source.mkdir()
            outside.write_text("secret", encoding="utf-8")
            (source / "escape").symlink_to(outside)
            with self.assertRaises(PermissionError):
                validate_no_escaping_symlinks(source)


if __name__ == "__main__":
    unittest.main()
