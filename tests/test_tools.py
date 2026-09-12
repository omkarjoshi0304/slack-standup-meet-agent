"""Unit tests for agent/tools.py (B3) — orchestration only, integrations mocked."""
from __future__ import annotations

import agent.tools as tools_module
from core.models import User
from core.types import BusyInterval, EventResult, Issue, Slot
from integrations import google_calendar, jira_client


def _user(user_id: str, tz: str = "UTC") -> User:
    return User(slack_user_id=user_id, tz=tz)


def test_get_sprint_summary_resolves_user_and_wraps_issues(monkeypatch):
    monkeypatch.setattr(tools_module, "_get_user", lambda user_id: _user(user_id))
    issue = Issue(key="PROJ-1", summary="Fix bug", status="Done", url="https://x/PROJ-1")
    monkeypatch.setattr(jira_client, "get_sprint_issues", lambda user: [issue])

    result = tools_module.get_sprint_summary.invoke({"user_id": "U1"})

    assert result == [issue.model_dump()]


def test_get_free_busy_resolves_user_and_wraps_intervals(monkeypatch):
    monkeypatch.setattr(tools_module, "_get_user", lambda user_id: _user(user_id))
    interval = BusyInterval(start="2026-09-14T09:00:00", end="2026-09-14T09:30:00")
    monkeypatch.setattr(google_calendar, "get_freebusy", lambda user, window: [interval])

    result = tools_module.get_free_busy.invoke(
        {"user_id": "U1", "window_start": "2026-09-14T09:00:00", "window_end": "2026-09-14T17:00:00"}
    )

    assert result == [interval.model_dump()]


def test_propose_and_book_meeting_wires_slot_and_event(monkeypatch):
    users = {"ORG": _user("ORG"), "U1": _user("U1"), "U2": _user("U2")}
    monkeypatch.setattr(tools_module, "_get_user", lambda user_id: users[user_id])
    monkeypatch.setattr(google_calendar, "get_freebusy", lambda user, window: [])

    slot = Slot(start="2026-09-14T09:00:00", end="2026-09-14T09:30:00")
    monkeypatch.setattr(tools_module, "best_common_slot", lambda **kwargs: slot)

    event = EventResult(event_id="evt1", meet_url="https://meet/evt1", html_link="https://cal/evt1")
    captured = {}

    def fake_create_event(organizer, attendees, slot):
        captured["organizer"] = organizer
        captured["attendees"] = attendees
        return event

    monkeypatch.setattr(google_calendar, "create_event", fake_create_event)

    result = tools_module.propose_and_book_meeting.invoke(
        {
            "organizer_user_id": "ORG",
            "attendee_user_ids": ["U1", "U2"],
            "window_start": "2026-09-14T09:00:00",
            "window_end": "2026-09-14T17:00:00",
            "duration_min": 30,
        }
    )

    assert result["booked"] is True
    assert result["event_id"] == "evt1"
    assert captured["organizer"].slack_user_id == "ORG"
    assert [a.slack_user_id for a in captured["attendees"]] == ["U1", "U2"]


def test_propose_and_book_meeting_reports_no_slot_found(monkeypatch):
    users = {"ORG": _user("ORG"), "U1": _user("U1")}
    monkeypatch.setattr(tools_module, "_get_user", lambda user_id: users[user_id])
    monkeypatch.setattr(google_calendar, "get_freebusy", lambda user, window: [])
    monkeypatch.setattr(tools_module, "best_common_slot", lambda **kwargs: None)

    result = tools_module.propose_and_book_meeting.invoke(
        {
            "organizer_user_id": "ORG",
            "attendee_user_ids": ["U1"],
            "window_start": "2026-09-14T09:00:00",
            "window_end": "2026-09-14T17:00:00",
            "duration_min": 30,
        }
    )

    assert result["booked"] is False
