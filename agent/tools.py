"""LangGraph tools wrapping integrations/*. Thin orchestration only — the real
Jira/Calendar logic lives in integrations/*, the slot math in agent/slots.py.

integrations/* are still stubs (raise NotImplementedError) until Epic C lands;
calling these tools for real will surface that until then, which is expected.
"""
from __future__ import annotations

from datetime import datetime

from langchain_core.tools import tool
from sqlmodel import select

from agent.slots import best_common_slot
from core.db import get_session
from core.models import User
from core.types import Window
from integrations import google_calendar, jira_client


def _get_user(user_id: str) -> User:
    with get_session() as session:
        user = session.exec(select(User).where(User.slack_user_id == user_id)).first()
    if user is None:
        raise ValueError(f"No linked user for Slack id {user_id}")
    return user


@tool
def get_sprint_summary(user_id: str) -> list[dict]:
    """Fetch the given user's current-sprint Jira issues."""
    user = _get_user(user_id)
    issues = jira_client.get_sprint_issues(user)
    return [issue.model_dump() for issue in issues]


@tool
def get_free_busy(user_id: str, window_start: str, window_end: str) -> list[dict]:
    """Fetch the given user's Google Calendar busy intervals over a window
    (ISO 8601 timestamps)."""
    user = _get_user(user_id)
    window = Window(start=datetime.fromisoformat(window_start), end=datetime.fromisoformat(window_end))
    busy = google_calendar.get_freebusy(user, window)
    return [interval.model_dump() for interval in busy]


@tool
def propose_and_book_meeting(
    organizer_user_id: str,
    attendee_user_ids: list[str],
    window_start: str,
    window_end: str,
    duration_min: int,
) -> dict:
    """Resolve attendees, compute the best common slot, and book it
    autonomously — no approval gate (see AGENTS.md's human-in-the-loop policy)."""
    organizer = _get_user(organizer_user_id)
    attendees = [_get_user(user_id) for user_id in attendee_user_ids]
    window = Window(start=datetime.fromisoformat(window_start), end=datetime.fromisoformat(window_end))

    # The organizer attends too, so their own calendar must factor into the
    # slot search even though they're not in the Calendar-invite `attendees`.
    everyone = [organizer, *attendees]
    busy = {person.slack_user_id: google_calendar.get_freebusy(person, window) for person in everyone}
    tz_by_user = {person.slack_user_id: person.tz for person in everyone}

    slot = best_common_slot(busy=busy, window=window, duration_min=duration_min, tz_by_user=tz_by_user)
    if slot is None:
        return {"booked": False, "reason": "no common slot found in the requested window"}

    result = google_calendar.create_event(organizer=organizer, attendees=attendees, slot=slot)
    return {"booked": True, "slot": slot.model_dump(), **result.model_dump()}
