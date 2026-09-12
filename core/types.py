"""Shared value objects passed between agent tools and integrations.

Plain data — not persisted, unlike core/models.py's SQLModel entities.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

UserId = str
Provider = Literal["jira", "google"]


class Issue(BaseModel):
    key: str
    summary: str
    status: str
    url: str


class Window(BaseModel):
    start: datetime
    end: datetime


class BusyInterval(BaseModel):
    start: datetime
    end: datetime


class Slot(BaseModel):
    start: datetime
    end: datetime


class EventResult(BaseModel):
    event_id: str
    meet_url: str
    html_link: str
