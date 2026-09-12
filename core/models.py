"""Persisted entities (SQLModel). See PLAN.md #3 for the design.

member_ids / attendee_ids are stored as comma-separated User.id strings —
SQLite has no native array column and this is a hackathon-scale team size.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from sqlmodel import Field, SQLModel, UniqueConstraint


class Workspace(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    slack_team_id: str = Field(unique=True, index=True)
    bot_token: str


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    slack_user_id: str = Field(unique=True, index=True)
    tz: str
    jira_account_id: str | None = None
    google_account_id: str | None = None
    # Set by the C2 account-linking flow. C1 exchanges this for a federated
    # connection's access token via Auth0 Token Vault.
    auth0_refresh_token: str | None = None


class StandupConfig(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id")
    channel_id: str
    member_ids: str
    schedule_cron: str
    tz: str
    active: bool = True


class StandupRunStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StandupRun(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("config_id", "run_date", name="uq_standup_run_config_date"),
    )

    id: int | None = Field(default=None, primary_key=True)
    config_id: int = Field(foreign_key="standupconfig.id")
    run_date: date
    status: StandupRunStatus = StandupRunStatus.PENDING
    digest_message_ts: str | None = None


class MeetingRequestStatus(str, Enum):
    DETECTED = "DETECTED"
    PROPOSED = "PROPOSED"
    CONFIRMED = "CONFIRMED"
    BOOKED = "BOOKED"
    FAILED = "FAILED"


class MeetingRequest(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    thread_ts: str
    organizer_id: int = Field(foreign_key="user.id")
    attendee_ids: str
    window_start: datetime
    window_end: datetime
    chosen_slot_start: datetime | None = None
    chosen_slot_end: datetime | None = None
    status: MeetingRequestStatus = MeetingRequestStatus.DETECTED
    calendar_event_id: str | None = None
