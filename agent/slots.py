"""Common-slot calculation. See PLAN.md Deep Dive D.

Frozen interface — see TASKS.md Epic 0 (F5). Implemented + unit-tested in B6.
"""
from __future__ import annotations

from core.types import BusyInterval, Slot, UserId, Window


def best_common_slot(
    busy: dict[UserId, list[BusyInterval]],
    window: Window,
    duration_min: int,
    tz_by_user: dict[UserId, str],
) -> Slot | None:
    """Merge busy intervals, invert against per-user working hours + tz,
    return the earliest gap >= duration_min, or None if no slot fits."""
    raise NotImplementedError("B6: implement the common-slot algorithm")
