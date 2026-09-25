# CONFIGURATION
# CLI entrypoint for manual, supervised V0 runs.
# No daemon, scheduler, Telegram gateway or automatic GitHub push is included.

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys

from .config import load_config
from .orchestrator import run_build


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes-builder")
    parser.add_argument("--config", type=Path, default=Path("config.toml"))
    parser.add_argument("--verbose", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="run the three-role V0 pipeline")
    run.add_argument("--source", type=Path, required=True)
    run.add_argument("--goal-file", type=Path, required=True)
    run.add_argument("--project-name")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _configure_logging(args.verbose)
    config = load_config(args.config)
    if args.command == "run":
        goal_text = args.goal_file.read_text(encoding="utf-8")
        state = run_build(config, args.source, goal_text, args.project_name)
        sys.stdout.write(json.dumps({"run_id": state.run_id, "phase": state.phase.value, "reason": state.reason}) + "\n")
        return 0 if state.phase.value == "APPROVED" else 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
