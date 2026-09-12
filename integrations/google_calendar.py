"""Google Calendar free/busy + event creation with a Meet link.

Frozen interface — see TASKS.md Epic 0 (F5). Implemented in C4/C5.
"""
from __future__ import annotations

from core.models import User
from core.types import BusyInterval, EventResult, Slot, Window


def get_freebusy(user: User, window: Window) -> list[BusyInterval]:
    raise NotImplementedError("C4: freebusy.query per user over the window")


def create_event(organizer: User, attendees: list[User], slot: Slot) -> EventResult:
    raise NotImplementedError(
        "C5: events.insert with conferenceDataVersion=1 (auto Meet link) + attendees"
    )
