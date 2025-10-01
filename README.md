# hello-world
Just another developer creating new stuff.

## Weekly summary agent

This repository includes a small agent that reads email and calendar data to
produce a weekly status briefing. Configure it with your IMAP credentials and an
iCalendar feed, then run it from the command line:

```bash
pip install -r requirements.txt
python -m weekly_agent --config config.json --output weekly-summary.txt
```

See `config.example.json` for the fields that need to be provided. Replace the
placeholder IMAP settings with your own credentials before running the agent.
The example calendar source references `examples/sample.ics`, which you can use
for quick local testing. The agent collects emails from the configured mailbox
and events from the calendar source for the requested window (defaults to the
last seven days) and writes a concise summary.

### Configuration reference

| Field | Description |
| ----- | ----------- |
| `email.host` | IMAP server hostname. |
| `email.username` / `email.password` | Credentials (consider using an app password). |
| `email.port` | IMAP port, default `993`. |
| `email.mailbox` | Mailbox to scan, default `INBOX`. |
| `email.use_ssl` | Whether to establish an SSL connection. |
| `calendar.source` | Path/URL to an `.ics` calendar feed (supports `http(s)` or local paths). |
| `calendar.local_tz` | Optional timezone name for displaying events (e.g., `America/New_York`). |
| `summary.window` | Reporting window as days or ISO 8601 period (e.g., `P7D`). |
| `summary.top_senders` | Number of top email senders to highlight. |
| `summary.top_events` | Number of calendar events to include. |
| `summary.top_messages` | Number of individual emails to highlight. |
| `summary.snippet_words` | Words captured for each email snippet. |
