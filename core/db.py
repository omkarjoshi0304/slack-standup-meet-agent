"""SQLite engine/session via SQLModel.

Reads DATABASE_URL directly rather than through core.config.Settings, so DB
access doesn't drag in unrelated required credentials (Slack/Auth0/Jira/Google)
just to open a session.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        database_url = os.environ.get("DATABASE_URL", "sqlite:///./standup_meet.db")
        _engine = create_engine(database_url, echo=False)
    return _engine


def init_db() -> None:
    """Create all tables. Call once at app startup."""
    SQLModel.metadata.create_all(get_engine())


@contextmanager
def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
