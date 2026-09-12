"""Persistence + idempotency constraint for core/models.py."""
from __future__ import annotations

from datetime import date

import pytest
from sqlmodel import Session, SQLModel, create_engine

from core.models import StandupConfig, StandupRun, Workspace


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_standup_run_unique_on_config_and_date(session):
    workspace = Workspace(slack_team_id="T1", bot_token="xoxb-fake")
    session.add(workspace)
    session.commit()
    session.refresh(workspace)

    config = StandupConfig(
        workspace_id=workspace.id,
        channel_id="C1",
        member_ids="1,2",
        schedule_cron="0 9 * * 1-5",
        tz="UTC",
    )
    session.add(config)
    session.commit()
    session.refresh(config)

    session.add(StandupRun(config_id=config.id, run_date=date(2026, 9, 12)))
    session.commit()

    session.add(StandupRun(config_id=config.id, run_date=date(2026, 9, 12)))
    with pytest.raises(Exception):
        session.commit()
