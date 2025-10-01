"""Utilities for summarizing weekly email and calendar activity."""

from .agent import WeeklyAgent
from .config import AgentConfig, CalendarConfig, EmailConfig, SummaryConfig

__all__ = [
    "WeeklyAgent",
    "AgentConfig",
    "CalendarConfig",
    "EmailConfig",
    "SummaryConfig",
]
