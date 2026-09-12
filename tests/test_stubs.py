"""Confirms the frozen Epic-0 interfaces exist with the agreed signatures (F5)."""
from __future__ import annotations

import pytest

from core.models import User
from core.types import Window
from integrations import auth0_vault, google_calendar, jira_client, slack_web


@pytest.fixture()
def user():
    return User(slack_user_id="U1", tz="UTC")


def test_auth0_get_token_stub(user):
    with pytest.raises(NotImplementedError):
        auth0_vault.get_token(user, "jira")


def test_jira_get_sprint_issues_stub(user):
    with pytest.raises(NotImplementedError):
        jira_client.get_sprint_issues(user)


def test_google_freebusy_stub(user):
    window = Window(start="2026-09-12T09:00:00", end="2026-09-12T17:00:00")
    with pytest.raises(NotImplementedError):
        google_calendar.get_freebusy(user, window)


def test_slack_post_message_stub():
    with pytest.raises(NotImplementedError):
        slack_web.post_message("C1", [])
