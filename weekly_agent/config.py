"""Configuration models for the weekly agent."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class EmailConfig:
    """Configuration for accessing an IMAP inbox."""

    host: str
    username: str
    password: str
    port: int = 993
    mailbox: str = "INBOX"
    use_ssl: bool = True
    timeout: int = 30


@dataclass(slots=True)
class CalendarConfig:
    """Configuration for retrieving calendar data."""

    source: str
    verify_ssl: bool = True
    local_tz: Optional[str] = None


def _parse_duration(value: str) -> timedelta:
    if value.upper().startswith("P"):
        # Support simple ISO-8601 periods like P7D
        if value.upper().endswith("D"):
            days = int(value[1:-1])
            return timedelta(days=days)
        raise ValueError(f"Unsupported duration format: {value}")
    if value.isdigit():
        return timedelta(days=int(value))
    raise ValueError(f"Unsupported duration format: {value}")


@dataclass(slots=True)
class SummaryConfig:
    """Configuration for summary generation."""

    window: timedelta = timedelta(days=7)
    top_senders: int = 5
    top_events: int = 10
    top_messages: int = 5
    snippet_words: int = 20

    def __post_init__(self) -> None:
        if isinstance(self.window, str):
            self.window = _parse_duration(self.window)
        elif isinstance(self.window, (int, float)):
            self.window = timedelta(days=float(self.window))
        elif not isinstance(self.window, timedelta):
            raise TypeError("window must be a timedelta, ISO period string, or day count")


@dataclass(slots=True)
class AgentConfig:
    """Aggregated configuration for the weekly agent."""

    email: EmailConfig
    calendar: CalendarConfig
    summary: SummaryConfig

    @classmethod
    def from_dict(cls, data: dict) -> "AgentConfig":
        if "email" not in data:
            raise KeyError("email configuration is required")
        if "calendar" not in data:
            raise KeyError("calendar configuration is required")
        email = EmailConfig(**data["email"])
        calendar = CalendarConfig(**data["calendar"])
        summary_data = data.get("summary", {})
        summary = SummaryConfig(**summary_data)
        return cls(email=email, calendar=calendar, summary=summary)

    @classmethod
    def from_json(cls, path: Path) -> "AgentConfig":
        import json

        with Path(path).expanduser().resolve().open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return cls.from_dict(data)
