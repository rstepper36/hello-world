"""Utilities for retrieving email data from an IMAP inbox."""

from __future__ import annotations

import email
import imaplib
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.message import Message
from typing import Generator, List

from .config import EmailConfig
from .models import EmailSummary

LOGGER = logging.getLogger(__name__)


@contextmanager
def _imap_connection(config: EmailConfig) -> Generator[imaplib.IMAP4, None, None]:
    client: imaplib.IMAP4
    if config.use_ssl:
        client = imaplib.IMAP4_SSL(config.host, config.port)
    else:
        client = imaplib.IMAP4(config.host, config.port)
    try:
        if config.timeout:
            try:
                client.socket().settimeout(config.timeout)
            except Exception:  # pragma: no cover - best effort
                LOGGER.debug("Unable to set IMAP timeout", exc_info=True)
        client.login(config.username, config.password)
        client.select(config.mailbox)
        yield client
    finally:
        try:
            client.logout()
        except Exception:  # pragma: no cover - best effort cleanup
            LOGGER.debug("Failed to logout from IMAP server", exc_info=True)


def _decode_header(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return str(make_header(decode_header(value)))
    return str(make_header(decode_header(value)))


def _message_snippet(message: Message, max_words: int) -> str:
    payloads: List[str] = []
    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain" and part.get_content_disposition() != "attachment":
                try:
                    payload = part.get_payload(decode=True)
                except Exception:  # pragma: no cover - defensive
                    continue
                if payload:
                    payloads.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
    else:
        try:
            payload = message.get_payload(decode=True)
        except Exception:  # pragma: no cover - defensive
            payload = None
        if payload:
            payloads.append(payload.decode(message.get_content_charset() or "utf-8", errors="replace"))

    text = " ".join(payloads).strip()
    words = text.split()
    if not words:
        return ""
    snippet_words = words[:max_words]
    snippet = " ".join(snippet_words)
    if len(words) > max_words:
        snippet += "…"
    return snippet


def _parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = email.utils.parsedate_to_datetime(value)
    if parsed is None:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class EmailReader:
    """Client for retrieving emails within a time window."""

    def __init__(self, config: EmailConfig) -> None:
        self.config = config

    def fetch_messages(self, start: datetime, end: datetime, *, snippet_words: int = 20) -> List[EmailSummary]:
        """Return a list of emails received within the time window."""

        messages: List[EmailSummary] = []
        since = start.strftime("%d-%b-%Y")
        before = (end + timedelta(days=1)).strftime("%d-%b-%Y")
        with _imap_connection(self.config) as client:
            status, response = client.search(None, f"(SINCE {since} BEFORE {before})")
            if status != "OK":
                LOGGER.warning("IMAP search failed: %s", response)
                return messages
            ids = response[0].split()
            for message_id in ids:
                status, data = client.fetch(message_id, "(RFC822 FLAGS)")
                if status != "OK" or not data:
                    continue
                raw_email = next((part for part in data if isinstance(part, tuple)), None)
                if raw_email is None:
                    continue
                message = email.message_from_bytes(raw_email[1])
                flag_bytes = next((part for part in data if isinstance(part, bytes)), b"")
                subject = _decode_header(message.get("Subject"))
                sender = _decode_header(message.get("From"))
                received_at = _parse_date(message.get("Date"))
                snippet = _message_snippet(message, snippet_words)
                is_unread = b"\\Seen" not in flag_bytes if flag_bytes else False
                thread_id = message.get("Message-ID")
                messages.append(
                    EmailSummary(
                        subject=subject,
                        sender=sender,
                        received_at=received_at,
                        snippet=snippet,
                        is_unread=is_unread,
                        thread_id=thread_id,
                    )
                )
        messages.sort(key=lambda msg: msg.received_at, reverse=True)
        return messages
