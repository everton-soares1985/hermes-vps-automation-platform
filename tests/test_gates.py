# CONFIGURATION
# Gate tests verify fail-closed behavior with deterministic local artifacts.

import json
from pathlib import Path
import tempfile
import unittest

from hermes_builder.gates import (
    validate_architect_delta,
    validate_implementer_delta,
    validate_review,
    validate_reviewer_delta,
)


class GateTests(unittest.TestCase):
    def test_architect_may_only_create_required_specs(self) -> None:
        delta = {
            "added": ["specs/FEATURE_SPEC.md", "specs/IMPLEMENTATION_PLAN.md", "specs/TASKS.md"],
            "modified": [],
            "deleted": [],
        }
        self.assertTrue(validate_architect_delta(delta).passed)
        delta["added"].append("app.py")
        self.assertFalse(validate_architect_delta(delta).passed)

    def test_review_requires_matching_sha_and_no_high_findings(self) -> None:
        payload = {
            "verdict": "APPROVED",
            "reviewed_git_sha": "abc",
            "critical_findings": [],
            "high_findings": [],
            "medium_findings": [],
            "acceptance_criteria": [{"criterion": "works", "status": "PASS", "evidence": "test"}],
            "test_commands": [{"command": "test", "exit_code": 0, "expected_exit_code": 0}],
            "summary": "ok",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "REVIEW.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertTrue(validate_review(path, "abc").passed)
            payload["high_findings"] = [{"id": "H1"}]
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertFalse(validate_review(path, "abc").passed)

    def test_review_accepts_an_expected_nonzero_exit_code(self) -> None:
        payload = {
            "verdict": "APPROVED",
            "reviewed_git_sha": "abc",
            "critical_findings": [],
            "high_findings": [],
            "acceptance_criteria": [{"criterion": "bad input fails", "status": "PASS", "evidence": "exit 2"}],
            "test_commands": [{"command": "negative test", "exit_code": 2, "expected_exit_code": 2}],
            "summary": "ok",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "REVIEW.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertTrue(validate_review(path, "abc").passed)
            payload["test_commands"][0]["expected_exit_code"] = 0
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertFalse(validate_review(path, "abc").passed)

    def test_implementer_cannot_weaken_specs(self) -> None:
        valid = {"added": ["app.py", "tests/test_app.py"], "modified": [], "deleted": []}
        self.assertTrue(validate_implementer_delta(valid).passed)
        valid["modified"].append("specs/FEATURE_SPEC.md")
        self.assertFalse(validate_implementer_delta(valid).passed)

    def test_reviewer_may_only_write_review_json(self) -> None:
        valid = {"added": ["REVIEW.json"], "modified": [], "deleted": []}
        self.assertTrue(validate_reviewer_delta(valid).passed)
        valid["modified"].append("app.py")
        self.assertFalse(validate_reviewer_delta(valid).passed)


if __name__ == "__main__":
    unittest.main()
