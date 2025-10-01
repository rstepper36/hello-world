"""Utilities for reading calendar events from iCalendar sources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Iterable, List, Optional
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests

from .config import CalendarConfig
from .models import CalendarEvent


@dataclass(slots=True)
class _RawEvent:
    summary: str
    start: datetime
    end: datetime
    location: Optional[str]
    description: Optional[str]
    all_day: bool


def _load_ics_data(config: CalendarConfig) -> str:
    parsed = urlparse(config.source)
    if parsed.scheme in {"http", "https"}:
        response = requests.get(config.source, timeout=30, verify=config.verify_ssl)
        response.raise_for_status()
        return response.text
    if parsed.scheme == "file":
        path = parsed.path
    else:
        path = config.source
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _parse_datetime(value: str, tzid: Optional[str], *, is_all_day: bool) -> datetime:
    value = value.strip()
    if len(value) == 8:
        dt = datetime.strptime(value, "%Y%m%d")
        if tzid:
            try:
                tz = ZoneInfo(tzid)
            except Exception:  # pragma: no cover - fallback
                tz = timezone.utc
            return dt.replace(tzinfo=tz)
        if is_all_day:
            return dt
        return dt.replace(tzinfo=timezone.utc)
    if value.endswith("Z"):
        dt = datetime.strptime(value, "%Y%m%dT%H%M%SZ")
        return dt.replace(tzinfo=timezone.utc)
    else:
        dt = datetime.strptime(value, "%Y%m%dT%H%M%S")
    if tzid:
        try:
            tz = ZoneInfo(tzid)
        except Exception:  # pragma: no cover - fallback to UTC
            return dt.replace(tzinfo=timezone.utc)
        return dt.replace(tzinfo=tz)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _tzid_from_key(key: str) -> Optional[str]:
    if ";" not in key:
        return None
    _, params = key.split(";", 1)
    for param in params.split(";"):
        if param.startswith("TZID="):
            return param.split("=", 1)[1]
    return None


def _unfold_ics_lines(ics_text: str) -> List[str]:
    lines: List[str] = []
    buffer = ""
    for raw_line in ics_text.splitlines():
        if raw_line.startswith(" ") or raw_line.startswith("\t"):
            buffer += raw_line[1:]
            continue
        if buffer:
            lines.append(buffer)
        buffer = raw_line
    if buffer:
        lines.append(buffer)
    return lines


def _decode_ics_text(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .strip()
    )


def _iter_events(ics_text: str) -> Iterable[_RawEvent]:
    lines = [line.strip() for line in _unfold_ics_lines(ics_text) if line.strip()]
    current: dict[str, str] = {}
    inside_event = False
    for line in lines:
        if line == "BEGIN:VEVENT":
            inside_event = True
            current = {}
            continue
        if line == "END:VEVENT" and inside_event:
            summary = current.get("SUMMARY", "(No title)")
            dtstart_key = next((key for key in current if key.startswith("DTSTART")), None)
            dtend_key = next((key for key in current if key.startswith("DTEND")), None)
            if not dtstart_key or not dtend_key:
                inside_event = False
                continue
            dtstart_value = current[dtstart_key]
            dtend_value = current[dtend_key]
            is_all_day = "VALUE=DATE" in dtstart_key
            event = _RawEvent(
                summary=summary,
                start=_parse_datetime(dtstart_value, _tzid_from_key(dtstart_key), is_all_day=is_all_day),
                end=_parse_datetime(dtend_value, _tzid_from_key(dtend_key), is_all_day=is_all_day),
                location=current.get("LOCATION"),
                description=current.get("DESCRIPTION"),
                all_day=is_all_day,
            )
            yield event
            inside_event = False
            continue
        if inside_event:
            if ":" in line:
                key, value = line.split(":", 1)
                current[key] = _decode_ics_text(value)


class CalendarReader:
    """Reads calendar events within a date range from an iCalendar source."""

    def __init__(self, config: CalendarConfig) -> None:
        self.config = config

    def fetch_events(self, start: datetime, end: datetime) -> List[CalendarEvent]:
        ics_data = _load_ics_data(self.config)
        events: List[CalendarEvent] = []
        for raw in _iter_events(ics_data):
            if raw.all_day:
                if self.config.local_tz:
                    try:
                        tz = ZoneInfo(self.config.local_tz)
                    except Exception:  # pragma: no cover - fallback
                        tz = timezone.utc
                else:
                    tz = timezone.utc
                start_dt = datetime.combine(raw.start.date(), time.min, tzinfo=tz)
                end_dt = datetime.combine(raw.end.date(), time.min, tzinfo=tz)
            else:
                start_dt = raw.start if raw.start.tzinfo else raw.start.replace(tzinfo=timezone.utc)
                end_dt = raw.end if raw.end.tzinfo else raw.end.replace(tzinfo=timezone.utc)
                if self.config.local_tz:
                    try:
                        tz = ZoneInfo(self.config.local_tz)
                        start_dt = start_dt.astimezone(tz)
                        end_dt = end_dt.astimezone(tz)
                    except Exception:  # pragma: no cover - fallback to UTC
                        start_dt = start_dt.astimezone(timezone.utc)
                        end_dt = end_dt.astimezone(timezone.utc)
                else:
                    start_dt = start_dt.astimezone(timezone.utc)
                    end_dt = end_dt.astimezone(timezone.utc)
            if end_dt < start or start_dt > end:
                continue
            events.append(
                CalendarEvent(
                    title=raw.summary,
                    start=start_dt,
                    end=end_dt,
                    location=raw.location,
                    description=raw.description,
                )
            )
        events.sort(key=lambda event: event.start)
        return events
