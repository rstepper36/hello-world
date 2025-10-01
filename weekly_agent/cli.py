"""Command line interface for the weekly agent."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .agent import WeeklyAgent
from .config import AgentConfig


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize weekly email and calendar activity.")
    parser.add_argument("--config", type=Path, default=Path("config.json"), help="Path to agent configuration JSON file")
    parser.add_argument("--start", type=str, default=None, help="Start of the reporting window (ISO-8601)")
    parser.add_argument("--end", type=str, default=None, help="End of the reporting window (ISO-8601)")
    parser.add_argument("--output", type=Path, default=None, help="Optional file to write the summary to")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = AgentConfig.from_json(args.config)
    agent = WeeklyAgent(config)
    start = _parse_datetime(args.start)
    end = _parse_datetime(args.end)
    summary = agent.summarize(start=start, end=end)

    if args.output:
        args.output.write_text(summary, encoding="utf-8")
    else:
        print(summary)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
