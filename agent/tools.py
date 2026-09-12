"""LangGraph tools wrapping integrations/*. Thin wrappers only — no business
logic here, that belongs in agent/slots.py and the integrations themselves.

Frozen interface — see TASKS.md Epic 0 (F5). Implemented in B3, bound to the
graph in B1. B7 wires propose_and_book_meeting end to end (autonomous, no
approval gate — see AGENTS.md's human-in-the-loop policy).
"""
from __future__ import annotations

from langchain_core.tools import tool


@tool
def get_sprint_summary(user_id: str) -> list[dict]:
    """Fetch the given user's current-sprint Jira issues."""
    raise NotImplementedError("B3: resolve User by id, call jira_client.get_sprint_issues")


@tool
def get_free_busy(user_id: str, window_start: str, window_end: str) -> list[dict]:
    """Fetch the given user's Google Calendar busy intervals over a window."""
    raise NotImplementedError("B3: resolve User by id, call google_calendar.get_freebusy")


@tool
def propose_and_book_meeting(attendee_user_ids: list[str], duration_min: int) -> dict:
    """Resolve attendees, compute the best common slot, and book it autonomously."""
    raise NotImplementedError(
        "B3/B7: wire slots.best_common_slot + google_calendar.create_event"
    )
