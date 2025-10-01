"""Generate human-friendly summaries for weekly activity."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import List, Sequence

from .config import SummaryConfig
from .models import CalendarEvent, EmailSummary


@dataclass(slots=True)
class SummarySection:
    title: str
    lines: List[str]


def _format_datetime(value: datetime) -> str:
    return value.strftime("%a %b %d %I:%M %p %Z")


class WeeklySummarizer:
    """Create a digest of recent email messages and calendar events."""

    def __init__(self, config: SummaryConfig) -> None:
        self.config = config

    def build_summary(
        self,
        emails: Sequence[EmailSummary],
        events: Sequence[CalendarEvent],
        start: datetime,
        end: datetime,
    ) -> str:
        sections: List[SummarySection] = []
        sections.append(self._email_overview(emails))
        sections.append(self._top_threads(emails))
        sections.append(self._calendar_highlights(events))
        header = self._header(start, end)
        body = "\n\n".join(self._format_section(section) for section in sections if section.lines)
        return f"{header}\n\n{body}".strip()

    def _header(self, start: datetime, end: datetime) -> str:
        window = f"{start.strftime('%b %d, %Y')} → {end.strftime('%b %d, %Y')}"
        return f"Weekly briefing ({window})"

    def _email_overview(self, emails: Sequence[EmailSummary]) -> SummarySection:
        unread = sum(1 for email in emails if email.is_unread)
        senders = Counter(email.sender or "(Unknown sender)" for email in emails)
        top_senders = senders.most_common(self.config.top_senders)
        lines = [
            f"Total emails: {len(emails)}",
            f"Unread emails: {unread}",
        ]
        if top_senders:
            sender_lines = ", ".join(f"{sender} ({count})" for sender, count in top_senders)
            lines.append(f"Top senders: {sender_lines}")
        return SummarySection(title="Email overview", lines=lines)

    def _top_threads(self, emails: Sequence[EmailSummary]) -> SummarySection:
        lines: List[str] = []
        for email in emails[: self.config.top_messages]:
            lines.append(
                f"• {email.subject or '(No subject)'} — {email.sender} ({email.received_at.strftime('%a %I:%M %p')})\n  {email.snippet}"
            )
        return SummarySection(title="Notable messages", lines=lines)

    def _calendar_highlights(self, events: Sequence[CalendarEvent]) -> SummarySection:
        lines: List[str] = []
        for event in events[: self.config.top_events]:
            location = f" @ {event.location}" if event.location else ""
            description = f"\n  {event.description}" if event.description else ""
            lines.append(
                f"• {event.title or '(No title)'} — {_format_datetime(event.start)} → {_format_datetime(event.end)}{location}{description}"
            )
        return SummarySection(title="Calendar highlights", lines=lines)

    def _format_section(self, section: SummarySection) -> str:
        lines = "\n".join(section.lines)
        return f"{section.title}\n{'-' * len(section.title)}\n{lines}"
