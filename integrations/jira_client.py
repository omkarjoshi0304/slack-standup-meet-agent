"""Sprint issues per user via Jira Cloud REST (JQL).

Frozen interface — see TASKS.md Epic 0 (F5). Implemented in C3.
"""
from __future__ import annotations

from core.models import User
from core.types import Issue


def get_sprint_issues(user: User) -> list[Issue]:
    raise NotImplementedError(
        "C3: JQL 'assignee = X AND sprint in openSprints() AND status != Done' via httpx"
    )
