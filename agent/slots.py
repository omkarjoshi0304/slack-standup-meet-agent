"""Common-slot calculation. See PLAN.md Deep Dive D.

Merges every attendee's busy intervals with their own non-working-hours
blocks (9-17 local time, per their timezone), then returns the earliest gap
in the merged result that is at least `duration_min` long.

Assumes `window.start`/`window.end` are timezone-aware datetimes (UTC is
fine — each attendee's working hours are computed in their own tz regardless
of what tz the window itself is expressed in).
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from core.types import BusyInterval, Slot, UserId, Window

WORKDAY_START = time(9, 0)
WORKDAY_END = time(17, 0)


def _non_working_intervals(window: Window, tz_name: str) -> list[tuple[datetime, datetime]]:
    """Blocks of time outside WORKDAY_START-WORKDAY_END, in `tz_name`, clipped to window."""
    tz = ZoneInfo(tz_name)
    local_start = window.start.astimezone(tz)
    local_end = window.end.astimezone(tz)

    out: list[tuple[datetime, datetime]] = []
    day = local_start.date()
    while day <= local_end.date():
        day_start = datetime.combine(day, time.min, tzinfo=tz)
        work_open = datetime.combine(day, WORKDAY_START, tzinfo=tz)
        work_close = datetime.combine(day, WORKDAY_END, tzinfo=tz)
        day_end = datetime.combine(day, time.max, tzinfo=tz)

        out.append((max(day_start, local_start), min(work_open, local_end)))
        out.append((max(work_close, local_start), min(day_end, local_end)))

        day += timedelta(days=1)

    return [(start, end) for start, end in out if start < end]


def _merge(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    merged: list[list[datetime]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(s, e) for s, e in merged]


def best_common_slot(
    busy: dict[UserId, list[BusyInterval]],
    window: Window,
    duration_min: int,
    tz_by_user: dict[UserId, str],
) -> Slot | None:
    """Merge busy intervals, invert against per-user working hours + tz,
    return the earliest gap >= duration_min, or None if no slot fits."""
    duration = timedelta(minutes=duration_min)

    blocked: list[tuple[datetime, datetime]] = []
    for user_busy in busy.values():
        for interval in user_busy:
            start = max(interval.start, window.start)
            end = min(interval.end, window.end)
            if start < end:
                blocked.append((start, end))

    # Working-hours restriction applies to every known attendee, even one
    # with zero busy events — so this is keyed off the union of both maps,
    # not just whoever happens to have a busy list.
    for user_id in set(busy) | set(tz_by_user):
        tz_name = tz_by_user.get(user_id, "UTC")
        blocked.extend(_non_working_intervals(window, tz_name))

    merged = _merge(blocked)

    cursor = window.start
    for start, end in merged:
        if start - cursor >= duration:
            return Slot(start=cursor, end=cursor + duration)
        cursor = max(cursor, end)

    if window.end - cursor >= duration:
        return Slot(start=cursor, end=cursor + duration)

    return None
