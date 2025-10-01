"""High level orchestration for weekly summaries."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from .config import AgentConfig
from .email_reader import EmailReader
from .calendar_reader import CalendarReader
from .summarizer import WeeklySummarizer


LOGGER = logging.getLogger(__name__)


class WeeklyAgent:
    """Agent that gathers email and calendar data to produce a weekly summary."""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self._email_reader = EmailReader(config.email)
        self._calendar_reader = CalendarReader(config.calendar)
        self._summarizer = WeeklySummarizer(config.summary)

    def summarize(
        self,
        *,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> str:
        end_dt = end or datetime.now(timezone.utc)
        start_dt = start or end_dt - self.config.summary.window
        try:
            emails = self._email_reader.fetch_messages(
                start_dt,
                end_dt,
                snippet_words=self.config.summary.snippet_words,
            )
        except Exception:  # pragma: no cover - defensive
            LOGGER.exception("Failed to fetch email data")
            emails = []
        try:
            events = self._calendar_reader.fetch_events(start_dt, end_dt)
        except Exception:  # pragma: no cover - defensive
            LOGGER.exception("Failed to fetch calendar data")
            events = []
        return self._summarizer.build_summary(emails, events, start_dt, end_dt)
