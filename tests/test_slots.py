"""Red starting point for B6 — best_common_slot is not implemented yet."""
from __future__ import annotations

from datetime import datetime

import pytest

from agent.slots import best_common_slot
from core.types import Window


def test_best_common_slot_not_implemented_yet():
    window = Window(start=datetime(2026, 9, 12, 9), end=datetime(2026, 9, 12, 17))
    with pytest.raises(NotImplementedError):
        best_common_slot(busy={}, window=window, duration_min=30, tz_by_user={})
