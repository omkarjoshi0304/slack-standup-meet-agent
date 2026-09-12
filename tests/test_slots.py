"""Unit tests for agent/slots.py's common-slot algorithm (B6)."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from agent.slots import best_common_slot
from core.types import BusyInterval, Slot, Window

UTC = ZoneInfo("UTC")


def _dt(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


def test_returns_window_start_when_nothing_is_busy():
    window = Window(start=_dt(2026, 9, 14, 9), end=_dt(2026, 9, 14, 17))

    slot = best_common_slot(busy={}, window=window, duration_min=30, tz_by_user={})

    assert slot == Slot(start=window.start, end=window.start + timedelta(minutes=30))


def test_skips_a_busy_interval_at_the_start():
    window = Window(start=_dt(2026, 9, 14, 9), end=_dt(2026, 9, 14, 17))
    busy = {"U1": [BusyInterval(start=_dt(2026, 9, 14, 9), end=_dt(2026, 9, 14, 9, 30))]}

    slot = best_common_slot(busy=busy, window=window, duration_min=30, tz_by_user={})

    assert slot == Slot(start=_dt(2026, 9, 14, 9, 30), end=_dt(2026, 9, 14, 10))


def test_returns_none_when_no_gap_fits():
    window = Window(start=_dt(2026, 9, 14, 9), end=_dt(2026, 9, 14, 17))
    busy = {"U1": [BusyInterval(start=_dt(2026, 9, 14, 9), end=_dt(2026, 9, 14, 17))]}

    slot = best_common_slot(busy=busy, window=window, duration_min=30, tz_by_user={})

    assert slot is None


def test_respects_attendee_working_hours_in_their_own_timezone():
    # Full 24h UTC window. Attendee is in Tokyo (UTC+9): their 9-17 workday
    # maps to 00:00-08:00 UTC, so the earliest slot should sit at window start.
    window = Window(start=_dt(2026, 9, 14, 0), end=_dt(2026, 9, 15, 0))

    slot = best_common_slot(
        busy={},
        window=window,
        duration_min=30,
        tz_by_user={"U1": "Asia/Tokyo"},
    )

    assert slot == Slot(start=window.start, end=window.start + timedelta(minutes=30))


def test_no_slot_when_window_is_entirely_outside_working_hours():
    # Window is a single evening, fully after everyone's workday ends.
    window = Window(start=_dt(2026, 9, 14, 18), end=_dt(2026, 9, 14, 20))

    slot = best_common_slot(busy={}, window=window, duration_min=30, tz_by_user={"U1": "UTC"})

    assert slot is None
