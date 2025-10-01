"""Data models used by the weekly agent."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class EmailSummary:
    """Simplified representation of an email message."""

    subject: str
    sender: str
    received_at: datetime
    snippet: str
    is_unread: bool
    thread_id: Optional[str] = None


@dataclass(slots=True)
class CalendarEvent:
    """Representation of a calendar event relevant for weekly planning."""

    title: str
    start: datetime
    end: datetime
    location: Optional[str] = None
    description: Optional[str] = None
